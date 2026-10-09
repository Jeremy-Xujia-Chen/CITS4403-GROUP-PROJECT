"""New-fit research worker. All cases supply their design-specific stay beta."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calibration'))
from reliable_worker import run as run_case
import reliable_worker
import raw_model

def run(case):
    if case.get('kind')!='competition':return run_case(case)
    c={k:v for k,v in case.items() if k!='kind'}
    # Initialize the same new IRS model as every other research case.
    if 'new' not in reliable_worker.MODELS:
        import json
        theta=json.loads((ROOT/'calibration/reliable-calibration/irs-fit-report.json').read_text())['chosen_theta']
        reliable_worker.MODELS['new']=raw_model.load(irs_theta=theta)
    ns=reliable_worker.MODELS['new'];state=ns['state_data'];np=ns['np'];pd=ns['pd']
    need=.5/state.job_index+.5*state.housing_capacity_index
    incentives=.25+.75*(need-need.min())/max(need.max()-need.min(),1e-9)
    policy=ns['policy_table']()
    for code,value in incentives.items():policy.loc[code,'migration_incentive']=float(value)
    params=dict(ns['PARAMS'],beta_current_state=c['beta_current_state'])
    model=ns['PolicySocialABM'](state,policy,n_agents=c['n_agents'],years=c['years'],seed=c['seed'],params=params,interaction_strength=1.)
    history,_,_=model.run();last=history[history.year==history.year.max()]
    return {'states':last[['state','net_migration','employment_rate','unfilled_jobs_state']].rename(columns={'unfilled_jobs_state':'unfilled_jobs'}).to_dict('records')}
