# CITS4403 Group Project

Young-adult interstate migration: policy incentives, social networks and capacity feedback.

A spatial agent-based model (ABM) of 18-35 year-olds moving between eight US states
(CA, TX, NY, FL, MA, NC, IL, WA). The core question:

> How strong must a geographically targeted housing-and-employment policy be to overcome
> young adults' social attachment, and when do migration chains and local capacity
> constraints amplify or offset that response?

## Status

Work in progress. The notebook is being built up section by section through pull requests.

## Setup

Python 3.10 is recommended.

```
pip install -r requirements.txt jupyter
jupyter notebook 0914-1_v8.ipynb
```

The final run guide will replace this draft in the last pull request.

## Rebuild scripts and data provenance (draft)

`PROVENANCE.csv` records the source, settings and limitations of all 29 cached CSVs. `abm_data/` preserves four byte-identical copies of the original cache files; it is unused by the notebook. The notebook reads `abm_outputs_research_plan_v7/` instead.

From the repository root, run `python rebuild_scripts/worker.py '{"policy":"combined","seed":201}'` (adjust quoting for your shell). From `rebuild_scripts/`, `import worker; worker.run({"policy": "combined", "seed": 201})` works as well. For a batch, use `python rebuild_scripts/batch.py cases.json results.pkl --jobs 2`; `cases.json` is a list of case objects.

To recompute the empirical anchor from locally downloaded Census 2023 1-year person ZIPs, use `python rebuild_scripts/acs_pums.py path/to/pums`. The script documents ZIP names, filters and the Puerto Rico scope distinction. No full empirical rebuild is claimed without those source ZIPs.
