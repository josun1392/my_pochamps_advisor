"""Retained TRAIN public inputs only. No sealed data, fitting, saves or battles."""
from copy import deepcopy
import os
from pathlib import Path

import numpy as np
import pytest
import torch

from advisor.experimental_candidate_context import CandidateContextPrototype, prototype_contract
from advisor.learned_policy import LearnedPolicy
from advisor.learned_combat_v5 import OLD_DIM, HP_EXTRA, HISTORY_EXTRA, TACTICAL
from advisor.learned_combat_v5_strategic import PREFIX, REF_WIDTH
from advisor.learned_public_categories import ACTION, BASE_ACTION
from advisor.learned_strategic_public import CONTEXT
from advisor.learned_parent_anchor import tensor_digest, optimizer_digest
from tests.test_legal_set_context import evidence, source, outputs, assert_bits_equal, permuted, set_mask, pp_pair, CAT

MEASUREMENTS = {}


@pytest.fixture
def prototype(source):
    return CandidateContextPrototype(source, opt_in=True)


def test_explicit_opt_in_and_no_training_production_registration():
    with pytest.raises(ValueError, match="explicit_opt_in"):CandidateContextPrototype(None)
    with pytest.raises(ValueError, match="trusted_learned_policy"):CandidateContextPrototype(None, opt_in=True)
    c=prototype_contract()
    assert c['reuses']['additional_parameters']==4160 and c['strength_evidence'] is False
    assert 'offline_public_scores_only' in c['scope']


def test_zero_and_disabled_paths_preserve_existing_fused_policy_bits(source, prototype, evidence):
    views=evidence[0]
    original_type=type(source.model.policy)
    for view in views[:64]:
        before=source.infer(view)
        x=torch.tensor(source.encoder.encode(view))[None]
        mask=np.array(view['action_mask'], bool)[None]
        original=outputs(source.model.policy,x,mask)
        for result in (prototype.score_public(view),prototype.score_public(view,use_context=False)):
            assert_bits_equal(original[0],result.logits)
            assert_bits_equal(original[1],result.probabilities)
            assert_bits_equal(original[-1],result.values)
            np.testing.assert_array_equal(before['action_probabilities'],result.probabilities[0].numpy())
            assert before['discounted_return_estimate']==float(result.values[0,0])
        assert source.infer(view)==before
    assert type(source.model.policy) is original_type
    assert prototype._policy.mlp_extractor.legal_set_residual.weight.count_nonzero()==0
    prototype.use_fixed_diagnostic_context()
    for view in views[:64]:
        x=torch.tensor(source.encoder.encode(view))[None]
        mask=np.array(view['action_mask'],bool)[None]
        original=outputs(source.model.policy,x,mask)
        disabled=prototype.score_public(view,use_context=False)
        for a,b in zip((original[0],original[1],original[-1]),
                       (disabled.logits,disabled.probabilities,disabled.values)):
            assert_bits_equal(a,b)
    MEASUREMENTS['zero_and_disabled']={'TRAIN_views':64,'logits_probabilities_values':'byte_equal','original_infer_unchanged':True}


def test_retained_C_PP_route_has_capacity_and_no_compulsory_response(source, prototype, evidence):
    views,cases,_=evidence
    prototype.use_fixed_diagnostic_context()
    changed={}
    for case in cases:
        x,mask=pp_pair(views,case,source.encoder)
        # Same-size single-view GEMMs avoid tile-dependent FP32 rounding in
        # mathematically identical rows of a two-view batch (see owner tests).
        with torch.no_grad():
            left=source.model.policy.mlp_extractor._public_rows(x[:1])
            right=source.model.policy.mlp_extractor._public_rows(x[1:])
        assert_bits_equal(left[0],right[0])
        assert_bits_equal(left[1][:,[case['a'],case['b']]],right[1][:,[case['a'],case['b']]])
        off=prototype._score_encoded(x,action_masks=mask,use_context=False)
        on=prototype._score_encoded(x,action_masks=mask)
        a,b=case['a'],case['b']
        torch.testing.assert_close(off.logits[0,a]-off.logits[0,b],off.logits[1,a]-off.logits[1,b],atol=4e-6,rtol=0)
        delta=abs(float((on.logits[0,a]-on.logits[0,b])-(on.logits[1,a]-on.logits[1,b])))
        changed[case['comparison']]=max(changed.get(case['comparison'],0),delta)
        assert_bits_equal(off.values,on.values)
    assert len(changed)==4 and min(changed.values())>1e-5
    MEASUREMENTS['C_PP_capacity']={'controlled_cases':len(cases),'max_absolute_pairwise_gap_change_by_family':changed,
        'original_A_B_context_and_rows':'byte_equal_same_size_single_view_calls',
        'critic':'byte_equal','fixture':'0.05*I_no_fitting'}
    case=cases[0];x,mask=pp_pair(views,case,source.encoder)
    for start in (6,10,27,31):mask[:,start+case['C_slot']]=False
    without_C=prototype._score_encoded(set_mask(x,mask),action_masks=mask)
    torch.testing.assert_close(without_C.logits[0,[case['a'],case['b']]],without_C.logits[1,[case['a'],case['b']]],atol=4e-6,rtol=0)
    prototype.zero_context()
    assert not prototype._policy.mlp_extractor.legal_set_residual.weight.count_nonzero()


def test_candidate_row_permutation_is_equivariant_with_fixed_global_context(source,prototype,evidence):
    prototype.use_fixed_diagnostic_context()
    views=evidence[0][:32]
    x=torch.tensor(np.stack([source.encoder.encode(v) for v in views]))
    masks=np.array([v['action_mask'] for v in views],bool)
    order=np.random.default_rng(161102731).permutation(35)
    before=prototype._score_encoded(x,action_masks=masks)
    after=prototype._score_encoded(permuted(x,order),action_masks=masks[:,order])
    torch.testing.assert_close(before.logits[:,order],after.logits,atol=1e-5,rtol=0)
    torch.testing.assert_close(before.probabilities[:,order],after.probabilities,atol=3e-6,rtol=0)
    torch.testing.assert_close(before.values,after.values,atol=3e-6,rtol=0)
    MEASUREMENTS['permutation']={'TRAIN_views':32,'max_logit_error':float((before.logits[:,order]-after.logits).abs().max()),
        'max_probability_error':float((before.probabilities[:,order]-after.probabilities).abs().max()),
        'max_value_error':float((before.values-after.values).abs().max()),'scope':'aligned_rows_fixed_context_not_native_move_slot_reordering'}


def test_illegal_padding_noise_is_excluded_from_context_pool(source,prototype,evidence):
    prototype.use_fixed_diagnostic_context();views=evidence[0][:16]
    x=torch.tensor(np.stack([source.encoder.encode(v) for v in views]));mask=np.array([v['action_mask'] for v in views],bool)
    noisy=x.clone();illegal=torch.as_tensor(~mask)[:,:,None]
    noisy[:,CONTEXT:OLD_DIM].reshape(-1,35,ACTION)[:,:,:BASE_ACTION-1]+=illegal*.125
    for offset,width in [(OLD_DIM+HP_EXTRA+HISTORY_EXTRA,TACTICAL),(PREFIX,REF_WIDTH)]:
        noisy[:,offset:offset+35*width].reshape(-1,35,width)[:]+=illegal*.125
    pooled=[];handle=prototype._policy.mlp_extractor.legal_set_residual.register_forward_pre_hook(lambda m,args:pooled.append(args[0].detach().clone()))
    try:
        original=prototype._score_encoded(x,action_masks=mask)
        actual=prototype._score_encoded(noisy,action_masks=mask)
    finally:handle.remove()
    assert len(pooled)==2;assert_bits_equal(pooled[0],pooled[1])
    assert_bits_equal(original.logits[torch.tensor(mask)],actual.logits[torch.tensor(mask)])
    assert not actual.probabilities[~torch.tensor(mask)].any()
    torch.testing.assert_close(original.probabilities,actual.probabilities,atol=2e-6,rtol=0)


def test_single_legal_action_and_real_retained_forced_switch(source,prototype,evidence):
    prototype.use_fixed_diagnostic_context()
    forced=next(v for v in evidence[0] if v['request_state']=='switch')
    result=prototype.score_public(forced)
    assert result.legal_mask.any() and all(i<6 for i in torch.where(result.legal_mask[0])[0].tolist())
    assert not result.probabilities[~result.legal_mask].any()
    x=torch.tensor(source.encoder.encode(forced))[None]
    mask=np.zeros((1,35),bool);index=int(np.flatnonzero(forced['action_mask'])[0]);mask[0,index]=True
    single=prototype._score_encoded(set_mask(x,mask),action_masks=mask)
    assert single.probabilities[0,index]==1 and not single.probabilities[~single.legal_mask].any()


def test_empty_nonbinary_mismatched_masks_and_invalid_transport_fail_closed(source,prototype,evidence):
    view=evidence[0][0];x=torch.tensor(source.encoder.encode(view))[None]
    mask=np.array(view['action_mask'],bool)[None]
    mismatch=mask.copy();mismatch[0,26]=not mismatch[0,26]
    for enabled in (True,False):
        with pytest.raises(ValueError,match='mask_mismatch'):prototype._score_encoded(x,action_masks=mismatch,use_context=enabled)
        for bad in (set_mask(x,np.zeros_like(mask)),set_mask(x,np.full(mask.shape,.5)),x*float('nan')):
            with pytest.raises(ValueError):prototype._score_encoded(bad,use_context=enabled)
    with pytest.raises(ValueError):prototype._score_encoded(None)


def test_missing_public_data_and_unknown_opponent_traits(source,prototype,evidence):
    view=evidence[0][0]
    for key in ('state','own_request','public_history'):
        invalid=deepcopy(view);invalid.pop(key)
        with pytest.raises(ValueError):prototype.score_public(invalid)
    with pytest.raises(ValueError):prototype.score_public(None)
    missing=deepcopy(view);unknown=deepcopy(view)
    for v in (missing,unknown):
        foe=v['state']['opponent_side'];row=foe['pokemon'][foe['active_identity']]
        for key in ('current_ability','known_item'):
            if v is missing:row.pop(key,None)
            else:row[key]={'knowledge':'unknown'}
    a,b=prototype.score_public(missing),prototype.score_public(unknown)
    assert_bits_equal(a.logits,b.logits);assert torch.isfinite(a.values).all()


@pytest.mark.parametrize('key',['native_state','teams','seed','future_seed','input_log','auxiliary_labels',
    'opponent_request','target_mask','labels','coordinator_v5_supervision'])
def test_private_roots_never_reach_prototype(key,prototype,evidence):
    view=deepcopy(evidence[0][0]);view[key]={'hidden':'not-an-input'}
    with pytest.raises(ValueError):prototype.score_public(view)


def test_copies_do_not_alias_original_or_enable_optimizer(source,prototype,evidence):
    original=tensor_digest(source.model.policy.state_dict()),optimizer_digest(source.model.policy)
    for name,parameter in source.model.policy.named_parameters():
        assert parameter.data_ptr()!=dict(prototype._base.named_parameters())[name].data_ptr()
        assert parameter.data_ptr()!=dict(prototype._policy.named_parameters())[name].data_ptr()
    prototype.use_fixed_diagnostic_context();prototype.score_public(evidence[0][0])
    assert original==(tensor_digest(source.model.policy.state_dict()),optimizer_digest(source.model.policy))
    for policy in (prototype._base,prototype._policy):
        with pytest.raises(RuntimeError,match='updates_forbidden'):policy.optimizer.step()
    assert not any(hasattr(prototype,name) for name in ('learn','train','save','infer'))


def test_original_16K_loading_and_zero_prototype_are_unchanged(evidence):
    path=os.environ.get('POKEADVICE_CONTEXT_16K')
    if not path:pytest.skip('retained 16K checkpoint not configured; never train a replacement')
    actor=LearnedPolicy(path,CAT,expected_model_id='9b512481427d08c4d997dfc4e479c9f22bf143346191af490d693449cd90e032')
    before=tensor_digest(actor.model.policy.state_dict()),optimizer_digest(actor.model.policy)
    view=evidence[0][0];proof=actor.infer(view)
    result=CandidateContextPrototype(actor,opt_in=True).score_public(view)
    np.testing.assert_array_equal(result.probabilities[0].numpy(),proof['action_probabilities'])
    assert float(result.values[0,0])==proof['discounted_return_estimate']
    assert before==(tensor_digest(actor.model.policy.state_dict()),optimizer_digest(actor.model.policy))
