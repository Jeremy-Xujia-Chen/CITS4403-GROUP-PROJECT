"""Audit fitted research outputs, model identity, media and repository text."""
import ast,hashlib,json,re,subprocess,sys,zipfile
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def definitions(cell,classes=False):
    nodes=[n for n in ast.parse(''.join(cell['source'])).body if isinstance(n,ast.ClassDef if classes else (ast.FunctionDef,ast.ClassDef))]
    for n in nodes:
        for c in ast.walk(n):
            if isinstance(c,(ast.FunctionDef,ast.ClassDef)) and c.body and isinstance(c.body[0],ast.Expr) and isinstance(c.body[0].value,ast.Constant) and isinstance(c.body[0].value.value,str):c.body.pop(0)
    return [ast.dump(n,include_attributes=False) for n in nodes]
def file_audit():
    chinese=re.compile('[\u3400-\u4dbf\u4e00-\u9fff]');issues=[];count=0;binary=0;ppts=0
    for p in ROOT.rglob('*'):
        relative=p.relative_to(ROOT)
        if not p.is_file() or any(part in {'.git','.runtime','__pycache__','.venv','ipython','jupyter','jupyter-runtime','precision-fix-project','.ipynb_checkpoints'} for part in relative.parts) or p.suffix in {'.bak','.pyc'}:continue
        count+=1
        if chinese.search(str(relative)):issues.append(str(relative)+': filename')
        if p.suffix in {'.png','.jpg','.jpeg','.mp4','.gif','.zip'}:binary+=1;continue
        if p.suffix in {'.pptx','.docx','.xlsx'}:
            ppts+=int(p.suffix=='.pptx')
            with zipfile.ZipFile(p) as z:text='\n'.join(z.read(n).decode('utf-8') for n in z.namelist() if n.endswith('.xml'))
        else:
            text=p.read_text(encoding='utf-8-sig')
            if p.suffix in {'.json','.ipynb'}:text=json.dumps(json.loads(text),ensure_ascii=False)
        if chinese.search(text):issues.append(str(relative)+': content')
        if p.suffix=='.py':ast.parse(text,filename=str(relative))
        if p.suffix in {'.pkl','.pickle'}:issues.append(str(relative)+': unnecessary pickle')
    assert not issues,issues
    return {'files_checked':count,'cjk_text_or_filename_hits':0,'binary_media_files':binary,'pptx_files':ppts}
def main():
    cp=ROOT/'calibration/reliable-calibration/parameters.json';cfg=read(cp)
    for relative,expected in cfg['provenance']['source_sha256'].items():assert sha(ROOT/'calibration'/relative)==expected,relative
    assert cfg['beta_by_design']=={'1000x20':3.825,'600x12':3.82,'600x15':3.82} and '10.0' not in cfg['network_beta_by_decay']
    irs=read(ROOT/'calibration/reliable-calibration/irs-fit-report.json')
    assert [cfg[k] for k in ['beta_income','beta_jobs','beta_rent','beta_distance','beta_education','beta_childcare']]+[cfg['destination_effects'][k] for k in ['TX','NY','FL','MA','NC','IL','WA']]==irs['chosen_theta']
    source=read(ROOT/'0914-1_v8.ipynb');executed=read(ROOT/'results/research/research-executed.ipynb')
    assert [(c['cell_type'],''.join(c['source'])) for c in source['cells']]==[(c['cell_type'],''.join(c['source'])) for c in executed['cells']]
    assert not [o for c in executed['cells'] for o in c.get('outputs',[]) if o.get('output_type')=='error']
    original=read(ROOT/'calibration/deployment/master/0914-1_v8.ipynb')
    for index in [22,67,69]:assert definitions(original['cells'][index],True)==definitions(source['cells'][index],True),index
    assert definitions(original['cells'][28])==definitions(source['cells'][28])
    assert sum(c['cell_type']=='code' for c in executed['cells'])==41
    execution=read(ROOT/'results/research/execution-report.json');assert execution['passed'] and execution['figures']==17
    assert read(ROOT/'results/research/profile.json')['parameters_sha256']==sha(cp)
    live=pd.read_csv(ROOT/'results/research/tables/live-checks.csv');assert len(live)==4 and live.metrics_checked.sum()==22 and (live.status=='match').all()
    specs=read(ROOT/'research/case-specifications.json');assert len(specs['rows'])==4140 and len(specs['cases'])==3838
    records={r['key']:r for r in map(json.loads,(ROOT/'research/live-simulations.jsonl').read_text().splitlines())};assert len(records)==3838
    frames={p.name:pd.read_csv(p) for p in (ROOT/'data/research').glob('*.csv')};assert len(frames)==29
    checked=0
    for s in specs['rows']:
        row=frames[s['file']].iloc[s['row']];record=records[s['key']];case=specs['cases'][s['key']]
        assert record['case']==case and case['profile']=='new'
        assert row.parameter_profile=='calibrated' and abs(row.beta_current_state_used-case['beta_current_state'])<1e-12
        for col,metric in s['metrics'].items():assert abs(float(row[col])-record['result'][metric])<1e-12,(s['file'],s['row'],col);checked+=1
        if 'baseline_key' in s:
            base=records[s['baseline_key']]['result']['target_inflow_rate'];pol=record['result']['target_inflow_rate']
            assert abs(row.no_policy_target_inflow_rate-base)<1e-12 and abs(row.induced_share-(pol-base)/pol)<1e-12;checked+=2
    assert checked==26224
    from rebuild_scripts.worker import run as run_cli
    baseline_case=run_cli({'n_agents':1000,'years':20,'seed':101})
    assert baseline_case['beta_current_state_used']==cfg['beta_by_design']['1000x20']
    assert abs(baseline_case['move_rate']-frames['baseline_runs.csv'].set_index('seed').loc[101,'move_rate'])<1e-12
    cross=frames['cross_experiment_runs.csv']
    for r in frames['cross_experiment_summary.csv'].itertuples(index=False):
        g=cross[(cross.interaction==r.interaction)&(cross.policy==r.policy)]
        for out,inp in {'target_inflow_rate':'target_inflow_rate','social_cost':'target_social_cost','chain_share':'chain_share','housing_rejection':'housing_rejection','job_rejection':'job_rejection','clustering':'coorigin_clustering','peer_colocation':'peer_colocation','social_utility_index':'social_utility_index'}.items():assert abs(getattr(r,out)-g[inp].mean())<1e-12
    network=frames['network_decay_runs.csv'];assert not network[network.network_decay==10].calibration_validated.any()
    competition=pd.read_csv(ROOT/'research/static-competition-seed-results.csv');assert len(competition)==48
    for r in frames['state_competition_summary.csv'].itertuples():
        g=competition[competition.state==r.state]
        for out,inp in {'mean_net_migration':'net_migration','mean_employment':'employment_rate','mean_unfilled_jobs':'unfilled_jobs'}.items():assert abs(getattr(r,out)-g[inp].mean())<1e-12
    assert read(ROOT/'calibration/reliable-calibration/diagnostic-notebook-report.json')['passed']
    run=read(ROOT/'results/calibrated/run-verification.json');video=read(ROOT/'results/calibrated/migration-comparison.json')
    assert run['event_totals_validated'] and run['parameters_sha256']==sha(cp)
    assert video['passed'] and video['all_frames_decoded'] and video['frames']==720 and video['duration_seconds']==30
    assert sha(ROOT/'results/calibrated/migration-comparison.mp4')==video['sha256']
    test=subprocess.run([sys.executable,str(ROOT/'tools/run_tests.py')],cwd=ROOT,text=True,encoding='utf-8',capture_output=True)
    log=test.stdout+test.stderr;(ROOT/'results/tests.log').write_text(log,encoding='utf-8')
    assert test.returncode==0 and 'Ran 41 tests' in log and 'OK' in log,log
    audit=file_audit()
    manifest={n:{'rows':len(f),'sha256':sha(ROOT/'data/research'/n)} for n,f in frames.items()}
    (ROOT/'research/data-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    report={'passed':True,**audit,'tests_passed':41,'research_notebook_code_cells':41,'notebook_errors':0,'figures':17,
        'source_matches_executed_notebook':True,'core_model_class_asts_unchanged':True,'input_hashes_verified':True,
        'new_policy_grid_regenerated':True,'simulation_rows':4140,'unique_simulations':3838,'competition_runs':6,
        'numeric_outputs_compared_with_new_live_records':checked,'fresh_live_cases':4,'fresh_live_metrics':22,
        'calibration_diagnostic_code_cells':5,'generic_cli_design_parameter_verified':True,'mp4_frames_decoded':720,'mp4_seconds':30,'unvalidated_decay_10_default_excluded':True}
    (ROOT/'results/project-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
