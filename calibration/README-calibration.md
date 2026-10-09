# Frozen calibration workbench

This is the complete, independently verified calibration artifact. The two
`download/` and `deployment/` source fixtures deliberately pin the original
V8 inputs and keep the recorded SHA256 checks reproducible. They are fixtures,
not separate deployment environments. The root project adds final-parameter
rounding and animation while retaining identical model class/function ASTs.

From the project root, use `python run_project.py --profile calibrated` for a
live demonstration and diagnostic execution. On Windows, run
`calibration/Reproduce-Calibration.ps1` to repeat IRS fitting and validate
existing simulation checkpoints. Add `-Fresh` to back up checkpoints and
actually recompute all model cases. The root `.venv` is used by default;
`-Python path/to/python.exe` selects another interpreter.

The original 4140-row policy grid is the published profile. New-fit policy
inference has not been recomputed. Decay=10 failed its declared validation and
is excluded from the defaults; its diagnostic remains in the report. Social,
demographic and policy settings remain assumptions, not newly observed data.
