# CITS4403 Group Project

An eight-state agent-based model of young-adult interstate migration, housing,
jobs and social attachment. States: CA, TX, NY, FL, MA, NC, IL and WA.

This complete project includes the published analysis, interactive migration
animation, a separately fitted parameter profile, full calibration records,
an executed validation Notebook, and an MP4 demonstration of the new profile.
Model class/function definitions retain the published V8 ASTs. Historical policy
results are explicitly labelled so they are not mistaken for new-fit results.

## Install and run the new profile

Use **Python 3.10.18**. From this directory on Windows:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-project.txt
.venv/Scripts/python.exe run_project.py --profile calibrated --video
```

On macOS/Linux use `.venv/bin/python` instead. An existing environment with the
pinned dependencies also works. The pinned `imageio-ffmpeg==0.6.0` package
supplies FFmpeg for `--video`. No environment or FFmpeg binary is committed.

Section 13 of `0914-1_v8.ipynb` re-runs four model cases live and checks them against the cached results (tolerance 1e-9).

The command executes five diagnostic Notebook cells in a real kernel, verifies
input hashes, runs baseline and intensity-1 combined policy using 600 agents,
12 years and seed 201, checks migration events against the independent metrics
entry point, exports an offline HTML animation, and renders/decodes every MP4
frame. Outputs:

- `results/calibrated/migration-animation.html`: playback, restart, year slider,
  speed and scenario controls; no external assets required.
- `results/calibrated/migration-comparison.mp4`: 30-second, 720p demonstration.
- `results/calibrated/migration-events.json` and `run-verification.json`: actual
  accepted moves, parameter SHA256 and resolved settings.
- `calibration/results/calibration-validation.ipynb` and `.html`: executed
  diagnostic Notebook with two live repeated cases and validation records.

Open `results/index.html` for video, animation and report links. Recorded events
are real simulator outputs; paths and within-year timing are illustrative.
Population labels include demographic replacement. A single demonstration
seed and its video do not estimate policy effects.

## What was fitted and checked

Registry: `calibration/reliable-calibration/parameters.json`.
Report: `calibration/results/reliable-calibration-report.html` (also Markdown).
The independently rebuilt ACS target is **3.87458%**:

| Design | Stay beta | Mean of 32 disjoint validation seeds |
|---|---:|---:|
| 1000 agents, 20 years | 3.8250 | 3.87094% |
| 600 agents, 12 years | 3.8200 | 3.87630% |

Both pass the declared simulation checks. These are conditional simulator fits,
not new real-world validation. The 1000x20 beta failed one expanded 600x12
transfer diagnostic; that failure is retained, and the 600x12 fit has a separate
training protocol and fresh validation seeds. Their bootstrap intervals overlap.
Other designs require checking.

Six route coefficients and seven destination effects are fitted to 50 verified
IRS routes with origin-group cross-validation. Historical IL/WA holdout RMSE
improves from 0.11559 to 0.09954; that holdout had already been seen during past
development. IRS tax-return routes are macro proxies, not young-adult-only data.
Rent/distance uncertainty remains wide. Priors, bounds and eight-origin scope
limit identification; these estimates are not causal effects.

Network decay 2/5 pass paired baseline checks. Decay 10 fails and is excluded
from defaults. Shared/scaled open-system attempt rates 0.0940/0.0678 pass checks
against the raw PUMS outside-eight-state origin share 0.6202649264. These are
simulator controls, not observed human migration probabilities. Social,
demographic and policy scenario coefficients remain assumptions.

## Repeat fitting and run individual cases

On Windows:

```powershell
calibration/Reproduce-Calibration.ps1
```

This refits IRS parameters, verifies/reuses compatible simulation checkpoints,
freshly repeats cases, runs four public CLI examples and executes the diagnostic
Notebook. Add `-Fresh` to back up checkpoints and actually recompute all
calibration and precision-control simulations. Use `-Python path/to/python.exe`
to select an existing interpreter. Full recomputation is substantially slower.
The individual Python scripts also run on other OSes; see
`calibration/WORKBENCH.md`. For one traced case:

```powershell
.venv/Scripts/python.exe calibration/run_reliable_case.py --case calibration/reliable-calibration/examples/baseline.json --output results/example-result.json
```

The workbench has immutable fixtures under `calibration/download/` and
`calibration/deployment/`. They pin the exact V8 inputs and recorded SHA256
checks; they are fixtures, not alternative deployments. The root model
definition ASTs have been compared with that snapshot. Reconstructed empirical
inputs and the official URL/hash source manifest are in `calibration/raw-rebuild/`.
The approximately 270MB PUMS downloads and virtual environment are not bundled.
The fitted pipeline uses the supplied verified numerical inputs. Rebuilding
them from microdata requires official downloads and the PUMS rebuild script.

## Published analysis and historical results

`0914-1_v8.ipynb` remains the **published profile**, stay beta=3.925, reading
the 29 original tables in `abm_outputs_research_plan_v7/`. Run all cells in a
Notebook editor from this directory. Its appended animation is that profile.
A live historical-profile animation can also be generated with:

```powershell
.venv/Scripts/python.exe run_project.py --profile published
```

`abm_data/` preserves original copies; `PROVENANCE.csv` records historical
recovery. The old three-row calibration's exact generation remains unresolved.
A historical static competition rule was subsequently recovered, but its cached
table contains state net migration only. The root Notebook now labels these
limits and corrects download behavior, the sweep endpoint and dependency name.

The CLI loader now extracts `EXTERNAL_ORIGIN_TARGET` from the Notebook, fixing
the previous open-system `NameError`. Network/open final calibration scalars
are rounded to four decimals after bisection, before simulation; iterations
retain full precision. Under the published profile, all 752 affected rows and
5,648 checked metrics match the original caches after this fix. Policy CSVs
are unchanged.

**The original 4140-row policy grid, inferential summaries and research figures
have not been rerun with new parameters.** The new animation/video are live
demonstrations only. Adopting the fit for policy conclusions requires rerunning
associated experiments and updating the report. `results/published/` preserves
the earlier video, separated from the new demonstration.

## Checks

```powershell
.venv/Scripts/python.exe -m unittest -v test_migration_animation
.venv/Scripts/python.exe calibration/verify_reliable_runner.py
.venv/Scripts/python.exe calibration/execute_calibration_notebook.py
```

`results/assembly-verification.json` records source commits, unchanged model ASTs
and the fitted parameter hash. Full protocols, seed lists, bootstrap results
and rejected candidates accompany the report. Repeat cases match exactly in
the pinned Windows environment; other numerical libraries require checking.

The standalone published-profile animation (`migration_animation.py`,
notebook section 14) was merged to `master` in #39 and is included here:

```powershell
.venv/Scripts/python.exe migration_animation.py --output migration_animation.html
```
