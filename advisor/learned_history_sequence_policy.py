"""Stateless fixed-window GRU inside maintained masked PPO, no hidden-state API."""
import torch
from torch import nn
from advisor.learned_history_sequence import OLD_DIMENSION,CAPACITY,ROW,FIELDS,META,VERSIONS
from advisor.learned_public_categories_policy import decode_bits,LATENT_CONTEXT,LATENT_ACTION
from advisor.learned_strategic_public import EXTRA as STRATEGIC_EXTRA,VERSION as V4
from advisor.learned_strategic_public_policy import StrategicPublicCategoricalExtractor,StrategicPublicCategoricalPolicy

HIDDEN=16
NEW_CONTEXT=HIDDEN+META-1
OLD_CONTEXT=LATENT_CONTEXT+STRATEGIC_EXTRA


class PublicHistorySequenceExtractor(StrategicPublicCategoricalExtractor):
    def __init__(self):
        super().__init__()
        self.history_embeddings=nn.ModuleDict({"event":nn.Embedding(64,8,padding_idx=0),
            "appearance":nn.Embedding(128,8,padding_idx=0),"detail":nn.Embedding(128,8,padding_idx=0)})
        self.history_gru=nn.GRU(116,HIDDEN,batch_first=True)
        self.context[0]=nn.Linear(OLD_CONTEXT+NEW_CONTEXT,64)
        self.critic[0]=nn.Linear(OLD_CONTEXT+NEW_CONTEXT+LATENT_ACTION,128)

    def _public_rows(self,features):
        old=features[:,:OLD_DIMENSION]
        sequence=features[:,OLD_DIMENSION:OLD_DIMENSION+CAPACITY*ROW].reshape(-1,CAPACITY,ROW)
        meta=features[:,-META:]
        if features.shape[1]!=OLD_DIMENSION+CAPACITY*ROW+META or not torch.all((meta==0)|(meta==1)):
            raise ValueError("invalid_public_sequence_meta")
        offset=0;values=[]
        for name,width in FIELDS:
            tokens=decode_bits(sequence[:,:,offset:offset+width]);offset+=width
            if name in ("actor","recipient"):
                if (tokens>66).any():raise ValueError("invalid_sequence_appearance_reference")
                embedding=self.history_embeddings["appearance"]
            elif name in ("event","detail"):embedding=self.history_embeddings[name]
            else:embedding=self.embeddings["category_"+ ("species" if name.endswith("species") else name)]
            values.append(embedding(tokens))
        numeric=sequence[:,:,offset:]
        if not torch.isfinite(numeric).all() or (numeric.abs()>1).any():raise ValueError("invalid_public_sequence_numeric")
        presence=numeric[:,:,0]
        if not torch.all((presence==0)|(presence==1)) or (presence[:,1:]>presence[:,:-1]).any():
            raise ValueError("invalid_public_sequence_padding")
        values.append(numeric)
        # A fresh zero hidden state is implicit in every independent call.
        output,_=self.history_gru(torch.cat(values,dim=-1))
        length=presence.sum(1).long()
        summary=output[torch.arange(len(output),device=output.device),(length-1).clamp(min=0)]*(length>0)[:,None]
        added=torch.cat((summary,meta[:,1:]),dim=1)*meta[:,:1]
        context,actions,mask=super()._public_rows(old)
        return torch.cat((context,added),dim=1),actions,mask

    def _actor(self,context,actions):
        shared=self.context(context)[:,None,:].expand(-1,35,-1)
        return self.scorer(torch.cat((shared,actions),dim=-1)).squeeze(-1)

    def _critic(self,context,actions,mask):
        pooled=(actions*mask).sum(1)/mask.sum(1).clamp(min=1)
        return self.critic(torch.cat((context,pooled),dim=1))

    def forward(self,features):
        context,actions,mask=self._public_rows(features)
        return self._actor(context,actions),self._critic(context,actions,mask)

    def forward_actor(self,features):
        context,actions,_=self._public_rows(features)
        return self._actor(context,actions)

    def forward_critic(self,features):
        context,actions,mask=self._public_rows(features)
        return self._critic(context,actions,mask)


class PublicHistorySequencePolicy(StrategicPublicCategoricalPolicy):
    def _build_mlp_extractor(self):self.mlp_extractor=PublicHistorySequenceExtractor()


def transfer_history_sequence_weights(target,source,target_encoder,source_encoder):
    if (type(source) is not StrategicPublicCategoricalPolicy or type(target) is not PublicHistorySequencePolicy
            or source_encoder.version!=V4 or target_encoder.version not in VERSIONS
            or source_encoder.catalog_fingerprint!=target_encoder.base.catalog_fingerprint
            or source_encoder.tokens!=target_encoder.tokens or next(target.parameters()).device.type!="cpu"):
        raise ValueError("v4_to_public_sequence_cpu_transfer_contract_required")
    # Same new-path tensors in ALL four arms, independent sampling seeds later.
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(91001)
        for embedding in target.mlp_extractor.history_embeddings.values():embedding.reset_parameters()
        target.mlp_extractor.history_gru.reset_parameters()
    old,new=source.state_dict(),target.state_dict()
    with torch.no_grad():
        for key,value in old.items():
            if key=="mlp_extractor.context.0.weight":
                new[key].zero_();new[key][:,:OLD_CONTEXT]=value
            elif key=="mlp_extractor.critic.0.weight":
                new[key].zero_();new[key][:,:OLD_CONTEXT]=value[:,:OLD_CONTEXT]
                new[key][:,OLD_CONTEXT+NEW_CONTEXT:]=value[:,OLD_CONTEXT:]
            else:
                if new[key].shape!=value.shape:raise ValueError("sequence_transfer_unexpected_tensor_shape")
                new[key].copy_(value)
        target.load_state_dict(new)
    target.optimizer=target.optimizer_class(target.parameters(),lr=target.optimizer.param_groups[0]["lr"],**target.optimizer_kwargs)
