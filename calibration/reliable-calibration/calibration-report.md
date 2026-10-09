# Fitted V8 parameters and reproducibility evidence

The IRS route coefficients are fitted from aggregate data. Stay and entry-attempt parameters match empirical targets inside the specified simulator. Policy, social and demographic settings remain declared scenario assumptions; these are conditional model estimates, not causal policy estimates or uniquely identified individual preferences.

All default research tables and figures now use the fitted profile. Historical caches exist only under calibration/deployment/master for control/provenance. The research rebuild includes 4,140 seed-level rows and six competition runs.

## Inputs and route fitting

The reconstructed inputs contain 88 state values and 50 IRS routes. IRS flows are tax-return counts, not specifically ages 18–35. The ACS anchor uses weighted PUMS observations at exactly ages 18–35. The PUMS external-origin composition retains Puerto Rico origins, whereas the overall move-rate anchor excludes them; see the source manifest for definitions and official URLs.

The regularized weighted route-share objective uses the original four-group mixture and parameter bounds. Analytic-gradient implementation differs from the original objective by at most 1.04e-17; its gradient check differs by at most 1.5e-12.

Leave-one-training-origin-out CV compares penalty scales 0.25, 1 and 4. The one-standard-error rule selects 0.25; coefficient penalty lambda=0.005, destination penalty lambda=0.0125. The six training origins are CA, TX, NY, FL, MA and NC. IL/WA were historically inspected, so their holdout is diagnostic, not new external validation.

Historical holdout RMSE is 0.099536 versus 0.115586 for a fresh default-penalty fit. Final theta is fitted on all eight origins after the selection rule. Same-start optimizer repeat maximum parameter difference: 0.0.

## Utility coefficients

| Parameter | Fitted value | Conditional bootstrap 2.5% | 97.5% |
|---|---:|---:|---:|
| beta_income | 1.077564579 | 0.830367 | 1.28723 |
| beta_jobs | 1.225962283 | 1.21581 | 1.24454 |
| beta_rent | 0.2510831381 | 0 | 0.702444 |
| beta_distance | 0.5990354282 | 0.222478 | 0.745299 |
| beta_education | 0.5022125559 | 0.439331 | 0.546431 |
| beta_childcare | 0.5271625085 | 0.500584 | 0.548231 |

The 200 bootstrap samples resample complete origin groups, with only eight origins and fixed priors, bounds and regularization. Rent and distance are weakly constrained. Narrow intervals can partly reflect priors and bounds; they do not identify exact real-world coefficients.

Destination effects use CA as the zero reference. The full-precision vector and all fixed assumptions are in parameters.json.

## Design-specific stay calibration

ACS move-rate target: 3.87457657%. Selection uses training seeds only; independent validation seeds do not select beta. Training absolute-error tolerance is 0.05 percentage points. Validation tolerance is 0.10 percentage points and the 95% simulation mean interval must contain the target. These are prespecified numerical acceptance rules, not universal scientific reliability thresholds.

| Design | Beta | Training seeds | Validation seeds | Validation mean | 95% simulation interval | Passed |
|---|---:|---|---|---:|---|---|
| 1000x20 | 3.8250 | 901-916 | 1901-1932 | 3.870938% | 3.813597%–3.928278% | True |
| 600x12 | 3.8200 | 901-932 | 3001-3032 | 3.876302% | 3.775482%–3.977123% | True |
| 600x15 | 3.8200 | 901-932 | 4001-4032 | 3.869792% | 3.794014%–3.945570% | True |

Beta seed-bootstrap intervals use 1,000 resamples of training seeds; they do not propagate IRS fit uncertainty or ACS sampling error. Four decimal places are an execution convention, not four-decimal statistical certainty.

The 3.8250 transfer to 600x12 failed on seeds 2001-2032 (mean 3.757378%, interval 3.665652%–3.849105%). That failure is retained. A separate 600x12 calibration and new seeds 3001-3032 validate 3.8200. The same 3.8250 control also passes on those new seeds; overlap and simulation noise do not prove systematic human preference changes with agent count.

## Network and open-system controls

| Decay | Stay beta | Validation mean | Paired difference from closed baseline | Passed |
|---|---:|---:|---:|---|
| 2 | 3.5980 | 3.903212% | 0.026910 percentage points | True |
| 5 | 3.3125 | 3.907552% | 0.031250 percentage points | True |
| 10 | 3.0678 | 4.009549% | 0.133247 percentage points | False |

Decay 10 fails its paired validation and is excluded from validated defaults. It appears only as a labelled diagnostic. Unadjusted network changes are sensitivity scenarios. Recalibration keeps network comparisons on a common model-rate scale; it is not a new empirical estimate of social ties.

PUMS outside-eight-state origin target: 62.02649264% (884486 / 1425981). Exchange attempts are conditional simulator control parameters, not real population move rates.

| Capacity mode | Attempt rate | Validation external share | 95% simulation interval | Passed |
|---|---:|---:|---|---|
| shared | 0.0940 | 61.924251% | 61.322639%–62.525864% | True |
| scaled | 0.0678 | 61.900124% | 61.286174%–62.514074% | True |

Network/open controls use 600 agents and 12 years, training seeds 901-916 and validation seeds 3001-3032. Open validation requires mean bias at most 1.5 percentage points and a simulation interval covering the target. Scalar rounding occurs only after fitting, before simulation.

## Historical precision control

A separate control preserves the original IRS fit and beta 3.9250. Final four-decimal rounding in network/open calibrations reproduces 752 historical rows, 704 unique cases and 5648 metrics with 0 mismatches. This resolves the numerical discrepancy, not the incomplete provenance of the old three-row beta table. The new report uses regenerated calibration tables instead.

## Reproduction and limits

Install the pinned root requirements-project.txt with Python 3.10.18. Reproduce-Calibration.ps1 -Fresh backs up simulator checkpoints and reruns calibration. research/calibrate_15y.py covers the additional horizon; research/build_research.py and research/summaries.py rebuild all research tables. Checkpoints reject changed input fingerprints. Source URLs, hashes, protocols, grids, bootstrap samples and seed-level observations are shipped.

Simulation t intervals describe uncertainty in seed means conditional on inputs and mechanisms; they exclude survey sampling error, structural error and causal uncertainty. Model social utility has no complete common-year eight-state BRFSS validation. Tulsa cash incentives are a scale reference only. Scenario and policy effects are conditional simulations, not validated forecasts.

See ../../results/research/research-executed.html for the complete freshly executed research report, and ../../research/rebuild-report.json for experiment counts.