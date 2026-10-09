"""Derive all eight simulated summary tables from fully rerun seed-level data."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.stats import t

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data/research'

def read(name):return pd.read_csv(DATA/(name+'.csv'))
def mean_ci(values):
    a=np.asarray(values,dtype=float);return a.mean(),t.ppf(.975,len(a)-1)*a.std(ddof=1)/np.sqrt(len(a))

def main():
    cross=read('cross_experiment_runs')
    metrics=['target_inflow_rate','mover_origin_attachment','target_social_cost','chain_share','housing_rejection','job_rejection','coorigin_clustering','peer_colocation','social_utility_index']
    summary=cross.groupby(['interaction','policy'])[metrics].mean().reset_index().rename(columns={'target_social_cost':'social_cost','coorigin_clustering':'clustering'})
    summary.to_csv(DATA/'cross_experiment_summary.csv',index=False)
    pairs=[]
    definitions={'d_target_inflow_rate':'target_inflow_rate','d_target_social_cost':'target_social_cost','d_target_chain_share':'chain_share','d_coorigin_clustering':'coorigin_clustering'}
    for interaction,g in cross.groupby('interaction'):
        baseline=g[g.policy=='baseline'].set_index('seed')
        for policy in ['housing','employment','combined']:
            pol=g[g.policy==policy].set_index('seed')
            for seed in pol.index:
                pairs.append({'policy':policy,'interaction':interaction,'seed':seed,**{label:pol.loc[seed,metric]-baseline.loc[seed,metric] for label,metric in definitions.items()}})
    per_seed=pd.DataFrame(pairs);effects=[]
    for policy in ['housing','employment','combined']:
        for metric in definitions:
            pivot=per_seed[per_seed.policy==policy].pivot(index='seed',columns='interaction',values=metric)
            effect,ci=mean_ci(pivot.strong-pivot.weak)
            effects.append({'policy':policy,'metric':metric,'strong_minus_weak_policy_effect':effect,'ci95_half_width':ci})
    effects=pd.DataFrame(effects)
    effects.to_csv(DATA/'interaction_modification.csv',index=False)
    paired=pd.concat([effects,per_seed],ignore_index=True)
    paired.to_csv(DATA/'paired_policy_effects.csv',index=False)
    groupings={
      'shock_summary':('shock_runs',['shock'],['move_rate','clustering','housing_rejection','social_utility_index','unfilled_jobs']),
      'social_threshold_sensitivity_summary':('social_threshold_sensitivity_runs',['threshold','scenario'],['move_rate','clustering','target_inflow','chain_share']),
      'network_homophily_summary':('network_homophily_runs',['network_homophily_share','scenario'],['clustering','peer_colocation','target_inflow','chain_share']),
      'rent_feedback_sensitivity_summary':('rent_feedback_sensitivity_runs',['rent_rejection_elasticity'],['target_inflow','target_housing_rejection','chain_share','final_rent'])}
    for output,(source,keys,metrics) in groupings.items():read(source).groupby(keys)[metrics].mean().reset_index().to_csv(DATA/(output+'.csv'),index=False)
    cash=read('tulsa_reference_runs');mean,ci=mean_ci(cash.induced_share)
    pd.DataFrame([{'reference_amount_usd':10000,'model_mean_induced_share':mean,'model_ci95_halfwidth':ci,'bartik_low':.58,'bartik_high':.70,'interpretation':'external reference only; not calibration'}]).to_csv(DATA/'tulsa_reference_summary.csv',index=False)

if __name__=='__main__':main()
