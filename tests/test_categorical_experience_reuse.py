"""Executed-only public categorical data and matched upstream offline updates."""
import json
import os
from pathlib import Path
import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")
from advisor.learned_action_encoder import make_encoder
from advisor.learned_offline import load_dataset, fit_offline, file_hash, PUBLIC_CATEGORICAL_SCHEMA
from advisor.learned_objective import objective_contract
from advisor.learning_resources import atomic_json
from advisor.learned_gym import ShowdownLearningEnv
from scripts.collect_showdown_public_trajectories import collect, terminal_label_eligible, close_owned_vector
from scripts.train_showdown_autonomous import optimizer_steps
from tests.test_public_categorical_observation import model

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "models/showdown_mc_domain_v1/catalog.json"
VERSION = "showdown-public-categorical-observation-v3"


class Budget:
    def stopping(self):
        return False


def test_truncation_and_rejected_episodes_never_supply_labels():
    assert terminal_label_eligible({"terminated": True, "truncated": False}, False)
    assert not terminal_label_eligible({"terminated": False, "truncated": True}, False)
    assert not terminal_label_eligible({"terminated": True, "truncated": False}, True)
    assert not terminal_label_eligible({"terminated": False, "truncated": False}, False)


def test_failed_owned_vector_skips_blocking_close():
    calls = []
    class Process:
        def is_alive(self): return True
        def terminate(self): calls.append("terminate")
        def join(self, timeout): calls.append(("join", timeout))
    class Vector:
        processes = [Process()]
        def close(self): raise AssertionError("broken IPC close must not be retried")
    close_owned_vector(Vector(), failed=True)
    assert calls == ["terminate", ("join", 1)]


@pytest.fixture(scope="module")
def checkout():
    p = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not p:
        pytest.skip("pinned native checkout required")
    return p


def test_collection_objective_is_opt_in_and_fail_closed(tmp_path):
    base = {"decisions": 32, "envs": 1, "memory_mib": 3072, "max_runtime_seconds": 60}
    for changes in ({"gamma": 1}, {"encoder_version": VERSION, "gamma": .99},
                    {"encoder_version": "unverified", "gamma": 1}):
        with pytest.raises(ValueError, match="collection_objective"):
            collect({**base, **changes}, tmp_path / "no_output")
    assert not (tmp_path / "no_output").exists()


def test_native_collection_and_matched_offline_updates(checkout, tmp_path):
    cfg = {"checkout": checkout, "catalog": str(CATALOG), "decisions": 64,
           "envs": 2, "memory_mib": 4096, "cpu_percent": 25, "max_runtime_seconds": 60,
           "encoder_version": VERSION, "gamma": 1.0, "seed": 1972,
           "curriculum_version": "showdown-learning-curriculum-v8",
           "behaviors": ["random", "champions_heuristic"], "opponents": ["max_power"]}
    path = tmp_path / "dataset"
    manifest = collect(cfg, path)
    encoder = make_encoder(CATALOG, VERSION)
    arrays, meta, identity = load_dataset(path, encoder, gamma=1)
    assert meta["schema_version"] == PUBLIC_CATEGORICAL_SCHEMA
    assert meta["training_objective"] == objective_contract(1, .95)
    assert meta["completed_episodes"] > 0 and meta["rows"] >= 64
    assert set(arrays["returns"]) <= {-1., 0., 1.}
    records = [json.loads(line) for line in (path / "public_diagnostics.jsonl").read_text().splitlines()]
    assert len(records) == len(arrays["actions"])
    assert all(r["row"] == i and r["action"] == int(arrays["actions"][i])
               and r["native_rejections"] == 0 and not r["terminal_encoding_unavailable"]
               for i, r in enumerate(records))
    assert all(not {"teams", "native_state", "checkpoint", "seed", "opponent_request"} & r.keys() for r in records)
    bc, awr = model(encoder), model(encoder)
    awr.policy.load_state_dict(bc.policy.state_dict())
    bc.gamma = awr.gamma = 1
    initial = {k: v.clone() for k, v in bc.policy.state_dict().items()}
    results = []
    for kind, m in (("bc", bc), ("awr", awr)):
        result = fit_offline(m, encoder, {"dataset": str(path), "dataset_id": identity,
            "epochs": 2, "mode": kind, "learning_rate": 5e-5}, 77, Budget())
        assert result["completed_epochs"] == 2 and result["parameter_l1_change"] > 0
        assert optimizer_steps(m) == result["optimizer_updates_this_launch"]
        results.append(result)
    assert results[0]["optimizer_updates_this_launch"] == results[1]["optimizer_updates_this_launch"]
    assert any(not torch.equal(v, bc.policy.state_dict()[k]) for k, v in initial.items())
    with pytest.raises(ValueError, match="contract"):
        load_dataset(path, encoder, gamma=.99)
    metadata = json.loads((path / "manifest.json").read_text())
    metadata["terminal_label_scope"] = "truncation_as_draw"
    atomic_json(path / "manifest.json", metadata)
    with pytest.raises(ValueError, match="contract"):
        load_dataset(path, encoder, gamma=1)


def test_collection_cache_survives_auto_reset_without_gym_info_leak(checkout):
    env = ShowdownLearningEnv(checkout, make_encoder(CATALOG, VERSION),
        curriculum_version="showdown-learning-curriculum-v8", opponents=["max_power"],
        collect_tactical_metrics=True, collect_public_trajectories=True, max_decisions=1)
    try:
        action = int(np.flatnonzero(env.action_masks())[-1])
        _, _, _, _, info = env.step(action)
        evidence = env.collection_step_diagnostics()
        assert evidence["action"] == action
        assert "collection_step_diagnostics" not in info
        assert all(not k.startswith("opponent:") for k in evidence["counts"])
        env.reset()
        assert env.collection_step_diagnostics() == evidence
    finally:
        env.close()


def test_unsupported_true_terminal_transport_never_is_a_data_label(checkout):
    env = ShowdownLearningEnv(checkout, make_encoder(CATALOG, VERSION),
        curriculum_version="showdown-learning-curriculum-v8", opponents=["max_power"],
        collect_tactical_metrics=True, collect_public_trajectories=True)
    encode = env._encode_public
    def reject_terminal(view):
        if view["terminated"]:
            raise ValueError("ambiguous_own_public_identity")
        return encode(view)
    env._encode_public = reject_terminal
    try:
        for _ in range(96):
            before = env.encoder.encode(env.current)
            action = env.behavior_action("max_power")
            x, reward, terminal, truncated, info = env.step(action)
            if terminal:
                np.testing.assert_array_equal(x, before)
                assert info["collector_terminal_encoding_unavailable"]
                assert env.collection_step_diagnostics()["terminal_encoding_unavailable"]
                assert not terminal_label_eligible(info["native_outcome"], True)
                assert not truncated and reward in (-1, 0, 1)
                break
        else:
            pytest.fail("actual native terminal episode did not complete")
    finally:
        env.close()
