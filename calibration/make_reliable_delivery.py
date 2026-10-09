"""Export the fitted parameter registry, uncertainty report and diagnostic notebook."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import shutil
import sys
import zipfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mistune
import nbformat

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'reliable-calibration';RESULTS=ROOT/'results'
NAMES=['beta_income','beta_jobs','beta_rent','beta_distance','beta_education','beta_childcare']

def read(name):return json.loads((OUT/name).read_text(encoding='utf-8'))

def main():
    irs=read('irs-fit-report.json');beta=read('beta-fit-report.json');ext=read('extension-fit-report.json')
    precision=read('precision-fix-report.json');scale=read('extended-scale-report.json')
    research=read('research-design-fit-report.json')
    assert precision['passed'] and beta['deterministic_repeat_max_difference']==0 and ext['repeat_max_difference']==0
    theta=irs['chosen_theta'];target=beta['target'];oldparams=json.loads((ROOT/'raw-rebuild/kernel-with-legacy.json').read_text())['parameters']
    environment={'python':sys.version,**{name:importlib.metadata.version(name) for name in ['numpy','pandas','scipy','matplotlib','joblib','nbformat','nbclient','nbconvert','ipykernel','mistune']}}
    assert sys.version_info[:3]==(3,10,18)
    inputs=[ROOT/'raw-rebuild/state-inputs-reconstructed.csv',ROOT/'raw-rebuild/irs-routes-reconstructed.csv',
        ROOT/'raw-rebuild/rebuilt/acs_young_adult_interstate_move_rate.csv',ROOT/'raw-rebuild/rebuilt/pums_external_origin_competition.csv',
        ROOT/'download/CITS4403-GROUP-PROJECT-master/0914-1_v8.ipynb',ROOT/'deployment/master/0914-1_v8.ipynb',ROOT/'raw_model.py',ROOT/'reliable_worker.py']
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    shutil.copy2(ROOT/'raw-rebuild/source-manifest.json',OUT/'input-source-manifest.json')
    parameters={'schema_version':1,'profile':'new','state_codes':['CA','TX','NY','FL','MA','NC','IL','WA'],
        **dict(zip(NAMES,theta[:6])),'destination_effects':dict(zip(['CA','TX','NY','FL','MA','NC','IL','WA'],[0.]+theta[6:])),
        'beta_current_state':beta['chosen_beta'],
        'beta_by_design':{'1000x20':beta['chosen_beta'],**({'600x12':research['chosen_beta']} if research['validation_criteria_passed'] else {})},
        'design_validation':{'1000x20':beta['validation_criteria_passed'],'600x12':research['validation_criteria_passed']},
        'network_beta_by_decay':{'0.0':research['chosen_beta'],**{str(r['decay']):r['beta_current_state'] for r in ext['network'] if r['validation_criteria_passed']}},
        'external_rate_by_capacity':{r['capacity_mode']:r['external_rate'] for r in ext['open'] if r['validation_criteria_passed']},
        'external_origin_target':ext['external_origin_target'],'final_scalar_precision_decimals':4,
        'interaction_levels':{'weak':.6,'medium':1.,'strong':1.4},
        'fit_temperature':.85,'simulation_temperature':.90,
        'case_scope':{'core_calibration':{'policy':'baseline','interaction':'medium'},'network_calibration':{'agents':600,'years':12,'policy':'baseline','interaction':'medium'},'external_calibration':{'agents':600,'years':12,'policy':'baseline','intensity':0.,'interaction':'medium'}},
        'fixed_structural_assumptions':{k:v for k,v in oldparams.items() if k not in NAMES+['beta_current_state']},
        'provenance':{'irs_fit':'Origin-group CV of regularized route-share fitting; historical IL/WA holdout evaluated without retuning.',
            'stay_fit':'16 training seeds, 1000 agents x 20 years, staged grid, target independently rebuilt ACS rate.',
            'simulation_validation_seeds':list(range(1901,1933)),'network_fit':'Match closed-model rate at 600 agents x 12 years; controlled comparison.',
            'research_design_fit':'32 training seeds 901-932; fresh validation 3001-3032 after failed transfer diagnostic; separate conditional 600x12 beta.',
            'external_fit':'Match raw PUMS outside-eight-state origin share at 600 agents x 12 years.','source_sha256':hashes,'environment':environment},
        'limits':['Scenario, demographic, policy and social coefficients listed as fixed assumptions are not newly estimated.',
            'Design-specific beta values are validated separately. Other agent counts/horizons require calibration.',
            'Parameters are conditional on model, priors and aggregate data; not identified causal effects or precise individual behavior estimates.',
            'Research-wide policy CSVs are generated using the new profile in data/research. Historical tables are calibration controls only.']}

    fit15_path=ROOT.parent/'research/calibration-600x15/fit-report.json'
    if fit15_path.exists():
        fit15=json.loads(fit15_path.read_text())
        assert fit15['validation_criteria_passed']
        parameters['beta_by_design']['600x15']=fit15['chosen_beta']
        parameters['design_validation']['600x15']=True
        parameters['provenance']['research_15year_fit']='32 training seeds 901-932; independent validation 4001-4032; staged grid and 1000 seed bootstraps.'
    rebuild_path=ROOT.parent/'research/rebuild-report.json'
    rebuilt=json.loads(rebuild_path.read_text()) if rebuild_path.exists() else {'new_policy_grid_regenerated':False}
    parameters['research_results']={'directory':'data/research','simulation_rows':rebuilt.get('simulation_rows',0),
        'new_policy_grid_regenerated':rebuilt['new_policy_grid_regenerated'],'network_decay_10':'Failed-calibration diagnostic only; excluded from validated defaults.'}
    (OUT/'parameters.json').write_text(json.dumps(parameters,indent=2),encoding='utf-8')
    report=['# Fitted V8 parameters and reproducibility evidence',
        'The IRS route coefficients are fitted from aggregate data. Stay and entry-attempt parameters match empirical targets inside the specified simulator. Policy, social and demographic settings remain declared scenario assumptions; these are conditional model estimates, not causal policy estimates or uniquely identified individual preferences.',
        'All default research tables and figures now use the fitted profile. Historical caches exist only under calibration/deployment/master for control/provenance. The research rebuild includes 4,140 seed-level rows and six competition runs.',
        '## Inputs and route fitting',
        'The reconstructed inputs contain 88 state values and 50 IRS routes. IRS flows are tax-return counts, not specifically ages 18–35. The ACS anchor uses weighted PUMS observations at exactly ages 18–35. The PUMS external-origin composition retains Puerto Rico origins, whereas the overall move-rate anchor excludes them; see the source manifest for definitions and official URLs.',
        f"The regularized weighted route-share objective uses the original four-group mixture and parameter bounds. Analytic-gradient implementation differs from the original objective by at most {irs['original_objective_max_difference']:.3g}; its gradient check differs by at most {irs['gradient_max_difference']:.3g}.",
        f"Leave-one-training-origin-out CV compares penalty scales 0.25, 1 and 4. The one-standard-error rule selects {irs['selected_scale']}; coefficient penalty lambda={.02*irs['selected_scale']:.4g}, destination penalty lambda={.05*irs['selected_scale']:.4g}. The six training origins are CA, TX, NY, FL, MA and NC. IL/WA were historically inspected, so their holdout is diagnostic, not new external validation.",
        f"Historical holdout RMSE is {irs['heldout_evaluation']['cv_selected_training_fit']['weighted_rmse']:.6f} versus {irs['heldout_evaluation']['historical_regularization_refit']['weighted_rmse']:.6f} for a fresh default-penalty fit. Final theta is fitted on all eight origins after the selection rule. Same-start optimizer repeat maximum parameter difference: {irs['deterministic_optimizer_repeat_max_difference']}.",
        '## Utility coefficients',
        '| Parameter | Fitted value | Conditional bootstrap 2.5% | 97.5% |',
        '|---|---:|---:|---:|']
    comparison=[]
    for i,name in enumerate(NAMES):
        stability=irs['coefficient_stability'][name]
        report.append(f"| {name} | {theta[i]:.10g} | {stability['bootstrap_p025']:.6g} | {stability['bootstrap_p975']:.6g} |")
        comparison.append({'parameter':name,'old':oldparams[name],'new':theta[i],'p025':stability['bootstrap_p025'],'p975':stability['bootstrap_p975']})
    report+=['The 200 bootstrap samples resample complete origin groups, with only eight origins and fixed priors, bounds and regularization. Rent and distance are weakly constrained. Narrow intervals can partly reflect priors and bounds; they do not identify exact real-world coefficients.',
        'Destination effects use CA as the zero reference. The full-precision vector and all fixed assumptions are in parameters.json.',
        '## Design-specific stay calibration',
        f'ACS move-rate target: {target:.8%}. Selection uses training seeds only; independent validation seeds do not select beta. Training absolute-error tolerance is 0.05 percentage points. Validation tolerance is 0.10 percentage points and the 95% simulation mean interval must contain the target. These are prespecified numerical acceptance rules, not universal scientific reliability thresholds.',
        '| Design | Beta | Training seeds | Validation seeds | Validation mean | 95% simulation interval | Passed |',
        '|---|---:|---|---|---:|---|---|']
    designs=[('1000x20',beta,beta['validation_new'],'901-916','1901-1932'),('600x12',research,research['validation_new'],'901-932','3001-3032')]
    if fit15_path.exists():designs.append(('600x15',fit15,fit15['validation_new'],'901-932','4001-4032'))
    for design,fit,val,train_seeds,val_seeds in designs:
        report.append(f"| {design} | {fit['chosen_beta']:.4f} | {train_seeds} | {val_seeds} | {val['mean']:.6%} | {val['ci95_low']:.6%}–{val['ci95_high']:.6%} | {fit['validation_criteria_passed']} |")
        comparison.append({'parameter':'beta_current_state_'+design,'old':3.925,'new':fit['chosen_beta'],'p025':fit['beta_seed_bootstrap_p025'],'p975':fit['beta_seed_bootstrap_p975']})
    pd.DataFrame(comparison).to_csv(OUT/'parameter-comparison.csv',index=False)
    report+=['Beta seed-bootstrap intervals use 1,000 resamples of training seeds; they do not propagate IRS fit uncertainty or ACS sampling error. Four decimal places are an execution convention, not four-decimal statistical certainty.',
        f"The 3.8250 transfer to 600x12 failed on seeds 2001-2032 (mean {scale['mean']:.6%}, interval {scale['ci95_low']:.6%}–{scale['ci95_high']:.6%}). That failure is retained. A separate 600x12 calibration and new seeds 3001-3032 validate 3.8200. The same 3.8250 control also passes on those new seeds; overlap and simulation noise do not prove systematic human preference changes with agent count.",
        '## Network and open-system controls',
        '| Decay | Stay beta | Validation mean | Paired difference from closed baseline | Passed |',
        '|---|---:|---:|---:|---|']
    for r in ext['network']:
        report.append(f"| {r['decay']:g} | {r['beta_current_state']:.4f} | {r['validation']['mean']:.6%} | {r['validation_paired_difference']['mean']*100:.6f} percentage points | {r['validation_criteria_passed']} |")
    report+=['Decay 10 fails its paired validation and is excluded from validated defaults. It appears only as a labelled diagnostic. Unadjusted network changes are sensitivity scenarios. Recalibration keeps network comparisons on a common model-rate scale; it is not a new empirical estimate of social ties.',
        f"PUMS outside-eight-state origin target: {ext['external_origin_target']:.8%} (884486 / 1425981). Exchange attempts are conditional simulator control parameters, not real population move rates.",
        '| Capacity mode | Attempt rate | Validation external share | 95% simulation interval | Passed |',
        '|---|---:|---:|---|---|']
    for r in ext['open']:
        v=r['validation'];report.append(f"| {r['capacity_mode']} | {r['external_rate']:.4f} | {v['mean']:.6%} | {v['ci95_low']:.6%}–{v['ci95_high']:.6%} | {r['validation_criteria_passed']} |")
    report+=['Network/open controls use 600 agents and 12 years, training seeds 901-916 and validation seeds 3001-3032. Open validation requires mean bias at most 1.5 percentage points and a simulation interval covering the target. Scalar rounding occurs only after fitting, before simulation.',
        '## Historical precision control',
        f"A separate control preserves the original IRS fit and beta 3.9250. Final four-decimal rounding in network/open calibrations reproduces {precision['published_setting_rows']} historical rows, {precision['unique_simulations']} unique cases and {precision['numeric_metrics_checked']} metrics with {precision['mismatch_count']} mismatches. This resolves the numerical discrepancy, not the incomplete provenance of the old three-row beta table. The new report uses regenerated calibration tables instead.",
        '## Reproduction and limits',
        'Install the pinned root requirements-project.txt with Python 3.10.18. Reproduce-Calibration.ps1 -Fresh backs up simulator checkpoints and reruns calibration. research/calibrate_15y.py covers the additional horizon; research/build_research.py and research/summaries.py rebuild all research tables. Checkpoints reject changed input fingerprints. Source URLs, hashes, protocols, grids, bootstrap samples and seed-level observations are shipped.',
        'Simulation t intervals describe uncertainty in seed means conditional on inputs and mechanisms; they exclude survey sampling error, structural error and causal uncertainty. Model social utility has no complete common-year eight-state BRFSS validation. Tulsa cash incentives are a scale reference only. Scenario and policy effects are conditional simulations, not validated forecasts.',
        'See ../../results/research/research-executed.html for the complete freshly executed research report, and ../../research/rebuild-report.json for experiment counts.']
    md='\n\n'.join(report).replace('|\n\n|','|\n|')
    (OUT/'calibration-report.md').write_text(md,encoding='utf-8')
    RESULTS.mkdir(exist_ok=True)
    html=mistune.create_markdown(plugins=['table'])(md)
    style='body{max-width:1100px;margin:32px auto;padding:0 24px;font:16px/1.65 system-ui;color:#163340}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border:1px solid #bfd0d7;padding:8px;text-align:left}th{background:#edf5f6}img{max-width:100%}a{color:#006b75}'
    (RESULTS/'reliable-calibration-report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Fitted V8 calibration evidence</title><style>'+style+'</style><body>'+html+'</body></html>',encoding='utf-8')
    nb=nbformat.read(OUT/'calibration-validation.ipynb',as_version=4)
    nb.cells[0].source='# Fitted parameters: calibration and independent validation\n\nThis Notebook validates the fitted profile and does not reuse historical policy conclusions.'
    nb.cells[-1].source='The checks demonstrate conditional simulator fit and reproducible execution. Simulation intervals exclude survey sampling and structural uncertainty. All research policy tables are separately rerun in data/research.'
    for c in nb.cells:
        if c.cell_type=='code':c.outputs=[];c.execution_count=None
    nbformat.write(nb,OUT/'calibration-validation.ipynb')
    status={'parameters_exported':True,'training_passed':beta['training_criterion_passed'],
        'independent_simulation_validation_passed':beta['validation_criteria_passed'],'precision_752_rows_passed':precision['passed'],
        'research_design_validation_passed':research['validation_criteria_passed'],
        'research_15year_validation_passed':fit15['validation_criteria_passed'] if fit15_path.exists() else False,
        'network_validation_by_decay':{str(r['decay']):r['validation_criteria_passed'] for r in ext['network']},
        'open_validation_by_capacity':{r['capacity_mode']:r['validation_criteria_passed'] for r in ext['open']},
        'new_policy_grid_regenerated':rebuilt['new_policy_grid_regenerated'],'calibration_command_writes_git_remote':False,'environment':environment}
    (OUT/'delivery-status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    print('English calibration evidence and design-specific registry ready',flush=True)

if __name__=='__main__':main()
