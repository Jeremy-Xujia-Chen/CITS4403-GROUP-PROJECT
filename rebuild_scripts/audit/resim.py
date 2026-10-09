"""Re-simulate every cached per-seed file that has no in-notebook generator, using the v8 model code
(rebuild_scripts/worker.py loads it verbatim from 0914-1_v8.ipynb), and compare with the cache."""
import os, sys, json, pickle, numpy as np, pandas as pd
from multiprocessing import Pool
PROJ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
os.chdir(PROJ + "/rebuild_scripts"); sys.path.insert(0, PROJ + "/rebuild_scripts")
import worker, v8lib
C = PROJ + "/abm_outputs_research_plan_v7/"
OUT = os.path.dirname(os.path.abspath(__file__))

def cases():
    cs = []
    for s in range(101, 109): cs.append(dict(id=("baseline", s), policy=("none", 0), n=1000, years=20, seed=s))
    for p in ["baseline", "housing", "employment", "combined"]:
        for i in ["weak", "medium", "strong"]:
            for s in range(201, 209): cs.append(dict(id=("cross", p, i, s), policy=("cross", 1.0, p), interaction=i, seed=s))
    for s in range(201, 209): cs.append(dict(id=("tulsa", s), policy=("incentive", 1.0), seed=s))
    for sh in ["baseline", "financial_crisis", "pandemic", "labor_shortage"]:
        for s in range(401, 407): cs.append(dict(id=("shock", sh, s), policy=("none", 0), years=15, shock=sh, seed=s))
    for hl in [False, True]:
        for nb in [False, True]:
            for s in range(501, 505): cs.append(dict(id=("entrant", hl, nb, s), policy=("none", 0), years=15, home_local=hl, net_bias=nb, seed=s))
    for th in [0.2, 0.35, 0.5]:
        for sc in ["baseline", "combined"]:
            for s in range(501, 505): cs.append(dict(id=("threshold", th, sc, s), policy=("none", 0) if sc == "baseline" else ("scaled_combined", 1.0),
                                                   params={"social_satisfaction_threshold": th}, seed=s))
    for hs in [0.0, 0.5]:
        for sc in ["baseline", "combined"]:
            for s in range(501, 505): cs.append(dict(id=("homophily", hs, sc, s), policy=("none", 0) if sc == "baseline" else ("scaled_combined", 1.0), homophily=hs, seed=s))
    for st in [0.85, 1.0, 1.15]:
        for s in range(501, 505): cs.append(dict(id=("param", st, s), policy=("scaled_combined", 1.0), params={"beta_current_state": 3.925 * st}, seed=s))
    for el in [0.0, 0.1, 0.15, 0.2]:
        for s in range(501, 505): cs.append(dict(id=("rent", el, s), policy=("scaled_combined", 2.0), params={"rent_rejection_elasticity": el}, seed=s))
    g = v8lib.load(); sd = g["state_data"]
    need = 0.5 * (1.0 / sd["job_index"]) + 0.5 * sd["housing_capacity_index"]   # V5 cell 33 rule
    need = (need - need.min()) / max(need.max() - need.min(), 1e-9)
    inc = (0.25 + 0.75 * need).to_dict()
    for s in range(401, 407): cs.append(dict(id=("e6", s), policy=("state", inc), seed=s))
    return cs

def calib_job(beta):
    """V5 cell 19 estimate_move_rate, run with the v8 model."""
    g = worker.G(); rates = []
    for seed in (901, 902, 903, 904, 905):
        p = dict(g["PARAMS"]); p["beta_current_state"] = float(beta)
        m = g["PolicySocialABM"](g["state_data"], g["policy_table"](), n_agents=500, years=6, seed=seed, params=p,
                                 interaction_strength=1.0, record_events=False)
        h, _, _ = m.run(); rates.append(h.groupby("year").first()["move_rate"].mean())
    return beta, float(np.mean(rates)), rates

def bisection(_):
    target = float(pd.read_csv(C + "acs_young_adult_interstate_move_rate.csv")["move_rate"].iloc[0])
    lo, hi = 1.5, 5.5; rows = []
    for it in range(8):
        mid = (lo + hi) / 2; _, r, _ = calib_job(mid)
        rows.append(dict(iteration=it + 1, beta_current_state=mid, simulated_move_rate=r, target_move_rate=target, absolute_error=abs(r - target)))
        lo, hi = (mid, hi) if r > target else (lo, mid)
    return rows, (lo + hi) / 2

if __name__ == "__main__":
    cs = cases()
    with Pool(8) as p:
        bis = p.apply_async(bisection, (0,))
        grid = p.map_async(calib_job, [3.875, 3.9, 3.925])
        rows = p.map(worker.run, cs, chunksize=1)
        res = dict(rows=rows, bisection=bis.get(), grid=grid.get())
    pickle.dump(res, open(OUT + "/resim.pkl", "wb")); print("done", len(rows))
