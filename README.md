# CITS4403 Group Project

Young-adult interstate migration: policy incentives, social networks and capacity feedback.

A spatial agent-based model (ABM) of 18-35 year-olds moving between eight US states
(CA, TX, NY, FL, MA, NC, IL, WA). The core question:

> How strong must a geographically targeted housing-and-employment policy be to overcome
> young adults' social attachment, and when do migration chains and local capacity
> constraints amplify or offset that response?

## How to run

1. Install Python 3.10 and the dependencies:

   ```
   pip install -r requirements.txt jupyter
   ```

2. Open `0914-1_v8.ipynb` from inside this folder and choose **Run All**. A full run takes about 30 seconds.

The notebook reads its data from `abm_outputs_research_plan_v7/`. Keep that folder name and keep it next to the notebook. The path is hard-coded in cell 14:

```python
RESULT_CACHE = Path("abm_outputs_research_plan_v7")
```

Section 13 re-runs four model cases live and checks them against the cached results. The tolerance is 1e-9.

## Contents

| Path | Description |
|---|---|
| `0914-1_v8.ipynb` | The main notebook. All model code lives here (`PolicySocialABM` in cell 22); saved outputs are kept |
| `abm_outputs_research_plan_v7/` | All 29 CSV files the notebook needs |
| `abm_data/` | The 4 CSV files that survived in the original cache. They are identical copies of files already in `abm_outputs_research_plan_v7/`, and the notebook does not use this folder |
| `PROVENANCE.csv` | Source, run settings and verification result for every CSV |
| `rebuild_scripts/` | Scripts used to rebuild the CSVs. They load the model code from the v8 notebook directly (see below) |
| `requirements.txt` | Package versions from the original author's environment |

## Where the data come from

The original cache folder held only 4 of the 29 CSV files; the other 25 were lost. They were restored as follows. `PROVENANCE.csv` gives the details for each file.

- **Real data (4 files).** The ACS files were recomputed from the 2023 ACS 1-year PUMS microdata. They match the outputs saved in v8 exactly.
- **Re-simulated (17 files).** These were re-run with the model code in the v8 notebook. The original agent counts, horizons and random seeds were recovered by matching the saved outputs, and every printed digit matches.
- **Rebuilt from v8's printed output (4 files).** These are entered from the values the notebook printed, not simulated:
  - `move_rate_calibration.csv` was produced by an earlier model build and cannot be reproduced with v8 code.
  - `state_competition_summary.csv` cannot be re-simulated because its incentive formula is not in v8.
  - The two BRFSS tables.
- **Original files (4 files).** These are unchanged: the intensity sweeps, network decay and open system results.

## Differences from the saved notebook output

All numbers match the outputs saved in the original notebook. Only these display details differ:

- **Cell 32 (power table).** It shows extra NaN rows, and seed counts appear as `53.0` instead of `53`. This is because the notebook reads `paired_policy_effects.csv` both as a summary table and as per-seed data, so the file has to hold both blocks.
- **Wide tables.** Some wrap at different column positions.
- **Section 13 verification cell.** It reports a different file count and different modification times.
- **Cell 14.** It also displays the by-state and by-age ACS tables.
- **Cell 22.** `PolicySocialABM` and some of its methods carry docstrings; the code is unchanged.

## Rebuild scripts and data provenance

`PROVENANCE.csv` records the source, settings and limitations of all 29 cached CSVs. `abm_data/` preserves four byte-identical copies of the original cache files; it is unused by the notebook. The notebook reads `abm_outputs_research_plan_v7/` instead.

From the repository root, run `python rebuild_scripts/worker.py '{"policy":"combined","seed":201}'` (adjust quoting for your shell). From `rebuild_scripts/`, `import worker; worker.run({"policy": "combined", "seed": 201})` works as well. For a batch, use `python rebuild_scripts/batch.py cases.json results.pkl --jobs 2`; `cases.json` is a list of case objects.

To recompute the empirical anchor from locally downloaded Census 2023 1-year person ZIPs, use `python rebuild_scripts/acs_pums.py path/to/pums`. The script documents ZIP names, filters and the Puerto Rico scope distinction. No full empirical rebuild is claimed without those source ZIPs.
## Interactive migration animation

Run section 14 at the end of `0914-1_v8.ipynb`. It displays an interactive replay and exports `migration_animation.html`. Trust the notebook to enable JavaScript in its embedded frame, or open the exported HTML directly in a modern browser. The export works offline; no new packages, map service, or external assets are needed.

Use **Play / Pause**, **Restart**, the year slider and the speed selector (0.5–4×). Switch between **No policy** and **Combined policy · intensity 1**. Both use 600 agents, 12 years, seed 201, medium interaction strength, and the notebook's existing calibrated parameters and policy function. The map shows accepted moves, social-chain moves, annual route totals, target-state inflow and end-year state population.

One dot is one recorded accepted agent move, including each member of a moving household. Route totals are validated against the model's annual inflow/outflow and move rate. The model has annual time steps: within-year ordering, travel paths and timing are illustrative. End-year populations also include demographic replacement. The animation runs two additional model instances without changing the model or the preceding analysis.

To export without opening Jupyter, run from the repository root:

```sh
python migration_animation.py --output migration_animation.html
```

For a smaller demonstration, add `--agents 100 --years 3 --seed 201`. The loader executes the existing notebook definitions and reads the supplied CSV cache. Keep `migration_animation.py`, `migration_animation_template.html` and the notebook together. The generated HTML needs no supporting files.

Run the animation tests with the existing requirements installed:

```sh
python -m unittest -v test_migration_animation
```
