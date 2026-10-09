"""Run one notebook ABM case and return cached metrics plus mechanism diagnostics."""

import argparse
import json

try:
    from . import v8lib
except ImportError:
    import v8lib

_namespace = None


def run(case):
    global _namespace
    if _namespace is None:
        _namespace = v8lib.load()
    ns = _namespace
    case = dict(case)
    seed = int(case.get("seed", 201))
    interaction = case.get("interaction", "medium")
    target = case.get("target_state", ns["FOCAL_STATE"])
    policy = case.get("policy", "baseline")
    intensity = float(case.get("intensity", 1.0))
    n_agents = int(case.get("n_agents", ns["EXPERIMENT_AGENTS"]))
    years = int(case.get("years", ns["EXPERIMENT_YEARS"]))
    params = dict(ns["PARAMS"], **case.get("params", {}))
    if "beta_current_state" in case:
        params["beta_current_state"] = float(case["beta_current_state"])
    saved = ns["FOCAL_STATE"]
    ns["FOCAL_STATE"] = target
    try:
        if "lever" in case:
            policies = ns["lever_policy"](target, case["lever"], intensity)
        else:
            policies = ns["cross_policy"](policy, intensity)
        kw = dict(seed=seed, n_agents=n_agents, years=years, params=params,
                  interaction_strength=ns["INTERACTION_LEVELS"][interaction])
        for key in ["entrant_home_local", "entrant_network_home_bias", "network_homophily_share"]:
            if key in case:
                kw[key] = case[key]
        if "shock" in case:
            kw["shocks"] = ns["SHOCK_SCENARIOS"][case["shock"]]
        decay = float(case.get("network_decay", 0.0))
        model_cls = ns["DistanceDecayABM"] if decay else ns["PolicySocialABM"]
        if decay:
            kw["network_decay"] = decay
        if "capacity_mode" in case:
            model_cls = ns["OpenSystemABM"]
            kw.update(external_rate=float(case["external_rate"]), capacity_mode=case["capacity_mode"])
        model = model_cls(ns["state_data"], policies, **kw)
        history, moves, _ = model.run()
        system = history.groupby("year").first()
        summary = ns["summarise_v7_run"](model, history, target)
        state_idx = model._state_indices()
        result = {**case, "target_state": target, "seed": seed, "interaction": interaction,
                  "n_agents": n_agents, "years": years, **summary,
                  "move_rate": float(system["move_rate"].mean()),
                  "same_state_contact_share": float(ns["np"].mean(state_idx[model.network] == state_idx[:, None])),
                  "moves_recorded": len(moves), "mechanism_rows": len(model.mechanism_history())}
        for key in ["peer_colocation", "social_utility_index", "unfilled_jobs"]:
            if key in system:
                result[key] = float(system[key].mean())
        if "capacity_mode" in case:
            ext = ns["pd"].DataFrame(model.external_rows)
            agent_years = history.groupby("year")["population"].sum().sum()
            internal = (system["move_rate"] * history.groupby("year")["population"].sum()).sum()
            mech = model.mechanism_history()
            result.update(target_total_inflow_rate=(mech["target_accepted"].sum() + ext["target_external_accepted"].sum()) / agent_years,
                          external_share_system=ext["external_accepted"].sum() / max(ext["external_accepted"].sum() + internal, 1),
                          housing_rejection=(mech["target_housing_rejected"].sum() + ext["target_external_rejected"].sum()) / max(mech["target_proposed"].sum() + ext["target_external_proposed"].sum(), 1))
        return result
    finally:
        ns["FOCAL_STATE"] = saved


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", help='JSON object, e.g. {"policy":"combined","seed":201}')
    print(json.dumps(run(json.loads(parser.parse_args().case)), indent=2, default=float))
