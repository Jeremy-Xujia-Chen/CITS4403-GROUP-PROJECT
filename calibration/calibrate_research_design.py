"""Separate 600x12 calibration after a failed transfer diagnostic; fresh validation."""
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
from calibrate_reliable_beta import ci, key
from reliable_worker import run

ROOT=Path(__file__).resolve().parent; OUT=ROOT/'reliable-calibration'
TRAIN=list(range(901,933)); VALIDATION=list(range(3001,3033))

def main():
    started=time.monotonic()
    target=float(pd.read_csv(ROOT/'raw-rebuild/rebuilt/acs_young_adult_interstate_move_rate.csv').move_rate.iloc[0])
    protocol={'agents':600,'years':12,'training_seeds':TRAIN,'validation_seeds':VALIDATION,
      'coarse_grid':np.round(np.arange(3.70,3.95001,.025),4).tolist(),
      'refined_grid':'coarse best +/-0.025, step 0.005',
      'selection':'Minimum absolute training mean error; lower beta on ties. Validation is read only after parameter selection.',
      'training_bias_tolerance':.0005,'validation_bias_tolerance':.001,'validation_ci_must_include_target':True,
      'reason':'The primary 1000x20 beta failed the expanded 600x12 transfer diagnostic. This is a new conditional design calibration, not an adjustment using validation seeds 2001-2032.',
      'precision_decimals':4}
    (OUT/'research-design-protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    irs=json.loads((OUT/'irs-fit-report.json').read_text())
    fingerprint=hashlib.sha256(json.dumps({'theta':irs['chosen_theta'],'protocol':protocol},sort_keys=True).encode()).hexdigest()
    stamp=OUT/'research-design-checkpoint-input.json'
    if stamp.exists():assert json.loads(stamp.read_text())['fingerprint']==fingerprint
    stamp.write_text(json.dumps({'fingerprint':fingerprint}),encoding='utf-8')
    path=OUT/'research-design-live.jsonl'; saved={}; grid=[]
    if path.exists():
        for line in path.read_text().splitlines():
            r=json.loads(line); saved[r['key']]=r
    def case(b,s):return {'profile':'new','beta_current_state':float(b),'seed':s,'n_agents':600,'years':12}
    with ProcessPoolExecutor(max_workers=8) as pool,path.open('a',encoding='utf-8') as stream:
        def batch(cases,label):
            pending={key(c):c for c in cases if key(c) not in saved}
            print(label,'new cases',len(pending),flush=True)
            for i,(k,value) in enumerate(zip(pending,pool.map(run,pending.values())),1):
                r={'key':k,'case':pending[k],'result':value};saved[k]=r
                stream.write(json.dumps(r)+'\n');stream.flush()
                if i%32==0:print(label,i,'/',len(pending),flush=True)
            return [saved[key(c)]['result']['move_rate'] for c in cases]
        def evaluate(points,label):
            rates=batch([case(b,s) for b in points for s in TRAIN],label); rows=[]
            for i,b in enumerate(points):
                stat=ci(rates[i*len(TRAIN):(i+1)*len(TRAIN)])
                rows.append({'phase':label,'beta_current_state':float(b),**stat,'absolute_error':abs(stat['mean']-target)})
            grid.extend(rows);pd.DataFrame(grid).to_csv(OUT/'research-design-grid.csv',index=False)
            best=min(rows,key=lambda r:(r['absolute_error'],r['beta_current_state']))
            print('Best',best,flush=True);return best
        best=evaluate(protocol['coarse_grid'],'research_coarse')
        assert best['beta_current_state'] not in [protocol['coarse_grid'][0],protocol['coarse_grid'][-1]]
        best=evaluate(np.round(np.arange(best['beta_current_state']-.025,best['beta_current_state']+.025001,.005),4).tolist(),'research_refined')
        beta=round(best['beta_current_state'],4)
        validation=ci(batch([case(beta,s) for s in VALIDATION],'research_new_validation'))
        comparison=ci(batch([case(3.825,s) for s in VALIDATION],'research_primary_beta_control'))
        repeat_cases=[case(beta,s) for s in [3001,3016,3032]]
        differences=[max(abs(v[m]-saved[key(c)]['result'][m]) for m in v) for c,v in zip(repeat_cases,pool.map(run,repeat_cases))]
        assert max(differences)<1e-12
    points=sorted(set(r['beta_current_state'] for r in grid))
    matrix=np.array([[saved[key(case(b,s))]['result']['move_rate'] for s in TRAIN] for b in points])
    rng=np.random.default_rng(4403); boot=[]
    for _ in range(1000):
        idx=rng.integers(0,len(TRAIN),len(TRAIN));boot.append(points[int(np.argmin(abs(matrix[:,idx].mean(axis=1)-target)))])
    pd.DataFrame({'bootstrap_beta':boot}).to_csv(OUT/'research-design-bootstrap.csv',index=False)
    report={'chosen_beta':beta,'target':target,'agents':600,'years':12,'training':best,
       'validation_new':{**validation,'absolute_bias':abs(validation['mean']-target)},
       'validation_primary_beta_control':comparison,
       'training_criterion_passed':best['absolute_error']<=.0005,
       'validation_criteria_passed':abs(validation['mean']-target)<=.001 and validation['ci95_low']<=target<=validation['ci95_high'],
       'beta_seed_bootstrap_p025':float(np.quantile(boot,.025)),'beta_seed_bootstrap_p975':float(np.quantile(boot,.975)),
       'deterministic_repeat_max_difference':max(differences),'unique_simulations':len(saved),'seconds':time.monotonic()-started,
       'limitation':'Conditional simulator-scale calibration. Not evidence that actual human preferences depend on agent count. Failed transfer diagnostic is retained.'}
    (OUT/'research-design-fit-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('RESEARCH DESIGN COMPLETE',json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
