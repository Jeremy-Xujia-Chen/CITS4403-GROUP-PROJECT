"""Load verbatim v8 definitions without reading any simulated result cache."""
import ast
import contextlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / 'deployment/master/0914-1_v8.ipynb'
_ns = None

def load(irs_theta=None):
    cells = json.loads(NOTEBOOK.read_text(encoding='utf-8'))['cells']
    ns = {'__name__':'v8_model_raw_audit', 'display':lambda *a, **k:None}
    with contextlib.redirect_stdout(io.StringIO()):
        for index in [2,4,5,7,8,9,10,14,16,18,20,22]:
            source = ''.join(cells[index]['source'])
            if index == 9 and irs_theta is not None:
                # Optional verified fit injection avoids repeating the same slow
                # pandas-based optimizer in every calibration worker. Defaults
                # retain the original Notebook fitting path unchanged.
                source=source.split('train_result = minimize(')[0]
            if index == 10 and irs_theta is not None:
                theta=ns['np'].array(irs_theta,dtype=float)
                ns['CALIBRATED_BETA']=theta[:6].copy()
                ns['DESTINATION_EFFECTS']=ns['pd'].Series(ns['np'].r_[0.,theta[6:]],index=ns['STATE_CODES'],name='destination_effect')
                ns['final_route_metrics']=ns['route_fit_metrics'](theta,ns['STATE_CODES'])
                continue
            if index == 4 and (ROOT/'raw-rebuild/state-inputs-reconstructed.csv').exists():
                data=ns['pd'].read_csv(ROOT/'raw-rebuild/state-inputs-reconstructed.csv',index_col='state')
                data['employment_rate_labor_force']=data['employed']/data['civilian_labor_force']
                data['vacancy_rate']=data['vacant_housing_units']/data['housing_units']
                data['ipeds_enrollment_per_young_adult']=data['ipeds_12mo_enrollment']/data['young_adult_population_est_18_35']
                ns['real_raw_data']=data
                continue
            if index == 8 and (ROOT/'raw-rebuild/irs-routes-reconstructed.csv').exists():
                node=ast.parse(source).body[0]
                routes=ns['pd'].read_csv(ROOT/'raw-rebuild/irs-routes-reconstructed.csv')
                raw_routes=[(r.origin,r.destination,int(r.returns)) for r in routes.itertuples(index=False)]
                lines=source.splitlines(keepends=True)
                source='IRS_ROUTES = '+repr(raw_routes)+'\n'+''.join(lines[node.end_lineno:])
            if index == 10: source = source.split('display(')[0]
            if index == 14:
                source = source.replace('Path("abm_outputs_research_plan_v7")',f'Path({str(ROOT / "raw-rebuild/rebuilt")!r})')
            if index == 16: source = source.split('fig, ax =')[0]
            exec(compile(source,f'raw-model:cell-{index}','exec'),ns)
        for index in [28,37,67,69]:
            source = ''.join(cells[index]['source']); lines=source.splitlines(keepends=True)
            for node in ast.parse(source).body:
                if isinstance(node,(ast.FunctionDef,ast.ClassDef)) or (
                    index==69 and isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EXTERNAL_ORIGIN_TARGET' for t in node.targets)
                ):
                    exec(compile(''.join(lines[node.lineno-1:node.end_lineno]),f'raw-model:cell-{index}','exec'),ns)
    ns['PARAMS']['beta_current_state']=3.925  # Published experimental setting, not a regenerated calibration claim.
    ns['INTERACTION_LEVELS']={'weak':.6,'medium':1.,'strong':1.4}
    return ns

def run(case):
    global _ns
    if _ns is None: _ns=load()
    ns=_ns; np=ns['np']; pd=ns['pd']
    case=dict(case); target=case.get('target_state','NY'); policy=case.get('policy','baseline')
    ns['FOCAL_STATE']=target
    intensity=case.get('intensity',1.)
    policies=ns['lever_policy'](target,case['lever'],intensity) if 'lever' in case else ns['cross_policy'](policy,intensity)
    params=dict(ns['PARAMS'],**case.get('params',{}))
    params['beta_current_state']=case.get('beta_current_state',3.925)
    kw=dict(seed=case['seed'],n_agents=case.get('n_agents',600),years=case.get('years',12),params=params,
            interaction_strength=ns['INTERACTION_LEVELS'][case.get('interaction','medium')])
    for key in ['entrant_home_local','entrant_network_home_bias','network_homophily_share']:
        if key in case:kw[key]=case[key]
    if 'shock' in case:kw['shocks']=ns['SHOCK_SCENARIOS'][case['shock']]
    cls=ns['PolicySocialABM']
    if case.get('network_decay',0):cls=ns['DistanceDecayABM'];kw['network_decay']=case['network_decay']
    if 'capacity_mode' in case:
        cls=ns['OpenSystemABM'];kw.update(external_rate=case['external_rate'],capacity_mode=case['capacity_mode'])
    model=cls(ns['state_data'],policies,**kw)
    history,moves,_=model.run(); system=history.groupby('year').first(); mech=model.mechanism_history()
    out=ns['summarise_v7_run'](model,history,target)
    out.update(move_rate=float(system.move_rate.mean()),peer_colocation=float(system.peer_colocation.iloc[-1]),
               social_utility_index=float(system.mean_social_utility_index.iloc[-1]),
               peer_colocation_mean=float(system.peer_colocation.mean()),social_utility_index_mean=float(system.mean_social_utility_index.mean()),
               housing_rejection_system=float(system.housing_rejection_rate.mean()),unfilled_jobs=float(system.unfilled_jobs.mean()),
               population_hhi=float(system.population_hhi.iloc[-1]),
               mover_origin_attachment=float(mech.target_origin_attachment_sum.sum()/max(mech.target_social_cost_n.sum(),1)),
               final_rent=float(model.state.loc[target,'rent_index']))
    si=model._state_indices();out['same_state_contact_share']=float(np.mean(si[model.network]==si[:,None]))
    if 'capacity_mode' in case:
        ext=pd.DataFrame(model.external_rows); ay=history.groupby('year').population.sum().sum()
        internal=(system.move_rate*history.groupby('year').population.sum()).sum()
        out.update(target_external_inflow_rate=float(ext.target_external_accepted.sum()/ay),
                   target_total_inflow_rate=float((mech.target_accepted.sum()+ext.target_external_accepted.sum())/ay),
                   external_share_system=float(ext.external_accepted.sum()/max(ext.external_accepted.sum()+internal,1)),
                   housing_rejection=float((mech.target_housing_rejected.sum()+ext.target_external_rejected.sum())/max(mech.target_proposed.sum()+ext.target_external_proposed.sum(),1)))
    return {k:float(v) for k,v in out.items()}
