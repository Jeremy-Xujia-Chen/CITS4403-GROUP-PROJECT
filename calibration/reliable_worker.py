"""Run original V8 model definitions with explicitly recorded IRS fit profiles."""
import json
from pathlib import Path
import pandas as pd
import raw_model

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'reliable-calibration';MODELS={}

def run(case):
    case=dict(case);profile=case.pop('profile','new')
    if profile not in ['original','new']:raise ValueError('Unknown fit profile.')
    if profile!='original' and 'beta_current_state' not in case:
        design=(case.get('n_agents',600),case.get('years',12))
        if design not in [(600,12),(1000,20)]:raise ValueError('Pass an explicitly calibrated beta for this unsupported design.')
        beta_report=OUT/('research-design-fit-report.json' if design==(600,12) else 'beta-fit-report.json')
        if not beta_report.exists():raise ValueError('Pass beta_current_state explicitly until calibration has finished.')
        case['beta_current_state']=json.loads(beta_report.read_text())['chosen_beta']
        if case.get('network_decay') and case.pop('recalibrated_network',False):
            if design!=(600,12):raise ValueError('Network parameters have been calibrated only at 600x12.')
            extension=json.loads((OUT/'extension-fit-report.json').read_text())
            candidate=next(r for r in extension['network'] if r['decay']==case['network_decay'])
            if not candidate['validation_criteria_passed']:raise ValueError('This network candidate failed validation; no calibrated default is available.')
            case['beta_current_state']=candidate['beta_current_state']
    if profile!='original' and 'capacity_mode' in case and 'external_rate' not in case:
        if (case.get('n_agents',600),case.get('years',12))!=(600,12):raise ValueError('External-rate defaults have been calibrated only at 600x12.')
        extension=json.loads((OUT/'extension-fit-report.json').read_text())
        candidate=next(r for r in extension['open'] if r['capacity_mode']==case['capacity_mode'])
        if not candidate['validation_criteria_passed']:raise ValueError('This external-rate candidate failed validation; no calibrated default is available.')
        case['external_rate']=candidate['external_rate']
    if profile not in MODELS:
        fit=json.loads((OUT/'irs-fit-report.json').read_text(encoding='utf-8'))
        theta=fit['original_theta'] if profile=='original' else fit['chosen_theta']
        MODELS[profile]=raw_model.load(irs_theta=theta)
        if profile!='original':
            empirical=pd.read_csv(ROOT/'raw-rebuild/rebuilt/pums_external_origin_competition.csv')
            MODELS[profile]['EXTERNAL_ORIGIN_TARGET']=float(empirical.weighted_from_other_us.sum()/empirical.weighted_interstate_inmovers.sum())
    raw_model._ns=MODELS[profile]
    return raw_model.run(case)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('case',help='JSON case with explicit beta_current_state, seed, n_agents and years')
    args=parser.parse_args();print(json.dumps(run(json.loads(args.case)),indent=2))
