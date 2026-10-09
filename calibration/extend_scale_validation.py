"""Additional simulation-scale diagnostic; never changes the selected parameters."""
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import numpy as np
from scipy.stats import t
from reliable_worker import run

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'reliable-calibration'
if __name__=='__main__':
    core=json.loads((OUT/'beta-fit-report.json').read_text());beta=core['chosen_beta'];seeds=list(range(2001,2033));known={}
    for line in (OUT/'beta-live.jsonl').read_text().splitlines():
        r=json.loads(line);c=r['case']
        if c['profile']=='new' and c['n_agents']==600 and c['years']==12 and c['beta_current_state']==beta:known[c['seed']]=r['result']
    path=OUT/'transfer-live.jsonl'
    if path.exists():
        for line in path.read_text().splitlines():
            r=json.loads(line);assert r['case']['beta_current_state']==beta;known[r['case']['seed']]=r['result']
    cases=[{'profile':'new','beta_current_state':beta,'n_agents':600,'years':12,'seed':s} for s in seeds if s not in known]
    with ProcessPoolExecutor(max_workers=8) as pool,path.open('a',encoding='utf-8') as stream:
        for c,value in zip(cases,pool.map(run,cases)):
            known[c['seed']]=value;stream.write(json.dumps({'case':c,'result':value})+'\n');stream.flush()
    rates=np.array([known[s]['move_rate'] for s in seeds]);half=float(t.ppf(.975,31)*rates.std(ddof=1)/np.sqrt(32));mean=float(rates.mean())
    report={'agents':600,'years':12,'seeds':seeds,'beta_current_state':beta,'mean':mean,'ci95_low':mean-half,'ci95_high':mean+half,
        'target':core['target'],'absolute_bias':abs(mean-core['target']),'n_seeds':32,
        'target_inside_ci':bool(mean-half<=core['target']<=mean+half),
        'scope':'Expanded diagnostic after the initial eight-seed transfer check; parameters were not adjusted using these results.'}
    (OUT/'extended-scale-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2),flush=True)
