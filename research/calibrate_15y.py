"""Predeclared 600x15 calibration for shock and entrant research designs."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calibration'))
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import time
import numpy as np
import pandas as pd
from calibrate_reliable_beta import ci,key
from reliable_worker import run

OUT=ROOT/'research/calibration-600x15'
TRAIN=list(range(901,933));VALIDATION=list(range(4001,4033))
def main():
    OUT.mkdir(parents=True,exist_ok=True);start=time.monotonic()
    target=float(pd.read_csv(ROOT/'calibration/raw-rebuild/rebuilt/acs_young_adult_interstate_move_rate.csv').move_rate.iloc[0])
    protocol={'agents':600,'years':15,'training_seeds':TRAIN,'validation_seeds':VALIDATION,
      'coarse_grid':np.round(np.arange(3.6,4.10001,.05),4).tolist(),'refined_grid':'coarse best +/-0.05, step 0.005',
      'selection':'Minimum absolute training mean error; lower beta on ties. Validation is not used for selection.',
      'training_bias_tolerance':.0005,'validation_bias_tolerance':.001,'validation_ci_must_include_target':True,
      'target':target,'reason':'Preserve the 15-year shock and entrant experiments with a separately calibrated horizon.',
      'precision_decimals':4,'bootstrap_replicates':1000,'bootstrap_seed':4403}
    (OUT/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    irs=json.loads((ROOT/'calibration/reliable-calibration/irs-fit-report.json').read_text())
    fingerprint=hashlib.sha256(json.dumps({'theta':irs['chosen_theta'],'protocol':protocol},sort_keys=True).encode()).hexdigest()
    stamp=OUT/'checkpoint-input.json'
    if stamp.exists():assert json.loads(stamp.read_text())['fingerprint']==fingerprint
    stamp.write_text(json.dumps({'fingerprint':fingerprint}),encoding='utf-8')
    saved={};path=OUT/'live.jsonl';grid=[]
    if path.exists():
        for line in path.read_text().splitlines():
            row=json.loads(line);saved[row['key']]=row
    def case(beta,seed):return {'profile':'new','beta_current_state':float(beta),'seed':seed,'n_agents':600,'years':15}
    with ProcessPoolExecutor(max_workers=8) as pool,path.open('a',encoding='utf-8') as stream:
        def batch(cases,label):
            pending={key(c):c for c in cases if key(c) not in saved};print(label,len(pending),'new cases',flush=True)
            for i,(k,val) in enumerate(zip(pending,pool.map(run,pending.values())),1):
                row={'key':k,'case':pending[k],'result':val};saved[k]=row;stream.write(json.dumps(row)+'\n');stream.flush()
                if i%32==0:print(label,i,'/',len(pending),flush=True)
            return [saved[key(c)]['result']['move_rate'] for c in cases]
        def evaluate(points,label):
            vals=batch([case(beta,s) for beta in points for s in TRAIN],label);rows=[]
            for i,beta in enumerate(points):
                stat=ci(vals[i*len(TRAIN):(i+1)*len(TRAIN)])
                rows.append({'phase':label,'beta_current_state':float(beta),**stat,'absolute_error':abs(stat['mean']-target)})
            grid.extend(rows);pd.DataFrame(grid).to_csv(OUT/'grid.csv',index=False)
            best=min(rows,key=lambda x:(x['absolute_error'],x['beta_current_state']));print('Best',best,flush=True);return best
        best=evaluate(protocol['coarse_grid'],'coarse')
        assert best['beta_current_state'] not in [protocol['coarse_grid'][0],protocol['coarse_grid'][-1]],'Search hit boundary; do not accept without extending training-only search.'
        best=evaluate(np.round(np.arange(best['beta_current_state']-.05,best['beta_current_state']+.050001,.005),4).tolist(),'refined')
        beta=round(best['beta_current_state'],4)
        validation=ci(batch([case(beta,s) for s in VALIDATION],'validation'))
        repeat=[case(beta,s) for s in [4001,4016,4032]]
        deltas=[max(abs(v[k]-saved[key(c)]['result'][k]) for k in v) for c,v in zip(repeat,pool.map(run,repeat))]
        assert max(deltas)<1e-12
    points=sorted({row['beta_current_state'] for row in grid})
    matrix=np.array([[saved[key(case(b,s))]['result']['move_rate'] for s in TRAIN] for b in points])
    rng=np.random.default_rng(4403);boot=[]
    for _ in range(1000):
        idx=rng.integers(0,len(TRAIN),len(TRAIN));boot.append(points[int(np.argmin(abs(matrix[:,idx].mean(axis=1)-target)))])
    pd.DataFrame({'bootstrap_beta':boot}).to_csv(OUT/'bootstrap.csv',index=False)
    result={'chosen_beta':beta,'target':target,'agents':600,'years':15,'training':best,'validation_new':{**validation,'absolute_bias':abs(validation['mean']-target)},
      'training_criterion_passed':best['absolute_error']<=.0005,'validation_criteria_passed':abs(validation['mean']-target)<=.001 and validation['ci95_low']<=target<=validation['ci95_high'],
      'beta_seed_bootstrap_p025':float(np.quantile(boot,.025)),'beta_seed_bootstrap_p975':float(np.quantile(boot,.975)),
      'deterministic_repeat_max_difference':max(deltas),'unique_simulations':len(saved),'seconds':time.monotonic()-start,
      'scope':'Conditional baseline calibration at 600x15; shock/policy/entrant alternatives remain scenario experiments, not additional empirical fits.'}
    (OUT/'fit-report.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
