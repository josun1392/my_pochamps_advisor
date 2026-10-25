from copy import deepcopy
from types import SimpleNamespace
import json
import numpy as np
import pytest
import torch
from torch import nn

from advisor.learned_update_credit import score_public, choose_alternative, normalized_advantage, UpdateCreditObserver
from advisor.learned_decision_snapshots import DecisionSnapshotRecorder, PPO_GAE_SCOPE
from tests.test_decision_snapshots import prepared, complete


class ProbePolicy(nn.Module):
    """Unit fixture only; no environment, optimizer or training."""
    def __init__(self):
        super().__init__(); self.scores = nn.Parameter(torch.linspace(-1, 1, 35))
        self.action_net = nn.Identity(); self.action_dist = SimpleNamespace()
    def set_training_mode(self, mode): self.train(mode)
    def forward(self, obs, action_masks, deterministic):
        assert deterministic
        z = self.action_net(self.scores[None].expand(len(obs), -1))
        mask = torch.as_tensor(action_masks, dtype=torch.bool)
        self.action_dist.distribution = torch.distributions.Categorical(logits=z.masked_fill(~mask, -1e8))
        return z.argmax(-1), obs[:, :1] * 0 + .25, None


def test_score_probe_preserves_weights_mode_RNG_and_legal_probabilities():
    policy = ProbePolicy(); policy.train(True); before = deepcopy(policy.state_dict()); rng = torch.get_rng_state().clone()
    mask = [int(i in (1, 6, 7)) for i in range(35)]
    result = score_public(policy, np.array([1.], np.float32), mask)
    assert policy.training and torch.equal(torch.get_rng_state(), rng)
    assert not policy.action_net._forward_pre_hooks
    assert all(torch.equal(v, before[k]) for k,v in policy.state_dict().items())
    assert all(p.grad is None for p in policy.parameters())
    assert result["value"] == .25 and result["argmax"] == 7
    assert sum(result["probabilities"]) == pytest.approx(1.)
    assert all(p == 0 for p,m in zip(result["probabilities"], mask) if not m)


def test_alternative_uses_preupdate_public_probabilities_not_hidden_or_outcomes():
    public = {"request_state": "move", "action_mask": [int(i in (1,6,7)) for i in range(35)],
              "own_request": {"active": [{"moves": [{"id":"tackle"},{"id":"recover"}]}]}}
    p = [0.] * 35; p[6] = .8; p[7] = .15; p[1] = .05
    assert choose_alternative(public, 1, p) == 6
    assert choose_alternative(public, 6, p) == 7
    changed = {**public, "unconsumed_hidden_test_marker": {"future_winner": "opponent"}}
    assert choose_alternative(changed, 6, p) == 7
    with pytest.raises(ValueError): choose_alternative(public, 0, p)


def test_positive_raw_GAE_can_have_negative_normalized_minibatch_advantage():
    raw = torch.tensor([1., 2., 4.]); before = raw.clone()
    assert normalized_advantage(raw, 0, True) < 0
    assert normalized_advantage(raw, 0, False) == 1.
    assert torch.equal(raw, before)


def test_actual_PPO_GAE_scope_is_explicit_and_frozen_default_preserved(tmp_path):
    env, recorder = prepared(tmp_path); recorder.gae_scope = PPO_GAE_SCOPE
    buffer = complete(env, recorder); recorder.join(buffer, 0)
    joined = json.loads(next((recorder.directory / "joins").glob("*.json")).read_text())
    assert joined["GAE_scope"] == PPO_GAE_SCOPE
    with pytest.raises(ValueError, match="explicit_snapshot"):
        DecisionSnapshotRecorder(tmp_path / "bad", policy_id="a"*64, gae_scope="counterfactual_optimal_label")


def test_optional_native_verification_parameters_fail_before_native_access(tmp_path):
    from scripts.pilot_foundation_decision_snapshots import native_comparisons
    with pytest.raises(ValueError, match="execution_contract"):
        native_comparisons({"future_seeds": []}, tmp_path, SimpleNamespace(roots=[]),
                           None, {}, None, original_replay_repetitions=3)


def test_update_credit_budget_fails_closed_before_file_or_model_access():
    from scripts.diagnose_foundation_update_credit import validate_plan
    with pytest.raises(ValueError, match="bounded_standard"):
        validate_plan({"transitions":16385})


def test_sample_observer_returns_original_tensors_and_rejects_wrong_row(tmp_path):
    from hashlib import sha256
    from advisor.learned_parent_anchor import optimizer_clock
    policy = ProbePolicy(); policy.optimizer = torch.optim.Adam(policy.parameters(), lr=5e-5)
    directory = tmp_path / "snapshots"; (directory / "public").mkdir(parents=True)
    public = {"request_state": "move", "action_mask": [int(i in (6,7)) for i in range(35)],
        "own_request": {"active":[{"moves":[{"id":"tackle"},{"id":"recover"}]}]}}
    features = np.array([100.], np.float32); pre = score_public(policy, features, public["action_mask"])
    root = {"id":"test", "rollout":0, "t":0, "action":6, "value":pre['value'],
        "old_logp":pre['log_probabilities'][6], "action_mask":public['action_mask'],
        "observation_sha256":sha256(features.tobytes()).hexdigest(), "advantage":float(torch.tensor(.8))}
    (directory / "public/test.json").write_text(json.dumps({"observation":public}))
    snapshots = SimpleNamespace(directory=directory, roots=[root], policy_id="a"*64)
    batch = SimpleNamespace(observations=torch.tensor([[100.],[200.],[300.]]),
        actions=torch.tensor([[6],[6],[7]]), advantages=torch.tensor([.8,1.2,-.4]))
    class Buffer:
        def _get_samples(self, indices): return batch
    model = SimpleNamespace(policy=policy, rollout_buffer=Buffer(), normalize_advantage=True)
    observer = UpdateCreditObserver(tmp_path/'credit', SimpleNamespace(encode=lambda _: features), snapshots, 'a'*64)
    observer.start(model, 0); observer.before_update(model)
    assert model.rollout_buffer._get_samples(np.array([0,1,2])) is batch
    event = observer.pending['minibatches'][0]
    assert not event['optimizer_applied'] and event['roots'][0]['raw_GAE']==root['advantage']
    assert optimizer_clock(policy)==0 and not policy.optimizer.state
    batch.observations[0,0] = 101.
    with pytest.raises(ValueError, match='row_binding'):
        model.rollout_buffer._get_samples(np.array([0,1,2]))
    observer.cleanup()
    assert '_get_samples' not in model.rollout_buffer.__dict__
