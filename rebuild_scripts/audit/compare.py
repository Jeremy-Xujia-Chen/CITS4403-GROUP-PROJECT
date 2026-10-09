import os, pickle, numpy as np, pandas as pd
from scipy.stats import t as student_t
C = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../abm_outputs_research_plan_v7/")
res = pickle.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "resim.pkl"), "rb"))
R = {r["case_id"]: r for r in res["rows"]}
report = []

def check(file, key_cols, keyfn, colmap):
    cached = pd.read_csv(C + file)
    worst = {}
    nrows_diff = 0; ncells_diff = 0
    for _, row in cached.iterrows():
        if any(pd.isna(row[k]) for k in key_cols): continue
        live = keyfn(row)
        bad = False
        for col, f in colmap.items():
            d = abs(float(row[col]) - float(f(live)))
            worst[col] = max(worst.get(col, 0), d)
            if d > 1e-9: bad = True; ncells_diff += 1
        nrows_diff += bad
    report.append((file, len(cached), nrows_diff, ncells_diff, max(worst.values())))
    if nrows_diff: print(file, {k: v for k, v in worst.items() if v > 1e-9})

k = lambda *a: R[a]
fin = lambda c: (lambda r: r[c + "_final"]); mean = lambda c: (lambda r: r[c + "_mean"]); same = lambda c: (lambda r: r[c])
check("baseline_runs.csv", ["seed"], lambda r: k("baseline", r.seed), {
    "move_rate": mean("move_rate"), "coorigin_clustering": same("coorigin_clustering"), "peer_colocation": fin("peer_colocation"),
    "housing_rejection": mean("housing_rejection_rate"), "mean_social_utility_index": fin("mean_social_utility_index"),
    "unfilled_jobs": mean("unfilled_jobs"), "population_hhi": fin("population_hhi")})
check("cross_experiment_runs.csv", ["seed"], lambda r: k("cross", r.policy, r.interaction, r.seed), {
    **{c: same(c) for c in ["target_inflow_rate", "target_social_cost", "chain_share", "housing_rejection", "job_rejection",
                            "coorigin_clustering", "mover_origin_attachment"]},
    "peer_colocation": fin("peer_colocation"), "social_utility_index": fin("mean_social_utility_index"), "move_rate": mean("move_rate")})
check("tulsa_reference_runs.csv", ["seed"], lambda r: (k("cross", "baseline", "medium", r.seed), k("tulsa", r.seed)), {
    "no_policy_target_inflow_rate": lambda p: p[0]["target_inflow_rate"], "incentive_target_inflow_rate": lambda p: p[1]["target_inflow_rate"],
    "induced_share": lambda p: (p[1]["target_inflow_rate"] - p[0]["target_inflow_rate"]) / p[1]["target_inflow_rate"]})
check("shock_runs.csv", ["seed"], lambda r: k("shock", r.shock, r.seed), {
    "move_rate": mean("move_rate"), "clustering": same("coorigin_clustering"), "housing_rejection": mean("housing_rejection_rate"),
    "social_utility_index": fin("mean_social_utility_index"), "unfilled_jobs": mean("unfilled_jobs")})
check("entrant_robustness_runs.csv", ["seed"], lambda r: k("entrant", bool(r.home_local), bool(r.network_home_bias), r.seed), {
    "coorigin_clustering": same("coorigin_clustering"), "peer_colocation": fin("peer_colocation"), "move_rate": mean("move_rate")})
check("social_threshold_sensitivity_runs.csv", ["seed"], lambda r: k("threshold", r.threshold, r.scenario, r.seed), {
    "move_rate": mean("move_rate"), "clustering": same("coorigin_clustering"), "peer_colocation": fin("peer_colocation"),
    "target_inflow": same("target_inflow_rate"), "chain_share": same("chain_share"), "target_social_cost": same("target_social_cost"),
    "housing_rejection": same("housing_rejection")})
check("network_homophily_runs.csv", ["seed"], lambda r: k("homophily", r.network_homophily_share, r.scenario, r.seed), {
    "clustering": same("coorigin_clustering"), "peer_colocation": fin("peer_colocation"), "target_inflow": same("target_inflow_rate"),
    "chain_share": same("chain_share"), "move_rate": mean("move_rate")})
check("parameter_sensitivity_runs.csv", ["seed"], lambda r: k("param", r.stay_scale, r.seed), {
    "target_inflow_rate": same("target_inflow_rate"), "target_social_cost": same("target_social_cost"),
    "target_chain_share": same("chain_share"), "coorigin_clustering": same("coorigin_clustering")})
check("rent_feedback_sensitivity_runs.csv", ["seed"], lambda r: k("rent", r.rent_rejection_elasticity, r.seed), {
    "target_inflow": same("target_inflow_rate"), "target_housing_rejection": same("housing_rejection"),
    "chain_share": same("chain_share"), "final_rent": same("target_rent_final")})
e6 = pd.read_csv(C + "state_competition_summary.csv")
live = {st: np.mean([R[("e6", s)][f"net_final_{st}"] for s in range(401, 407)]) for st in e6.state}
d = max(abs(e6.set_index("state").mean_net_migration[st] - live[st]) for st in live)
report.append(("state_competition_summary.csv (net migration)", len(e6), int(d > 1e-9), 0, d))
print(pd.DataFrame(report, columns=["file", "rows", "rows_differing", "cells_differing", "max_abs_diff"]).to_string())

# ---- calibration
print("\nV5 calibration routine run with the v8 model (500 agents x 6 years, seeds 901-905):")
cal = pd.read_csv(C + "move_rate_calibration.csv")
for beta, rate, _ in res["grid"]:
    c = cal[np.isclose(cal.beta_current_state, beta)].simulated_move_rate.iloc[0]
    print(f"  beta {beta}: cached {c:.5f}  current model {rate:.5f}")
rows, final = res["bisection"]; print(pd.DataFrame(rows).round(5).to_string()); print("  bisection result:", round(final, 4))

# ---- cached summaries vs aggregates of cached runs
def ci(x): x = np.asarray(x, float); return student_t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
def cmp(name, a, b):
    d = np.nanmax(np.abs(a.to_numpy(float) - b.to_numpy(float))); print(f"  {name}: max |diff| = {d:.2e}")
print("\nCached summary files vs recomputed from cached runs:")
cr = pd.read_csv(C + "cross_experiment_runs.csv"); cs = pd.read_csv(C + "cross_experiment_summary.csv")
agg = cr.groupby(["interaction", "policy"]).agg(target_inflow_rate=("target_inflow_rate", "mean"), mover_origin_attachment=("mover_origin_attachment", "mean"),
      social_cost=("target_social_cost", "mean"), chain_share=("chain_share", "mean"), housing_rejection=("housing_rejection", "mean"),
      job_rejection=("job_rejection", "mean"), clustering=("coorigin_clustering", "mean"), peer_colocation=("peer_colocation", "mean"),
      social_utility_index=("social_utility_index", "mean")).reset_index()
cmp("cross_experiment_summary", cs.drop(columns=["interaction", "policy"]), agg.drop(columns=["interaction", "policy"]))
w = cr.pivot_table(index=["interaction", "seed"], columns="policy", values=["target_inflow_rate", "target_social_cost", "chain_share", "coorigin_clustering"])
im = pd.read_csv(C + "interaction_modification.csv"); rows = []
mm = {"d_target_inflow_rate": "target_inflow_rate", "d_target_social_cost": "target_social_cost", "d_target_chain_share": "chain_share", "d_coorigin_clustering": "coorigin_clustering"}
for _, r in im.iterrows():
    eff = w[mm[r.metric]][r.policy] - w[mm[r.metric]]["baseline"]; d = (eff.xs("strong") - eff.xs("weak")).to_numpy()
    rows.append((d.mean(), ci(d)))
cmp("interaction_modification", im[["strong_minus_weak_policy_effect", "ci95_half_width"]], pd.DataFrame(rows))
pe = pd.read_csv(C + "paired_policy_effects.csv"); top = pe.iloc[:12]
cmp("paired_policy_effects (summary block, stored at 4 dp)", top[["strong_minus_weak_policy_effect", "ci95_half_width"]], im[["strong_minus_weak_policy_effect", "ci95_half_width"]].round(4))
per = pe.iloc[12:]; rows = []
for _, r in per.iterrows():
    rows.append([w[mm[m]][r.policy].loc[(r.interaction, r.seed)] - w[mm[m]]["baseline"].loc[(r.interaction, r.seed)] for m in mm])
cmp("paired_policy_effects (per-seed block)", per[list(mm)], pd.DataFrame(rows))
tr = pd.read_csv(C + "tulsa_reference_runs.csv"); ts = pd.read_csv(C + "tulsa_reference_summary.csv")
cmp("tulsa_reference_summary", ts[["model_mean_induced_share", "model_ci95_halfwidth"]], pd.DataFrame([[tr.induced_share.mean(), ci(tr.induced_share)]]))
sr = pd.read_csv(C + "shock_runs.csv"); ss = pd.read_csv(C + "shock_summary.csv").set_index("shock")
cmp("shock_summary", ss, sr.groupby("shock")[list(ss.columns)].mean().loc[ss.index])
for f, keys, cols in [("social_threshold_sensitivity", ["threshold", "scenario"], ["move_rate", "clustering", "target_inflow", "chain_share"]),
                      ("network_homophily", ["network_homophily_share", "scenario"], ["clustering", "peer_colocation", "target_inflow", "chain_share"]),
                      ("rent_feedback_sensitivity", ["rent_rejection_elasticity"], ["target_inflow", "target_housing_rejection", "chain_share", "final_rent"])]:
    r = pd.read_csv(C + f + "_runs.csv"); s = pd.read_csv(C + f + "_summary.csv")
    cmp(f + "_summary", s[cols], r.groupby(keys)[cols].mean().reset_index()[cols])
