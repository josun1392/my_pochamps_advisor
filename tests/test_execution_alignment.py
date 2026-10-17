"""Execution study identity, probability and clustered inference contracts."""

from copy import deepcopy
import json
from types import SimpleNamespace
import numpy as np
import pytest
from advisor.learned_execution_alignment import (
    content_hash, durable_json, game_slots, masked_sample, sampling_rng, verify_record, cluster_analysis,
)


def test_masked_sampling_probability_boundaries_and_common_random_numbers():
    probabilities = np.zeros(35)
    probabilities[6], probabilities[11] = .25, .75
    mask = probabilities > 0
    assert masked_sample(probabilities, mask, 0.) == 6
    assert masked_sample(probabilities, mask, .25) == 11
    assert masked_sample(probabilities, mask, np.nextafter(1., 0.)) == 11
    first = sampling_rng("train", 123, "p1", "league_anchor", "sample0").random(10000)
    second = sampling_rng("train", 123, "p1", "league_anchor", "sample0").random(10000)
    np.testing.assert_array_equal(first, second)
    assert not np.array_equal(first, sampling_rng("train", 123, "p1", "league_anchor", "sample1").random(10000))
    fraction = np.mean([masked_sample(probabilities, mask, uniform) == 6 for uniform in first])
    assert abs(fraction - .25) < .02


@pytest.mark.parametrize("defect", ["illegal_mass", "negative", "nonfinite", "not_normalized", "empty_mask"])
def test_sampling_invalid_distributions_fail_closed(defect):
    probabilities = np.zeros(35)
    probabilities[6] = 1.
    mask = probabilities > 0
    if defect == "illegal_mass":
        mask[6], mask[7] = False, True
    elif defect == "negative":
        probabilities[6] = -1.
    elif defect == "nonfinite":
        probabilities[6] = np.nan
    elif defect == "not_normalized":
        probabilities[6] = .5
    else:
        mask[:] = False
    with pytest.raises(ValueError, match="invalid_masked"):
        masked_sample(probabilities, mask, .5)


def test_game_record_atomic_identity_hash_and_no_overwrite(tmp_path):
    slot = game_slots([{"scope": "train", "index": 1, "scenario_sha256": "frozen"}])[0]
    record = {"canonical_scenario_sha256": "frozen", "winner": "self"}
    path = tmp_path / "record.json"
    durable_json(path, {"slot": slot, "record": record, "record_sha256": content_hash(record)})
    assert verify_record(path, slot) == record
    with pytest.raises(FileExistsError):
        durable_json(path, {})
    corrupted = json.loads(path.read_text())
    corrupted["record"]["winner"] = "opponent"
    path.write_text(json.dumps(corrupted))
    with pytest.raises(ValueError, match="identity_or_hash"):
        verify_record(path, slot)


def synthetic_records():
    cases = [{"scope": scope, "index": index, "scenario_sha256": str(index)}
             for scope in ("train", "validation") for index in range(128)]
    rows = []
    for slot in game_slots(cases):
        case = slot["case"]
        win = case % 2 == 0
        if slot["policy"] == "candidate" and slot["mode"] != "argmax" and case % 4 == 1:
            win = True
        rows.append({"study_slot": slot, "winner": "self" if win else "opponent", "truncated": False})
    return rows


def test_case_cluster_retains_seat_rival_stream_dependence_and_weighting():
    records = synthetic_records()
    result = cluster_analysis(records, bootstrap_seed=17, resamples=1000)
    primary = result["scopes"]["validation"]["strata"]["all"]
    assert primary["argmax"]["estimate"] == 0
    assert primary["sampling"]["estimate"] == .25
    assert primary["interaction"]["estimate"] == .25
    draws = np.random.default_rng(17).integers(0, 128, (1000, 128))
    expected = (np.arange(128) % 4 == 1).astype(float)
    np.testing.assert_array_equal(primary["interaction"]["cluster_bootstrap_95"],
                                  np.quantile(expected[draws].mean(axis=1), [.025, .975]))
    assert result["alignment_gate_pass"]
    assert result["training_seed_count"] == 1


def test_incomplete_duplicate_and_censored_studies_cannot_pass():
    records = synthetic_records()
    with pytest.raises(ValueError, match="incomplete"):
        cluster_analysis(records[:-1])
    duplicate = deepcopy(records)
    duplicate[1] = duplicate[0]
    with pytest.raises(ValueError, match="duplicate"):
        cluster_analysis(duplicate)
    records[0]["truncated"] = True
    result = cluster_analysis(records, resamples=100)
    assert not result["gates"]["no_censored_native_outcomes"]
    assert not result["alignment_gate_pass"]


def test_frozen_provider_has_evaluator_identity_and_cannot_retarget():
    from scripts.evaluate_combat_execution_alignment import FrozenCaseProvider

    case = {"scope": "train", "index": 99, "scenario_sha256": "frozen", "scenario": {"teams": {}}}
    provider = FrozenCaseProvider(case)
    assert provider.identity["scenario_sha256"] == "frozen"
    observed = provider("validation", 99)
    observed["teams"]["changed"] = True
    assert not case["scenario"]["teams"]
    with pytest.raises(ValueError, match="access_mismatch"):
        provider("test", 99)
    with pytest.raises(ValueError, match="access_mismatch"):
        provider("validation", 100)


def test_packaging_fault_after_native_callback_preserves_game_receipt(tmp_path, monkeypatch):
    import scripts.evaluate_combat_execution_alignment as runner

    case = {"scope": "train", "index": 1, "scenario_sha256": "frozen", "scenario": {}}
    plan = {"checkout": "unused", "catalog": "unused", "models": {
        name: {"sha256": name} for name in ("candidate", "control", "league_s0", "league_anchor")}}
    policy = SimpleNamespace(infer=lambda view: {}, model_id="candidate")
    monkeypatch.setattr(runner, "WORKER", {"plan": plan, "output": tmp_path, "deadline": float("inf"),
        "policies": {"candidate": policy, "league_s0": object()}, "network": {}})

    def packaging_error(*args, **kwargs):
        assert kwargs["case_provider"].identity["scenario_sha256"] == "frozen"
        kwargs["progress"]([{"canonical_scenario_sha256": "frozen", "winner": "self", "truncated": False}])
        raise RuntimeError("injected_after_native_before_summary")

    monkeypatch.setattr(runner.evaluator, "evaluate", packaging_error)
    with pytest.raises(RuntimeError, match="injected_after_native"):
        runner.chunk_worker({"id": "train_000", "cases": [case]})
    slot = game_slots([case])[0]
    record = verify_record(tmp_path / "chunks/train_000/game_000.json", slot)
    assert record["winner"] == "self"
    assert (tmp_path / "STOP").exists()
    assert policy.infer({}) == {}


def test_uncertain_started_game_is_not_replayed(tmp_path, monkeypatch):
    import scripts.evaluate_combat_execution_alignment as runner
    from advisor.learned_training_operations import TrainingJournal

    case = {"scope": "train", "index": 1, "scenario_sha256": "frozen"}
    directory = tmp_path / "chunks/train_000"
    directory.mkdir(parents=True)
    journal = TrainingJournal(directory, {})
    journal.append("game_started", slot_index=0)
    monkeypatch.setattr(runner, "WORKER", {"plan": {}, "output": tmp_path, "policies": {}})
    with pytest.raises(ValueError, match="uncertain_game_consumption"):
        runner.chunk_worker({"id": "train_000", "cases": [case]})
    assert not list(directory.glob("game_*.json"))


def test_control_and_identical_SHA_rival_are_separate_policy_instances(tmp_path, monkeypatch):
    import scripts.evaluate_combat_execution_alignment as runner

    plan = {"catalog": "unused", "models": {name: {"path": "same.zip", "sha256": "same"}
        for name in ("candidate", "control", "league_s0", "league_anchor")}}
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    monkeypatch.setattr(runner, "verify_plan", lambda value: None)
    monkeypatch.setattr(runner, "enforce_local_network_only", lambda: {})
    monkeypatch.setattr(runner, "LearnedPolicy", lambda *args, **kwargs: SimpleNamespace(model_id="same"))
    monkeypatch.setattr(runner, "WORKER", {})
    runner.initialize(path, tmp_path, 1e20)
    assert runner.WORKER["policies"]["control"] is not runner.WORKER["policies"]["league_s0"]
