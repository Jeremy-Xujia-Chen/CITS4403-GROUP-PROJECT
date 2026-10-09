"""Run regression tests with temporary files confined to this checkout."""
import sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
if __name__=='__main__':
    temp=ROOT/'.runtime/test-temp';temp.mkdir(parents=True,exist_ok=True);tempfile.tempdir=str(temp)
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),top_level_dir=str(ROOT))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromName('rebuild_scripts.test_worker_validation'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
