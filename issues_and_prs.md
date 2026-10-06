# Member B: issues and PRs (copy-paste ready)

Create each issue and PR by hand on github.com (no `gh`/API). Merge into `master` in global order; PR-n depends on PR-(n-1).

My tasks: PR-02, PR-03, PR-05, PR-07, PR-09, PR-11, PR-13, PR-15, PR-17, PR-19

---

## 02 - Empirical state inputs for the eight modelled states  (Member B)

### Issue #2: Empirical state inputs for the eight modelled states

**Assignee:** Member B  
**Labels:** notebook, member-B  
**Notebook cells:** 3-5

**Background**

Every simulation needs the same eight-state table (CA, TX, NY, FL, MA, NC, IL, WA) describing population, housing, jobs and income. This is Section 1 of the notebook and the data foundation for all later sections.

**Tasks**
- [ ] Add the Section 1 heading and `build_real_state_snapshot()` (cell 4)
- [ ] Add `mean_index` and `prepare_state_data()` (cell 5) that turn the raw snapshot into the `state_data` table
- [ ] Print or display the resulting table so reviewers can see the inputs

**Files**
- `0914-1_v8.ipynb` (cells 3-5)

**Out of scope**

Spatial coordinates, IRS routes and calibration (PR-03, PR-04).

**Acceptance criteria**
- [ ] `state_data` has one row per state with every column later sections read
- [ ] Index helpers give sensible values on the 8-state table
- [ ] Cells run on top of PR-01

**Dependencies**

Blocked by PR-01. PRs are merged strictly in order because the notebook is a single JSON file.

### PR-02: `state-inputs`

**Title:** Empirical state inputs for the eight modelled states  
**Base:** `master`

**Description** (paste into the PR body)

````markdown
## Summary

Every simulation needs the same eight-state table (CA, TX, NY, FL, MA, NC, IL, WA) describing population, housing, jobs and income. This is Section 1 of the notebook and the data foundation for all later sections.

Closes #2

## What's included
- Add the Section 1 heading and `build_real_state_snapshot()` (cell 4)
- Add `mean_index` and `prepare_state_data()` (cell 5) that turn the raw snapshot into the `state_data` table
- Print or display the resulting table so reviewers can see the inputs

## Files
- `0914-1_v8.ipynb` (cells 3-5)

## How to verify
1. Run cells 0-5 top to bottom
2. Check that `state_data` has 8 rows, one per state code

## Notes for reviewers

- Out of scope: Spatial coordinates, IRS routes and calibration (PR-03, PR-04).
- Depends on PR-01; rebase on `master` after it is merged.
- Cells are copied unchanged from the reference notebook (outputs kept); no numbers or model behaviour are altered.
````

---


## 03 - Spatial environment: coordinates, distances and IRS routes  (Member B)

### Issue #3: Spatial environment: coordinates, distances and IRS routes

**Assignee:** Member B  
**Labels:** notebook, member-B  
**Notebook cells:** 6-8

**Background**

Destination choice in the model depends on distance and on observed IRS migration routes. This PR adds the geographic inputs and the route table that the destination-attractiveness calibration (PR-04) is fitted to.

**Tasks**
- [ ] Add the Section 2 heading
- [ ] Add `STATE_COORDS` and `haversine_km` (cell 7) and compute pairwise distances between the eight states
- [ ] Add the `IRS_ROUTES` table (cell 8) of observed interstate routes

**Files**
- `0914-1_v8.ipynb` (cells 6-8)

**Out of scope**

The calibration itself and the map (PR-04).

**Acceptance criteria**
- [ ] Pairwise distance matrix is computed for all 8 states
- [ ] `IRS_ROUTES` loads and only references modelled states
- [ ] Cells run on top of PR-02

**Dependencies**

Blocked by PR-02. PRs are merged strictly in order because the notebook is a single JSON file.

### PR-03: `spatial-environment`

**Title:** Spatial environment: coordinates, distances and IRS routes  
**Base:** `master`

**Description** (paste into the PR body)

````markdown
## Summary

Destination choice in the model depends on distance and on observed IRS migration routes. This PR adds the geographic inputs and the route table that the destination-attractiveness calibration (PR-04) is fitted to.

Closes #3

## What's included
- Add the Section 2 heading
- Add `STATE_COORDS` and `haversine_km` (cell 7) and compute pairwise distances between the eight states
- Add the `IRS_ROUTES` table (cell 8) of observed interstate routes

## Files
- `0914-1_v8.ipynb` (cells 6-8)

## How to verify
1. Run cells 0-8 top to bottom
2. Spot-check a few pairwise distances for plausibility (coast to coast should be several thousand km)

## Notes for reviewers

- Out of scope: The calibration itself and the map (PR-04).
- Depends on PR-02; rebase on `master` after it is merged.
- Cells are copied unchanged from the reference notebook (outputs kept); no numbers or model behaviour are altered.
````

---


## 05 - ACS PUMS move-rate anchor and external-origin scope audit  (Member B)

### Issue #5: ACS PUMS move-rate anchor and external-origin scope audit

**Assignee:** Member B  
**Labels:** notebook, member-B  
**Notebook cells:** 13-16

**Background**

The overall yearly interstate move rate of 18-35 year-olds is the empirical target the model is calibrated to. It comes from the 2023 ACS 1-year PUMS person files for the eight states, computed once and stored as CSVs.

The main model covers only eight states. To show how much that closed-system choice leaves out, this diagnostic measures the share of 2023 interstate in-movers to the eight states who previously lived elsewhere (about 62%). It motivates the open-system check in PR-18.

**Tasks**
- [ ] Add Section 3 text and the loader cell: read the three ACS CSVs from `abm_outputs_research_plan_v7/` (path hard-coded as `RESULT_CACHE`) and set `MOVE_RATE_TARGET`
- [ ] Add the three ACS CSVs
- [ ] Add `rebuild_scripts/acs_pums.py`, the script that recomputes the ACS numbers from the PUMS person ZIPs (ages 18-35, `MIG==3`, `MIGSP` 1-56 and different from current state)
- [ ] Add Section 3.1 text explaining this is a scope diagnostic, not a calibrated destination model
- [ ] Add the cell that reads `pums_external_origin_competition.csv` and builds `EXTERNAL_ORIGIN_SHARE`
- [ ] Add the CSV

**Files**
- `0914-1_v8.ipynb` (cells 13-16)
- `abm_outputs_research_plan_v7/acs_young_adult_interstate_move_rate.csv`
- `abm_outputs_research_plan_v7/acs_young_adult_interstate_move_rate_by_state.csv`
- `abm_outputs_research_plan_v7/acs_young_adult_interstate_move_rate_by_age.csv`
- `rebuild_scripts/acs_pums.py`
- `abm_outputs_research_plan_v7/pums_external_origin_competition.csv`

**Out of scope**

Any simulation of outside movers (PR-18).

**Acceptance criteria**
- [ ] `MOVE_RATE_TARGET` is read from the CSV, not hard-coded
- [ ] By-state and by-age tables load without error
- [ ] `acs_pums.py` documents its input ZIP names and filters
- [ ] The external-origin share is printed and matches the CSV
- [ ] Wording makes clear this is a diagnostic only
- [ ] Cells run on top of PR-04

**Dependencies**

Blocked by PR-04. PRs are merged strictly in order because the notebook is a single JSON file.

### PR-05: `acs-anchor-and-origin-audit`

**Title:** ACS PUMS move-rate anchor and external-origin scope audit  
**Base:** `master`

**Description** (paste into the PR body)

````markdown
## Summary

The overall yearly interstate move rate of 18-35 year-olds is the empirical target the model is calibrated to. It comes from the 2023 ACS 1-year PUMS person files for the eight states, computed once and stored as CSVs.

The main model covers only eight states. To show how much that closed-system choice leaves out, this diagnostic measures the share of 2023 interstate in-movers to the eight states who previously lived elsewhere (about 62%). It motivates the open-system check in PR-18.

Closes #5

## What's included
- Add Section 3 text and the loader cell: read the three ACS CSVs from `abm_outputs_research_plan_v7/` (path hard-coded as `RESULT_CACHE`) and set `MOVE_RATE_TARGET`
- Add the three ACS CSVs
- Add `rebuild_scripts/acs_pums.py`, the script that recomputes the ACS numbers from the PUMS person ZIPs (ages 18-35, `MIG==3`, `MIGSP` 1-56 and different from current state)
- Add Section 3.1 text explaining this is a scope diagnostic, not a calibrated destination model
- Add the cell that reads `pums_external_origin_competition.csv` and builds `EXTERNAL_ORIGIN_SHARE`
- Add the CSV

## Files
- `0914-1_v8.ipynb` (cells 13-16)
- `abm_outputs_research_plan_v7/acs_young_adult_interstate_move_rate.csv`
- `abm_outputs_research_plan_v7/acs_young_adult_interstate_move_rate_by_state.csv`
- `abm_outputs_research_plan_v7/acs_young_adult_interstate_move_rate_by_age.csv`
- `rebuild_scripts/acs_pums.py`
- `abm_outputs_research_plan_v7/pums_external_origin_competition.csv`

## How to verify
1. Run cells 0-16 top to bottom
2. Run the notebook up to cell 14 from the repository root
3. Print `MOVE_RATE_TARGET` and compare with the reference notebook
4. Run the notebook through cell 16
5. Check the printed share is about 0.62

## Notes for reviewers

- Out of scope: Any simulation of outside movers (PR-18).
- Depends on PR-04; rebase on `master` after it is merged.
- Cells are copied unchanged from the reference notebook (outputs kept); no numbers or model behaviour are altered.
- Combines former plan items 05 and 06 after the team shrank to two members.
````

---

## 07 - PolicySocialABM part 1: class skeleton, shocks and household steps  (Member B)

### Issue #7: PolicySocialABM part 1: class skeleton, shocks and household steps

**Assignee:** Member B  
**Labels:** notebook, member-B  
**Notebook cells:** 21-22 (first part)

**Background**

`PolicySocialABM` is the heart of the project (about 720 lines in one cell). It is added in three PRs so each can be reviewed. This first part gives the class its constructor, deterministic randomness and the household and family steps.

**Tasks**
- [ ] Add the Section 6 description (cell 21)
- [ ] Add the start of cell 22: `__init__`, `_rng`, `_counts`, `_state_indices`, `_home_indices`, `_shock_factors`, `_household_formation_step`, `_family_step`
- [ ] Cut cell 22 at a method boundary so the notebook still parses; PR-08 and PR-09 extend the same cell

**Files**
- `0914-1_v8.ipynb` (cells 21-22 (first part))

**Out of scope**

Rewiring, demography, utility and the migration step (PR-08, PR-09).

**Acceptance criteria**
- [ ] The class can be instantiated with `state_data` and a policy table
- [ ] Household and family steps run without error
- [ ] Per-agent, per-year randomness is deterministic for a given seed
- [ ] Cells run on top of PR-06

**Dependencies**

Blocked by PR-06. PRs are merged strictly in order because the notebook is a single JSON file.

### PR-07: `abm-core-part1`

**Title:** PolicySocialABM part 1: class skeleton, shocks and household steps  
**Base:** `master`

**Description** (paste into the PR body)

````markdown
## Summary

`PolicySocialABM` is the heart of the project (about 720 lines in one cell). It is added in three PRs so each can be reviewed. This first part gives the class its constructor, deterministic randomness and the household and family steps.

Closes #7

## What's included
- Add the Section 6 description (cell 21)
- Add the start of cell 22: `__init__`, `_rng`, `_counts`, `_state_indices`, `_home_indices`, `_shock_factors`, `_household_formation_step`, `_family_step`
- Cut cell 22 at a method boundary so the notebook still parses; PR-08 and PR-09 extend the same cell

## Files
- `0914-1_v8.ipynb` (cells 21-22 (first part))

## How to verify
1. Run cells 0-22 top to bottom
2. Instantiate `PolicySocialABM` and call the household and family steps for a few years

## Notes for reviewers

- Out of scope: Rewiring, demography, utility and the migration step (PR-08, PR-09).
- Depends on PR-06; rebase on `master` after it is merged.
- Cells are copied unchanged from the reference notebook (outputs kept); no numbers or model behaviour are altered.
````

---

## 09 - PolicySocialABM part 3: migration step, mechanisms and run loop  (Member B)

### Issue #9: PolicySocialABM part 3: migration step, mechanisms and run loop

**Assignee:** Member B  
**Labels:** notebook, member-B  
**Notebook cells:** 22 (complete)

**Background**

The last third of the class: the yearly migration decision with housing and job rationing, rent feedback, mechanism bookkeeping and the run loop. After this PR the model can be run end to end.

**Tasks**
- [ ] Complete cell 22 with `_migration_step` (proposed vs accepted moves, soft capacity, rent response)
- [ ] Add `mechanism_history` and `run`
- [ ] Replace the shorter cell 22 from PR-08 with the full cell

**Files**
- `0914-1_v8.ipynb` (cells 22 (complete))

**Out of scope**

Calibrating the stay preference (PR-10).

**Acceptance criteria**
- [ ] A 1000-agent, 20-year run completes and returns history, moves and mechanism data
- [ ] The same seed gives identical results on re-run
- [ ] Cell 22 matches the reference cell
- [ ] Cells run on top of PR-08

**Dependencies**

Blocked by PR-08. PRs are merged strictly in order because the notebook is a single JSON file.

### PR-09: `abm-core-part3`

**Title:** PolicySocialABM part 3: migration step, mechanisms and run loop  
**Base:** `master`

**Description** (paste into the PR body)

````markdown
## Summary

The last third of the class: the yearly migration decision with housing and job rationing, rent feedback, mechanism bookkeeping and the run loop. After this PR the model can be run end to end.

Closes #9

## What's included
- Complete cell 22 with `_migration_step` (proposed vs accepted moves, soft capacity, rent response)
- Add `mechanism_history` and `run`
- Replace the shorter cell 22 from PR-08 with the full cell

## Files
- `0914-1_v8.ipynb` (cells 22 (complete))

## How to verify
1. Run cells 0-22 top to bottom
2. Run the full class once with the default `PARAMS`
3. Run it twice with one seed and compare the histories

## Notes for reviewers

- Out of scope: Calibrating the stay preference (PR-10).
- Depends on PR-08; rebase on `master` after it is merged.
- Cells are copied unchanged from the reference notebook (outputs kept); no numbers or model behaviour are altered.
````

---

## 11 - Paired interaction test, power check and plots  (Member B)

### Issue #11: Paired interaction test, power check and plots

**Assignee:** Member B  
**Labels:** notebook, member-B  
**Notebook cells:** 29-34

**Background**

Separate simulations cannot show whether ties change the policy effect. This PR compares each seed with and without policy, tests strong-minus-weak differences, checks whether non-significant results are informative, and draws the evidence.

**Tasks**
- [ ] Add the paired policy-effect and interaction test (cell 30)
- [ ] Add `power_summary` (cell 32): minimum detectable effect at 80% power and seeds needed
- [ ] Add the forest plot and the policy x tie heatmap (cell 34)
- [ ] Add both CSVs

**Files**
- `0914-1_v8.ipynb` (cells 29-34)
- `abm_outputs_research_plan_v7/paired_policy_effects.csv`
- `abm_outputs_research_plan_v7/interaction_modification.csv`

**Out of scope**

Intensity sweeps (PR-12).

**Acceptance criteria**
- [ ] Interaction effects with 95% t intervals are shown
- [ ] The power table reports minimum detectable effect and seeds needed
- [ ] The forest plot and heatmap render
- [ ] Cells run on top of PR-10

**Dependencies**

Blocked by PR-10. PRs are merged strictly in order because the notebook is a single JSON file.

### PR-11: `interaction-power-plots`

**Title:** Paired interaction test, power check and plots  
**Base:** `master`

**Description** (paste into the PR body)

````markdown
## Summary

Separate simulations cannot show whether ties change the policy effect. This PR compares each seed with and without policy, tests strong-minus-weak differences, checks whether non-significant results are informative, and draws the evidence.

Closes #11

## What's included
- Add the paired policy-effect and interaction test (cell 30)
- Add `power_summary` (cell 32): minimum detectable effect at 80% power and seeds needed
- Add the forest plot and the policy x tie heatmap (cell 34)
- Add both CSVs

## Files
- `0914-1_v8.ipynb` (cells 29-34)
- `abm_outputs_research_plan_v7/paired_policy_effects.csv`
- `abm_outputs_research_plan_v7/interaction_modification.csv`

## How to verify
1. Run cells 0-34 top to bottom
2. Run the notebook through cell 34
3. Compare the printed tables and figures with the reference outputs

## Notes for reviewers

- Out of scope: Intensity sweeps (PR-12).
- Depends on PR-10; rebase on `master` after it is merged.
- Cells are copied unchanged from the reference notebook (outputs kept); no numbers or model behaviour are altered.
````

---

## 13 - Tulsa reference and Hill saturation fit  (Member B)

### Issue #13: Tulsa reference and Hill saturation fit

**Assignee:** Member B  
**Labels:** notebook, member-B  
**Notebook cells:** 40-43

**Background**

A finite grid cannot show where a response levels off. A Hill saturation curve estimates the ceiling, and a reference dollar mapping (1 unit = $10,000, from Tulsa Remote with the Bartik 58-70% but-for range) makes intensity interpretable without claiming representativeness.

**Tasks**
- [ ] Add Section 10.1: `TULSA_DOLLAR_PER_INTENSITY`, `BARTIK_BUT_FOR_LOW/HIGH`, `intensity_to_dollar_equivalent`, reference-only table
- [ ] Add Section 10.2: `hill_with_baseline`, `fit_hill`, seed bootstrap (`HILL_BOOTSTRAP = 300`), intensities at 90% and 95% of the fitted gain
- [ ] Add both Tulsa CSVs

**Files**
- `0914-1_v8.ipynb` (cells 40-43)
- `abm_outputs_research_plan_v7/tulsa_reference_runs.csv`
- `abm_outputs_research_plan_v7/tulsa_reference_summary.csv`

**Out of scope**

Cost and net-benefit tables (PR-14).

**Acceptance criteria**
- [ ] The dollar table is clearly labelled reference-only
- [ ] The Hill fit reports ceiling, half-response K and 90% / 95% intensities per tie level
- [ ] Bootstrap intervals are shown
- [ ] Cells run on top of PR-12

**Dependencies**

Blocked by PR-12. PRs are merged strictly in order because the notebook is a single JSON file.

### PR-13: `tulsa-and-hill-fit`

**Title:** Tulsa reference and Hill saturation fit  
**Base:** `master`

**Description** (paste into the PR body)

````markdown
## Summary

A finite grid cannot show where a response levels off. A Hill saturation curve estimates the ceiling, and a reference dollar mapping (1 unit = $10,000, from Tulsa Remote with the Bartik 58-70% but-for range) makes intensity interpretable without claiming representativeness.

Closes #13

## What's included
- Add Section 10.1: `TULSA_DOLLAR_PER_INTENSITY`, `BARTIK_BUT_FOR_LOW/HIGH`, `intensity_to_dollar_equivalent`, reference-only table
- Add Section 10.2: `hill_with_baseline`, `fit_hill`, seed bootstrap (`HILL_BOOTSTRAP = 300`), intensities at 90% and 95% of the fitted gain
- Add both Tulsa CSVs

## Files
- `0914-1_v8.ipynb` (cells 40-43)
- `abm_outputs_research_plan_v7/tulsa_reference_runs.csv`
- `abm_outputs_research_plan_v7/tulsa_reference_summary.csv`

## How to verify
1. Run cells 0-43 top to bottom
2. Run the notebook through cell 43
3. Compare the fitted parameters with the reference outputs

## Notes for reviewers

- Out of scope: Cost and net-benefit tables (PR-14).
- Depends on PR-12; rebase on `master` after it is merged.
- Cells are copied unchanged from the reference notebook (outputs kept); no numbers or model behaviour are altered.
````

---

## 15 - Extreme shocks and static interstate competition  (Member B)

### Issue #15: Extreme shocks and static interstate competition

**Assignee:** Member B  
**Labels:** notebook, member-B  
**Notebook cells:** 52-56

**Background**

To see how the system behaves outside normal conditions, the model is exposed to exogenous shocks (financial crisis, pandemic, labour shortage) with linear recovery. A stylised static competition scenario is kept only as a footnote.

**Tasks**
- [ ] Add Section 11: `SHOCK_NAMES`, the shock runs (4 scenarios x 6 seeds 401-406 = 24 rows) and summary
- [ ] Add Section 12: the static interstate competition footnote
- [ ] Add the three CSVs

**Files**
- `0914-1_v8.ipynb` (cells 52-56)
- `abm_outputs_research_plan_v7/shock_runs.csv`
- `abm_outputs_research_plan_v7/shock_summary.csv`
- `abm_outputs_research_plan_v7/state_competition_summary.csv`

**Out of scope**

Robustness checks (PR-16).

**Acceptance criteria**
- [ ] The shock summary shows unfilled jobs and move rate per scenario
- [ ] The labour-shortage result (unfilled jobs rise sharply, move rate barely changes) is reproduced
- [ ] Section 12 is labelled as a footnote
- [ ] Cells run on top of PR-14

**Dependencies**

Blocked by PR-14. PRs are merged strictly in order because the notebook is a single JSON file.

### PR-15: `shocks-and-competition`

**Title:** Extreme shocks and static interstate competition  
**Base:** `master`

**Description** (paste into the PR body)

````markdown
## Summary

To see how the system behaves outside normal conditions, the model is exposed to exogenous shocks (financial crisis, pandemic, labour shortage) with linear recovery. A stylised static competition scenario is kept only as a footnote.

Closes #15

## What's included
- Add Section 11: `SHOCK_NAMES`, the shock runs (4 scenarios x 6 seeds 401-406 = 24 rows) and summary
- Add Section 12: the static interstate competition footnote
- Add the three CSVs

## Files
- `0914-1_v8.ipynb` (cells 52-56)
- `abm_outputs_research_plan_v7/shock_runs.csv`
- `abm_outputs_research_plan_v7/shock_summary.csv`
- `abm_outputs_research_plan_v7/state_competition_summary.csv`

## How to verify
1. Run cells 0-56 top to bottom
2. Run the notebook through cell 56
3. Check `shock_runs` has 24 rows

## Notes for reviewers

- Out of scope: Robustness checks (PR-16).
- Depends on PR-14; rebase on `master` after it is merged.
- Cells are copied unchanged from the reference notebook (outputs kept); no numbers or model behaviour are altered.
````

---

## 17 - BRFSS coverage audit and distance-decay networks  (Member B)

### Issue #17: BRFSS coverage audit and distance-decay networks

**Assignee:** Member B  
**Labels:** notebook, member-B  
**Notebook cells:** 64-67

**Background**

Two more checks. First, whether validating the model's state ranking against BRFSS life satisfaction is defensible at all (the audit shows the common-year eight-state coverage is not). Second, a different social-network mechanism: contacts that decay with distance.

**Tasks**
- [ ] Add Section 13.3: the BRFSS coverage audit tables and the conclusion that a common-year validation is not defensible
- [ ] Add Section 13.4: `DistanceDecayABM` (subclass of `PolicySocialABM`), `NETWORK_DECAYS = [0, 2, 5, 10]`, `run_decay_case`, `strong_minus_weak`
- [ ] Add the three CSVs (the decay runs have 384 rows)

**Files**
- `0914-1_v8.ipynb` (cells 64-67)
- `abm_outputs_research_plan_v7/brfss_2023_coverage_audit.csv`
- `abm_outputs_research_plan_v7/brfss_validation_status.csv`
- `abm_outputs_research_plan_v7/network_decay_runs.csv`

**Out of scope**

Open-system competition (PR-18).

**Acceptance criteria**
- [ ] The BRFSS audit tables print the coverage gaps
- [ ] `DistanceDecayABM` runs and the cache reproduces its results
- [ ] Decay results are compared with the random-network baseline
- [ ] Cells run on top of PR-16

**Dependencies**

Blocked by PR-16. PRs are merged strictly in order because the notebook is a single JSON file.

### PR-17: `brfss-and-distance-decay`

**Title:** BRFSS coverage audit and distance-decay networks  
**Base:** `master`

**Description** (paste into the PR body)

````markdown
## Summary

Two more checks. First, whether validating the model's state ranking against BRFSS life satisfaction is defensible at all (the audit shows the common-year eight-state coverage is not). Second, a different social-network mechanism: contacts that decay with distance.

Closes #17

## What's included
- Add Section 13.3: the BRFSS coverage audit tables and the conclusion that a common-year validation is not defensible
- Add Section 13.4: `DistanceDecayABM` (subclass of `PolicySocialABM`), `NETWORK_DECAYS = [0, 2, 5, 10]`, `run_decay_case`, `strong_minus_weak`
- Add the three CSVs (the decay runs have 384 rows)

## Files
- `0914-1_v8.ipynb` (cells 64-67)
- `abm_outputs_research_plan_v7/brfss_2023_coverage_audit.csv`
- `abm_outputs_research_plan_v7/brfss_validation_status.csv`
- `abm_outputs_research_plan_v7/network_decay_runs.csv`

## How to verify
1. Run cells 0-67 top to bottom
2. Run the notebook through cell 67
3. Run one `DistanceDecayABM` case live and compare with its cached row

## Notes for reviewers

- Out of scope: Open-system competition (PR-18).
- Depends on PR-16; rebase on `master` after it is merged.
- Cells are copied unchanged from the reference notebook (outputs kept); no numbers or model behaviour are altered.
````

---

## 19 - Rebuild scripts, provenance table and duplicate data folder  (Member B)

### Issue #19: Rebuild scripts, provenance table and duplicate data folder

**Assignee:** Member B  
**Labels:** docs, member-B  
**Notebook cells:** none (non-notebook)

**Background**

Most cached CSVs were lost from the original cache and rebuilt by re-running the notebook's own model code. These scripts make that process repeatable.

Readers need to know where every cached CSV came from: real data, re-simulated, rebuilt from printed output, or original. The four files that survived in the original cache are kept as a separate folder.

**Tasks**
- [ ] Add `v8lib.py`: loads the model cells of the notebook verbatim into a namespace
- [ ] Add `worker.py`: runs one ABM case and returns a rich metric record
- [ ] Add `batch.py`: runs a JSON list of cases in parallel and saves a pickle
- [ ] Add `PROVENANCE.csv` with source, settings and verification for every cached CSV (29 rows)
- [ ] Add the four `abm_data/` CSVs (byte-identical copies of files in the cache)
- [ ] Note in the README draft that `abm_data/` is unused by the notebook

**Files**
- `rebuild_scripts/v8lib.py`
- `rebuild_scripts/worker.py`
- `rebuild_scripts/batch.py`
- `PROVENANCE.csv`
- `abm_data/open_system_runs.csv`
- `abm_data/state_intensity_sweep_runs.csv`
- `abm_data/lever_intensity_sweep_runs.csv`
- `abm_data/network_decay_runs.csv`

**Out of scope**

Final README (PR-20).

**Acceptance criteria**
- [ ] `worker.run` reproduces a cached case from `v8lib.load()`
- [ ] Scripts read the notebook by relative path
- [ ] Each script has a one-line docstring
- [ ] `PROVENANCE.csv` lists all 29 cached CSVs
- [ ] `abm_data/` files are byte-identical to the cache copies
- [ ] The README note on `abm_data/` is present

**Dependencies**

Blocked by PR-18. PRs are merged strictly in order because the notebook is a single JSON file.

### PR-19: `rebuild-and-provenance`

**Title:** Rebuild scripts, provenance table and duplicate data folder  
**Base:** `master`

**Description** (paste into the PR body)

````markdown
## Summary

Most cached CSVs were lost from the original cache and rebuilt by re-running the notebook's own model code. These scripts make that process repeatable.

Readers need to know where every cached CSV came from: real data, re-simulated, rebuilt from printed output, or original. The four files that survived in the original cache are kept as a separate folder.

Closes #19

## What's included
- Add `v8lib.py`: loads the model cells of the notebook verbatim into a namespace
- Add `worker.py`: runs one ABM case and returns a rich metric record
- Add `batch.py`: runs a JSON list of cases in parallel and saves a pickle
- Add `PROVENANCE.csv` with source, settings and verification for every cached CSV (29 rows)
- Add the four `abm_data/` CSVs (byte-identical copies of files in the cache)
- Note in the README draft that `abm_data/` is unused by the notebook

## Files
- `rebuild_scripts/v8lib.py`
- `rebuild_scripts/worker.py`
- `rebuild_scripts/batch.py`
- `PROVENANCE.csv`
- `abm_data/open_system_runs.csv`
- `abm_data/state_intensity_sweep_runs.csv`
- `abm_data/lever_intensity_sweep_runs.csv`
- `abm_data/network_decay_runs.csv`

## How to verify
1. From `rebuild_scripts/`, run one case through `worker.run` and compare with the cached row
2. `diff` each `abm_data/` file against its twin in the cache folder
3. Check every cached CSV appears in `PROVENANCE.csv`

## Notes for reviewers

- Out of scope: Final README (PR-20).
- Depends on PR-18; rebase on `master` after it is merged.
- Cells are copied unchanged from the reference notebook (outputs kept); no numbers or model behaviour are altered.
- Combines former plan items 25 and 26 after the team shrank to two members.
````

---
