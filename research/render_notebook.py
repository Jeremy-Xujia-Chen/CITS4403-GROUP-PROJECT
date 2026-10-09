"""Execute the fitted research report in a clean kernel and export HTML/figures."""
import base64,json,os,sys,tempfile,time
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    runtime=ROOT/'.runtime';runtime.mkdir(exist_ok=True)
    tempdir=runtime/'temp';tempdir.mkdir(exist_ok=True);tempfile.tempdir=str(tempdir)
    os.environ.update(TEMP=str(tempdir),TMP=str(tempdir),PYTHONUTF8='1',PYTHONIOENCODING='utf-8',
        IPYTHONDIR=str(runtime/'ipython'),JUPYTER_RUNTIME_DIR=str(runtime/'jupyter-runtime'),JUPYTER_PATH=str(runtime/'jupyter'),
        OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',MPLBACKEND='Agg')
    kernel=runtime/'jupyter/kernels/research';kernel.mkdir(parents=True,exist_ok=True)
    (kernel/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'Fitted research','language':'python'}))
    out=ROOT/'results/research';out.mkdir(parents=True,exist_ok=True)
    nb=nbformat.read(ROOT/'0914-1_v8.ipynb',as_version=4);start=time.monotonic()
    print('Starting fresh research kernel',flush=True)
    client=NotebookClient(nb,timeout=900,startup_timeout=60,kernel_name='research',resources={'metadata':{'path':str(ROOT)}})
    client.on_cell_execute=lambda cell,cell_index,**kw:print('Research cell',cell_index,flush=True)
    try:client.execute()
    finally:nbformat.write(nb,out/'research-executed.ipynb')
    assert not [o for c in nb.cells for o in c.get('outputs',[]) if o.output_type=='error']
    nbformat.write(nb,ROOT/'0914-1_v8.ipynb')
    html,_=HTMLExporter().from_notebook_node(nb);(out/'research-executed.html').write_text(html,encoding='utf-8')
    figs=out/'figures';figs.mkdir(exist_ok=True);count=0
    for i,c in enumerate(nb.cells):
        for j,o in enumerate(c.get('outputs',[])):
            if 'image/png' in o.get('data',{}):
                (figs/f'cell-{i:02d}-{j}.png').write_bytes(base64.b64decode(o.data['image/png']));count+=1
    report={'passed':True,'code_cells':sum(c.cell_type=='code' for c in nb.cells),'error_outputs':0,'figures':count,'seconds':time.monotonic()-start,'profile':'calibrated-research'}
    (out/'execution-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
