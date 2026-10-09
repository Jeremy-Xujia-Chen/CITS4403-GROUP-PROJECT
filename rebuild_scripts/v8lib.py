"""Load the model code of 0914-1_v8.ipynb verbatim into a namespace (no other notebook is used)."""
import json, io, contextlib
NB = '../0914-1_v8.ipynb'
def load(beta_stay=3.925):
    nb = json.load(open(NB))
    g = {'display': lambda *a, **k: None}
    src = '\n'.join(''.join(nb['cells'][i]['source']) for i in [2,4,5,7,8,9,10,18,20,22])
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(src, 'v8', 'exec'), g)
    g['PARAMS']['beta_current_state'] = beta_stay
    g['INTERACTION_LEVELS'] = {"weak": 0.60, "medium": 1.00, "strong": 1.40}
    g['STANDARD_INTENSITY'] = 1.0
    exec(compile(''.join(nb['cells'][37]['source']), 'c37', 'exec'), g)
    exec(compile(''.join(nb['cells'][69]['source']).split('class OpenSystemABM')[0], 'c69', 'exec'), g)
    return g
