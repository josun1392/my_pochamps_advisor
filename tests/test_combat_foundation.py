"""Native foundation learning, finite update guards and strict recovery."""

from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
import torch
from stable_baselines3.common.vec_env import DummyVecEnv
from sb3_contrib.common.maskable.buffers import MaskableRolloutBuffer

from advisor.learned_combat_foundation import (
    FoundationCombatPPO, FoundationCombatPolicy, FoundationCombatEncoder, foundation_contract, transfer_foundation_weights,
)
from advisor.learned_combat_v5_strategic import VERSION, StrategicCombatV5Encoder
from advisor.learned_policy import LearnedPolicy
from advisor.learned_parallel import LearningEnvFactory
from scripts.train_showdown_autonomous import BudgetCallback, optimizer_steps, save_checkpoint, validate_config
from tests.test_combat_v5_strategic import checkout, views, CAT, model
from tests.test_integrated_combat_v5 import outputs
from advisor.learned_strategic_public import StrategicPublicCategoricalEncoder
from advisor.learned_strategic_public_policy import StrategicPublicCategoricalPolicy


class Budget:
    def stopping(self):
        return False


def foundation_model(vector):
    return FoundationCombatPPO(FoundationCombatPolicy, vector, n_steps=8, batch_size=8,
        n_epochs=1, gamma=1., gae_lambda=.95, ent_coef=.01, zero_avoiding_beta=.001,
        seed=95017, device='cpu')


def test_fresh_v4_transfer_and_fused_distribution_values(views):
    encoder = StrategicCombatV5Encoder(CAT)
    previous_encoder = StrategicPublicCategoricalEncoder(CAT)
    previous = model(previous_encoder, StrategicPublicCategoricalPolicy)
    target = foundation_model(previous.get_env())
    transfer_foundation_weights(target.policy, previous.policy, encoder, previous_encoder)
    assert not target.policy.optimizer.state
    for view in views:
        features = torch.as_tensor(encoder.encode(view))[None]
        mask = np.asarray(view['action_mask'], bool)[None]
        expected = outputs(previous.policy, torch.as_tensor(previous_encoder.encode(view))[None], mask)
        actual = outputs(target.policy, features, mask)
        for before, after in zip(expected, actual):
            torch.testing.assert_close(before, after, atol=5e-6, rtol=0)
        _, values, _ = target.policy(features, deterministic=True, action_masks=mask)
        torch.testing.assert_close(target.policy.action_dist.distribution.probs, actual[1], atol=5e-7, rtol=0)
        torch.testing.assert_close(values, actual[2], atol=5e-7, rtol=0)


def test_optimized_public_encoder_is_bit_identical_and_rejects_private_inputs(views):
    original = StrategicCombatV5Encoder(CAT)
    optimized = FoundationCombatEncoder(CAT)
    assert optimized.feature_contract == original.feature_contract
    assert optimized.catalog_fingerprint == original.catalog_fingerprint
    for view in views:
        np.testing.assert_array_equal(original.encode(view), optimized.encode(view))
        for key in ('opponent_request', 'future_seed', 'coordinator_v5_supervision'):
            with pytest.raises(ValueError, match='privileged_input'):
                optimized.encode({**view, key: {}})


def test_hand_calculated_gae_does_not_cross_episode_boundary():
    import gymnasium as gym
    buffer = MaskableRolloutBuffer(3, gym.spaces.Box(-2, 4, (1,), dtype=np.float32),
        gym.spaces.Discrete(35), gamma=1., gae_lambda=.95, n_envs=1)
    buffer.rewards[:, 0] = [0., 1., 0.]
    buffer.values[:, 0] = [.2, .4, -.1]
    buffer.episode_starts[:, 0] = [1., 0., 1.]
    buffer.compute_returns_and_advantage(torch.tensor([.3]), np.array([False]))
    np.testing.assert_allclose(buffer.advantages[:, 0], [.77, .6, .4], atol=1e-6)
    np.testing.assert_allclose(buffer.returns[:, 0], [.97, 1., .3], atol=1e-6)


def test_config_fails_closed_for_unversioned_or_unsafe_foundation():
    config = {'schema_version': 'showdown-autonomous-training-v1', 'max_runtime_seconds': 60,
        'envs': 1, 'cpu_percent': 50, 'memory_mib': 2048, 'transition_budget_scope': 'trained_rollouts_v1',
        'experiments': [{'name': 'foundation', 'seed': 95017, 'steps': 128, 'encoder_version': VERSION,
            'combat_foundation': foundation_contract(), 'gamma': 1., 'gae_lambda': .95,
            'zero_avoiding_beta': .001, 'ent_coef': .01}]}
    validate_config(config)
    for key, value in [('cpu_percent', 51), ('memory_mib', 13000), ('cpu_threads', 2)]:
        changed = deepcopy(config)
        changed[key] = value
        with pytest.raises(ValueError, match='foundation_training_contract'):
            validate_config(changed)


def test_native_learning_recovery_masks_rewards_and_gradient_guard(checkout, tmp_path):
    encoder = StrategicCombatV5Encoder(CAT)
    factory = LearningEnvFactory(checkout, str(CAT), VERSION, 95000000,
        'showdown-learning-curriculum-v8', ('max_power',), {}, max_decisions=8,
        terminal_transport_version='native-opaque-terminal-transport-v1', foundation_profile=True)
    vector = DummyVecEnv([factory])
    try:
        learner = foundation_model(vector)
        before = {key: value.clone() for key, value in learner.policy.state_dict().items()}
        learner.learn(16, callback=BudgetCallback(Budget()))
        assert optimizer_steps(learner) == 2
        assert any(not torch.equal(value, before[key]) for key, value in learner.policy.state_dict().items())
        assert learner.logger.name_to_value['foundation/clipped_gradient_norm_max'] <= .50001
        assert learner.logger.name_to_value['foundation/gradient_norm_max'] > 0
        assert learner.logger.name_to_value['foundation/auxiliary_forward_seconds'] > 0
        assert vector.env_method('drain_foundation_profile')[0]['native_bridge_wait_seconds'] > 0
        assert all(row['truncated'] or row['terminated'] for row in vector.env_method('drain_completed')[0])
        saved = save_checkpoint(learner, encoder, tmp_path / 'saved', {})
        restored = LearnedPolicy(saved, CAT)
        assert type(restored.model) is FoundationCombatPPO
        assert restored.metadata['combat_foundation'] == foundation_contract()
        assert optimizer_steps(restored.model) == optimizer_steps(learner)
        for key, value in learner.policy.state_dict().items():
            torch.testing.assert_close(value, restored.model.policy.state_dict()[key], rtol=0, atol=0)
        for original_state, restored_state in zip(learner.policy.optimizer.state.values(), restored.model.policy.optimizer.state.values()):
            for key in original_state:
                torch.testing.assert_close(original_state[key], restored_state[key], rtol=0, atol=0)
        view = vector.get_attr('current')[0]
        result = restored.infer(view)
        probabilities = np.asarray(result['action_probabilities'])
        assert not probabilities[~np.asarray(view['action_mask'], bool)].any()
        restored.model.set_env(vector)
        restored.model.learn(8, reset_num_timesteps=False, callback=BudgetCallback(Budget()))
        assert optimizer_steps(restored.model) == 3
        parameter = next(restored.model.policy.parameters())
        hook = parameter.register_hook(lambda gradient: torch.full_like(gradient, float('nan')))
        snapshot = {key: value.clone() for key, value in restored.model.policy.state_dict().items()}
        steps = optimizer_steps(restored.model)
        try:
            with pytest.raises((ValueError, RuntimeError), match='(nonfinite|invalid_clipped)'):
                restored.model.learn(8, reset_num_timesteps=False, callback=BudgetCallback(Budget()))
        finally:
            hook.remove()
        assert optimizer_steps(restored.model) == steps
        assert all(torch.equal(value, snapshot[key]) for key, value in restored.model.policy.state_dict().items())
        metadata_path = Path(saved).with_suffix('.json')
        metadata = json.loads(metadata_path.read_text())
        metadata['combat_foundation']['gradient_guard'] = 'disabled'
        metadata_path.write_text(json.dumps(metadata))
        with pytest.raises(ValueError, match='foundation_checkpoint_contract'):
            LearnedPolicy(saved, CAT)
    finally:
        vector.close()
