"""Run one ABM case with the verbatim model code of 0914-1_v8.ipynb and return a rich metric record."""
import numpy as np, pandas as pd, v8lib
_G = None
def G():
    global _G
    if _G is None: _G = v8lib.load()
    return _G

def make_policy(g, spec, target):
    kind, x = spec[0], spec[1]
    if kind == 'none': return g['policy_table']()
    if kind == 'cross': return g['cross_policy'](spec[2], x) if len(spec) > 2 else None
    if kind == 'lever': return g['lever_policy'](target, spec[2], x)
    if kind == 'state': return g['policy_table'](state_incentives=x)
    if kind == 'eq': return g['policy_table'](state_incentives={st: x for st in g['STATE_CODES']})
    if kind == 'incentive': return g['policy_table'](target, migration_incentive=x)
    if kind == 'scaled_combined':   # combined package, policy-effect scale via params handled by caller
        return g['policy_table'](target, housing=x, employment=x, migration_incentive=x)
    raise ValueError(kind)

def run(case):
    g = G()
    c = dict(case)
    target = c.get('target', g['FOCAL_STATE'])
    params = dict(g['PARAMS'])
    params.update(c.get('params', {}))
    g['FOCAL_STATE'] = target
    pol = make_policy(g, c['policy'], target)
    shocks = g['SHOCK_SCENARIOS'][c['shock']] if c.get('shock') else None
    m = g['PolicySocialABM'](g['state_data'], pol, n_agents=c.get('n', 600), years=c.get('years', 12),
                             seed=c['seed'], params=params,
                             interaction_strength=g['INTERACTION_LEVELS'][c.get('interaction', 'medium')],
                             shocks=shocks, entrant_home_local=c.get('home_local', False),
                             entrant_network_home_bias=c.get('net_bias', False),
                             network_homophily_share=c.get('homophily', 0.0))
    h, moves, _ = m.run()
    mech = m.mechanism_history()
    s = g['summarise_v7_run'](m, h, target)
    sysl = h.groupby('year').first()
    out = dict(case_id=c['id'], target=target, **s)
    out['agent_years'] = h.groupby('year')['population'].sum().sum()
    out['target_accepted'] = mech['target_accepted'].sum()
    out['target_proposed'] = mech['target_proposed'].sum()
    for k in ['target_origin_attachment_sum', 'target_social_cost_n', 'target_social_cost_sum', 'target_chain_moves', 'target_housing_rejected']:
        if k in mech: out[k] = mech[k].sum()
    out['mover_origin_attachment'] = out.get('target_origin_attachment_sum', np.nan) / max(out.get('target_social_cost_n', 1), 1)
    for col in ['peer_colocation', 'coorigin_clustering', 'population_hhi', 'move_rate', 'housing_rejection_rate',
                'mean_social_utility_index', 'mean_rent_burden_system', 'births', 'unfilled_jobs']:
        out[col + '_mean'] = sysl[col].mean(); out[col + '_final'] = sysl[col].iloc[-1]
    tgt = h[h['state'] == target]
    out['target_rent_final'] = tgt['rent_index'].iloc[-1]; out['target_rent_mean'] = tgt['rent_index'].mean()
    out['target_inflow_hist'] = tgt['inflow'].sum()
    for st, gs in h.groupby('state'):
        out[f'net_final_{st}'] = gs['net_migration'].iloc[-1]; out[f'net_mean_{st}'] = gs['net_migration'].mean()
        out[f'net_sum_{st}'] = gs['net_migration'].sum()
        out[f'emp_final_{st}'] = gs['employment_rate'].iloc[-1]; out[f'unf_final_{st}'] = gs['unfilled_jobs_state'].iloc[-1]
        out[f'pop_final_{st}'] = gs['population'].iloc[-1]
    out['mech_cols'] = ','.join(mech.columns)
    out['move_series'] = list(sysl['move_rate'])
    out['inflow_all_rate'] = h['inflow'].sum() / out['agent_years']
    out['pop_series'] = list(h.groupby('year')['population'].sum())
    out['hh_moves'] = len(moves)
    return out
