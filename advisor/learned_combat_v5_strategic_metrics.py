"""Held-out proper scores versus public-only priors; private labels loss-only."""
import numpy as np
import torch
from advisor.learned_combat_v5_strategic_aux import supervision_targets
from advisor.learned_combat_v5 import FAMILIES
from advisor.learned_combat_v5_strategic import PREFIX,REF_WIDTH
from advisor.learned_combat_v5_references import FIELDS

def score(p,y):
    p=np.asarray(p,dtype=float);p=p/max(p.sum(),1e-12)
    confidence=float(p.max());correct=int(p.argmax()==y)
    return {'n':1,'correct':correct,'top5':int(y in np.argsort(p)[-5:]),
      'nll_sum':float(-np.log(max(p[y],1e-12))),'brier_sum':float((p*p).sum()-2*p[y]+1),
      'bins':{str(min(9,int(confidence*10))):[1,confidence,correct]}}

def merge(target,row):
    for k,v in row.items():
        if isinstance(v,dict):merge(target.setdefault(k,{}),v)
        elif isinstance(v,list):target[k]=[a+b for a,b in zip(target.get(k,[0]*len(v)),v)]
        else:target[k]=target.get(k,0)+v

class StrategicV5PredictionMetrics:
    def __init__(self):self.stats={'sampled_public_decisions':0,'categorical':{},'moves':{},'reference_coverage':{}}
    @property
    def rows(self):return self.stats['sampled_public_decisions']
    def observe(self,player,before,opponent_before,after):
        y=supervision_targets(before,opponent_before,after['public_history'][len(before['public_history']):],player.encoder)
        x=torch.tensor(player.encoder.encode(before))[None]
        with torch.no_grad():
            logits,support,_,km=player.model.policy.opponent_predictions(x)
            prior=player.model.policy.opponent_prior_predictions(x)
        self.observe_arrays(x.numpy()[0],y,logits,support,km,prior)
    def observe_arrays(self,x,y,logits,support,km,prior):
        self.stats['sampled_public_decisions']+=1
        for kind in ('action','abilities','items'):
            target=y[kind];row=self.stats['categorical'].setdefault(kind,{})
            if target<0 or kind!='action' and not y['unknown_'+kind]:continue
            mask=support[kind][0].cpu().numpy().astype(bool)
            if not mask[target]:merge(row,{'out_of_public_support':1});continue
            model=logits[kind][0].masked_fill(~support[kind][0].bool(),-1e8).softmax(0).cpu().numpy()
            for name,p in [('model',model),('train_species_frequency_prior',prior[kind][0].cpu().numpy()),('public_possibility_uniform',mask/mask.sum())]:
                merge(row.setdefault(name,{}),score(p,target))
            if kind=='action':
                family=FAMILIES[y['action_family']] if y['action_family']>=0 else 'unclassified'
                for name,p in [('model',model),('prior',prior[kind][0].cpu().numpy())]:
                    merge(row.setdefault('by_executed_family',{}).setdefault(family,{}).setdefault(name,{}),score(p,target))
        if y['moves_complete']:
            mask=support['moves'][0].cpu().numpy().astype(bool);truth=np.zeros(len(mask));truth[[t for t in y['moves'] if t>0]]=1
            row=self.stats['moves']
            if truth[~mask].any():merge(row,{'out_of_public_support':1})
            else:
                mask &= ~km[0].cpu().numpy().astype(bool)
                if mask.any():
                    for name,p in [('model',logits['moves'][0].sigmoid().cpu().numpy()),('train_species_frequency_prior',prior['moves'][0].cpu().numpy()),('public_possibility_uniform',np.full(len(mask),min(.95,4/mask.sum())))]:
                        p=np.asarray(p,dtype=float);q=np.clip(p,1e-8,1-1e-8);t=truth[mask];top=np.argsort(np.where(mask,p,-1))[-min(4,int(mask.sum())):]
                        merge(row.setdefault(name,{}),{'rows':1,'unknown_cells':int(mask.sum()),'positive_cells':int(t.sum()),
                          'bce_sum':float((-t*np.log(q[mask])-(1-t)*np.log(1-q[mask])).sum()),'brier_sum':float(((p[mask]-t)**2).sum()),
                          'top4_hits':int(truth[top].sum()),'predicted_count_sum':float(p[mask].sum())})
        refs=x[PREFIX:PREFIX+35*REF_WIDTH].reshape(35,REF_WIDTH)
        for i,name in enumerate(FIELDS):
            if name.endswith(('available','known','unknown','effect','reference')) or name=='known_ability_blocks':
                merge(self.stats['reference_coverage'],{name+'_rows':int(np.count_nonzero(refs[:,i]))})
    def result(self):
        return {'schema_version':'showdown-v5-strategic-heldout-metrics-v3','scope':'first_up_to_8_nonwait_public_decisions_per_battle_unknown_labels_only',**self.stats}
