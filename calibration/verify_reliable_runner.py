"""Exercise exported cases through the public CLI, without simulation checkpoints."""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
from reliable_worker import run

ROOT=Path(__file__).resolve().parent; OUT=ROOT/'reliable-calibration'
if __name__=='__main__':
    checks=[]
    for name in ['baseline','combined','network','open-scaled']:
        output=OUT/(name+'-live-result.json')
        result=subprocess.run([sys.executable,str(ROOT/'run_reliable_case.py'),'--case',str(OUT/'examples'/(name+'.json')),'--output',str(output)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        assert result.returncode==0,result.stderr
        record=json.loads(output.read_text());assert all(math.isfinite(v) for v in record['metrics'].values())
        assert 0<=record['metrics']['move_rate']<=1
        assert record['parameters_sha256']==hashlib.sha256((OUT/'parameters.json').read_bytes()).hexdigest()
        checks.append({'example':name,'passed':True,'resolved_case':record['case'],'move_rate':record['metrics']['move_rate']})
        print('Actual public CLI example passed:',name,flush=True)
    negative={'profile':'new','seed':1,'n_agents':600,'years':12,'network_decay':10.,'recalibrated_network':True}
    try:run(negative)
    except ValueError as error:
        assert 'failed validation' in str(error)
    else:raise AssertionError('An unvalidated network default was accepted.')
    report={'passed':True,'actual_cli_cases':checks,'unvalidated_network_default_rejected':True,'case_results_use_checkpoints':False}
    (OUT/'runner-verification-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Exported runner verification complete.',flush=True)
