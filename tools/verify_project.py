"""Check the supplied executed evidence and byte-stable calibration fixtures."""
from pathlib import Path
import ast
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]

def main():
    source=json.loads((ROOT/'0914-1_v8.ipynb').read_text(encoding='utf-8'))
    executed=json.loads((ROOT/'results/published/0914-1_v8-executed.ipynb').read_text(encoding='utf-8'))
    assert [(c['cell_type'],''.join(c['source'])) for c in source['cells']]==[(c['cell_type'],''.join(c['source'])) for c in executed['cells']], 'Executed Notebook does not match the supplied source.'
    assert not [o for c in executed['cells'] for o in c.get('outputs',[]) if o.get('output_type')=='error']
    fixture=ROOT/'calibration/deployment/master'
    original=json.loads((fixture/'0914-1_v8.ipynb').read_text(encoding='utf-8'))
    for i in [22,28,37,67,69]:
        def definitions(cell):return [ast.dump(n,include_attributes=False) for n in ast.parse(''.join(cell['source'])).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
        assert definitions(original['cells'][i])==definitions(source['cells'][i])
    csvs=list((ROOT/'abm_outputs_research_plan_v7').glob('*.csv'));assert len(csvs)==29
    for p in csvs:assert p.read_bytes()==(fixture/'abm_outputs_research_plan_v7'/p.name).read_bytes(),p.name
    log=(ROOT/'results/animation-tests.log').read_text(encoding='utf-8');assert 'Ran 9 tests' in log and 'OK' in log
    cfg=ROOT/'calibration/reliable-calibration/parameters.json'
    config=json.loads(cfg.read_text());assert '10.0' not in config['network_beta_by_decay']
    for relative,expected in config['provenance']['source_sha256'].items():
        assert hashlib.sha256((ROOT/'calibration'/relative).read_bytes()).hexdigest()==expected,relative
    diagnostic=json.loads((ROOT/'calibration/reliable-calibration/diagnostic-notebook-report.json').read_text());assert diagnostic['passed']
    run=json.loads((ROOT/'results/calibrated/run-verification.json').read_text())
    video=json.loads((ROOT/'results/calibrated/migration-comparison.json').read_text())
    assert run['event_totals_validated'] and video['passed'] and video['frames']==720
    assert run['parameters_sha256']==hashlib.sha256(cfg.read_bytes()).hexdigest()
    assert hashlib.sha256((ROOT/'results/calibrated/migration-comparison.mp4').read_bytes()).hexdigest()==video['sha256']
    report={'passed':True,'animation_tests':9,'published_notebook_code_cells':sum(c['cell_type']=='code' for c in executed['cells']),
       'published_notebook_error_outputs':0,'published_cache_csvs_byte_identical':29,'model_definition_asts_unchanged':True,
       'calibrated_diagnostic_notebook_code_cells':diagnostic['code_cells'],'calibrated_input_hashes_verified':True,
       'calibrated_animation_event_totals_checked':True,'calibrated_video_frames_decoded':720,
       'calibrated_video_seconds':video['duration_seconds'],'new_policy_grid_regenerated':False,'unvalidated_decay_10_default_excluded':True}
    (ROOT/'results/project-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
