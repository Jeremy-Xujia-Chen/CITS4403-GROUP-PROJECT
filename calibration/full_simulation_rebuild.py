"""Re-run every cached simulation row; checkpoint independent model outputs."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import time
import pandas as pd
from raw_model import run

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'raw-rebuild'
CACHE=ROOT/'deployment/master/abm_outputs_research_plan_v7'

def identifier(case):return hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest()

def specifications():
    specs=[]; cases={}
    direct=['target_inflow_rate','target_social_cost','chain_share','housing_rejection','job_rejection','coorigin_clustering','mover_origin_attachment','peer_colocation','social_utility_index','move_rate','same_state_contact_share','target_external_inflow_rate','target_total_inflow_rate','external_share_system']
    names=['baseline_runs','cross_experiment_runs','shock_runs','entrant_robustness_runs','social_threshold_sensitivity_runs','network_homophily_runs','parameter_sensitivity_runs','rent_feedback_sensitivity_runs','lever_intensity_sweep_runs','state_intensity_sweep_runs','network_decay_runs','open_system_runs','tulsa_reference_runs']
    for name in names:
        frame=pd.read_csv(CACHE/(name+'.csv'))
        for index,row in frame.iterrows():
            case={'seed':int(row.seed)}
            metrics={k:k for k in direct if k in frame.columns}
            if name=='baseline_runs':
                case.update(n_agents=1000,years=20)
                metrics.update(housing_rejection='housing_rejection_system',mean_social_utility_index='social_utility_index',unfilled_jobs='unfilled_jobs',population_hhi='population_hhi')
            elif name=='shock_runs':
                case.update(shock=row.shock,years=15)
                metrics.update(clustering='coorigin_clustering',housing_rejection='housing_rejection_system',unfilled_jobs='unfilled_jobs')
            elif name=='entrant_robustness_runs':
                case.update(years=15,entrant_home_local=bool(row.home_local),entrant_network_home_bias=bool(row.network_home_bias))
            elif name=='social_threshold_sensitivity_runs':
                case.update(policy=row.scenario,params={'social_satisfaction_threshold':float(row.threshold)})
                metrics.update(clustering='coorigin_clustering',target_inflow='target_inflow_rate')
            elif name=='network_homophily_runs':
                case.update(policy=row.scenario,network_homophily_share=float(row.network_homophily_share))
                metrics.update(clustering='coorigin_clustering',target_inflow='target_inflow_rate')
            elif name=='parameter_sensitivity_runs':
                case.update(policy='combined',beta_current_state=3.925*float(row.stay_scale))
                assert row.policy_scale==1
                metrics.update(target_chain_share='chain_share')
            elif name=='rent_feedback_sensitivity_runs':
                case.update(policy=row.policy,intensity=float(row.intensity),interaction=row.interaction,params={'rent_rejection_elasticity':float(row.rent_rejection_elasticity)})
                metrics.update(target_inflow='target_inflow_rate',target_housing_rejection='housing_rejection',final_rent='final_rent')
            elif name in ['lever_intensity_sweep_runs','state_intensity_sweep_runs']:
                case.update(target_state=row.target_state,lever=row.lever,intensity=float(row.intensity),interaction=row.interaction)
            elif name=='network_decay_runs':
                case.update(policy=row.policy,interaction=row.interaction,network_decay=float(row.network_decay),beta_current_state=float(row.beta_current_state))
            elif name=='open_system_runs':
                case.update(policy=row.policy,intensity=float(row.intensity),interaction=row.interaction,capacity_mode=row.capacity_mode,external_rate=float(row.external_rate))
            elif name=='cross_experiment_runs':
                case.update(policy=row.policy,intensity=float(row.intensity),interaction=row.interaction,target_state=row.target_state)
            elif name=='tulsa_reference_runs':
                case.update(lever='migration_incentive',intensity=float(row.intensity));metrics={'incentive_target_inflow_rate':'target_inflow_rate'}
            # Normalize effective no-policy / combined settings to avoid duplicate simulations.
            case.setdefault('n_agents',600);case.setdefault('years',12);case.setdefault('target_state','NY');case.setdefault('interaction','medium');case.setdefault('beta_current_state',3.925)
            if not case.get('network_decay',0):case.pop('network_decay',None)
            if case.get('network_homophily_share')==0:case.pop('network_homophily_share')
            if 'shock' in case and case['shock']=='baseline':case.pop('shock')
            key=identifier(case);cases[key]=case
            specs.append({'file':name+'.csv','row':int(index),'key':key,'metrics':metrics})
            if name=='tulsa_reference_runs':
                base={k:v for k,v in case.items() if k not in ['lever','intensity']};basekey=identifier(base);cases[basekey]=base
                specs[-1]['baseline_key']=basekey
    return specs,cases

def compare(specs, results):
    files={}; failures=[]; total=0
    for spec in specs:
        name=spec['file']
        if name not in files:files[name]=pd.read_csv(CACHE/name)
        frame=files[name];row=frame.loc[spec['row']];live=results[spec['key']]['result']
        for col,metric in spec['metrics'].items():
            value=live[metric];difference=abs(value-float(row[col]));total+=1
            frame.loc[spec['row'],col]=value
            if difference>1e-9:failures.append({'file':name,'row':spec['row'],'metric':col,'expected':float(row[col]),'actual':value,'difference':difference})
        if 'baseline_key' in spec:
            base=results[spec['baseline_key']]['result']['target_inflow_rate'];incentive=live['target_inflow_rate']
            for col,value in [('no_policy_target_inflow_rate',base),('induced_share',(incentive-base)/incentive)]:
                difference=abs(value-float(row[col]));total+=1;frame.loc[spec['row'],col]=value
                if difference>1e-9:failures.append({'file':name,'row':spec['row'],'metric':col,'expected':float(row[col]),'actual':value,'difference':difference})
    for name,frame in files.items():frame.to_csv(OUT/'rebuilt'/name,index=False)
    report={'all_rows_completed':True,'simulation_rows':len(specs),'unique_simulations':len(results),'numeric_metrics_checked':total,'files':{n:len(f) for n,f in files.items()},'mismatch_count':len(failures),'mismatches':failures,'passed':not failures,
            'method':'Verbatim notebook model; raw ACS rebuilt first; no simulated results read by model loader; published case settings recovered from cached labels; endogenous rate calibration checked separately.'}
    (OUT/'simulation-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='mismatches'}),flush=True)

def main():
    OUT.mkdir(exist_ok=True);specs,cases=specifications()
    (OUT/'case-specifications.json').write_text(json.dumps({'rows':specs,'cases':cases},indent=2),encoding='utf-8')
    checkpoint=OUT/'live-simulations.jsonl';results={}
    if checkpoint.exists():
        for line in checkpoint.read_text(encoding='utf-8').splitlines():
            r=json.loads(line);results[r['key']]=r
    pending={k:v for k,v in cases.items() if k not in results};start=time.time();jobs=min(8,os.cpu_count() or 2)
    print(f'{len(specs)} rows; {len(cases)} unique cases; {len(pending)} pending; {jobs} processes',flush=True)
    with ProcessPoolExecutor(max_workers=jobs) as pool,checkpoint.open('a',encoding='utf-8') as stream:
        futures={pool.submit(run,c):k for k,c in pending.items()}
        for future in as_completed(futures):
            key=futures[future];r={'key':key,'case':cases[key],'result':future.result()};results[key]=r
            stream.write(json.dumps(r)+'\n');stream.flush()
            if len(results)%50==0:
                status={'completed':len(results),'total':len(cases),'seconds':round(time.time()-start,1)}
                (OUT/'progress.json').write_text(json.dumps(status),encoding='utf-8');print(json.dumps(status),flush=True)
    compare(specs,results)
    (OUT/'progress.json').write_text(json.dumps({'completed':len(results),'total':len(cases),'phase':'complete','seconds':round(time.time()-start,1)}),encoding='utf-8')

if __name__=='__main__':main()
