from copy import deepcopy
from types import SimpleNamespace
import json
import random

import numpy as np
import pytest

from advisor.learned_decision_snapshots import (
    DecisionSnapshotRecorder, digest, outside_git, read_root, replay_original, write_new,
)
from advisor.learned_gym import ShowdownLearningEnv


def view(side="self", n=0):
    return {"episode_id": "original", "revision": n, "side": side, "turn": n + 1,
            "request_state": "move", "action_mask": [int(i in (6, 7)) for i in range(35)],
            "choices": ["move " + str(i - 5) if i in (6, 7) else None for i in range(35)],
            "public_history": [str(i) for i in range(n)], "events": [],
            "own_request": {}, "state": {"hp": 100 - n}}


class Encoder:
    def encode(self, v):
        assert not {"native_state", "checkpoint", "future_seed", "opponent_request"} & set(v)
        return np.array([v["state"]["hp"]], dtype=np.float32)


class Native:
    def __init__(self): self.n = 0
    def observation(self, side, **_): return view(side, self.n)
    def save(self):
        body = {"schema_version": "test-only", "decisions": self.n,
                "native_state": {"n": self.n, "prng": [1, 2, 3, 4]}}
        return {**body, "digest": digest(body)}
    def restart(self, cp): self.n = cp["native_state"]["n"]
    def step(self, actions, revision):
        assert revision == self.n
        self.n += 1
        return {"revision": self.n, "decisions": self.n, "terminated": True,
                "truncated": False, "winner": "self", "rewards": {"self": 1, "opponent": -1},
                "action_rejected": False}


def prepared(tmp_path):
    native = Native()
    env = SimpleNamespace(native=native, encoder=Encoder(), split="train", current=view())
    recorder = DecisionSnapshotRecorder(tmp_path / "records", policy_id="a" * 64)
    recorder.prepare(env, step=0, rollout=0, t=0)
    return env, recorder


def complete(env, recorder):
    views = {s: env.native.observation(s) for s in ("self", "opponent")}
    actions = {"self": 6, "opponent": 7}
    recorder.native_before(env.native, views, actions)
    result = env.native.step(actions, revision=0)
    recorder.native_after(env.native, result)
    recorder.selected(action=6, value=.25, logp=-.5,
                      features=env.encoder.encode(env.current), mask=env.current["action_mask"])
    buffer = SimpleNamespace(actions=np.array([[[6]]]), values=np.array([[.25]]),
        log_probs=np.array([[-.5]]), observations=np.array([[[100]]], dtype=np.float32),
        action_masks=np.array([[env.current["action_mask"]]]), advantages=np.array([[.75]]),
        returns=np.array([[1.]]), rewards=np.array([[1.]]), episode_starts=np.array([[True]]))
    return buffer


def test_pre_actor_native_capture_public_isolation_and_exact_GAE_join(tmp_path):
    env, recorder = prepared(tmp_path)
    original = deepcopy(env.current)
    assert recorder.prepared is not None and "action" not in recorder.prepared
    assert env.current == original
    assert list((tmp_path / "records/private").glob("*.gz"))
    buffer = complete(env, recorder)
    recorder.join(buffer, 0); recorder.finish()
    root = recorder.roots[0]
    assert root["advantage"] == .75 and root["value"] == .25 and root["joined"]
    assert root["native_terminal_recorded"] and len(root["trace"]) == 1
    public = json.loads(next((tmp_path / "records/public").glob("*.json")).read_text())
    assert public["observation"] == original and "native_state" not in json.dumps(public)
    cp = read_root(recorder.directory, root)
    one = replay_original(env.native, cp, root, original)
    two = replay_original(env.native, cp, root, original)
    assert one == two and one["terminal"]["winner"] == "self"


def test_default_native_step_does_not_save_or_instrument():
    env = ShowdownLearningEnv.__new__(ShowdownLearningEnv)
    env.native = Native()
    env.native.save = lambda: (_ for _ in ()).throw(AssertionError("default must not save"))
    env.current = view(); env.opponent = SimpleNamespace(act=lambda _: 7)
    env.collect_tactical_metrics = False; env._rejected_choices = 0
    result = env._native_step(6)
    assert result["terminated"]


def test_mask_action_and_GAE_mismatch_fail_closed(tmp_path):
    env, recorder = prepared(tmp_path)
    buffer = complete(env, recorder)
    buffer.actions[0, 0, 0] = 7
    with pytest.raises(ValueError, match="GAE_join"):
        recorder.join(buffer, 0)
    with pytest.raises(ValueError, match="unsettled"):
        recorder.finish()
    with pytest.raises(ValueError, match="integrity_or_GAE"):
        read_root(recorder.directory, recorder.roots[0])


def test_corrupt_payload_and_suffix_fail_closed(tmp_path):
    env, recorder = prepared(tmp_path)
    buffer = complete(env, recorder); recorder.join(buffer, 0)
    root = recorder.roots[0]; cp = read_root(recorder.directory, root)
    changed = deepcopy(root); changed["trace"][0]["native_digest_after"] = "bad"
    with pytest.raises(ValueError, match="suffix_replay"):
        replay_original(env.native, cp, changed, env.current)
    changed = deepcopy(root); changed["native_terminal_recorded"] = False
    with pytest.raises(ValueError, match="complete_native_suffix"):
        replay_original(env.native, cp, changed, env.current)
    p = next((recorder.directory / "private").glob("*.gz")); p.write_bytes(b"bad")
    with pytest.raises(ValueError, match="integrity"):
        read_root(recorder.directory, root)


def test_sampling_bounds_no_RNG_effect_and_no_git_outputs(tmp_path):
    env, recorder = prepared(tmp_path)
    buffer = complete(env, recorder); recorder.join(buffer, 0)
    env.current = env.native.observation("self")
    state = random.getstate()
    recorder.prepare(env, step=1, rollout=0, t=1)
    assert random.getstate() == state and len(recorder.roots) == 1
    env.split = "validation"
    with pytest.raises(ValueError, match="boundary"):
        recorder.prepare(env, step=64, rollout=0, t=64)
    repo = tmp_path / "repo"; repo.mkdir(); (repo / ".git").write_text("gitdir: elsewhere")
    with pytest.raises(ValueError, match="non_git"):
        outside_git(repo / "records")
    with pytest.raises(ValueError, match="bounded"):
        DecisionSnapshotRecorder(tmp_path / "bad", policy_id="a" * 64, max_snapshots=33)


def test_snapshot_cap_and_prepared_boundary(tmp_path):
    env, recorder = prepared(tmp_path)
    with pytest.raises(ValueError, match="boundary"):
        recorder.prepare(env, step=0, rollout=0, t=0)
    buffer = complete(env, recorder); recorder.join(buffer, 0)
    recorder.maximum = 1; env.current = env.native.observation("self")
    recorder.prepare(env, step=64, rollout=0, t=64)
    assert recorder.prepared is None and len(recorder.roots) == 1


def test_wait_and_retry_boundaries_remain_in_same_PPO_join(tmp_path):
    class TwoBoundaries(Native):
        def step(self, actions, revision):
            r = super().step(actions, revision)
            r.update(terminated=self.n == 2, winner="self" if self.n == 2 else None,
                     rewards={"self": int(self.n == 2), "opponent": -int(self.n == 2)},
                     action_rejected=self.n == 1)
            return r
    env, recorder = prepared(tmp_path)
    env.native = TwoBoundaries()
    for _ in range(2):
        v = {s: env.native.observation(s) for s in ("self", "opponent")}
        recorder.native_before(env.native, v, {"self": 6, "opponent": 7})
        recorder.native_after(env.native, env.native.step({"self": 6, "opponent": 7}, revision=env.native.n))
    recorder.selected(action=6, value=.25, logp=-.5,
                      features=env.encoder.encode(env.current), mask=env.current["action_mask"])
    root = recorder.roots[0]
    root["joined"] = True  # This test isolates native suffix replay from GAE checks above.
    result = replay_original(env.native, read_root(recorder.directory, root), root, env.current)
    assert result["matched_native_steps"] == 2 and root["trace"][0]["result"]["action_rejected"]
    with pytest.raises(TimeoutError, match="stop"):
        replay_original(env.native, read_root(recorder.directory, root), root, env.current, stopping=lambda: True)


def test_storage_boundary_and_different_public_state_fail(tmp_path):
    env, recorder = prepared(tmp_path)
    env.native.n = 1
    with pytest.raises(ValueError, match="changed_between"):
        recorder.native_before(env.native, {s: env.native.observation(s) for s in ("self", "opponent")},
                               {"self": 6, "opponent": 7})
    env.native.n = 0
    recorder.bytes = recorder.byte_cap
    recorder.native_before(env.native, {s: env.native.observation(s) for s in ("self", "opponent")},
                           {"self": 6, "opponent": 7})
    with pytest.raises(ValueError, match="storage_cap"):
        recorder.native_after(env.native, env.native.step({"self": 6, "opponent": 7}, revision=0))


def test_failed_native_unit_consumes_budget_and_no_automatic_retry(tmp_path):
    from scripts.pilot_foundation_decision_snapshots import NativeBudget
    budget = NativeBudget(tmp_path, maximum=1)
    with pytest.raises(TimeoutError):
        budget.run("failed", lambda: (_ for _ in ()).throw(TimeoutError("original failure")))
    assert budget.count == 1
    with pytest.raises(ValueError, match="cap"):
        budget.run("extra", lambda: {})
    assert len((tmp_path / "ledger.jsonl").read_text().splitlines()) == 1


def test_pilot_invalid_contract_fails_before_model_or_native_access():
    from scripts.pilot_foundation_decision_snapshots import validate_plan
    with pytest.raises(ValueError, match="bounded"):
        validate_plan({"transitions": 2049})


def test_public_transport_preserves_insertion_order_without_feature_remapping(tmp_path):
    original = {"observed_pokemon": {"z_first_seen": 1, "a_later_seen": 2}}
    path = tmp_path / "public.json"
    write_new(path, original)
    loaded = json.loads(path.read_text())
    assert list(loaded["observed_pokemon"]) == ["z_first_seen", "a_later_seen"]
    assert digest(loaded) == digest(original)
    with pytest.raises(FileExistsError): write_new(path, original)
