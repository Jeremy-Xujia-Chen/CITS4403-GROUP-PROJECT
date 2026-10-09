import sys, pickle, json, pandas as pd
from multiprocessing import Pool
import worker
if __name__ == '__main__':
    cases = json.load(open(sys.argv[1]))
    with Pool(8) as p: rows = p.map(worker.run, cases, chunksize=1)
    pd.DataFrame(rows).to_pickle(sys.argv[2]); print('done', len(rows))
