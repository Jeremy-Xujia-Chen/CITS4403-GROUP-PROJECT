# Young-adult interstate migration: fitted V8

An eight-state agent-based research model of migration, social ties, policy incentives, housing capacity and employment. The current research report, all 4,140 experiment rows, derived tables and figures use the new IRS fit and independently validated, design-specific stay parameters. The six static state-competition runs also use the fitted profile.

## Run locally

Use Python 3.10.18 and the pinned dependencies:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-project.txt
.venv/Scripts/python.exe tools/run_tests.py
.venv/Scripts/python.exe tools/verify_project.py
.venv/Scripts/python.exe run_project.py --profile calibrated --skip-notebook --video
```

Open `results/calibrated/migration-animation.html` for the self-contained animation and `results/calibrated/migration-comparison.mp4` for the decoded video. Replay dots represent accepted model moves; within-year timing and travel paths are illustrative.

The complete executed research report is `results/research/research-executed.html`; its editable source is `0914-1_v8.ipynb`. Open `results/index.html` for links to the main evidence.

## Reproduce research results

```powershell
.venv/Scripts/python.exe research/build_research.py --jobs 8
.venv/Scripts/python.exe research/summaries.py
.venv/Scripts/python.exe research/render_notebook.py
```

The shipped checkpoint contains actual newly simulated cases and input fingerprints. To force a complete simulator rerun, move `research/live-simulations.jsonl` to a backup, then run the commands above. This computes 3,838 unique model cases, represented by 4,140 experiment rows plus six competition runs. Shared cases are deduplicated; no historical simulation cache supplies the new metrics.

Parameter and source hashes are in `calibration/reliable-calibration/parameters.json`. The baseline design (1,000 agents, 20 years) uses beta 3.8250. Policy designs (600 agents, 12 years) and shock/entrant designs (600 agents, 15 years) use separately validated beta 3.8200. Decay 2 and 5 have validated conditional recalibrations; the failed decay-10 candidate is a labelled diagnostic, excluded from validated defaults. Open entry-attempt rates are 0.0940 (shared capacity) and 0.0678 (scaled capacity), with exact PUMS composition target 0.6202649263910248.

## Reproduce parameter fitting

```powershell
powershell -File calibration/Reproduce-Calibration.ps1 -Fresh -Python .venv/Scripts/python.exe
.venv/Scripts/python.exe research/calibrate_15y.py
```

`-Fresh` backs up simulator checkpoints before rerunning. Research 15-year checkpoints can likewise be backed up to force recomputation. Calibration rejects mismatched source fingerprints. See `calibration/reliable-calibration/calibration-report.md` for methods, training/validation seeds, conditional bootstrap uncertainty and retained failures, and `calibration/raw-rebuild/source-manifest.json` for official source URLs and hashes.

Large original PUMS downloads and virtual environments are excluded from the project. The verified numeric input reconstructions and source manifest are included. A fresh remote raw-data extraction requires downloading the cited original sources; packaged simulation reconstruction does not require network access.

## Interpretation

IRS coefficients fit aggregate route shares, not causal individual preferences. Stay and entry-attempt rates are simulator calibration controls. Social, policy and demographic coefficients are declared structural/scenario assumptions. Simulation seed intervals exclude survey sampling and structural uncertainty. The social utility index is an internal diagnostic; no complete common-year eight-state BRFSS welfare validation is claimed. Tulsa cash payments provide an external scale reference only.

Historical data are retained under `calibration/deployment/master` solely as provenance and precision-control fixtures. The old three-row stay-calibration table has incomplete generation history; it is not the source of the new default parameters. The historical 752-row network/open precision control matches after final four-decimal rounding.

See [repository map](docs/REPOSITORY.md). PR #47 contains no PPT/PPTX file, so no presentation change is asserted.
