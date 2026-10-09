"""Predeclared grid calibration with new, disjoint simulation validation seeds."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
from scipy.stats import t
from reliable_worker import run

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'reliable-calibration'
TRAIN=list(range(901,917));VALIDATION=list(range(1901,1933))

def key(case):return hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest()
def ci(values):
    a=np.array(values);mean=float(a.mean());half=float(t.ppf(.975,len(a)-1)*a.std(ddof=1)/np.sqrt(len(a)))
    return {'n_seeds':len(a),'mean':mean,'ci95_low':mean-half,'ci95_high':mean+half,'ci95_halfwidth':half,'seed_sd':float(a.std(ddof=1))}

def main():
    OUT.mkdir(exist_ok=True);start=time.monotonic()
    target=float(pd.read_csv(ROOT/'raw-rebuild/rebuilt/acs_young_adult_interstate_move_rate.csv').move_rate.iloc[0])
    protocol={'target':target,'training_seeds':TRAIN,'validation_seeds':VALIDATION,'primary_agents':1000,'primary_years':20,
        'coarse_grid':np.round(np.arange(3.4,4.60001,.15),4).tolist(),'fine_grid':'coarse best +/-0.15, step 0.025','refined_grid':'fine best +/-0.025, step 0.005',
        'selection':'Minimum absolute training-seed mean error; lowest beta on ties; validation never used to select beta.',
        'training_bias_tolerance':.0005,'validation_bias_tolerance':.001,'validation_ci_must_include_target':True,
        'transfer_checks':[{'agents':600,'years':12,'seeds':list(range(2001,2009))},{'agents':2000,'years':20,'seeds':list(range(2101,2109))}],
        'bootstrap_replicates':1000,'bootstrap_seed':4403,'precision_decimals':4,
        'model_claim':'Current V8 conditional on chosen IRS route fit and existing structural assumptions. Simulation CIs are not survey-data or causal-effect CIs.'}
    (OUT/'beta-protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    checkpoint=OUT/'beta-live.jsonl';results={}
    if checkpoint.exists():
        for line in checkpoint.read_text(encoding='utf-8').splitlines():
            r=json.loads(line);results[r['key']]=r
    irs_fit=json.loads((OUT/'irs-fit-report.json').read_text(encoding='utf-8'))
    model_fingerprint=hashlib.sha256(json.dumps({'chosen_theta':irs_fit['chosen_theta'],'original_theta':irs_fit['original_theta'],'source_sha256':irs_fit['source_sha256']},sort_keys=True).encode()).hexdigest()
    stamp=OUT/'beta-checkpoint-input.json'
    if stamp.exists():
        previous=json.loads(stamp.read_text())
        if 'model_fingerprint' in previous:assert previous['model_fingerprint']==model_fingerprint,'Fit changed; use a new checkpoint.'
        else:assert previous['irs_fit_sha256']==hashlib.sha256((OUT/'irs-fit-report.json').read_bytes()).hexdigest(),'Fit changed; use a new checkpoint.'
    stamp.write_text(json.dumps({'model_fingerprint':model_fingerprint}),encoding='utf-8')
    grid=[]
    def case(beta,seed,agents=1000,years=20,profile='new'):
        return {'profile':profile,'beta_current_state':float(beta),'seed':int(seed),'n_agents':agents,'years':years}
    with ProcessPoolExecutor(max_workers=8) as pool,checkpoint.open('a',encoding='utf-8') as stream:
        def batch(cases,label):
            pending={key(c):c for c in cases if key(c) not in results};total=len(pending);done=0
            print(label,'new simulations',total,flush=True)
            futures={pool.submit(run,c):k for k,c in pending.items()}
            for future in as_completed(futures):
                k=futures[future];r={'key':k,'case':pending[k],'result':future.result()};results[k]=r
                stream.write(json.dumps(r)+'\n');stream.flush();done+=1
                if done%16==0 or done==total:
                    progress={'phase':label,'completed':done,'total':total,'all_unique_cases':len(results),'seconds':round(time.monotonic()-start,1)}
                    (OUT/'beta-progress.json').write_text(json.dumps(progress),encoding='utf-8');print(json.dumps(progress),flush=True)
            return [results[key(c)]['result']['move_rate'] for c in cases]
        def evaluate(betas,label):
            cases=[case(b,s) for b in betas for s in TRAIN];rates=batch(cases,label)
            rows=[]
            for i,b in enumerate(betas):
                a=rates[i*len(TRAIN):(i+1)*len(TRAIN)];stat=ci(a)
                rows.append({'phase':label,'beta_current_state':float(b),**stat,'target_move_rate':target,'absolute_error':abs(stat['mean']-target)})
            grid.extend(rows);frame=pd.DataFrame(grid);frame.to_csv(OUT/'beta-grid.csv',index=False)
            best=min(rows,key=lambda r:(r['absolute_error'],r['beta_current_state']))
            print(label,'best',best,flush=True);return best
        best=evaluate(protocol['coarse_grid'],'coarse')
        assert best['beta_current_state'] not in [protocol['coarse_grid'][0],protocol['coarse_grid'][-1]],'Best on predeclared boundary; protocol insufficient.'
        best=evaluate(np.round(np.arange(best['beta_current_state']-.15,best['beta_current_state']+.150001,.025),4).tolist(),'fine')
        best=evaluate(np.round(np.arange(best['beta_current_state']-.025,best['beta_current_state']+.025001,.005),4).tolist(),'refined')
        beta=round(best['beta_current_state'],4)
        validation_new=batch([case(beta,s) for s in VALIDATION],'independent_validation_new')
        validation_old=batch([case(3.925,s,profile='original') for s in VALIDATION],'independent_validation_published')
        new_stats=ci(validation_new);old_stats=ci(validation_old)
        transfers=[]
        for design in protocol['transfer_checks']:
            rates=batch([case(beta,s,design['agents'],design['years']) for s in design['seeds']],f"transfer_{design['agents']}_{design['years']}")
            transfers.append({**design,**ci(rates),'absolute_bias':abs(np.mean(rates)-target)})
        # Execute again without consulting the checkpoint to test actual model reproducibility.
        repeat_cases=[case(beta,s) for s in [1901,1916,1932]]
        repeat_values=list(pool.map(run,repeat_cases));differences=[]
        for c,value in zip(repeat_cases,repeat_values):
            prior=results[key(c)]['result'];differences.append(max(abs(value[m]-prior[m]) for m in value))
        assert max(differences)<1e-12
    points=sorted(set(r['beta_current_state'] for r in grid))
    matrix=np.array([[results[key(case(b,s))]['result']['move_rate'] for s in TRAIN] for b in points])
    rng=np.random.default_rng(4403);selected=[]
    for _ in range(1000):
        sampled=rng.integers(0,len(TRAIN),len(TRAIN));errors=np.abs(matrix[:,sampled].mean(axis=1)-target)
        selected.append(points[int(np.argmin(errors))])
    pd.DataFrame({'bootstrap_beta':selected}).to_csv(OUT/'beta-seed-bootstrap.csv',index=False)
    training_ok=best['absolute_error']<=protocol['training_bias_tolerance']
    validation_ok=abs(new_stats['mean']-target)<=protocol['validation_bias_tolerance'] and new_stats['ci95_low']<=target<=new_stats['ci95_high']
    report={'chosen_beta':beta,'training':best,'validation_new':{**new_stats,'absolute_bias':abs(new_stats['mean']-target),'relative_bias':(new_stats['mean']-target)/target},
        'validation_published':{**old_stats,'absolute_bias':abs(old_stats['mean']-target)},'target':target,
        'training_criterion_passed':training_ok,'validation_criteria_passed':validation_ok,
        'validation_absolute_bias_improved':abs(new_stats['mean']-target)<abs(old_stats['mean']-target),
        'transfer_checks':transfers,'beta_seed_bootstrap_p025':float(np.quantile(selected,.025)),'beta_seed_bootstrap_p975':float(np.quantile(selected,.975)),
        'deterministic_repeat_cases':repeat_cases,'deterministic_repeat_max_difference':max(differences),
        'unique_simulations':len(results),'seconds':time.monotonic()-start,
        'limitations':['Bootstrap covers simulation-seed uncertainty conditional on the finite search grid and input data.','ACS survey sampling uncertainty and uncertainty in demographic or social assumptions are not included.','Validation seeds check the simulator, not predictions against new real-world migration data.']}
    (OUT/'beta-fit-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('BETA CALIBRATION COMPLETE',json.dumps(report,indent=2),flush=True)
    (OUT/'beta-progress.json').write_text(json.dumps({'phase':'complete','chosen_beta':beta,'all_unique_cases':len(results),'seconds':round(time.monotonic()-start,1)}),encoding='utf-8')

if __name__=='__main__':main()
