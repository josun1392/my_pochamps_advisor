"""Public metadata sharing for offline selected-response prediction only.

No learned move-ID rows, hidden set support, private target mask or search.
P(family|public) * P(revealed move OR unknown family|family,public).
Known candidate identities bind results; their scores share one metadata net.
"""
import numpy as np
import torch
from torch import nn
from advisor.learned_encoder import TYPES, fingerprint
from advisor.learned_response_predictor import ResponseEncoder, FAMILIES, move_family
from advisor.learned_tactics_encoder import TacticalObservationEncoder

VERSION="foundation-public-metadata-hierarchical-response-v1"
FLAGS=("contact","sound","bullet","punch","bite","pulse","slicing","wind")


class MetadataEncoder:
    def __init__(self,public_encoder):
        if not isinstance(public_encoder,ResponseEncoder):raise ValueError("public_response_encoder_required")
        self.public=public_encoder;helper=TacticalObservationEncoder(public_encoder.catalog)
        rows=[]
        for mid in public_encoder.moves:
            native=public_encoder.native[mid];catalog=public_encoder.catalog["moves"].get(mid,{})
            family=move_family(mid,public_encoder.tactics,public_encoder.native)
            row=[float(family==f)for f in FAMILIES]+[float(native.get("type")==t)for t in TYPES]
            row += [float(native.get("category")==c)for c in("Physical","Special","Status")]
            row += [min(float(native.get("power",0))/150,2),float(catalog.get("accuracy",0)),float(native.get("priority",0))/5]
            row += list(helper._tactic(mid))+[float(bool(native.get("flags",{}).get(f)))for f in FLAGS]
            row += [float(bool(native.get("referenceSupported"))),0.]
            rows.append(row)
        width=len(rows[0]);assert all(len(row)==width for row in rows)
        for f in FAMILIES:
            if f=="switch":continue
            row=[0.]*width;row[FAMILIES.index(f)]=1.;row[-1]=1.;rows.append(row)
        row=[0.]*width;row[FAMILIES.index("switch")]=1.;row[-1]=1.;rows.append(row)
        self.metadata=np.asarray(rows,np.float32)
        self.base_dimension=public_encoder.dimension-len(public_encoder.moves)
        self.dimension=self.base_dimension+2*width+7
        self.outputs=public_encoder.outputs;self.family_index=public_encoder.family_index
        self.identity={"schema_version":VERSION,"public_contract":public_encoder.fingerprint,
            "metadata":fingerprint(self.metadata.tolist()),"metadata_width":width,"context_dimension":self.dimension,
            "context":"legacy_numeric_and_apparent_species_no_known_move_ID_columns_plus_revealed_metadata_mean_max_family_counts",
            "decoder":"six_public_families_then_shared_metadata_candidate_scorer",
            "outputs":self.outputs,"candidate_support":"unchanged_revealed_current_actor_moves_plus_unknown5_and_switch",
            "no_learned_move_ID_parameters":True,"private_mask_in_forward_or_normalization":False}
        self.fingerprint=fingerprint(self.identity)

    def context(self,x,support):
        x=np.asarray(x,np.float32);support=np.asarray(support,bool);one=x.ndim==1
        if one:x=x[None];support=support[None]
        m=len(self.public.moves)
        if x.ndim!=2 or x.shape[1]!=self.public.dimension or support.shape!=(len(x),len(self.outputs)):
            raise ValueError("hierarchical_public_transport_shape")
        if not np.array_equal(x[:,-m:].astype(bool),support[:,:m]) or not support[:,m:].all():
            raise ValueError("hierarchical_support_not_public_revelations")
        known=support[:,:m];count=known.sum(1);den=np.maximum(count,1)[:,None]
        mean=known.astype(np.float32)@self.metadata[:m]/den
        maximum=np.zeros_like(mean)
        for i,row in enumerate(known):
            if row.any():maximum[i]=self.metadata[:m][row].max(0)
        families=known.astype(np.float32)@self.metadata[:m,:6]/4
        result=np.concatenate((x[:,:self.base_dimension],mean,maximum,families,count[:,None]/4),axis=1).astype(np.float32)
        if result.shape!=(len(x),self.dimension) or not np.isfinite(result).all():raise ValueError("invalid_hierarchical_context")
        return result[0]if one else result

    def encode(self,view):
        x,s=self.public.encode(view)
        return self.context(x,s),s


class HierarchicalResponseModel(nn.Module):
    def __init__(self,encoder):
        super().__init__()
        self.context_net=nn.Sequential(nn.Linear(encoder.dimension,128),nn.Tanh(),nn.Linear(128,64),nn.Tanh())
        self.family_head=nn.Linear(64,6)
        self.candidate_net=nn.Sequential(nn.Linear(64+encoder.metadata.shape[1],64),nn.Tanh(),nn.Linear(64,1))
        self.register_buffer("metadata",torch.tensor(encoder.metadata))
        self.register_buffer("family_index",torch.tensor(encoder.family_index,dtype=torch.long))
        self.encoder_fingerprint=encoder.fingerprint

    def packed_log_probabilities(self,context,indices,valid):
        if context.ndim!=2 or indices.ndim!=2 or indices.shape!=valid.shape or not valid.any(1).all():
            raise ValueError("hierarchical_public_candidates_required")
        latent=self.context_net(context);meta=self.metadata[indices]
        scores=self.candidate_net(torch.cat((latent[:,None,:].expand(-1,indices.shape[1],-1),meta),-1)).squeeze(-1)
        families=self.family_index[indices];family_log=torch.log_softmax(self.family_head(latent),-1)
        parts=[]
        for f in range(6):
            allowed=valid&(families==f)
            if not allowed.any(1).all():raise ValueError("hierarchical_unknown_family_missing")
            denominator=torch.logsumexp(scores.masked_fill(~allowed,-torch.inf),1)
            parts.append(denominator)
        denominators=torch.stack(parts,1)
        result=family_log.gather(1,families)+scores-denominators.gather(1,families)
        return result.masked_fill(~valid,-torch.inf)

    def forward(self,context,support):
        if support.dtype!=torch.bool or support.ndim!=2 or support.shape[1]!=len(self.family_index):
            raise ValueError("hierarchical_public_support_shape")
        positions=[torch.nonzero(row,as_tuple=False).flatten()for row in support]
        width=max(map(len,positions));indices=torch.zeros((len(context),width),dtype=torch.long,device=context.device)
        valid=torch.zeros_like(indices,dtype=torch.bool)
        for i,pos in enumerate(positions):indices[i,:len(pos)]=pos;valid[i,:len(pos)]=True
        lp=self.packed_log_probabilities(context,indices,valid)
        full=torch.full(support.shape,-torch.inf,dtype=lp.dtype,device=lp.device)
        # Padding index0 never overwrites a real index0 candidate.
        return full.scatter_reduce(1,indices,lp,reduce="amax",include_self=True)

    def probabilities(self,context,support,temperature=1.):
        if not .5<=float(temperature)<=5.:raise ValueError("hierarchical_temperature_out_of_bounds")
        return torch.softmax((self(context,support)/temperature).masked_fill(~support,-1e9),-1)
