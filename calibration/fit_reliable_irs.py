"""Deterministic route calibration with origin-group CV and analytic gradients."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from raw_model import load

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'reliable-calibration'
NAMES=['beta_income','beta_jobs','beta_rent','beta_distance','beta_education','beta_childcare']
TRAIN=['CA','TX','NY','FL','MA','NC'];HOLDOUT=['IL','WA']
SCALES=[.25,1.,4.]

def original_theta():
    p=json.loads((ROOT/'raw-rebuild/kernel-with-legacy.json').read_text())['parameters']
    fe=pd.read_csv(ROOT/'results/master/tables/DESTINATION_EFFECTS.csv',index_col=0).destination_effect
    return np.r_[[p[k] for k in NAMES],fe.iloc[1:].to_numpy()]

class RouteFit:
    def __init__(self,ns):
        self.ns=ns;self.groups={};self.prior=ns['PRIOR_BETA'];self.scales=ns['PRIOR_SCALE']
        self.initial=np.r_[self.prior,np.zeros(7)];self.bounds=ns['bounds']
        for origin in ns['STATE_CODES']:
            df=ns['irs_flows'][ns['irs_flows'].origin==origin]
            dest=df.destination.tolist();pos=np.array([ns['STATE_POS'][d] for d in dest])
            college=np.clip(ns['state_data'].loc[origin,'college_share_proxy']*.82,.05,.70)
            matrices=[];mix=[]
            for educated,ew in [(0,1-college),(1,college)]:
                for child,cw in [(0,.75),(1,.25)]:
                    f=ns['CAL_FEATURES']
                    x=np.column_stack([f['log_income'][pos],f['jobs'][pos],-f['rent'][pos],
                        -ns['distance_index'].loc[origin,dest].to_numpy(),(1-educated)*f['education'][pos],child*f['childcare'][pos]])
                    z=np.eye(8)[pos,1:]
                    matrices.append(np.column_stack([x,z])/ns['CALIBRATION_TEMPERATURE']);mix.append(ew*cw)
            self.groups[origin]=(np.array(matrices),np.array(mix),df.observed_share.to_numpy(),np.sqrt(df.returns.to_numpy()))
    def predictions(self,theta,origin):
        x,mix,obs,w=self.groups[origin]
        u=x@theta;u-=u.max(axis=1,keepdims=True);p=np.exp(u);p/=p.sum(axis=1,keepdims=True)
        pred=mix@p
        dp=p[:,:,None]*(x-np.sum(p[:,:,None]*x,axis=1)[:,None,:])
        return pred,np.sum(mix[:,None,None]*dp,axis=0),obs,w
    def objective(self,theta,origins,scale=1.):
        weights=Counter(origins);numerator=0.;denominator=0.;gradient=np.zeros(13)
        for origin,count in weights.items():
            pred,dp,obs,w=self.predictions(theta,origin);diff=pred-obs
            numerator+=count*np.dot(w,diff*diff);denominator+=count*w.sum()
            gradient+=count*(2*w*diff)@dp
        loss=numerator/denominator;gradient/=denominator
        lb=.02*scale;lf=.05*scale
        loss+=lb*np.mean(((theta[:6]-self.prior)/self.scales)**2)+lf*np.mean(theta[6:]**2)
        gradient[:6]+=2*lb/6*(theta[:6]-self.prior)/self.scales**2
        gradient[6:]+=2*lf/7*theta[6:]
        return float(loss),gradient
    def fit(self,origins,scale=1.,initial=None):
        r=minimize(self.objective,self.initial if initial is None else initial,args=(origins,scale),jac=True,
            method='L-BFGS-B',bounds=self.bounds,options={'maxiter':700,'ftol':1e-12,'gtol':1e-8})
        assert r.success,r.message
        return r
    def metrics(self,theta,origins):
        predictions=[];actual=[];weights=[]
        for o in origins:
            p,_,a,w=self.predictions(theta,o);predictions.extend(p);actual.extend(a);weights.extend(w)
        p=np.array(predictions);a=np.array(actual);w=np.array(weights)
        return {'weighted_rmse':float(np.sqrt(np.average((p-a)**2,weights=w))),
            'weighted_mae':float(np.average(np.abs(p-a),weights=w)),'correlation':float(np.corrcoef(p,a)[0,1])}

def main():
    OUT.mkdir(exist_ok=True);start=time.monotonic();old=original_theta();ns=load(irs_theta=old);f=RouteFit(ns)
    equivalence=[]
    for theta in [old,f.initial,np.clip(old+.03,*np.array(f.bounds).T)]:
        for origins in [TRAIN,HOLDOUT,ns['STATE_CODES']]:
            ours=f.objective(theta,origins)[0];original=ns['calibration_loss'](theta,origins)
            difference=abs(ours-original);assert difference<1e-13,difference;equivalence.append(difference)
    theta=old.copy();_,grad=f.objective(theta,TRAIN);epsilon=1e-6
    finite=np.array([(f.objective(theta+np.eye(13)[i]*epsilon,TRAIN)[0]-f.objective(theta-np.eye(13)[i]*epsilon,TRAIN)[0])/(2*epsilon) for i in range(13)])
    assert np.max(np.abs(grad-finite))<1e-7
    cv=[]
    for scale in SCALES:
        scores=[]
        for origin in TRAIN:
            fit=f.fit([o for o in TRAIN if o!=origin],scale)
            score=f.metrics(fit.x,[origin])['weighted_rmse'];scores.append(score)
            cv.append({'scale':scale,'heldout_origin':origin,'weighted_rmse':score})
        print('Origin CV',scale,np.mean(scores),flush=True)
    table=pd.DataFrame(cv);table.to_csv(OUT/'irs-origin-cv.csv',index=False)
    means=table.groupby('scale').weighted_rmse.agg(['mean','std','count']);means['se']=means['std']/np.sqrt(means['count'])
    best=means['mean'].idxmin();cutoff=means.loc[best,'mean']+means.loc[best,'se']
    selected=float(max(means[means['mean']<=cutoff].index));print('Predeclared one-SE selected regularization scale',selected,flush=True)
    train_fit=f.fit(TRAIN,selected);default_train=f.fit(TRAIN,1.)
    evaluation={'prior':f.metrics(f.initial,HOLDOUT),'historical_regularization_refit':f.metrics(default_train.x,HOLDOUT),
        'cv_selected_training_fit':f.metrics(train_fit.x,HOLDOUT)}
    # If the predeclared candidate does not beat the already published model on
    # held-out origins, retain the published fit. Never tune another candidate
    # after examining this validation outcome.
    candidate_accepted=evaluation['cv_selected_training_fit']['weighted_rmse']<evaluation['historical_regularization_refit']['weighted_rmse']
    starts=[f.initial,old,np.clip(f.initial+np.random.default_rng(4403).normal(0,.02,13),*np.array(f.bounds).T)]
    fits=[f.fit(ns['STATE_CODES'],selected,s) for s in starts]
    best_start=min(range(len(fits)),key=lambda i:fits[i].fun);final=fits[best_start]
    chosen=final.x if candidate_accepted else old
    chosen_scale=selected if candidate_accepted else 1.
    # Conditional origin-cluster bootstrap describes stability, not causal identification.
    rng=np.random.default_rng(4403);boot=[]
    for i in range(200):
        origins=rng.choice(ns['STATE_CODES'],size=8,replace=True).tolist()
        fit=f.fit(origins,chosen_scale,chosen)
        boot.append(fit.x[:6])
    boot=np.array(boot);pd.DataFrame(boot,columns=NAMES).to_csv(OUT/'irs-cluster-bootstrap.csv',index=False)
    ranges={k:{'chosen':float(chosen[i]),'bootstrap_p025':float(np.quantile(boot[:,i],.025)),'bootstrap_p975':float(np.quantile(boot[:,i],.975))} for i,k in enumerate(NAMES)}
    # Repeating the deterministic optimizer from the same start is the reproducibility check.
    repeat_same=f.fit(ns['STATE_CODES'],selected,starts[best_start])
    assert np.max(np.abs(repeat_same.x-final.x))<1e-12
    report={'method':'Same four-group mixture probability and regularized weighted MSE as original; analytic gradient numerically checked; deterministic bounded L-BFGS-B.',
        'original_objective_max_difference':max(equivalence),'gradient_max_difference':float(np.max(np.abs(grad-finite))),
        'training_origins':TRAIN,'historical_holdout_origins':HOLDOUT,'regularization_scales':SCALES,'cv_summary':means.reset_index().to_dict('records'),
        'selection_rule':'Largest penalty within one standard error of the smallest mean leave-one-training-origin-out RMSE; no holdout tuning.',
        'selected_scale':selected,'heldout_evaluation':evaluation,'candidate_adopted':bool(candidate_accepted),
        'adoption_rule':'Adopt preselected candidate only if it improves the historical two-origin holdout RMSE over a fresh default-penalty training fit; otherwise retain original published parameters without further tuning.',
        'chosen_scale':chosen_scale,'chosen_theta':chosen.tolist(),'original_theta':old.tolist(),'candidate_final_theta':final.x.tolist(),
        'chosen_all_origin_metrics':f.metrics(chosen,ns['STATE_CODES']),'coefficient_stability':ranges,
        'deterministic_optimizer_repeat_max_difference':float(np.max(np.abs(repeat_same.x-final.x))),
        'limitations':['IRS tax-return routes are a macro proxy, not young-adult-only data.','The historical holdout was already examined during earlier development; it is not new external validation.','Only eight origin clusters; bootstrap intervals are conditional on fixed priors, bounds and penalty and do not identify causal effects.'],
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'raw-rebuild/state-inputs-reconstructed.csv',ROOT/'raw-rebuild/irs-routes-reconstructed.csv',ROOT/'download/CITS4403-GROUP-PROJECT-master/0914-1_v8.ipynb']},'seconds':time.monotonic()-start}
    (OUT/'irs-fit-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('IRS fit complete',evaluation,'adopted',candidate_accepted,flush=True)

if __name__=='__main__':main()
