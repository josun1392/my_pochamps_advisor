"""Properly timed likelihood losses; private supervision is loss-only."""
import numpy as np
import torch
from torch.nn import functional as F
from advisor.learned_combat_v5_aux import IntegratedCombatV5PPO,supervision_targets as legacy_targets
from advisor.learned_combat_v5_strategic import VERSION,PRIOR_SIZES

AUX_VERSION='showdown-combat-v5-strategic-supervision-v3'
def auxiliary_contract():
    return {'schema_version':AUX_VERSION,'coefficient':.02,'shared_encoder_gradient_scale':0.,
      'target':'next_public_executed_move_token_or_switch_not_cancelled_private_intent',
      'hidden_targets':'unknown_only_current_predecision_opponent_owned_request_loss_only',
      'loss':'proper_CE_and_per_decision_unknown_move_BCE_no_arbitrary_class_weights',
      'sampler':'public_executed_family_stratified_inverse_proposal_self_normalized_importance',
      'beliefs':'train_only_smoothed_prior_plus_bounded_residual; PPO_stop_gradient_predictions',
      'rewards':'unchanged_native_terminal','rollout':'time_major_current_rollout_only'}

def next_public_action(events,role,encoder):
    for line in events:
        p=line.split('|')
        if len(p)<3 or not p[2].startswith(role+'a: '):continue
        if p[1]=='switch':return PRIOR_SIZES['action']-1
        if p[1] in ('drag','cant','faint'):return -1
        if p[1]=='move' and len(p)>3 and not any(x.startswith('[from]') for x in p[4:]):return encoder.token('moves',p[3])
    return -1

def supervision_targets(public_before,opponent_before,events,encoder):
    row=legacy_targets(public_before,opponent_before,events,encoder)
    row['schema_version']=AUX_VERSION;row['action_family']=row['action']
    row['action']=next_public_action(events,'p2' if public_before['side']=='self' else 'p1',encoder)
    return row

def supervised_loss(policy,observations,labels,weights=None):
    logits,support,_,km=policy.opponent_predictions(observations,auxiliary=True)
    w=torch.ones(len(labels),device=observations.device) if weights is None else torch.as_tensor(weights,device=observations.device,dtype=torch.float32)
    losses=[];metrics={}
    for kind in ('action','abilities','items'):
        y=torch.as_tensor([r[kind] for r in labels],device=observations.device)
        valid=y>=0;valid &= support[kind].gather(1,y.clamp(min=0)[:,None]).squeeze(1).bool()
        if kind!='action':valid &= torch.as_tensor([r['unknown_'+kind] for r in labels],device=observations.device)
        metrics[kind+'_targets']=int(valid.sum())
        if valid.any():
            z=logits[kind].masked_fill(~support[kind].bool(),-1e8)
            per=F.cross_entropy(z[valid],y[valid],reduction='none');loss=(per*w[valid]).sum()/w[valid].sum()
            losses.append(loss);metrics[kind+'_loss']=float(loss.detach());metrics[kind+'_accuracy']=float((z[valid].argmax(1)==y[valid]).float().mean())
    truth=torch.zeros_like(logits['moves']);ids=torch.as_tensor([r['moves'] for r in labels],device=observations.device)
    truth.scatter_(1,ids,1);truth[:,0]=0
    complete=torch.as_tensor([r['moves_complete'] for r in labels],device=observations.device)
    complete &= ~((truth>0)&~support['moves'].bool()).any(1)
    mask=support['moves'].bool()&~km.bool();valid=complete&mask.any(1)
    metrics['moves_targets']=int(valid.sum())
    if valid.any():
        per=(F.binary_cross_entropy_with_logits(logits['moves'],truth,reduction='none')*mask).sum(1)/mask.sum(1).clamp(min=1)
        loss=(per[valid]*w[valid]).sum()/w[valid].sum();losses.append(loss);metrics['moves_loss']=float(loss.detach())
    loss=torch.stack(losses).mean() if losses else sum(v.sum()*0 for v in logits.values())
    if not torch.isfinite(loss):raise ValueError('nonfinite_strategic_auxiliary_loss')
    return loss,metrics

class StrategicCombatV5PPO(IntegratedCombatV5PPO):
    def _excluded_save_params(self):return super()._excluded_save_params()+['_aux_groups','_aux_weights']
    def auxiliary_metadata(self):return auxiliary_contract()
    def begin_auxiliary_rollout(self):super().begin_auxiliary_rollout();self._aux_groups=None
    def record_auxiliary(self,infos):
        rows=[i.get('coordinator_v5_supervision') for i in infos]
        if any(not isinstance(r,dict) or r.get('schema_version')!=AUX_VERSION for r in rows):raise ValueError('strategic_supervision_contract')
        self._auxiliary_rows.extend(rows)
        if not hasattr(self,'v5_target_counts'):self.v5_target_counts={}
        for r in rows:
            for k in ('public_decisions','action_token:'+str(r['action']) if r['action']>=0 else 'unobserved_no_action_label',
                      'action_family:'+str(r['action_family'])):self.v5_target_counts[k]=self.v5_target_counts.get(k,0)+1
    def _auxiliary_indices(self,n):
        if self._aux_groups is None:
            self._aux_groups={}
            for i,r in enumerate(self._auxiliary_rows):self._aux_groups.setdefault(r['action_family'],[]).append(i)
        keys=list(self._aux_groups);groups=np.random.choice(keys,min(128,n));ids=[];weights=[]
        for g in groups:
            pool=self._aux_groups[g];ids.append(pool[np.random.randint(len(pool))]);weights.append(len(pool)*len(keys)/len(self._auxiliary_rows))
        self._aux_weights=weights
        return np.asarray(ids)
    def _supervised_loss(self,observations,labels):return supervised_loss(self.policy,observations,labels,self._aux_weights)
    def train(self):
        super().train();pred=0.;combat=0.
        for name,p in self.policy.named_parameters():
            if p.grad is not None:
                norm=float(p.grad.detach().square().sum())
                if 'prediction_' in name:pred+=norm
                else:combat+=norm
        self.logger.record('train/v5_prediction_gradient_norm',pred**.5)
        self.logger.record('train/v5_combat_gradient_norm',combat**.5)
