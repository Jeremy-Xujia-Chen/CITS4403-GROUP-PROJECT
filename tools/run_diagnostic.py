"""Run the fitted calibration diagnostic with checkout-local temporary files."""
import os,runpy,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    temp=ROOT/'.runtime/diagnostic-temp';temp.mkdir(parents=True,exist_ok=True)
    tempfile.tempdir=str(temp);os.environ.update(TEMP=str(temp),TMP=str(temp),PYTHONUTF8='1')
    runpy.run_path(str(ROOT/'calibration/execute_calibration_notebook.py'),run_name='__main__')
