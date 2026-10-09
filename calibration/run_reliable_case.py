"""Read a case JSON, apply fitted defaults, and export a traced simulation."""
import argparse
import hashlib
import json
from pathlib import Path
from reliable_worker import run

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'reliable-calibration'
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--case',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();case=json.loads(Path(args.case).read_text(encoding='utf-8'))
    parameters=OUT/'parameters.json';config=json.loads(parameters.read_text(encoding='utf-8'))
    case.setdefault('profile','new');case.setdefault('n_agents',1000);case.setdefault('years',20)
    if case['profile']!='new':raise ValueError('This runner exports the new profile only; use reliable_worker.py for explicit original-profile controls.')
    irs=json.loads((OUT/'irs-fit-report.json').read_text())
    names=['beta_income','beta_jobs','beta_rent','beta_distance','beta_education','beta_childcare']
    registry_theta=[config[name] for name in names]+[config['destination_effects'][name] for name in ['TX','NY','FL','MA','NC','IL','WA']]
    if registry_theta!=irs['chosen_theta']:raise ValueError('Registry and fitted model coefficients differ; regenerate the registry.')
    for relative,expected in config['provenance']['source_sha256'].items():
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=expected:raise ValueError('Input changed: '+relative)
    design=str(case['n_agents'])+'x'+str(case['years'])
    if design not in config['beta_by_design'] and 'beta_current_state' not in case:raise ValueError('This design requires separate calibration.')
    case.setdefault('beta_current_state',config['beta_by_design'].get(design))
    if case.get('network_decay') and case.pop('recalibrated_network',False):
        if design!='600x12':raise ValueError('Network fit applies only to 600x12.')
        decay=str(float(case['network_decay']))
        if decay not in config['network_beta_by_decay']:raise ValueError('This network candidate has not passed validation; no calibrated default is available.')
        case['beta_current_state']=config['network_beta_by_decay'][decay]
    if 'capacity_mode' in case:
        if design!='600x12' and 'external_rate' not in case:raise ValueError('Open-system fit applies only to 600x12.')
        case.setdefault('external_rate',config['external_rate_by_capacity'][case['capacity_mode']])
    result={'case':case,'parameters_sha256':hashlib.sha256(parameters.read_bytes()).hexdigest(),'metrics':run(case)}
    Path(args.output).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
