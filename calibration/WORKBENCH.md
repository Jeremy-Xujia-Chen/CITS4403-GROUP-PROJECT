# Calibration workbench

Start with `reliable-calibration/calibration-report.md` and `README-calibration.md`.
`raw_model.py` loads model definitions verbatim from the hash-pinned historical Notebook, injects fitted IRS theta and uses verified numeric empirical reconstructions. Scenario mechanisms remain unchanged. `reliable_worker.py` receives explicit design parameters.

Historical tables in deployment/master are used only to define the experiment grid and validate the historical precision control. New research metrics live in ../data/research. The original Notebook has a duplicate hash-pinned source in download for provenance. Do not change these byte-stable inputs without refitting and clearing incompatible checkpoints.
