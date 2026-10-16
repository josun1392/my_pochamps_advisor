"""One compact V5 for transferred and scratch PPO; all forward inputs public."""
import torch
from torch import nn
from advisor.learned_combat_v5 import (VERSION, APPEARANCE_SUPPORT_VERSION, VERSIONS, OLD_DIM, DIMENSION, HP_EXTRA, HISTORY_EXTRA,
    TACTICAL, SIZES, SUPPORT, KNOWN_BITS, FAMILIES)
from advisor.learned_history_sequence_policy import PublicHistorySequenceExtractor, NEW_CONTEXT as HIST_CONTEXT, OLD_CONTEXT
from advisor.learned_strategic_public_policy import StrategicPublicCategoricalPolicy
from advisor.learned_public_categories_policy import decode_bits, LATENT_ACTION
from advisor.learned_public_categories import BASE_ACTION, ACTION, REFERENCE_BITS, BITS
from advisor.learned_strategic_public import CONTEXT

PRED_CONTEXT = 16+12+12+len(FAMILIES)+3  # expected categorical embeddings + uncertainty
PUBLIC_CONTEXT = OLD_CONTEXT+HIST_CONTEXT+HP_EXTRA
NEW_CONTEXT = HIST_CONTEXT+HP_EXTRA+PRED_CONTEXT
NEW_ACTION = 4+TACTICAL


class IntegratedCombatV5Extractor(PublicHistorySequenceExtractor):
    def __init__(self):
        super().__init__()
        self.prediction_encoder=nn.Sequential(nn.Linear(PUBLIC_CONTEXT,64),nn.Tanh())
        self.prediction_heads=nn.ModuleDict({
            "head_action":nn.Linear(64,len(FAMILIES)),
            **{"head_"+k:nn.Linear(64,n) for k,n in SIZES.items()}})
        self.context[0]=nn.Linear(OLD_CONTEXT+NEW_CONTEXT,64)
        self.scorer[0]=nn.Linear(64+LATENT_ACTION+NEW_ACTION,128)
        self.critic[0]=nn.Linear(OLD_CONTEXT+NEW_CONTEXT+LATENT_ACTION+NEW_ACTION,128)

    def _prediction_input(self,public_context,auxiliary):
        return public_context.detach()+.1*(public_context-public_context.detach()) if auxiliary else public_context

    def components(self,features,*,auxiliary=False):
        if features.shape[1]!=DIMENSION:raise ValueError("v5_input_shape_mismatch")
        offset=OLD_DIM
        hp=features[:,offset:offset+HP_EXTRA];offset+=HP_EXTRA
        if not torch.isfinite(hp).all() or (hp<0).any() or (hp>4).any():raise ValueError("invalid_v5_own_hp")
        hp_rows=hp.reshape(-1,6,4)
        if not torch.all((hp_rows[:,:,2:]==0)|(hp_rows[:,:,2:]==1)):raise ValueError("invalid_v5_hp_knowledge")
        sequence=features[:,offset:offset+HISTORY_EXTRA];offset+=HISTORY_EXTRA
        context,actions,mask=super()._public_rows(torch.cat((features[:,:OLD_DIM],sequence),dim=1))
        raw=features[:,CONTEXT:OLD_DIM].reshape(-1,35,ACTION)
        refs=decode_bits(raw[:,:,BASE_ACTION-1:BASE_ACTION-1+REFERENCE_BITS])
        if (refs>6).any():raise ValueError("v5_nonown_candidate_hp_binding")
        bank=torch.cat((hp_rows.new_zeros((len(hp_rows),1,4)),hp_rows),dim=1)
        candidate_hp=bank.gather(1,refs[:,:,None].expand(-1,-1,4))
        tactic=features[:,offset:offset+35*TACTICAL].reshape(-1,35,TACTICAL);offset+=35*TACTICAL
        if not torch.isfinite(tactic).all() or (tactic.abs()>4).any():raise ValueError("invalid_v5_tactical_feature")
        public_context=torch.cat((context,hp),dim=1)
        # Auxiliary gradients to the reused public encoder are deliberately 0.1x.
        input_context=self._prediction_input(public_context,auxiliary)
        latent=self.prediction_encoder(input_context)
        logits={k.removeprefix("head_"):head(latent) for k,head in self.prediction_heads.items()}
        supports={}
        for k,n in SIZES.items():
            supports[k]=features[:,offset:offset+n];offset+=n
            if not torch.all((supports[k]==0)|(supports[k]==1)) or not supports[k].any(1).all():
                raise ValueError("invalid_v5_public_prediction_support")
        known={}
        for k in ("abilities","items"):
            known[k]=decode_bits(features[:,offset:offset+BITS[k]]);offset+=BITS[k]
        moves_known=features[:,offset:]
        if moves_known.shape[1]!=SIZES["moves"] or not torch.all((moves_known==0)|(moves_known==1)):
            raise ValueError("invalid_v5_known_moves")
        return context,actions,mask,hp,candidate_hp,tactic,logits,supports,known,moves_known

    def predictions(self,features,*,auxiliary=False):
        return self.components(features,auxiliary=auxiliary)[6:]

    def _public_rows(self,features):
        context,actions,mask,hp,chp,tactic,logits,support,known,km=self.components(features)
        summary=[];entropies=[]
        for kind in ("moves","abilities","items"):
            if kind=="moves":
                probabilities=logits[kind].sigmoid()*support[kind]
                probabilities=torch.maximum(probabilities,km)
                weights=probabilities/probabilities.sum(1,keepdim=True).clamp(min=1e-6)
            else:
                weights=logits[kind].masked_fill(~support[kind].bool(),-1e8).softmax(1)
                token=known[kind];is_known=token>1
                if (token>=SIZES[kind]).any():raise ValueError("v5_known_token_out_of_bounds")
                onehot=torch.nn.functional.one_hot(token,SIZES[kind]).to(weights)
                weights=torch.where(is_known[:,None],onehot,weights)
            summary.append(weights@self.embeddings["category_"+kind].weight)
            entropies.append(-(weights*weights.clamp(min=1e-8).log()).sum(1,keepdim=True)/8)
        summary.extend([logits["action"].softmax(1),*entropies])
        return torch.cat((context,hp,*summary),dim=1),torch.cat((actions,chp,tactic),dim=-1),mask


class IntegratedCombatV5Policy(StrategicPublicCategoricalPolicy):
    def _build_mlp_extractor(self):self.mlp_extractor=IntegratedCombatV5Extractor()
    def opponent_predictions(self,features,*,auxiliary=False):
        return self.mlp_extractor.predictions(features,auxiliary=auxiliary)


def transfer_combat_v5_weights(target,source,target_encoder,source_encoder):
    if (type(source) is not StrategicPublicCategoricalPolicy or type(target) is not IntegratedCombatV5Policy
            or source_encoder.version!="showdown-public-categorical-observation-v4" or target_encoder.version not in VERSIONS
            or source_encoder.catalog_fingerprint!=target_encoder.base.catalog_fingerprint
            or source_encoder.tokens!=target_encoder.tokens):
        raise ValueError("strict_v4_to_integrated_v5_transfer_required")
    old,new=source.state_dict(),target.state_dict()
    with torch.no_grad():
        for key,value in old.items():
            if key=="mlp_extractor.context.0.weight":
                new[key].zero_();new[key][:,:OLD_CONTEXT]=value
            elif key=="mlp_extractor.scorer.0.weight":
                new[key].zero_();new[key][:,:64+LATENT_ACTION]=value
            elif key=="mlp_extractor.critic.0.weight":
                new[key].zero_();new[key][:,:OLD_CONTEXT]=value[:,:OLD_CONTEXT]
                new[key][:,OLD_CONTEXT+NEW_CONTEXT:OLD_CONTEXT+NEW_CONTEXT+LATENT_ACTION]=value[:,OLD_CONTEXT:]
            else:
                if new[key].shape!=value.shape:raise ValueError("v5_transfer_unexpected_shape")
                new[key].copy_(value)
        target.load_state_dict(new)
    target.optimizer=target.optimizer_class(target.parameters(),lr=target.optimizer.param_groups[0]["lr"],**target.optimizer_kwargs)


def transfer_combat_v5_appearance_weights(target,source,target_encoder,source_encoder):
    """Explicit same-layout v1->v2 migration; fresh Adam, changed public support.

    Weights are identical; inference on repaired appearance-support states may
    change. This is never an encoder relabel or uninterrupted optimizer resume.
    """
    if (type(source) is not IntegratedCombatV5Policy or type(target) is not IntegratedCombatV5Policy
            or source_encoder.version!=VERSION or target_encoder.version!=APPEARANCE_SUPPORT_VERSION
            or source_encoder.tokens!=target_encoder.tokens
            or source_encoder.base.catalog_fingerprint!=target_encoder.base.catalog_fingerprint):
        raise ValueError("strict_integrated_v5_v1_to_v2_migration_required")
    target.load_state_dict(source.state_dict(),strict=True)
    target.optimizer=target.optimizer_class(target.parameters(),lr=target.optimizer.param_groups[0]["lr"],**target.optimizer_kwargs)
