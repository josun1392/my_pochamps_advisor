"""Operational fault injection without PPO optimization or native evaluation."""

from copy import deepcopy
import json
from types import SimpleNamespace
import threading
import gymnasium as gym
import numpy as np
import pytest
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.vec_env import DummyVecEnv

from advisor.learned_training_operations import (
    ACCOUNTING_VERSION, CompletedRollouts, RetryMonitor, TrainingJournal, read_journal,
)
from scripts.train_showdown_autonomous import BudgetCallback, optimizer_steps


def retry(revision, case=12, episode="native-a"):
    return {"episode_id": episode, "episode_case": case, "revision_before": revision,
            "before": {"self": {"action_index": 0, "action_mask": [1, 0]}}}


def test_eight_retry_gate_works_without_external_callback():
    monitor = RetryMonitor()
    assert not monitor.inspect([retry(index) for index in range(7)], [], 32768)
    assert monitor.inspect([retry(7)], [], 32768)[0]["reason"] == "eight_retries_same_episode"


def test_retry_gate_crosses_checkpoint_and_serialization_boundaries():
    first = RetryMonitor()
    assert not first.inspect([retry(index) for index in range(5)], [], 32768)
    restored = RetryMonitor(json.loads(json.dumps(first.pending)))
    assert not restored.inspect([retry(4), retry(5), retry(6)], [], 32768)
    alerts = restored.inspect([retry(7)], [{"episode_identity": {"case_index": 12}}], 32768)
    assert [row["reason"] for row in alerts] == ["eight_retries_same_episode"]
    assert not restored.pending


def test_retry_rate_and_mask_illegality_are_distinct():
    assert not RetryMonitor().inspect([retry(0)], [], 100)
    assert RetryMonitor().inspect([retry(0), retry(1)], [], 100)[0]["reason"] == "interval_retry_rate_above_one_percent"
    record = retry(0)
    record["before"]["self"]["action_index"] = 1
    assert RetryMonitor().inspect([record], [], 32768)[0]["reason"] == "mask_illegal_retry_choice"


def test_retry_episode_identity_does_not_merge_distinct_native_episodes():
    monitor = RetryMonitor()
    assert not monitor.inspect([retry(index) for index in range(7)] + [retry(0, episode="native-b")], [], 32768)


def test_completed_rollouts_count_only_observed_optimizer_progress():
    ledger = CompletedRollouts()
    ledger.collected(512, 0)
    ledger.settle(0)
    assert ledger.transitions == 0
    ledger.collected(512, 0)
    ledger.settle(16)
    ledger.settle(16)
    assert ledger.transitions == 512
    ledger.collected(512, 16)
    with pytest.raises(ValueError, match="unsettled"):
        ledger.collected(512, 16)
    with pytest.raises(ValueError, match="regressed"):
        ledger.settle(15)


class MaskEnv(gym.Env):
    observation_space = gym.spaces.Box(-1., 1., (2,), dtype=np.float32)
    action_space = gym.spaces.Discrete(35)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        return np.zeros(2, dtype=np.float32), {}

    def step(self, action):
        assert action == 0
        return np.zeros(2, dtype=np.float32), 0., False, False, {}

    def action_masks(self):
        return np.arange(35) == 0


@pytest.mark.parametrize("stop_at", [1, 7, 8, 9])
def test_upstream_stop_boundary_never_counts_unoptimized_rollout(stop_at):
    torch.set_num_threads(1)
    vector = DummyVecEnv([MaskEnv])
    model = MaskablePPO("MlpPolicy", vector, n_steps=8, batch_size=8, n_epochs=1, seed=42)
    before = deepcopy(model.policy.state_dict())
    budget = SimpleNamespace(stopping=lambda: model.num_timesteps >= stop_at)
    callback = BudgetCallback(budget)
    _, callback = model._setup_learn(8, callback=callback)
    callback.on_training_start({}, {})
    complete = model.collect_rollouts(vector, callback, model.rollout_buffer, n_rollout_steps=8)
    callback.on_training_end()
    assert complete == (stop_at > 8)
    assert callback.completed_rollouts.transitions == 0
    assert optimizer_steps(model) == 0
    assert all(torch.equal(value, before[key]) for key, value in model.policy.state_dict().items())
    if stop_at == 8:
        assert model.num_timesteps // 8 * 8 == 8
        assert model.rollout_buffer.pos == 7 and not model.rollout_buffer.full
    vector.close()


def test_journal_survives_kill_tail_and_separates_observed_from_durable(tmp_path):
    durable = {"transitions": 512, "trained_rollout_transitions": 512, "completed_battles": 40,
               "optimizer_steps": 16, "latest": "immutable.zip"}
    journal = TrainingJournal(tmp_path, durable)
    journal.append("running", transitions=700, completed_battles=52)
    with journal.path.open("ab") as stream:
        stream.write(b'{"sequence":2')
    original = journal.path.read_bytes()
    restored = TrainingJournal(tmp_path, durable)
    first = read_journal(restored.path)["records"][0]
    interrupted = first["observed"]["interrupted_launches"][0]
    assert interrupted["incomplete_tail_preserved"]
    assert interrupted["exit_cause"] == "unknown"
    assert interrupted["exact_uncommitted_training_work"] is None
    assert interrupted["last_observation"]["observed"]["transitions"] == 700
    assert first["durable_checkpoint"]["transitions"] == 512
    assert journal.path.read_bytes() == original
    restored.publish({**durable, "transitions": 1024, "trained_rollout_transitions": 1024})
    restored.append("launch_end", status="stopped")
    assert read_journal(restored.path)["records"][-1]["durable_checkpoint"]["transitions"] == 1024


def test_journal_middle_corruption_fails_closed(tmp_path):
    journal = TrainingJournal(tmp_path, {})
    with journal.path.open("ab") as stream:
        stream.write(b'not-json\n')
    with pytest.raises(json.JSONDecodeError):
        TrainingJournal(tmp_path, {})


def test_journal_fsync_and_nonfinite_rejection(tmp_path, monkeypatch):
    syncs = []
    monkeypatch.setattr("advisor.learned_training_operations.os.fsync", syncs.append)
    journal = TrainingJournal(tmp_path, {})
    assert len(syncs) == 1
    with pytest.raises(ValueError):
        journal.append("running", metric=float("nan"))
    assert len(read_journal(journal.path)["records"]) == 1
    assert ACCOUNTING_VERSION == "completed-optimizer-rollouts-v2"


def test_callback_settles_only_successful_prior_rollout_without_optimization(monkeypatch):
    import scripts.train_showdown_autonomous as trainer

    model = SimpleNamespace(clock=0)
    monkeypatch.setattr(trainer, "optimizer_steps", lambda value: value.clock)
    monkeypatch.setattr(trainer, "require_finite_ppo", lambda *args, **kwargs: None)
    callback = BudgetCallback(SimpleNamespace(stopping=lambda: False))
    callback.model = model
    callback.completed_rollouts.collected(512, 0)
    model.clock = 16
    callback._on_rollout_start()
    assert callback.completed_rollouts.transitions == 512
    callback._on_training_end()
    assert callback.completed_rollouts.transitions == 512


def test_resume_cannot_reinterpret_legacy_accounting_or_remove_stop(tmp_path, monkeypatch):
    import scripts.train_showdown_autonomous as trainer

    state = {"config_fingerprint": "frozen", "trained_rollout_transitions": 589824}
    original = json.dumps(state).encode()
    (tmp_path / "state.json").write_bytes(original)
    (tmp_path / "STOP").touch()
    monkeypatch.setattr(trainer, "validate_config", lambda value: None)
    monkeypatch.setattr(trainer, "training_config_fingerprint", lambda value: ("frozen", {}))
    monkeypatch.setattr(trainer, "RuntimeLimit", lambda *args: SimpleNamespace(finished=threading.Event()))
    job = SimpleNamespace(inherited_job=False, usage=lambda: {})
    with pytest.raises(ValueError, match="accounting_version_mismatch"):
        trainer.run({"max_runtime_seconds": 30}, tmp_path, resume=True, resource_job=job)
    assert (tmp_path / "state.json").read_bytes() == original
    assert (tmp_path / "STOP").exists()
    assert not (tmp_path / "run.lock").exists()
