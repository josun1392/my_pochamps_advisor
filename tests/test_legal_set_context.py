"""Offline frozen-checkpoint contracts. No optimizer step or native execution."""
from copy import deepcopy
import json
import os
from pathlib import Path

import numpy as np
import pytest
import torch

from advisor.learned_legal_set_context import (
    LegalSetContextFoundationPolicy, extend_foundation_legal_set_context,
    legal_set_context_contract, model_legal_set_context_contract,
)
from advisor.learned_policy import LearnedPolicy
from advisor.learned_parent_anchor import tensor_digest, optimizer_digest, optimizer_clock
from advisor.learned_combat_v5 import OLD_DIM, HP_EXTRA, HISTORY_EXTRA, TACTICAL
from advisor.learned_combat_v5_strategic import PREFIX, REF_WIDTH
from advisor.learned_strategic_public import CONTEXT
from advisor.learned_public_categories import ACTION, BASE_ACTION
from advisor.learned_regularized_ppo import checkpoint_algorithm

CAT = Path(__file__).resolve().parents[1] / 'models/showdown_mc_domain_v1/catalog.json'


def test_contract_fails_closed_without_foundation_and_training_is_not_enabled():
    c = legal_set_context_contract()
    assert c['additional_parameters'] == 4160
    with pytest.raises(ValueError, match='legal_set_context'):
        checkpoint_algorithm({'actor_set_context': c})
    from scripts.train_showdown_autonomous import validate_config
    config = {'schema_version': 'showdown-autonomous-training-v1', 'max_runtime_seconds': 60, 'experiments': [
        {'name': 'not-approved', 'steps': 512, 'seed': 1, 'actor_set_context': c}]}
    with pytest.raises(ValueError, match='offline_contract_only'):
        validate_config(config)


@pytest.fixture(scope='module')
def evidence():
    root = os.environ.get('POKEADVICE_LEGAL_SET_EVIDENCE')
    if not root:
        pytest.skip('trusted retained public observations not configured; never create native fixtures')
    root = Path(root)
    public = Path(os.environ['POKEADVICE_LEGAL_SET_CAPTURE'])
    views = [json.loads(line)['public_before'] for line in public.read_text(encoding='utf8').splitlines()]
    for name in ['A_110021', 'A_111037', 'A_99221', 'A_99222']:
        study = ('foundation-temperature-schedule-matched-v1-20261024' if name in ('A_110021', 'A_111037')
                 else 'foundation-two-group-curriculum-v1-20261024')
        for file in sorted((root.parent / study / 'runs' / name / 'public_signal_joins').glob('public_*.json')):
            views.append(json.loads(file.read_text())['observation'])
    assert len(views) == 1024
    return views, json.loads((root / 'PP_routing_cases.json').read_text()), root


@pytest.fixture(scope='module')
def source():
    parent = os.environ.get('POKEADVICE_LEGAL_SET_PARENT')
    if not parent:
        pytest.skip('trusted original Foundation parent not configured')
    loaded = LearnedPolicy(parent, CAT, expected_model_id=
        '9b3eb94aabea1fb25e75dfdba0b733c2a9acd45434ae368a86e14d8979950ccf')
    loaded.model.policy.set_training_mode(False)
    before = tensor_digest(loaded.model.policy.state_dict()), optimizer_digest(loaded.model.policy)
    yield loaded
    assert before == (tensor_digest(loaded.model.policy.state_dict()), optimizer_digest(loaded.model.policy))


@pytest.fixture
def target(source):
    model = extend_foundation_legal_set_context(source.model)
    # Any accidental optimizer/PPO call is an immediate test failure.
    def forbidden(*args, **kwargs):
        raise AssertionError('offline contract tests cannot train')
    model.policy.optimizer.step = forbidden
    model.learn = forbidden
    return model


def outputs(policy, features, masks):
    with torch.no_grad():
        logits = policy.mlp_extractor.forward_actor(features)
        distribution = policy.get_distribution(features, action_masks=masks)
        probabilities = distribution.distribution.probs.clone()
        actions = probabilities.argmax(1)
        logp = distribution.log_prob(actions).clone()
        value = policy.predict_values(features)
    return logits, probabilities, logp, actions, value


def assert_bits_equal(a, b):
    assert a.dtype == b.dtype and a.shape == b.shape
    assert a.detach().cpu().numpy().tobytes() == b.detach().cpu().numpy().tobytes()


def assert_old_Adam(source_policy, target_policy):
    old, new = dict(source_policy.named_parameters()), dict(target_policy.named_parameters())
    assert set(new) - set(old) == {
        'mlp_extractor.legal_set_residual.weight', 'mlp_extractor.legal_set_residual.bias'}
    for name, parameter in old.items():
        assert_bits_equal(parameter, new[name])
        a, b = source_policy.optimizer.state.get(parameter, {}), target_policy.optimizer.state.get(new[name], {})
        assert a.keys() == b.keys()
        for key, value in a.items():
            if torch.is_tensor(value):
                assert_bits_equal(value, b[key])
            else:
                assert value == b[key]
    for name in set(new) - set(old):
        assert not target_policy.optimizer.state.get(new[name])
    for key, value in source_policy.optimizer.param_groups[0].items():
        if key != 'params':
            assert value == target_policy.optimizer.param_groups[0][key]
    assert optimizer_clock(source_policy) == optimizer_clock(target_policy) == 32768


def test_zero_initial_outputs_and_named_Adam_are_bit_exact(source, target, evidence):
    views, _, _ = evidence
    assert_old_Adam(source.model.policy, target.policy)
    assert sum(p.numel() for p in target.policy.parameters()) == 679099
    assert model_legal_set_context_contract(target) == legal_set_context_contract()
    for start in range(0, len(views), 32):
        batch = views[start:start + 32]
        x = torch.tensor(np.stack([source.encoder.encode(v) for v in batch]))
        mask = np.array([v['action_mask'] for v in batch], bool)
        for left, right in zip(outputs(source.model.policy, x, mask), outputs(target.policy, x, mask)):
            assert_bits_equal(left, right)
        with torch.no_grad():
            old_logp = source.model.policy.get_distribution(x, action_masks=mask).distribution.logits.clone()
            new_logp = target.policy.get_distribution(x, action_masks=mask).distribution.logits.clone()
            assert_bits_equal(old_logp, new_logp)  # Every action, not just argmax.
            old_forward = source.model.policy(x, deterministic=True, action_masks=mask)
            new_forward = target.policy(x, deterministic=True, action_masks=mask)
            for left, right in zip(old_forward, new_forward):
                assert_bits_equal(left, right)


def test_inherited_request_slot_sensitivity_is_unchanged(source, target, evidence):
    views, _, root = evidence
    cases = json.loads((root / 'slot_order_cases.json').read_text())
    assert len(cases) == 867
    changed = 0
    for case in cases:
        view = views[case['view']]
        revised = deepcopy(view)
        moves = revised['own_request']['active'][0]['moves']
        active = next(p for p in revised['own_request']['side']['pokemon'] if p.get('active'))
        order = list(reversed(range(len(moves))))
        revised['own_request']['active'][0]['moves'] = [moves[i] for i in order]
        active['moves'] = [active['moves'][i] for i in order]
        permutation = np.arange(35)
        for start in (6, 10, 27, 31):
            for new, old in enumerate(order):
                permutation[start + new] = start + old
        revised['action_mask'] = [view['action_mask'][int(i)] for i in permutation]
        actions = []
        for public in (view, revised):
            x = torch.tensor(source.encoder.encode(public))[None]
            mask = np.asarray(public['action_mask'], bool)[None]
            original, extension = outputs(source.model.policy, x, mask), outputs(target.policy, x, mask)
            for left, right in zip(original, extension):
                assert_bits_equal(left, right)
            actions.append(int(extension[3][0]))
        differs = actions[0] != permutation[actions[1]]
        assert differs == case['original_semantic_argmax_changed']
        changed += differs
    assert changed == 50


def pp_pair(views, case, encoder):
    lo, hi = deepcopy(views[case['view']]), deepcopy(views[case['view']])
    for view, pp in [(lo, case['PP_low']), (hi, case['PP_high'])]:
        view['own_request']['active'][0]['moves'][case['C_slot']]['pp'] = pp
    return torch.tensor(np.stack([encoder.encode(lo), encoder.encode(hi)])), np.array([lo['action_mask']] * 2, bool)


def test_other_legal_C_PP_changes_pairwise_gap_and_residual_has_gradients(source, target, evidence):
    views, cases, _ = evidence
    residual = target.policy.mlp_extractor.legal_set_residual
    with torch.no_grad():
        residual.weight.copy_(.05 * torch.eye(64))  # Fixed diagnostic fixture, never fitted.
    changes = {}
    for case in cases:
        x, mask = pp_pair(views, case, source.encoder)
        old = outputs(source.model.policy, x, mask)
        actual = outputs(target.policy, x, mask)
        a, b = case['a'], case['b']
        # Different GEMM row tiles can differ at a few FP32 ulps even though
        # these two mathematical inputs are identical (single-row audit is exact).
        torch.testing.assert_close(old[0][0, a] - old[0][0, b], old[0][1, a] - old[0][1, b], atol=4e-6, rtol=0)
        delta = float((actual[0][0, a] - actual[0][0, b]) - (actual[0][1, a] - actual[0][1, b]))
        changes[case['comparison']] = max(changes.get(case['comparison'], 0), abs(delta))
        assert_bits_equal(old[-1], actual[-1])  # Original critic, including nonzero residual.
    assert len(changes) == 4 and min(changes.values()) > 1e-5
    residual.zero_grad(set_to_none=True)
    with torch.no_grad():
        residual.weight.zero_()
    x, mask = pp_pair(views, cases[0], source.encoder)
    z = target.policy.mlp_extractor.forward_actor(x)
    gradient = torch.autograd.grad(z[0, cases[0]['a']] - z[0, cases[0]['b']],
                                   (residual.weight, residual.bias))
    assert all(torch.isfinite(g).all() and g.norm() > 0 for g in gradient)
    value = target.policy.predict_values(x)
    assert torch.autograd.grad(value.sum(), (residual.weight, residual.bias), allow_unused=True) == (None, None)
    assert_old_Adam(source.model.policy, target.policy)


def permuted(x, permutation):
    y = x.clone()
    for offset, width in [(CONTEXT, ACTION), (OLD_DIM + HP_EXTRA + HISTORY_EXTRA, TACTICAL), (PREFIX, REF_WIDTH)]:
        y[:, offset:offset + 35 * width] = x[:, offset:offset + 35 * width].reshape(-1, 35, width)[:, permutation].flatten(1)
    return y


def set_mask(x, masks):
    result = x.clone()
    result[:, CONTEXT:OLD_DIM].reshape(-1, 35, ACTION)[:, :, -1] = torch.as_tensor(masks, dtype=x.dtype)
    return result


def test_nonzero_path_permutation_masks_illegal_padding_and_candidate_counts(source, target, evidence):
    views, cases, _ = evidence
    with torch.no_grad():
        target.policy.mlp_extractor.legal_set_residual.weight.copy_(.05 * torch.eye(64))
    x = torch.tensor(np.stack([source.encoder.encode(v) for v in views[:32]]))
    mask = np.array([v['action_mask'] for v in views[:32]], bool)
    permutation = np.random.default_rng(73011).permutation(35)
    left, right = outputs(target.policy, x, mask), outputs(target.policy, permuted(x, permutation), mask[:, permutation])
    torch.testing.assert_close(left[0][:, permutation], right[0], atol=1e-5, rtol=0)
    torch.testing.assert_close(left[1][:, permutation], right[1], atol=3e-6, rtol=0)
    torch.testing.assert_close(left[-1], right[-1], atol=3e-6, rtol=0)
    noisy = x.clone()
    rows = noisy[:, CONTEXT:OLD_DIM].reshape(-1, 35, ACTION)
    rows[:, :, :BASE_ACTION - 1] += torch.as_tensor(~mask)[:, :, None] * .125
    for offset, width in [(OLD_DIM + HP_EXTRA + HISTORY_EXTRA, TACTICAL), (PREFIX, REF_WIDTH)]:
        noisy[:, offset:offset + 35 * width].reshape(-1, 35, width)[:] += torch.as_tensor(~mask)[:, :, None] * .125
    pooled = []
    handle = target.policy.mlp_extractor.legal_set_residual.register_forward_pre_hook(
        lambda module, args: pooled.append(args[0].detach().clone()))
    try:
        outputs(target.policy, x, mask)
        noise_output = outputs(target.policy, noisy, mask)
    finally:
        handle.remove()
    assert len(pooled) == 4
    assert_bits_equal(pooled[0], pooled[2])
    assert_bits_equal(left[0][torch.as_tensor(mask)], noise_output[0][torch.as_tensor(mask)])
    # Upstream Categorical normalizes ALL raw logits once before masking;
    # changed illegal logits can change rounding of that common normalizer.
    torch.testing.assert_close(left[1], noise_output[1], atol=2e-6, rtol=0)
    case = cases[0]
    pp, mm = pp_pair(views, case, source.encoder)
    for start in (6, 10, 27, 31):
        mm[:, start + case['C_slot']] = False
    pp = set_mask(pp, mm)
    z = outputs(target.policy, pp, mm)[0]
    torch.testing.assert_close(z[0, [case['a'], case['b']]], z[1, [case['a'], case['b']]], atol=4e-6, rtol=0)
    only = np.zeros_like(mm); only[:, case['a']] = True
    single = outputs(target.policy, set_mask(pp, only), only)
    assert torch.equal(single[1][:, case['a']], torch.ones(2))
    assert not single[1][~torch.tensor(only)].any()


def test_explicit_mask_mismatch_empty_nonbinary_and_private_roots_fail_closed(source, target, evidence):
    view = evidence[0][0];x = torch.tensor(source.encoder.encode(view))[None]
    mask = np.array(view['action_mask'], bool)[None];bad = mask.copy();bad[0, 26] = not bad[0, 26]
    for method in [lambda: target.policy(x, action_masks=bad), lambda: target.policy.get_distribution(x, action_masks=bad),
                   lambda: target.policy.evaluate_actions(x, torch.tensor([int(np.flatnonzero(mask[0])[0])]), action_masks=bad)]:
        with pytest.raises(ValueError, match='explicit_mask_mismatch'):method()
    for bad_tensor in [set_mask(x, np.zeros_like(mask)), set_mask(x, np.full(mask.shape, .5)), x * float('nan')]:
        with pytest.raises(ValueError, match='legal_set_context'):target.policy.get_distribution(bad_tensor)
    implicit = target.policy.get_distribution(x).distribution.probs
    explicit = target.policy.get_distribution(x, action_masks=mask).distribution.probs
    assert_bits_equal(implicit, explicit)
    for key in ('opponent_request', 'native_state', 'future_seed', 'auxiliary_labels'):
        with pytest.raises(ValueError):source.encoder.encode({**view, key: {}})


def test_checkpoint_roundtrip_keeps_named_Adam_and_rejects_lost_contract(source, target, evidence, tmp_path):
    from scripts.train_showdown_autonomous import save_checkpoint
    with torch.no_grad():
        target.policy.mlp_extractor.legal_set_residual.weight.copy_(.05 * torch.eye(64))
    # Remove test-only instance guards before serialization (never execute them).
    del target.policy.optimizer.step
    del target.learn
    path = save_checkpoint(target, source.encoder, tmp_path / 'new', {})
    restored = LearnedPolicy(path, CAT)
    assert type(restored.model.policy) is LegalSetContextFoundationPolicy
    for name, value in target.policy.state_dict().items():assert_bits_equal(value, restored.model.policy.state_dict()[name])
    assert_old_Adam(source.model.policy, restored.model.policy)
    x = torch.tensor(source.encoder.encode(evidence[0][0]))[None];mask = np.array(evidence[0][0]['action_mask'], bool)[None]
    for left, right in zip(outputs(target.policy, x, mask), outputs(restored.model.policy, x, mask)):assert_bits_equal(left, right)
    metadata_path = Path(path).with_suffix('.json');original = json.loads(metadata_path.read_text())
    for corrupt in [{k:v for k,v in original.items() if k != 'actor_set_context'},
                    {**original, 'actor_set_context': {**original['actor_set_context'], 'additional_parameters': 1}}]:
        metadata_path.write_text(json.dumps(corrupt))
        with pytest.raises(ValueError, match='legal_set_context'):LearnedPolicy(path, CAT)
    metadata_path.write_text(json.dumps(original))
    assert type(LearnedPolicy(os.environ['POKEADVICE_LEGAL_SET_PARENT'], CAT).model.policy).__name__ == 'FoundationCombatPolicy'
