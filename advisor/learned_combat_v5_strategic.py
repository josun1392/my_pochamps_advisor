"""Corrected integrated V5: public support/prior transport and references.

v1/v2 encoders remain immutable. Private labels are produced by a separate
coordinator module and are never accepted by this public encoder.
"""
from functools import lru_cache
from pathlib import Path
import json,hashlib
import numpy as np
from advisor.learned_encoder import identifier,fingerprint
from advisor.learned_combat_v5 import (IntegratedCombatV5Encoder,APPEARANCE_SUPPORT_VERSION,inventory,
    OLD_DIM,HP_EXTRA,HISTORY_EXTRA,TACTICAL,SIZES,PRED_EXTRA,active_public,current_public_prediction_knowledge)
from advisor.learned_combat_v5_references import reference_features,WIDTH,TYPE_WIDTH,FIELDS
from advisor.learned_public_categories import token_bits,BITS
from advisor.showdown_bridge import SHOWDOWN_COMMIT,FORMAT_ID

VERSION='showdown-public-categorical-observation-v5-integrated-v3'
PREFIX=IntegratedCombatV5Encoder.dimension
REF_WIDTH=WIDTH+TYPE_WIDTH
PRIOR_SIZES={**SIZES,'action':SIZES['moves']+1}
DIMENSION=PREFIX+35*REF_WIDTH+sum(PRIOR_SIZES.values())
PRIOR_PATH=Path(__file__).resolve().parents[1]/'models/showdown_combat_priors_v3/catalog.json'

@lru_cache(maxsize=1)
def priors():
    raw=PRIOR_PATH.read_bytes();d=json.loads(raw)
    if d.get('schema_version')!='showdown-public-combat-priors-v3' or d['engine_commit']!=SHOWDOWN_COMMIT or d['format_id']!=FORMAT_ID:raise ValueError('invalid_public_combat_prior_authority')
    return d,hashlib.sha256(raw).hexdigest()

def public_species_candidates(view):
    inv=inventory();row=active_public(view);current=identifier(row.get('details',''))
    candidates=[current] if current in inv['species'] else []
    # Appearance-vs-individual-slot ambiguity is NOT evidence every preview
    # species could be the current species. Only native Illusion possibilities
    # widen the displayed species domain (or explicit public transformation).
    if row.get('identity_scope')!='public_protocol_replacement_confirmed':
        for p in view['state']['opponent_side']['preview']:
            name=identifier(p['details']);entry=inv['species'].get(name)
            if entry and any(identifier(a)=='illusion' for a in entry['abilities']):candidates.append(name)
    return list(dict.fromkeys(candidates))

def prediction_public_rows(view,encoder):
    inv=inventory();data,_=priors();row=active_public(view);names=public_species_candidates(view)
    role='p2' if view['side']=='self' else 'p1'
    changed=any(role in x and any(e in x for e in ('|-ability|','|-transform|','|move: Skill Swap','|move: Role Play','|ability: Mummy','|ability: Lingering Aroma')) for x in view['public_history'])
    moves_changed=any(role in x and ('|-transform|' in x or '|-start|' in x and any(m in x.lower() for m in ('mimic','sketch'))) for x in view['public_history'])
    support={k:np.zeros(n,np.float32) for k,n in SIZES.items()};known=[];known_moves=np.zeros(SIZES['moves'],np.float32)
    entries=[inv['species'][n] for n in names]
    abilities=encoder.tokens['abilities'].keys() if changed or not entries else {a for n,e in zip(names,entries) for a in (
        inv['public_dex'][n]['abilities'].values() if e['kind'] not in ('selectable','cosmetic') else e['abilities'])}
    moves=encoder.tokens['moves'].keys() if moves_changed or not entries else {m for e in entries for m in e['moves']}
    for kind,values in (('abilities',abilities),('items',inv['items']),('moves',moves)):
        for value in values:
            token=encoder.tokens[kind].get(identifier(value))
            if token is not None:support[kind][token]=1
    support['items'][2]=1;knowledge=current_public_prediction_knowledge(view)
    known_ids={}
    for kind in ('abilities','items'):
        value=knowledge[kind];token=1 if isinstance(value,dict) else 2 if value is None else encoder.token(kind,value)
        known_ids[kind]=token
        if token>1:support[kind][token]=1
        known+=token_bits(token,BITS[kind])
    for mid in row.get('known_moves',[]):
        token=encoder.token('moves',mid);support['moves'][token]=1
        if not moves_changed:known_moves[token]=1
    if any(not v.any() for v in support.values()):raise ValueError('empty_v5_v3_public_support')
    probabilities={}
    for kind,n in SIZES.items():
        allowed=support[kind];counts=np.zeros(n,np.float64);global_counts=np.zeros(n,np.float64)
        for name,count in data['global_counts'][kind].items():
            token=2 if kind=='items' and not name else encoder.tokens[kind].get(name)
            if token is not None:global_counts[token]+=count
        global_counts*=allowed
        if not global_counts.any():global_counts=allowed.copy()
        categorical=kind!='moves';allowed_n=allowed.sum()
        if categorical:
            base=.5*allowed/allowed_n+.5*global_counts/max(1,global_counts.sum())
        else:
            # Sparse smoothed prior: average <=4 current moves, NOT sigmoid(.0)=.5
            # over hundreds of legal negatives. No class-reweighted likelihood.
            base=np.minimum(.95,4*(.5*allowed/allowed_n+.5*global_counts/max(1,global_counts.sum())))
        models=[]
        for name in names:
            entry=inv['species'][name];key=identifier(entry['start_species']);s=data['species'].get(key)
            if not s:continue
            cnt=np.zeros(n,np.float64)
            for value,count in s[kind].items():
                token=2 if kind=='items' and not value else encoder.tokens[kind].get(value)
                if token is not None:cnt[token]+=count
            cnt*=allowed;den=s['sets']+16
            if categorical:
                q=(cnt+16*base);q=q/q.sum() if q.sum() else base
            else:q=(cnt+16*base)/den
            models.append(q)
        q=np.mean(models,axis=0) if models else base
        q=np.clip(q,1e-5,1-1e-5)*allowed
        if categorical:q/=q.sum()
        probabilities[kind]=q.astype(np.float32)
    action_support=np.r_[support['moves'],1.].astype(np.float32)
    struggle=encoder.tokens['moves'].get('struggle')
    if struggle is not None:action_support[struggle]=1
    count=np.zeros(PRIOR_SIZES['action'],np.float64)
    for token,n in data['executed_action_counts'].items():count[int(token)]=n
    # Public set marginal + TRAIN-only execution frequency, never opponent's
    # private request/legality. Current public reveals increase move plausibility.
    occurrence=np.maximum(probabilities['moves'],known_moves)
    move_weight=(count[:-1]+1)*occurrence*action_support[:-1]
    if not move_weight.any():move_weight=action_support[:-1].copy()
    # A set-marginal probability is not an action-family prior. Normalize the
    # conditional move distribution separately; otherwise multiplying only
    # move classes by sparse set marginals spuriously inflates switch mass.
    switch_probability=(count[-1]+1)/(count.sum()+2)
    action=np.r_[move_weight/move_weight.sum()*(1-switch_probability),switch_probability]
    probabilities['action']=action.astype(np.float32)
    transport=np.concatenate([support[k] for k in SIZES]+[np.asarray(known,np.float32),known_moves])
    return transport,np.concatenate([probabilities[k] for k in PRIOR_SIZES])

class StrategicCombatV5Encoder(IntegratedCombatV5Encoder):
    dimension=DIMENSION
    def __init__(self,catalog):
        super().__init__(catalog,version=APPEARANCE_SUPPORT_VERSION);parent=self.catalog_fingerprint
        self.version=VERSION;d,sha=priors()
        self.feature_contract={**self.feature_contract,'version':VERSION,'schema_version':'showdown-integrated-combat-v5-strategic-contract-v3',
            'dimension':DIMENSION,'observation_dimension':DIMENSION,'parent_v2_fingerprint':parent,'public_priors_sha256':sha,
            'public_priors_train_subset_sha256':d['training_subset_sha256'],'reference_fields':list(FIELDS),
            'reference_scope':'conditional_native_compatible_noncritical_single_hit_independent_stat_endpoints_not_actual_damage_KO_or_order',
            'reference_boost_projection':'showdown-public-boost-projection-v1_copy_swap_caps_unknown_preservation_legacy_prefix_unchanged',
            'public_support':'displayed_species_plus_only_publicly_possible_Illusion_species_runtime_widened',
            'prediction':'executed_move_token_1024_or_observed_switch_1024; unknown_only_hidden_labels',
            'belief_interface':'PPO_stop_gradient_predictions; auxiliary_detached_public_trunk; bounded_residual_logits',
            'prior_transport':'probabilities_from_train_only_smoothed_species_counts_not_ordinal_categories',
            'action_prior':'empirical_switch_rate_times_separately_normalized_public_supported_conditional_move_distribution',
            'layout':'V2_prefix_with_versioned_refined_support_then35x42_reference_rows_then2817_public_priors'}
        self.catalog_fingerprint=fingerprint(self.feature_contract)
    def encode(self,view):
        # Parent supplies public validation, binary identities, HP/history and
        # historical semantics. Only THIS version replaces prediction support.
        old=super().encode(view);transport,prob=prediction_public_rows(view,self.base)
        old[-PRED_EXTRA:]=transport
        refs,threat=reference_features(view,self.base,priors()[0]['native_moves'])
        return np.concatenate((old,np.concatenate((refs,threat),axis=1).flatten(),prob)).astype(np.float32)
