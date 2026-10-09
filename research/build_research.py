"""Rerun the complete published experiment design using the fitted profile."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
import hashlib
import json
from pathlib import Path
import sys
import time
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];CAL=ROOT/'calibration';OUT=ROOT/'research';DATA=ROOT/'data/research'
sys.path.insert(0,str(CAL))
from full_simulation_rebuild import specifications,identifier,CACHE
from worker import run

def definitions(known_only=False):
    specs,oldcases=specifications();config=json.loads((CAL/'reliable-calibration/parameters.json').read_text())
    ext=json.loads((CAL/'reliable-calibration/extension-fit-report.json').read_text())
    beta15=json.loads((OUT/'calibration-600x15/fit-report.json').read_text())['chosen_beta'] if (OUT/'calibration-600x15/fit-report.json').exists() else None
    betas={'1000x20':config['beta_by_design']['1000x20'],'600x12':config['beta_by_design']['600x12'],'600x15':beta15}
    network={str(float(r['decay'])):r for r in ext['network']};result=[];cases={}
    for spec in specs:
        case=dict(oldcases[spec['key']]);design=f"{case['n_agents']}x{case['years']}"
        if known_only and design=='600x15':continue
        if betas[design] is None:raise ValueError('First calibrate 600x15 with research/calibrate_15y.py')
        beta=betas[design];row=pd.read_csv(CACHE/spec['file']).iloc[spec['row']]
        case.update(profile='new',beta_current_state=beta)
        labels={'beta_current_state':beta}
        if spec['file']=='parameter_sensitivity_runs.csv':case['beta_current_state']=round(beta*float(row.stay_scale),8)
        if spec['file']=='network_decay_runs.csv':
            if bool(row.recalibrated) and float(row.network_decay)>0:case['beta_current_state']=network[str(float(row.network_decay))]['beta_current_state']
            labels={'beta_current_state':case['beta_current_state'],'calibration_validated':bool(float(row.network_decay)==0 or (row.recalibrated and network[str(float(row.network_decay))]['validation_criteria_passed']))}
        if spec['file']=='open_system_runs.csv':case['external_rate']=config['external_rate_by_capacity'][row.capacity_mode];labels['external_rate']=case['external_rate']
        key=identifier(case);cases[key]=case
        s={**spec,'key':key,'new_labels':labels,'design':design}
        if 'baseline_key' in s:
            base={k:v for k,v in case.items() if k not in ['lever','intensity']};s['baseline_key']=identifier(base);cases[s['baseline_key']]=base
        result.append(s)
    for seed in range(401,407):
        case={'kind':'competition','profile':'new','beta_current_state':betas['600x12'],'n_agents':600,'years':12,'seed':seed}
        cases[identifier(case)]=case
    return result,cases,betas

def export(specs,cases,saved,betas):
    DATA.mkdir(exist_ok=True);frames={};changed=[];metrics=0
    for spec in specs:
        name=spec['file']
        if name not in frames:frames[name]=pd.read_csv(CACHE/name)
        frame=frames[name];old=frame.iloc[spec['row']].copy();val=saved[spec['key']]['result']
        for col,metric in spec['metrics'].items():
            frame.loc[spec['row'],col]=val[metric];metrics+=1
            if abs(val[metric]-float(old[col]))>1e-9:changed.append((name,spec['row'],col))
        for label,value in spec['new_labels'].items():
            if label in frame.columns or label=='calibration_validated':frame.loc[spec['row'],label]=value
        if 'baseline_key' in spec:
            base=saved[spec['baseline_key']]['result']['target_inflow_rate'];pol=val['target_inflow_rate']
            for col,value in [('no_policy_target_inflow_rate',base),('induced_share',(pol-base)/pol if pol else float('nan'))]:
                frame.loc[spec['row'],col]=value;metrics+=1
        frame.loc[spec['row'],'parameter_profile']='calibrated'
        frame.loc[spec['row'],'beta_current_state_used']=cases[spec['key']]['beta_current_state']
    for name,frame in frames.items():frame.to_csv(DATA/name,index=False)
    rows=[]
    for key,case in cases.items():
        if case.get('kind')=='competition':
            for row in saved[key]['result']['states']:rows.append({'seed':case['seed'],**row})
    full=pd.DataFrame(rows);full.to_csv(OUT/'static-competition-seed-results.csv',index=False)
    summary=full.groupby('state')[['net_migration','employment_rate','unfilled_jobs']].mean().reset_index().rename(columns={'net_migration':'mean_net_migration','employment_rate':'mean_employment','unfilled_jobs':'mean_unfilled_jobs'})
    summary.to_csv(DATA/'state_competition_summary.csv',index=False)
    reference=['acs_young_adult_interstate_move_rate.csv','acs_young_adult_interstate_move_rate_by_state.csv','acs_young_adult_interstate_move_rate_by_age.csv','pums_external_origin_competition.csv','brfss_2023_coverage_audit.csv','brfss_validation_status.csv']
    for name in reference:
        (DATA/name).write_bytes((CAL/'raw-rebuild/rebuilt'/name).read_bytes())
    rows=[]
    for design,filename in [('1000x20',CAL/'reliable-calibration/beta-fit-report.json'),('600x12',CAL/'reliable-calibration/research-design-fit-report.json'),('600x15',OUT/'calibration-600x15/fit-report.json')]:
        fit=json.loads(filename.read_text());rows.append({'design':design,'beta_current_state':fit['chosen_beta'],'simulated_move_rate':fit['training']['mean'],'target_move_rate':fit['target'],'absolute_error':fit['training']['absolute_error'],'validation_passed':fit['validation_criteria_passed']})
    pd.DataFrame(rows).to_csv(DATA/'move_rate_calibration.csv',index=False)
    report={'complete':True,'profile':'new','simulation_rows':len(specs),'unique_simulations':len(cases),'static_competition_runs':6,
      'files':{k:len(v) for k,v in frames.items()},'numeric_outputs_written':metrics,'changed_metric_cells_from_published':len(changed),
      'betas_by_design':betas,'new_policy_grid_regenerated':True,'decay10_scope':'Explicit failed-calibration diagnostic, excluded from validated policy conclusions and defaults.'}
    (OUT/'rebuild-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2),flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--known-only',action='store_true');parser.add_argument('--jobs',type=int,default=8);args=parser.parse_args()
    specs,cases,betas=definitions(args.known_only);OUT.mkdir(exist_ok=True)
    # Source fingerprints prevent reusing records after changing model/empirical inputs.
    cfg=json.loads((CAL/'reliable-calibration/parameters.json').read_text())
    for relative,expected in cfg['provenance']['source_sha256'].items():
        assert hashlib.sha256((CAL/relative).read_bytes()).hexdigest()==expected, 'Input or adapter changed: '+relative
    fingerprint=hashlib.sha256(json.dumps({'theta':json.loads((CAL/'reliable-calibration/irs-fit-report.json').read_text())['chosen_theta'],
      'sources':cfg['provenance']['source_sha256'],'worker':hashlib.sha256((OUT/'worker.py').read_bytes()).hexdigest()},sort_keys=True).encode()).hexdigest()
    stamp=OUT/'checkpoint-input.json'
    if stamp.exists():assert json.loads(stamp.read_text())['fingerprint']==fingerprint,'Model input changed; checkpoint cannot be reused.'
    stamp.write_text(json.dumps({'fingerprint':fingerprint}),encoding='utf-8')
    path=OUT/'live-simulations.jsonl';saved={}
    if path.exists():
        for line in path.read_text().splitlines():
            row=json.loads(line);saved[row['key']]=row
    pending={k:c for k,c in cases.items() if k not in saved};print(len(specs),'rows;',len(cases),'unique;',len(pending),'pending',flush=True)
    start=time.monotonic()
    with ProcessPoolExecutor(max_workers=args.jobs) as pool,path.open('a',encoding='utf-8') as stream:
        futures={pool.submit(run,c):key for key,c in pending.items()}
        for i,future in enumerate(as_completed(futures),1):
            key=futures[future];row={'key':key,'case':cases[key],'result':future.result()};saved[key]=row;stream.write(json.dumps(row)+'\n');stream.flush()
            if i%25==0:
                progress={'completed_this_run':i,'pending_at_start':len(pending),'saved_total':len(saved),'seconds':round(time.monotonic()-start,1)}
                (OUT/'progress.json').write_text(json.dumps(progress),encoding='utf-8');print(json.dumps(progress),flush=True)
    if args.known_only:print('Known designs complete; 600x15 export deferred until calibration.',flush=True)
    else:
        (OUT/'case-specifications.json').write_text(json.dumps({'rows':specs,'cases':cases},indent=2),encoding='utf-8')
        export(specs,cases,saved,betas)
if __name__=='__main__':main()
