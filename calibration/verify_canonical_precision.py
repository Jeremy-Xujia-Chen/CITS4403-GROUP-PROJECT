"""Freshly rerun all affected published cases using the fixed precision rule."""
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import time
import pandas as pd
from calibration_precision import canonical_parameter
from full_simulation_rebuild import specifications,identifier,CACHE
from reliable_worker import run

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'reliable-calibration'

def patch_project():
    source=ROOT/'download/CITS4403-GROUP-PROJECT-master';work=OUT/'precision-fix-project'
    shutil.copytree(source,work,dirs_exist_ok=True)
    path=work/'0914-1_v8.ipynb';nb=json.loads(path.read_text(encoding='utf-8'));changes=[]
    for index,before,after in [(67,'betas[decay] = (lo + hi) / 2','betas[decay] = round((lo + hi) / 2, 4)'),
                               (69,'rate = (lo + hi) / 2','rate = round((lo + hi) / 2, 4)')]:
        original=''.join(nb['cells'][index]['source']);assert original.count(before)==1
        updated=original.replace(before,after);nb['cells'][index]['source']=updated.splitlines(keepends=True)
        changes.append(''.join(difflib.unified_diff(original.splitlines(keepends=True),updated.splitlines(keepends=True),fromfile=f'cell-{index}-original',tofile=f'cell-{index}-precision-fixed')))
    path.write_text(json.dumps(nb,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
    (OUT/'precision-fix.patch').write_text('\n'.join(changes),encoding='utf-8')
    (work/'VERIFICATION-SCOPE.md').write_text('This copy fixes final parameter precision only. It retains the published IRS fit, beta=3.925 and published caches. New fitted parameters are separate in parameters.json; these old policy tables are not new-fit outputs.\n',encoding='utf-8')
    # Preserve the already verified local CLI constant-extraction correction.
    shutil.copy2(ROOT/'deployment/master/rebuild_scripts/v8lib.py',work/'rebuild_scripts/v8lib.py')
    return path

def main():
    path=patch_project();start=time.monotonic();cal=json.loads((ROOT/'raw-rebuild/calibration-report.json').read_text())
    betas={r['decay']:canonical_parameter(r['beta_full_precision']) for r in cal['network']}
    rates={r['capacity_mode']:canonical_parameter(r['external_rate_full_precision']) for r in cal['open']}
    specs,cases=specifications();specs=[s for s in specs if s['file'] in ['network_decay_runs.csv','open_system_runs.csv']]
    pending={};frames={name:pd.read_csv(CACHE/name) for name in ['network_decay_runs.csv','open_system_runs.csv']}
    for s in specs:
        c=dict(cases[s['key']]);row=frames[s['file']].iloc[s['row']]
        if s['file']=='network_decay_runs.csv' and row.recalibrated and row.network_decay:c['beta_current_state']=betas[float(row.network_decay)]
        elif s['file']=='open_system_runs.csv':c['external_rate']=rates[row.capacity_mode]
        c['profile']='original';s['canonical_key']=identifier(c);pending[s['canonical_key']]=c
    checkpoint=OUT/'canonical-precision-live.jsonl';results={}
    if checkpoint.exists():
        for line in checkpoint.read_text().splitlines():
            r=json.loads(line);results[r['key']]=r['result']
    todo={k:c for k,c in pending.items() if k not in results};print('Canonical precision cases',len(specs),'unique',len(pending),'new',len(todo),flush=True)
    with ProcessPoolExecutor(max_workers=8) as pool,checkpoint.open('a',encoding='utf-8') as stream:
        futures={pool.submit(run,c):k for k,c in todo.items()}
        for count,future in enumerate(as_completed(futures),1):
            k=futures[future];value=future.result();results[k]=value
            stream.write(json.dumps({'key':k,'case':todo[k],'result':value})+'\n');stream.flush()
            if count%50==0:print('Precision verified',count,'/',len(todo),flush=True)
    mismatches=[];checked=0
    for s in specs:
        row=frames[s['file']].iloc[s['row']];value=results[s['canonical_key']]
        for column,metric in s['metrics'].items():
            delta=abs(float(row[column])-value[metric]);checked+=1
            if delta>1e-9:mismatches.append({'file':s['file'],'row':s['row'],'metric':column,'difference':delta})
            frames[s['file']].loc[s['row'],column]=value[metric]
    folder=OUT/'precision-rebuilt';folder.mkdir(exist_ok=True)
    for name,frame in frames.items():frame.to_csv(folder/name,index=False)
    report={'published_setting_rows':len(specs),'unique_simulations':len(pending),'numeric_metrics_checked':checked,
        'mismatch_count':len(mismatches),'mismatches':mismatches,'passed':not mismatches,
        'rounding_rule':'Final beta and external rate rounded to four decimals after bisection, before any policy simulation; fitting iterations remain full precision.',
        'patched_notebook':str(path),'patched_source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'network_final_betas':betas,'open_final_rates':rates,'seconds':time.monotonic()-start,
        'scope':'Exact affected published case grid, original IRS fit and beta=3.925; outputs obtained from actual fresh model runs. These are precision-control results, not new-fit policy results.'}
    (OUT/'precision-fix-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='mismatches'},indent=2),flush=True)
    assert report['passed'],report['mismatch_count']

if __name__=='__main__':main()
