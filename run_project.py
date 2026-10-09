"""Run an explicitly selected published or independently fitted project profile."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
CAL=ROOT/'calibration'

def checked_command(*arguments):
    subprocess.run([sys.executable,*map(str,arguments)],cwd=ROOT,check=True)

def read_json(path):
    """Read a JSON file as UTF-8 regardless of the platform default encoding."""
    return json.loads(Path(path).read_text(encoding='utf-8'))

THETA_NAMES=['beta_income','beta_jobs','beta_rent','beta_distance','beta_education','beta_childcare']
DESTINATIONS=['TX','NY','FL','MA','NC','IL','WA']

def load_registry(config_path,irs_path):
    """Return the parameter registry and its IRS theta vector, checking both agree."""
    config=read_json(config_path)
    irs=read_json(irs_path)
    missing=[k for k in THETA_NAMES if k not in config]
    missing+=[f'destination_effects.{s}' for s in DESTINATIONS if s not in config.get('destination_effects',{})]
    if missing:
        raise ValueError(f'{config_path} is missing: '+', '.join(missing))
    theta=[config[k] for k in THETA_NAMES]+[config['destination_effects'][s] for s in DESTINATIONS]
    if theta!=irs['chosen_theta']:
        raise ValueError('Registry and fitted model differ.')
    return config,theta

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=['calibrated','published'],default='calibrated')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--seed',type=int,default=201)
    parser.add_argument('--video',action='store_true',help='Also render and decode-check a 30-second MP4.')
    parser.add_argument('--skip-notebook',action='store_true',help='Generate only the live animation, without the diagnostic Notebook.')
    args=parser.parse_args()
    out=(args.output or ROOT/'results'/args.profile).resolve();out.mkdir(parents=True,exist_ok=True)
    os.environ.update(PYTHONUTF8='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    sys.path.insert(0,str(CAL))
    from migration_animation import make_comparison
    if args.profile=='calibrated':
        checked_command(CAL/'verify_calibration_inputs.py')
        if not args.skip_notebook:checked_command(CAL/'execute_calibration_notebook.py')
        config_path=CAL/'reliable-calibration/parameters.json'
        config,theta=load_registry(config_path,CAL/'reliable-calibration/irs-fit-report.json')
        from raw_model import load
        ns=load(irs_theta=theta)
        beta=config['beta_by_design']['600x12'];ns['PARAMS']['beta_current_state']=beta
        trace={'profile':'calibrated','parameters_sha256':hashlib.sha256(config_path.read_bytes()).hexdigest(),
           'beta_current_state':beta,'agents':600,'years':12,'seed':args.seed,
           'scope':'Live demonstration, not the regenerated research-wide policy grid.'}
    else:
        from rebuild_scripts.v8lib import load
        ns=load();beta=float(ns['PARAMS']['beta_current_state'])
        trace={'profile':'published','beta_current_state':beta,'agents':600,'years':12,'seed':args.seed,
           'scope':'Historical published configuration; old policy caches belong to this profile.'}
    animation=make_comparison(ns,n_agents=600,years=12,seed=args.seed)
    prefix='New fit' if args.profile=='calibrated' else 'Published profile'
    for scenario in animation.payload['scenarios']:scenario['name']=prefix+' · '+scenario['name']
    animation.payload['parameter_profile']=trace
    animation.save(out/'migration-animation.html')
    (out/'migration-events.json').write_text(json.dumps(animation.payload,indent=2),encoding='utf-8')
    # Independently repeat the metrics path and compare event totals with its
    # mean move rate, proving the animation uses the exported fitted profile.
    if args.profile=='calibrated':
        from reliable_worker import run
        for policy,scenario in zip(['baseline','combined'],animation.payload['scenarios']):
            observed=sum(len(frame['moves']) for frame in scenario['frames'])/(600*12)
            expected=run({'profile':'new','seed':args.seed,'n_agents':600,'years':12,'beta_current_state':beta,'policy':policy})['move_rate']
            assert abs(observed-expected)<1e-12,(policy,observed,expected)
    trace['accepted_moves']={s['name']:sum(len(f['moves']) for f in s['frames']) for s in animation.payload['scenarios']}
    trace['event_totals_validated']=True
    (out/'run-verification.json').write_text(json.dumps(trace,indent=2),encoding='utf-8')
    if args.video:checked_command(ROOT/'tools/export_video.py','--events',out/'migration-events.json','--output',out/'migration-comparison.mp4')
    print('Project run completed:',out,flush=True)
    print(json.dumps(trace,indent=2),flush=True)

if __name__=='__main__':main()
