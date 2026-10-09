"""Calibrate internal network controls and external share using the new core fit."""
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
from scipy.stats import t
from reliable_worker import run
from calibration_precision import canonical_parameter

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'reliable-calibration'
TRAIN=list(range(901,917));VALIDATION=list(range(3001,3033))
def identifier(case):return hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest()
def summary(values,target):
    a=np.array(values);m=float(a.mean());half=float(t.ppf(.975,len(a)-1)*a.std(ddof=1)/np.sqrt(len(a)))
    return {'mean':m,'n':len(a),'ci95_low':m-half,'ci95_high':m+half,'absolute_error':abs(m-target),'target':target}

def main():
    start=time.monotonic();core=json.loads((OUT/'research-design-fit-report.json').read_text());beta=core['chosen_beta']
    data=pd.read_csv(ROOT/'raw-rebuild/rebuilt/pums_external_origin_competition.csv')
    external_target=float(data.weighted_from_other_us.sum()/data.weighted_interstate_inmovers.sum())
    protocol={'beta_current_state':beta,'training_seeds':TRAIN,'validation_seeds':VALIDATION,'agents':600,'years':12,
        'network_steps':9,'network_target':'Closed-model mean migration rate on the same training seeds; this is a controlled network comparison, not a separate empirical estimate.',
        'external_target':external_target,'external_target_source':'sum(weighted_from_other_us) / sum(weighted_interstate_inmovers) in independently rebuilt ACS PUMS table.',
        'external_rate_bounds':[.03,.25],'external_steps':8,'final_precision_decimals':4,
        'selection':'Evaluate bisection endpoint and all visited candidates, choose lowest absolute training error; round chosen final value before validation.',
        'network_validation_absolute_difference_tolerance':.001,'open_validation_absolute_error_tolerance':.015}
    (OUT/'extension-protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    saved={};path=OUT/'extension-live.jsonl'
    if path.exists():
        for line in path.read_text().splitlines():
            r=json.loads(line);saved[r['key']]=r['result']
    irs=json.loads((OUT/'irs-fit-report.json').read_text())
    fingerprint=hashlib.sha256(json.dumps({'theta':irs['chosen_theta'],'protocol':protocol},sort_keys=True).encode()).hexdigest()
    stamp=OUT/'extension-checkpoint-input.json'
    if stamp.exists():assert json.loads(stamp.read_text())['fingerprint']==fingerprint,'Extension configuration changed.'
    stamp.write_text(json.dumps({'fingerprint':fingerprint}),encoding='utf-8')
    with ProcessPoolExecutor(max_workers=8) as pool,path.open('a',encoding='utf-8') as stream:
        def rates(parameters,seeds,metric):
            cases=[{'profile':'new','beta_current_state':beta,'n_agents':600,'years':12,**parameters,'seed':s} for s in seeds]
            pending={identifier(c):c for c in cases if identifier(c) not in saved}
            for k,value in zip(pending,pool.map(run,pending.values())):
                saved[k]=value;stream.write(json.dumps({'key':k,'case':pending[k],'result':value})+'\n');stream.flush()
            return [saved[identifier(c)][metric] for c in cases]
        baseline=rates({},TRAIN,'move_rate');target=float(np.mean(baseline));network=[]
        validation_base=rates({},VALIDATION,'move_rate');validation_target=float(np.mean(validation_base))
        for decay in [2.,5.,10.]:
            lo,hi=1.5,beta;steps=[]
            for index in range(9):
                mid=(lo+hi)/2;mean=float(np.mean(rates({'network_decay':decay,'beta_current_state':mid},TRAIN,'move_rate')))
                steps.append({'beta':mid,'move_rate':mean});lo,hi=(mid,hi) if mean>target else (lo,mid)
                print('New network',decay,'step',index+1,'mean',mean,flush=True)
            endpoint=(lo+hi)/2
            steps.append({'beta':endpoint,'move_rate':float(np.mean(rates({'network_decay':decay,'beta_current_state':endpoint},TRAIN,'move_rate')))})
            selected=min(steps,key=lambda r:(abs(r['move_rate']-target),r['beta']))['beta']
            value=canonical_parameter(selected)
            training=summary(rates({'network_decay':decay,'beta_current_state':value},TRAIN,'move_rate'),target)
            validation_rates=rates({'network_decay':decay,'beta_current_state':value},VALIDATION,'move_rate')
            validation=summary(validation_rates,validation_target)
            paired=summary(np.array(validation_rates)-np.array(validation_base),0.)
            network.append({'decay':decay,'beta_full_precision':selected,'beta_current_state':value,'training':training,'validation':validation,
                'validation_paired_difference':paired,'validation_criteria_passed':abs(paired['mean'])<=.001 and paired['ci95_low']<=0<=paired['ci95_high'],'steps':steps})
        opens=[]
        for mode in ['shared','scaled']:
            lo,hi=.03,.25;steps=[]
            for index in range(8):
                mid=(lo+hi)/2;mean=float(np.mean(rates({'capacity_mode':mode,'external_rate':mid,'intensity':0.},TRAIN,'external_share_system')))
                steps.append({'external_rate':mid,'external_share':mean});lo,hi=(mid,hi) if mean<external_target else (lo,mid)
                print('New open',mode,'step',index+1,'share',mean,flush=True)
            endpoint=(lo+hi)/2
            steps.append({'external_rate':endpoint,'external_share':float(np.mean(rates({'capacity_mode':mode,'external_rate':endpoint,'intensity':0.},TRAIN,'external_share_system')))})
            selected=min(steps,key=lambda r:(abs(r['external_share']-external_target),r['external_rate']))['external_rate']
            value=canonical_parameter(selected)
            pars={'capacity_mode':mode,'external_rate':value,'intensity':0.}
            validation=summary(rates(pars,VALIDATION,'external_share_system'),external_target)
            opens.append({'capacity_mode':mode,'external_rate_full_precision':selected,'external_rate':value,
                'training':summary(rates(pars,TRAIN,'external_share_system'),external_target),
                'validation':validation,'validation_criteria_passed':validation['absolute_error']<=.015 and validation['ci95_low']<=external_target<=validation['ci95_high'],'steps':steps})
        # Fresh repeat controls on one calibrated network and both open modes.
        repeat_cases=[{'profile':'new','seed':3001,'n_agents':600,'years':12,'beta_current_state':network[0]['beta_current_state'],'network_decay':2.}]
        repeat_cases.extend({'profile':'new','seed':3001,'n_agents':600,'years':12,'beta_current_state':beta,'capacity_mode':r['capacity_mode'],'external_rate':r['external_rate'],'intensity':0.} for r in opens)
        deltas=[]
        for case,value in zip(repeat_cases,pool.map(run,repeat_cases)):
            prior=saved[identifier(case)];deltas.append(max(abs(value[k]-prior[k]) for k in value))
        assert max(deltas)<1e-12
    report={'network_target_training':summary(baseline,target),'network_target_validation':summary(validation_base,validation_target),
        'network':network,'open':opens,'core_beta':beta,'agents':600,'years':12,'external_origin_target':external_target,'unique_simulations':len(saved),
        'repeat_max_difference':max(deltas),'seconds':time.monotonic()-start,
        'scope':'Conditional endogenous model controls. Network calibration targets the closed model; external exchange calibration targets independently rebuilt PUMS origin composition. Validation CIs describe simulation seed variation only.'}
    (OUT/'extension-fit-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('NEW EXTENSIONS COMPLETE',json.dumps({k:v for k,v in report.items() if k not in ['network','open']},indent=2),flush=True)

if __name__=='__main__':main()
