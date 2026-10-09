"""Larger-sample check of beta_current_state: grid x 20 seeds x N_AGENTS x N_YEARS (env CAL_N, CAL_Y), same seeds at every beta."""
import os, sys, pickle, numpy as np
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
os.chdir(os.path.join(HERE, ".."))
import worker
BETAS = [round(x, 3) for x in np.arange(3.80, 4.0001, 0.025)]
SEEDS = list(range(901, 921))
N_AGENTS, N_YEARS = int(os.environ.get("CAL_N", 600)), int(os.environ.get("CAL_Y", 12))
def run(case):
    beta, seed = case; g = worker.G()
    p = dict(g["PARAMS"]); p["beta_current_state"] = beta
    m = g["PolicySocialABM"](g["state_data"], g["policy_table"](), n_agents=N_AGENTS, years=N_YEARS, seed=seed, params=p,
                             interaction_strength=1.0, record_events=False)
    h, _, _ = m.run(); return beta, seed, h.groupby("year").first()["move_rate"].mean()
if __name__ == "__main__":
    with Pool(8) as pool: rows = pool.map(run, [(b, s) for b in BETAS for s in SEEDS], chunksize=1)
    pickle.dump(rows, open(os.path.join(HERE, f"calib_grid_{N_AGENTS}x{N_YEARS}.pkl"), "wb")); print("done", len(rows))
