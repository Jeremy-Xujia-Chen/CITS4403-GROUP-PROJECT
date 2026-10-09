param([switch]$Fresh, [string]$Python='')
$ErrorActionPreference='Stop'
$calibrationRoot=$PSScriptRoot
$calibrationPython=$Python
if (-not $calibrationPython) { $calibrationPython=Join-Path (Split-Path -Parent $calibrationRoot) '.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $calibrationPython)) { $calibrationPython=(Get-Command python -ErrorAction Stop).Source }
$env:PYTHONUTF8='1'
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
if (-not $Fresh) {
    & $calibrationPython (Join-Path $calibrationRoot 'verify_calibration_inputs.py')
    if ($LASTEXITCODE -ne 0) { throw 'Calibration inputs changed; use -Fresh for a new fit.' }
}
if ($Fresh) {
    $calibrationStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    foreach ($name in @('beta-live.jsonl','beta-checkpoint-input.json','transfer-live.jsonl','research-design-live.jsonl','research-design-checkpoint-input.json','canonical-precision-live.jsonl','extension-live.jsonl','extension-checkpoint-input.json')) {
        $checkpoint=Join-Path $calibrationRoot "reliable-calibration\$name"
        if (Test-Path -LiteralPath $checkpoint) {
            Move-Item -LiteralPath $checkpoint -Destination "$checkpoint.$calibrationStamp.bak"
        }
    }
}
foreach ($script in @('fit_reliable_irs.py','calibrate_reliable_beta.py','extend_scale_validation.py','calibrate_research_design.py','verify_canonical_precision.py','calibrate_reliable_extensions.py','make_reliable_delivery.py','verify_reliable_runner.py','execute_calibration_notebook.py')) {
    & $calibrationPython (Join-Path $calibrationRoot $script)
    if ($LASTEXITCODE -ne 0) { throw "Calibration step failed: $script" }
}
# Repackage the execution evidence once the diagnostic kernel check has completed.
& $calibrationPython (Join-Path $calibrationRoot 'make_reliable_delivery.py')
if ($LASTEXITCODE -ne 0) { throw 'Final calibration delivery failed' }
