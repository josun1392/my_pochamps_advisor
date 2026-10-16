"""Training-only targets/losses. Private labels never enter a policy forward.

The actor/critic and prediction heads all see the same public feature tensor.
Only a separate loss receives native opponent-owned request ground truth.
"""
import numpy as np
import torch
from torch.nn import functional as F
from advisor.learned_combat_v5 import VERSION, FAMILIES, SIZES, active_public, current_public_prediction_knowledge
from advisor.learned_encoder import identifier
from advisor.learned_regularized_ppo import RegularizedMaskablePPO

AUX_VERSION="showdown-combat-v5-supervision-v1"


def auxiliary_contract():
    return {"schema_version":AUX_VERSION,"coefficient":.02,"shared_encoder_gradient_scale":.1,
            "target_loss_weights":{"action":1.,"abilities":1.,"items":1.,"moves":1.},
            "loss":"mean_of_available_cross_entropy_or_legal_support_binary_cross_entropy",
            "scope":"next_public_executed_event_family_and_predecision_current_active_opponent_request",
            "negative_labels":"only_complete_current_native_move_list_legal_support",
            "rewards":"unchanged_native_terminal_no_auxiliary_reward",
            "forward":"public_features_only_no_teacher_forcing_private_labels",
            "collection":"fresh_current_rollout_only_no_cross_episode_label_shift"}


def next_public_family(events,role,catalog,tactics):
    for line in events:
        p=line.split("|")
        if len(p)<3 or not p[2].startswith(role+"a: "):continue
        if p[1]=="switch":return FAMILIES.index("switch")
        # Drag/cant/cancelled/unobserved selection is not an executed action label.
        if p[1] in {"drag","cant","faint"}:return -1
        if p[1]!="move" or len(p)<4 or any(x.startswith("[from]") for x in p[4:]):continue
        mid=identifier(p[3]);m=catalog["moves"].get(mid);t=tactics["moves"].get(mid,{})
        if m is None:return -1
        if mid in {"protect","detect","endure","substitute","kingsshield","banefulbunker","spikyshield","silktrap","burningbulwark","obstruct"}:kind="defense"
        elif mid in {"wish","rest","roost","slackoff","recover","softboiled","milkdrink","morningsun","moonlight","synthesis","shoreup","strengthsap","lifedew"}:kind="recovery"
        elif m.get("category") in {"Physical","Special"}:kind="attack"
        elif t.get("target")=="self" and any(v>0 for v in t.get("boosts",{}).values()):kind="setup"
        else:kind="status_or_field"
        return FAMILIES.index(kind)
    return -1


def supervision_targets(public_before,opponent_before,events,encoder):
    """Explicit predecision active target, NOT the newly switched-in actor.

    Opponent request is coordinator-only. Do not call this function from encode,
    infer, get_distribution, predict_values, or an inference feature producer.
    """
    role="p2" if public_before["side"]=="self" else "p1"
    side=opponent_before["own_request"].get("side",{})
    if side and side.get("id")!=role:raise ValueError("v5_supervision_wrong_owner")
    actor=next((p for p in side.get("pokemon",[]) if p.get("active")),None)
    row={"schema_version":AUX_VERSION,"action":next_public_family(events,role,encoder.catalog,encoder.tactics),
         "abilities":-1,"items":-1,"moves":[0]*4,"moves_complete":False,
         "unknown_abilities":isinstance(current_public_prediction_knowledge(public_before)["abilities"],dict),
         "unknown_items":isinstance(current_public_prediction_knowledge(public_before)["items"],dict)}
    if actor is not None:
        for kind,key in (("abilities","ability"),("items","item")):
            value=actor.get(key)
            if isinstance(value,str):row[kind]=encoder.token(kind,value) if value else 2
        moves=actor.get("moves",[])
        if 1<=len(moves)<=4:
            tokens=[encoder.token("moves",m) for m in moves]
            if all(t>2 for t in tokens):
                row["moves"]=tokens+[0]*(4-len(tokens));row["moves_complete"]=True
    return row


def supervised_loss(policy,observations,labels):
    logits,supports,_,_=policy.opponent_predictions(observations,auxiliary=True)
    metrics={};losses=[]
    for kind in ("action","abilities","items"):
        target=torch.as_tensor([x[kind] for x in labels],device=observations.device)
        valid=target>=0
        if kind!="action":
            valid &= supports[kind].gather(1,target.clamp(min=0)[:,None]).squeeze(1).bool()
            scores=logits[kind].masked_fill(~supports[kind].bool(),-1e8)
        else:scores=logits[kind]
        metrics[kind+"_targets"]=int(valid.sum())
        if valid.any():
            loss=F.cross_entropy(scores[valid],target[valid]);losses.append(loss)
            metrics[kind+"_loss"]=float(loss.detach())
            metrics[kind+"_accuracy"]=float((scores[valid].argmax(1)==target[valid]).float().mean())
    complete=torch.as_tensor([x["moves_complete"] for x in labels],device=observations.device)
    targets=torch.zeros_like(logits["moves"])
    indices=torch.as_tensor([x["moves"] for x in labels],device=observations.device)
    targets.scatter_(1,indices,1);targets[:,0]=0
    complete &= ~((targets>0)&(~supports["moves"].bool())).any(1)
    mask=supports["moves"]*complete[:,None]
    metrics["moves_targets"]=int(complete.sum())
    if mask.any():
        loss=(F.binary_cross_entropy_with_logits(logits["moves"],targets,reduction="none")*mask).sum()/mask.sum()
        losses.append(loss);metrics["moves_loss"]=float(loss.detach())
    loss=torch.stack(losses).mean() if losses else sum(v.sum()*0 for v in logits.values())
    if not torch.isfinite(loss):raise ValueError("nonfinite_v5_auxiliary_loss")
    return loss,metrics


class IntegratedCombatV5PPO(RegularizedMaskablePPO):
    """Maintained PPO optimizer/GAE; separate bounded supervised entropy seam."""
    def _excluded_save_params(self):
        return super()._excluded_save_params()+["_auxiliary_rows","_auxiliary_observations"]
    def auxiliary_metadata(self):return auxiliary_contract()
    def begin_auxiliary_rollout(self):self._auxiliary_rows=[]
    def record_auxiliary(self,infos):
        rows=[info.get("coordinator_v5_supervision") for info in infos]
        if any(not isinstance(r,dict) or r.get("schema_version")!=AUX_VERSION for r in rows):
            raise ValueError("v5_supervision_missing_or_mistimed")
        self._auxiliary_rows.extend(rows)
        if not hasattr(self,"v5_target_counts"):self.v5_target_counts={}
        for row in rows:
            names=["public_decisions", *(["action:"+FAMILIES[row["action"]]] if row["action"]>=0 else ["unobserved_action_no_label"])]
            names += [kind+":"+("unknown" if row["unknown_"+kind] else "publicly_known") for kind in ("abilities","items") if row[kind]>=0]
            if row["moves_complete"]:names.append("complete_current_moves_loss_targets")
            for name in names:self.v5_target_counts[name]=self.v5_target_counts.get(name,0)+1
    def freeze_auxiliary_rollout(self):
        # Same time-major order as the appended targets, before SB3 swaps axes.
        self._auxiliary_observations=self.rollout_buffer.observations.reshape(-1,self.observation_space.shape[0]).copy()
        if len(self._auxiliary_rows)!=len(self._auxiliary_observations):raise ValueError("v5_rollout_target_alignment")
    def train(self):
        if not hasattr(self,"_auxiliary_rows") or len(self._auxiliary_rows)!=self.n_steps*self.n_envs:
            raise ValueError("v5_training_requires_aligned_coordinator_supervision")
        if self.ent_coef<=0:raise ValueError("v5_auxiliary_requires_entropy_seam")
        original=self.policy.evaluate_actions;had="evaluate_actions" in self.policy.__dict__;old=self.policy.__dict__.get("evaluate_actions")
        losses=[];entropies=[];last={}
        def evaluate(obs,actions,action_masks=None):
            nonlocal last
            values,logp,entropy=original(obs,actions,action_masks=action_masks)
            # Does not call get_distribution: the PPO action distribution and
            # legality state used by the enclosing KL regularizer stay intact.
            ids=np.random.randint(0,len(self._auxiliary_rows),size=min(128,len(obs)))
            x=torch.as_tensor(self._auxiliary_observations[ids],device=self.device)
            loss,last=supervised_loss(self.policy,x,[self._auxiliary_rows[i] for i in ids])
            losses.append(float(loss.detach()));entropies.append(float(entropy.detach().mean()))
            return values,logp,entropy-(auxiliary_contract()["coefficient"]/self.ent_coef)*loss
        self.policy.evaluate_actions=evaluate
        try:super().train()
        finally:
            if had:self.policy.evaluate_actions=old
            else:del self.policy.evaluate_actions
        self.logger.record("train/v5_auxiliary_loss",float(np.mean(losses)))
        self.logger.record("train/v5_auxiliary_weighted_loss",.02*float(np.mean(losses)))
        self.logger.record("train/true_action_entropy",float(np.mean(entropies)))
        for k,v in last.items():self.logger.record("train/v5_"+k,v)
