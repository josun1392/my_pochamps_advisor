"""Public reward, maintained buffer and persistence gates; no native starts."""
from copy import deepcopy
from types import SimpleNamespace
import os

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pytest
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.vec_env import DummyVecEnv

from advisor.learned_public_potential import (
    potential_contract, validate_contract, public_phi, public_progress, PublicPotentialReward, PARENT_SHA,
)
from advisor.learned_potential_ppo import PotentialFoundationPPO, validate_model, validate_loaded, initial_model
from advisor.learned_combat_foundation import FoundationCombatPPO, foundation_contract
from advisor.learned_objective import objective_contract, require_resume_objective
from advisor.learned_gae_lambda import gae_arrays


def view(events=(), *, side="self", episode="e1", revision=1, terminated=False, truncated=False):
    return {"side": side, "episode_id": episode, "revision": revision, "turn": 1,
        "terminated": terminated, "truncated": truncated,
        "public_history": ["|start", "|turn|1", *events]}


F = "|faint|p2a: Target"


@pytest.mark.parametrize("side,expected", [("self", 1/30), ("opponent", -1/30)])
def test_owner_relative_public_faint_only(side, expected):
    o = view([F], side=side)
    assert public_phi(o) == pytest.approx(expected)
    altered = deepcopy(o)
    altered.update(opponent_request={"hidden_moves": ["secret"]}, future_seed=1,
        own_request={"private": "irrelevant"}, state={"hidden": "irrelevant"}, action_mask=[0]*35)
    assert public_phi(altered) == public_phi(o)  # explicit input whitelist


def test_bounds_revived_events_not_current_alive_estimate_and_illusion():
    events = []
    for _ in range(5):
        events.extend([F, "|-heal|p2a: Target|100/100|[from] move: Revival Blessing"])
    assert public_progress(view(events))["opponent_faints"] == 5
    assert public_phi(view(events)) == pytest.approx(.1)
    o = view(["|switch|p2a: Apparent|Pikachu, L50|100/100", "|replace|p2a: Real|Zoroark, L50|100/100", F])
    assert public_phi(o) == pytest.approx(1/30)
    o["terminated"] = True
    assert public_phi(o) == 0


@pytest.mark.parametrize("change", [
    {"public_history": []}, {"public_history": ["|start", "|start", "|turn|1"]},
    {"public_history": ["|start", "|turn|2"]}, {"public_history": ["|start", "|turn|1", "|turn|1"]},
    {"public_history": ["|start", "|turn|1", F, F]},
    {"public_history": ["|start", "|turn|1", "|faint|p3a: Hidden"]},
    {"public_history": ["|start", "|turn|1", "|seed|1,2,3,4"]},
    {"episode_id": None}, {"side": "p1"}, {"revision": True}, {"turn": 2},
    {"terminated": True, "truncated": True},
])
def test_missing_unknown_duplicate_or_noncausal_history_fails_closed(change):
    with pytest.raises(ValueError):
        public_phi({**view(), **change})


class FakeNative(gym.Env):
    observation_space = spaces.Box(-10, 10, (2,), dtype=np.float32)
    action_space = spaces.Discrete(35)

    def __init__(self, steps=None):
        self.steps = steps or [((), 0., False, False)]
        self.n = 0

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.n += 1
        self.current = view(episode=f"e{self.n}")
        self.i = 0
        return np.zeros(2, np.float32), {}

    def action_masks(self):
        return np.array([True]*2+[False]*33)

    def step(self, action):
        events, reward, terminated, truncated = self.steps[self.i]
        self.i += 1
        self.current["public_history"].extend(events)
        self.current["revision"] += 1
        self.current.update(terminated=terminated, truncated=truncated)
        info = {"native_outcome": {"terminated": terminated, "truncated": truncated,
            "rewards": {"self": reward, "opponent": -reward}}}
        return np.ones(2, np.float32), reward, terminated, truncated, info


@pytest.mark.parametrize("terminal_reward", [-1., 0., 1.])
def test_episode_telescoping_and_native_infos_unchanged(terminal_reward):
    raw = FakeNative([((F,), 0., False, False), ((), terminal_reward, True, False)])
    e = PublicPotentialReward(raw, potential_contract())
    e.reset()
    first = e.step(0)
    second = e.step(0)
    assert first[1] == pytest.approx(1/30)
    assert second[1] == pytest.approx(terminal_reward-1/30)
    assert first[1]+second[1] == pytest.approx(terminal_reward)
    assert second[4]["native_outcome"]["rewards"]["self"] == terminal_reward
    assert second[4]["public_potential"]["episode_shaped_return"] == pytest.approx(terminal_reward)
    with pytest.raises(ValueError):
        e.step(0)  # cannot bridge terminal to next episode
    e.reset()
    assert public_phi(e.current) == 0


def test_one_outer_difference_after_wait_and_forced_or_retry_refresh_zero():
    e = PublicPotentialReward(FakeNative([
        ((F, "|faint|p1a: Own"), 0., False, False), # multiple native changes inside one learner step
        (("|request_refresh|public",), 0., False, False),
        (("|switch|p1a: Reserve|Blissey, L50|100/100",), 0., False, False),
    ]), potential_contract())
    e.reset()
    assert e.step(0)[1] == 0.
    assert e.step(0)[1] == 0.
    assert e.step(0)[1] == 0.


@pytest.mark.parametrize("what", ["owner", "prefix", "revision", "predecision"])
def test_transition_binding_and_fail_closed_prevent_reexecution(what):
    raw = FakeNative()
    e = PublicPotentialReward(raw, potential_contract())
    e.reset()
    if what == "predecision":
        raw.current["public_history"].append(F)
    else:
        original = raw.step
        def wrong(a):
            result = original(a)
            if what == "owner": raw.current["episode_id"] = "other"
            elif what == "prefix": raw.current["public_history"].insert(1, "|message|old")
            else: raw.current["revision"] = 1
            return result
        raw.step = wrong
    with pytest.raises(ValueError): e.step(0)
    with pytest.raises(ValueError): e.step(0)


def test_maintained_PPO_timeout_bootstrap_once_and_vec_auto_reset():
    # Two one-step timeouts. The real maintained collector adds .6 once to each
    # shaped env reward. No native battle, optimizer step or custom GAE.
    vector = DummyVecEnv([lambda: PublicPotentialReward(
        FakeNative([((F,), 0., False, True)]), potential_contract())])
    model = MaskablePPO("MlpPolicy", vector, n_steps=2, batch_size=2,
        gamma=1., gae_lambda=.95, device="cpu", seed=1)
    _, callback = model._setup_learn(2)
    model.policy.predict_values = lambda obs: torch.full((len(obs), 1), .6)
    assert model.collect_rollouts(vector, callback, model.rollout_buffer, n_rollout_steps=2)
    assert np.allclose(model.rollout_buffer.rewards[:, 0], .6+1/30)
    assert np.allclose(model.rollout_buffer.returns[:, 0], .6+1/30)
    assert public_phi(vector.get_attr("current")[0]) == 0  # fresh auto-reset
    assert not model.policy.optimizer.state  # 0 Adam updates
    vector.close()


def test_critic_coordinate_cancellation_is_null_control_not_new_credit():
    v = np.array([[.2], [.3], [.4]], np.float32)
    phi = np.array([[0.], [1/30], [2/30], [0.]], np.float32)
    r = np.array([[0.], [0.], [1.]], np.float32)
    shaped = r+phi[1:]-phi[:-1]
    starts = np.array([[1.], [0.], [0.]], np.float32)
    native = gae_arrays(v, r, starts, np.array([0.]), np.array([True]), .95)
    shifted = gae_arrays(v-phi[:-1], shaped, starts, np.array([0.]), np.array([True]), .95)
    unshifted = gae_arrays(v, shaped, starts, np.array([0.]), np.array([True]), .95)
    assert np.allclose(shifted, native, atol=1e-7)
    assert not np.allclose(unshifted, native)
    assert np.allclose(shaped.sum(), r.sum())


def shell(cls, marker=None):
    m = object.__new__(cls)
    m.gamma = 1.; m.gae_lambda = .95
    m.rollout_buffer = SimpleNamespace(gamma=1., gae_lambda=.95)
    if marker is not None: m.public_potential_reward = marker
    return m


def test_versioned_contract_loader_and_wrong_algorithm_reject():
    from advisor.learned_regularized_ppo import checkpoint_algorithm
    from advisor.learned_combat_v5_strategic_aux import auxiliary_contract
    marker = potential_contract()
    meta = {"combat_foundation": foundation_contract(), "encoder_version": foundation_contract()["encoder"],
        "integrated_auxiliary": auxiliary_contract(), "gamma": 1., "gae_lambda": .95,
        "public_potential_reward": marker, "public_potential_trained": 0,
        "training_objective": objective_contract(1., .95, marker)}
    assert checkpoint_algorithm(meta) is PotentialFoundationPPO
    m = shell(PotentialFoundationPPO, marker); m.public_potential_trained = 0
    validate_loaded(m, meta)
    for field in ["training_objective", "public_potential_reward", "public_potential_trained"]:
        bad = deepcopy(meta); bad.pop(field)
        with pytest.raises(ValueError):
            cls = checkpoint_algorithm(bad)
            validate_loaded(m, bad)
    for key in ["alpha", "count_cap", "budget"]:
        bad = deepcopy(marker); bad[key] = 1
        with pytest.raises(ValueError): validate_contract(bad)
    with pytest.raises(ValueError): validate_model(shell(FoundationCombatPPO, marker))
    with pytest.raises(ValueError): validate_model(shell(PotentialFoundationPPO))
    with pytest.raises(ValueError): require_resume_objective(m, {"gamma":1., "gae_lambda":.95}, foundation_contract()["encoder"])
    m.public_potential_trained = 65536; m.n_steps = 128; m.n_envs = 4
    with pytest.raises(ValueError, match="budget"): m.train()


def test_legacy_objective_and_model_path_remain_unshaped():
    old = objective_contract(1., .95)
    assert old["reward"] == "native_sparse_terminal_win_loss_draw"
    assert "public_potential_reward" not in old
    validate_model(shell(FoundationCombatPPO))
    e = FakeNative([((F,), 0., False, False)])
    e.reset(); assert e.step(0)[1] == 0  # opt-in absent: original reward


def test_same_four_arm_architecture_and_frozen_evaluation_budget():
    from advisor.learned_potential_study import matched_configs, game_slots, POLICIES
    from advisor.learned_potential_ppo import RECORDER_VERSION
    from advisor.learned_ppo_contract_audit import VERSION as AUDIT
    configs = {}
    for key in POLICIES[1:]:
        marker = potential_contract() if key.startswith("B") else None
        e = {"name":key, "seed":int(key[2:]), "steps":65536, "initial_model_id":PARENT_SHA,
            "fresh_optimizer":False, "gae_lambda":.95, "objective":objective_contract(1., .95, marker)["objective_id"]}
        if marker: e["public_potential_reward"] = marker
        c = {"envs":4, "cpu_percent":50, "memory_mib":12288, "device":"cpu", "vector_backend":"subproc",
            "transition_budget_scope":"trained_rollouts_v1", "checkpoint_evaluation_mode":"disabled_for_frozen_study_v1",
            "checkpoint_steps":16384, "ppo_update_audit":AUDIT, "potential_matched_rollout":RECORDER_VERSION,
            "experiments":[e]}
        if marker: c["potential_first_rollout_reference"] = "reference"
        configs[key] = c
    assert matched_configs(configs, PARENT_SHA)["max_new_Adam"] == 8192
    bad = deepcopy(configs); bad["B_128021"]["experiments"][0]["fresh_optimizer"] = True
    with pytest.raises(ValueError): matched_configs(bad, PARENT_SHA)
    cases = [{"scope":"train" if i < 96 else "heldout", "index":i, "scenario_sha256":str(i)} for i in range(192)]
    slots = game_slots(cases)
    assert len(slots) == 5760
    for key in POLICIES:
        assert sum(s["policy"] == key and s["scope"] == "heldout" for s in slots) == 576


def test_original_parent_transfer_save_load_and_resume_preserve_Adam_without_update(tmp_path):
    parent = os.environ.get("POKEADVICE_POTENTIAL_PARENT")
    if not parent: pytest.skip("trusted parent opt-in; zero native and Adam updates")
    from pathlib import Path
    from advisor.learned_policy import LearnedPolicy
    from advisor.learned_parent_anchor import tensor_digest, optimizer_digest
    from scripts.train_showdown_autonomous import save_checkpoint
    catalog = Path(__file__).resolve().parents[1]/"models/showdown_mc_domain_v1/catalog.json"
    original = LearnedPolicy(parent, catalog, expected_model_id=PARENT_SHA)
    exp = {"public_potential_reward":potential_contract(), "fresh_optimizer":False}
    converted = initial_model(original.model, parent, exp, resume=False)
    path = save_checkpoint(converted, original.encoder, tmp_path/"shaped", {})
    loaded = LearnedPolicy(path, catalog).model
    assert type(loaded) is PotentialFoundationPPO
    assert tensor_digest(original.model.policy.state_dict()) == tensor_digest(loaded.policy.state_dict())
    assert optimizer_digest(original.model.policy) == optimizer_digest(loaded.policy)
    assert initial_model(loaded, path, exp, resume=True) is loaded
    with pytest.raises(ValueError): initial_model(loaded, path, {}, resume=True)


def test_first_rollout_matching_ignores_only_intentional_reward_and_GAE_changes(tmp_path):
    import gzip
    import json
    from advisor.learned_potential_ppo import PotentialSignalRecorder
    ref, own = tmp_path/"A", tmp_path/"B"
    ref.mkdir(); own.mkdir()
    name = "rollout_1049088_fixed"
    fields = ("raw_logits", "probabilities", "native_masks", "actions", "old_logp", "values",
        "episode_starts", "last_values", "last_dones")
    data = {k:np.zeros(4, np.float32) for k in fields}
    raw = np.array([[0.], [1.]])
    for folder, change in [(ref, 0.), (own, .03)]:
        np.savez(folder/(name+".audit.npz"), **data, rewards=raw+change, advantages=raw+change)
        np.savez(folder/(name+".potential.npz"), raw_native_rewards=raw)
        rows = [{"observation_sha256":str(i), "legal_mask_bits":3, "action":0,
            "old_logp":0., "value":0., "raw_native_reward":0., "reward":change,
            "episode_start":False, "done":False, "truncated":False} for i in range(512)]
        with gzip.open(folder/(name+".jsonl.gz"), "wt", encoding="utf8") as f:
            for row in rows: f.write(json.dumps(row)+"\n")
    recorder = PotentialSignalRecorder(own, None, reference=ref)
    assert recorder.compare_first(name, {"raw_native_rewards":raw})["public_rows_exact"] == 512
    with pytest.raises(ValueError, match="native_rewards"):
        recorder.compare_first(name, {"raw_native_rewards":raw+1})
    np.savez(own/(name+".audit.npz"), **{**data, "values":np.ones(4)})
    with pytest.raises(ValueError, match="policy_or_execution"):
        recorder.compare_first(name, {"raw_native_rewards":raw})


def test_analysis_gate_does_not_confuse_parent_or_seat_diagnostics_with_primary():
    from advisor.learned_potential_study import game_slots, analyze
    cases = [{"scope":s, "index":i, "scenario_sha256":str(i)} for i,s in enumerate(("train", "heldout"))]
    rows = [{"slot":s, "record":{"winner":"self" if s["policy"].startswith("B") else "opponent",
        "truncated":False}} for s in game_slots(cases)]
    assert analyze(rows, cases, resamples=32)["conclusion"] == "PROMISING_REQUIRES_INDEPENDENT_CONFIRMATION"
    with pytest.raises(ValueError): analyze(rows[:-1], cases, resamples=32)
