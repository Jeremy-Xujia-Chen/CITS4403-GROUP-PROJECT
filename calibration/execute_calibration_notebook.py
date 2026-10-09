"""Execute the diagnostic Notebook with a fresh actual calibrated model case."""
import json
import os
from pathlib import Path
import sys
import time
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'reliable-calibration';RESULTS=ROOT/'results'
if __name__=='__main__':
    os.environ.update(PYTHONIOENCODING='utf-8',IPYTHONDIR=str(ROOT/'ipython'),JUPYTER_RUNTIME_DIR=str(ROOT/'jupyter-runtime'),JUPYTER_PATH=str(ROOT/'jupyter'))
    kernel=ROOT/'jupyter/kernels/cits4403-310';kernel.mkdir(parents=True,exist_ok=True)
    (kernel/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'Calibration Python 3.10.18','language':'python'}),encoding='utf-8')
    nb=nbformat.read(OUT/'calibration-validation.ipynb',as_version=4);start=time.monotonic()
    client=NotebookClient(nb,timeout=300,startup_timeout=60,kernel_name='cits4403-310',resources={'metadata':{'path':str(ROOT)}})
    client.on_cell_execute=lambda cell,cell_index,**kw:print('Calibration diagnostic cell',cell_index,flush=True)
    client.execute();errors=[o for c in nb.cells for o in c.get('outputs',[]) if o.output_type=='error'];assert not errors
    nbformat.write(nb,RESULTS/'calibration-validation.ipynb');html,_=HTMLExporter().from_notebook_node(nb)
    (RESULTS/'calibration-validation.html').write_text(html,encoding='utf-8')
    report={'passed':True,'code_cells':sum(c.cell_type=='code' for c in nb.cells),'error_outputs':len(errors),'actual_new_profile_case_repeated':True,'seconds':time.monotonic()-start}
    (OUT/'diagnostic-notebook-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)
