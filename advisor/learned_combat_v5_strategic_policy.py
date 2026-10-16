"""Proper-scored prediction bottleneck plus conditional tactical references."""
import torch
from torch import nn
from advisor.learned_combat_v5_policy import IntegratedCombatV5Extractor,OLD_CONTEXT,HIST_CONTEXT,HP_EXTRA
from advisor.learned_combat_v5 import SIZES,OLD_DIM
from advisor.learned_combat_v5_strategic import VERSION,PREFIX,DIMENSION,REF_WIDTH,PRIOR_SIZES,priors
from advisor.learned_combat_v5_references import WIDTH,TYPE_WIDTH
from advisor.learned_public_categories_policy import LATENT_ACTION
from advisor.learned_strategic_public_policy import StrategicPublicCategoricalPolicy
from advisor.learned_encoder import TYPES

PRED_CONTEXT=16+12+12+16+1+4
NEW_CONTEXT=HIST_CONTEXT+HP_EXTRA+PRED_CONTEXT
NEW_ACTION=4+10+WIDTH+1

class StrategicCombatV5Extractor(IntegratedCombatV5Extractor):
    def __init__(self):
        super().__init__()
        self.prediction_heads['head_action']=nn.Linear(64,PRIOR_SIZES['action'])
        self.context[0]=nn.Linear(OLD_CONTEXT+NEW_CONTEXT,64)
        self.scorer[0]=nn.Linear(64+LATENT_ACTION+NEW_ACTION,128)
        self.critic[0]=nn.Linear(OLD_CONTEXT+NEW_CONTEXT+LATENT_ACTION+NEW_ACTION,128)
        # Fixed public canonical move types; no set or opponent choice attached.
        from advisor.learned_combat_v5 import IntegratedCombatV5Encoder
        from pathlib import Path
        catalog=Path(__file__).resolve().parents[1]/'models/showdown_mc_domain_v1/catalog.json'
        tokens=IntegratedCombatV5Encoder(catalog).tokens['moves'];table=torch.zeros((PRIOR_SIZES['action'],TYPE_WIDTH))
        for name,token in tokens.items():
            m=priors()[0]['native_moves'].get(name,{})
            if m.get('category') in ('Physical','Special') and m.get('type') in TYPES:table[token,TYPES.index(m['type'])]=1
        self.register_buffer('action_type_table',table)

    def _prediction_input(self,public_context,auxiliary):
        # Belief likelihood cannot overwrite combat trunk; PPO cannot turn head
        # logits into arbitrary latent codes. Updated predictions still change
        # actor features on the next forward pass.
        return public_context.detach()

    def components(self,features,*,auxiliary=False):
        if features.shape[1]!=DIMENSION:raise ValueError('strategic_v5_input_shape')
        values=list(super().components(features[:,:PREFIX],auxiliary=auxiliary))
        refs=features[:,PREFIX:PREFIX+35*REF_WIDTH].reshape(-1,35,REF_WIDTH)
        if not torch.isfinite(refs).all() or (refs.abs()>4).any():raise ValueError('invalid_public_reference_values')
        offset=PREFIX+35*REF_WIDTH;baseline={}
        for k,n in PRIOR_SIZES.items():
            p=features[:,offset:offset+n];offset+=n
            if not torch.isfinite(p).all() or (p<0).any() or (p>1).any():raise ValueError('invalid_public_prior')
            if k!='moves' and not torch.allclose(p.sum(1),torch.ones_like(p[:,0]),atol=1e-5):raise ValueError('unnormalized_public_prior')
            baseline[k]=p
        logits,support=values[6],values[7];support['action']=(baseline['action']>0).to(features)
        for k in logits:
            p=baseline[k].clamp(1e-6,1-1e-6)
            prior=p.log()-torch.log1p(-p) if k=='moves' else p.log()
            logits[k]=prior+2*torch.tanh(logits[k]/2)
        return (*values,refs,baseline)

    def predictions(self,features,*,auxiliary=False):
        v=self.components(features,auxiliary=auxiliary)
        return v[6],v[7],v[8],v[9]

    def _public_rows(self,features):
        context,actions,mask,hp,chp,tactic,logits,support,known,km,refs,baseline=self.components(features)
        summaries=[];entropy=[]
        for k in ('moves','abilities','items'):
            z=logits[k].detach()
            if k=='moves':
                p=torch.maximum(z.sigmoid()*support[k],km);w=p/p.sum(1,keepdim=True).clamp(min=1e-6)
            else:
                w=z.masked_fill(~support[k].bool(),-1e8).softmax(1)
                one=torch.nn.functional.one_hot(known[k],SIZES[k]).to(w)
                w=torch.where((known[k]>1)[:,None],one,w)
            summaries.append(w@self.embeddings['category_'+k].weight)
            entropy.append(-(w*w.clamp(min=1e-8).log()).sum(1,keepdim=True)/8)
        ap=logits['action'].detach().masked_fill(~support['action'].bool(),-1e8).softmax(1)
        summaries.extend([ap[:,:SIZES['moves']]@self.embeddings['category_moves'].weight,ap[:,-1:]])
        entropy.append(-(ap*ap.clamp(min=1e-8).log()).sum(1,keepdim=True)/8)
        threat=(refs[:,:,WIDTH:]*(ap@self.action_type_table)[:,None,:]).sum(-1,keepdim=True)
        return torch.cat((context,hp,*summaries,*entropy),dim=1),torch.cat((actions,chp,tactic,refs[:,:,:WIDTH],threat),dim=-1),mask

class StrategicCombatV5Policy(StrategicPublicCategoricalPolicy):
    def _build_mlp_extractor(self):self.mlp_extractor=StrategicCombatV5Extractor()
    def _build(self,lr_schedule):
        super()._build(lr_schedule)
        # SB3 orthogonal initialization runs after extractor construction.
        with torch.no_grad():
            for head in self.mlp_extractor.prediction_heads.values():head.weight.zero_();head.bias.zero_()
    def opponent_predictions(self,features,*,auxiliary=False):return self.mlp_extractor.predictions(features,auxiliary=auxiliary)
    def opponent_prior_predictions(self,features):return self.mlp_extractor.components(features)[-1]

def transfer_strategic_combat_v5_weights(target,source,target_encoder,source_encoder):
    if (type(source) is not StrategicPublicCategoricalPolicy or type(target) is not StrategicCombatV5Policy
        or source_encoder.version!='showdown-public-categorical-observation-v4' or target_encoder.version!=VERSION
        or source_encoder.tokens!=target_encoder.tokens or source_encoder.catalog_fingerprint!=target_encoder.base.catalog_fingerprint):
        raise ValueError('strict_v4_to_strategic_v5_transfer_required')
    old,new=source.state_dict(),target.state_dict()
    with torch.no_grad():
        for k,v in old.items():
            if k=='mlp_extractor.context.0.weight':new[k].zero_();new[k][:,:OLD_CONTEXT]=v
            elif k=='mlp_extractor.scorer.0.weight':new[k].zero_();new[k][:,:64+LATENT_ACTION]=v
            elif k=='mlp_extractor.critic.0.weight':
                new[k].zero_();new[k][:,:OLD_CONTEXT]=v[:,:OLD_CONTEXT];new[k][:,OLD_CONTEXT+NEW_CONTEXT:OLD_CONTEXT+NEW_CONTEXT+LATENT_ACTION]=v[:,OLD_CONTEXT:]
            else:
                if new[k].shape!=v.shape:raise ValueError('strategic_transfer_shape')
                new[k].copy_(v)
        target.load_state_dict(new)
    target.optimizer=target.optimizer_class(target.parameters(),lr=target.optimizer.param_groups[0]['lr'],**target.optimizer_kwargs)
