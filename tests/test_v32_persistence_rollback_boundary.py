from copy import deepcopy
from pathlib import Path

import pytest
import llm.advisor_observation_replay_persistence as persistence_module
from llm.advisor_battle_state_store import BattleStateStore
from llm.advisor_observation_replay_coordinator import ObservationReplayCoordinator
from llm.advisor_observation_replay_persistence import ObservationReplayPersistence
from llm.advisor_reducer_state_model import STATE_MODEL_VERSION


def state(hp=80, sequence=None, session="s"):
    return {"state_version": STATE_MODEL_VERSION, "session_id": session, "self_side": {"active_slot_index": 0, "pokemon": {0: {"pokemon_id": "p", "current_hp": hp, "max_hp": 100, "fainted": False, "condition": None, "known_item": None}}, "side_conditions": []}, "opponent_side": {"active_slot_index": 0, "pokemon": {}}, "field": {"weather": None, "terrain": None}, "last_applied_observation_sequence": sequence, "q12": {"x": 1}}


def observation(observation_id="o1", turn=1):
    return {"observation_id": observation_id, "observation_sequence": turn, "event_kind": "used_move_observed", "session_id": "s", "turn_number": turn, "payload": {}}


def snapshot(events):
    return {"status": "ready", "session_id": "s", "ordered_observations": events}


def setup(hp=80, sequence=None, ledger=None):
    store = BattleStateStore(state(hp, sequence)); coordinator = ObservationReplayCoordinator(store)
    coordinator.replace_applied_ledger("s", ledger or {})
    return store, coordinator, ObservationReplayPersistence()


def read_pair(store, coordinator):
    read = store.read_snapshot(); return deepcopy(read["state"]), read["state_fingerprint"], coordinator.export_applied_ledger("s")


def test_normal_cas_rejects_lower_sequence_without_mutation():
    store, coordinator, _ = setup(60, 4); before = read_pair(store, coordinator)
    result = store.compare_and_replace(state(90, 3), expected_session_id="s", expected_base_fingerprint=before[1])
    assert result["status"] == "sequence_regression"
    assert read_pair(store, coordinator) == before


def test_rollback_only_restores_exact_snapshot_but_normal_cas_remains_monotonic():
    store, coordinator, _ = setup(80, 1); old = store.capture_rollback_snapshot("s"); base = store.read_snapshot()
    target = state(40, 2); applied = store.compare_and_replace(target, expected_session_id="s", expected_base_fingerprint=base["state_fingerprint"])
    result = store.compare_and_restore_snapshot(expected_current_fingerprint=applied["current_fingerprint"], rollback_snapshot=old)
    assert result["status"] == "rollback_restored"
    assert store.read_snapshot()["state"] == old["state"]
    assert store.read_snapshot()["state_fingerprint"] == old["state_fingerprint"]


def test_rollback_conflict_preserves_concurrent_writer_without_retry():
    store, coordinator, _ = setup(80, 1); old = store.capture_rollback_snapshot("s"); base = store.read_snapshot()
    target = store.compare_and_replace(state(60, 2), expected_session_id="s", expected_base_fingerprint=base["state_fingerprint"])
    store.compare_and_replace(state(30, 3), expected_session_id="s", expected_base_fingerprint=target["current_fingerprint"])
    before = read_pair(store, coordinator)
    assert store.compare_and_restore_snapshot(expected_current_fingerprint=target["current_fingerprint"], rollback_snapshot=old)["status"] == "rollback_cas_conflict"
    assert read_pair(store, coordinator) == before


def test_cross_session_and_tampered_rollback_snapshots_are_rejected_without_mutation():
    store, coordinator, _ = setup(80, 2); before = read_pair(store, coordinator)
    other = BattleStateStore(state(20, 1, "other")).capture_rollback_snapshot("other")
    assert store.compare_and_restore_snapshot(expected_current_fingerprint=before[1], rollback_snapshot=other)["status"] == "rollback_session_mismatch"
    valid = store.capture_rollback_snapshot("s")
    for tampered in ({**valid, "state": state(1, 1)}, {**valid, "state_fingerprint": "bad"}, {key: value for key, value in valid.items() if key != "state"}, {**valid, "state": []}):
        assert store.compare_and_restore_snapshot(expected_current_fingerprint=before[1], rollback_snapshot=tampered)["status"] == "invalid_rollback_snapshot"
        assert read_pair(store, coordinator) == before


def test_restore_ledger_failure_rolls_store_back_with_no_ledger_leakage(monkeypatch):
    store, coordinator, service = setup(80, 1, {"old": observation("old")}); before = read_pair(store, coordinator)
    target_store, target_coordinator, _ = setup(40, 2, {"new": observation("new", 2)})
    candidate = service.validate(service.export_envelope(target_store, target_coordinator, "s")["envelope"])
    monkeypatch.setattr(coordinator, "replace_applied_ledger", lambda *_: False)
    result = service.restore(store, coordinator, candidate, before[1])
    assert result == {"status": "restore_rolled_back"}
    assert read_pair(store, coordinator) == before
    assert coordinator.preview(snapshot([observation("new", 2)]))["status"] != "already_applied"


def test_ledger_failure_with_concurrent_writer_returns_sanitized_critical_status(monkeypatch):
    store, coordinator, service = setup(80, 1, {"old": observation("old")}); target_store, target_coordinator, _ = setup(40, 2, {"new": observation("new", 2)})
    candidate = service.validate(service.export_envelope(target_store, target_coordinator, "s")["envelope"]); base = store.read_snapshot()
    def fail_after_concurrent_writer(*_):
        current = store.read_snapshot(); store.compare_and_replace(state(10, 3), expected_session_id="s", expected_base_fingerprint=current["state_fingerprint"]); return False
    monkeypatch.setattr(coordinator, "replace_applied_ledger", fail_after_concurrent_writer)
    result = service.restore(store, coordinator, candidate, base["state_fingerprint"])
    assert result == {"status": "critical_restore_inconsistency"}
    assert store.read_snapshot()["state"] == state(10, 3)
    assert coordinator.export_applied_ledger("s") == {"old": observation("old")}
    assert "Traceback" not in repr(result) and "\\" not in repr(result)


def test_full_map_replacement_failure_has_no_partial_target_entries(monkeypatch):
    store, coordinator, service = setup(80, 1, {"old": observation("old")}); before = read_pair(store, coordinator)
    target_store, target_coordinator, _ = setup(40, 2, {"a": observation("a", 2), "b": observation("b", 3)})
    candidate = service.validate(service.export_envelope(target_store, target_coordinator, "s")["envelope"])
    old_internal_map = coordinator._applied["s"]
    calls = []
    def fail_before_assignment(*args): calls.append(args); return False
    monkeypatch.setattr(coordinator, "replace_applied_ledger", fail_before_assignment)
    assert service.restore(store, coordinator, candidate, before[1]) == {"status": "restore_rolled_back"}
    assert read_pair(store, coordinator) == before
    assert coordinator._applied["s"] is old_internal_map
    assert set(coordinator._applied["s"]) == {"old"}
    assert len(calls) == 1


def test_successful_restore_duplicate_apply_is_idempotent_and_conflict_is_non_mutating():
    target_store, target_coordinator, service = setup(40, 2, {"o1": observation()})
    envelope = service.export_envelope(target_store, target_coordinator, "s")["envelope"]
    store, coordinator, _ = setup(80, 1); base = store.read_snapshot(); candidate = service.validate(envelope)
    result = service.restore(store, coordinator, candidate, base["state_fingerprint"])
    assert result["status"] == "restored" and store.read_snapshot()["session_id"] == "s"
    result["state_snapshot"]["self_side"]["pokemon"][0]["current_hp"] = 1
    assert store.read_snapshot()["state"]["self_side"]["pokemon"][0]["current_hp"] == 40
    before = read_pair(store, coordinator)
    assert coordinator.apply_confirmed_observations(snapshot([observation()]))["status"] == "already_applied"
    assert read_pair(store, coordinator) == before
    conflict = coordinator.apply_confirmed_observations(snapshot([observation("o1", 9)]))
    assert conflict["status"] == "transition_invalid"
    assert conflict["conflicts"] == [{"observation_id": "o1", "reason": "conflicting_applied_observation"}]
    assert read_pair(store, coordinator) == before


def test_same_id_altered_canonical_content_conflicts_without_mutation():
    store, coordinator, _ = setup(80, 1, {"o1": observation()}); before = read_pair(store, coordinator)
    result = coordinator.preview(snapshot([observation("o1", 9)]))
    assert result["status"] == "transition_invalid" and result["conflicts"][0]["observation_id"] == "o1"
    assert read_pair(store, coordinator) == before


def test_load_only_non_mutation_and_detached_aliases(tmp_path):
    store, coordinator, service = setup(80, 1, {"o1": observation()}); first = service.export_envelope(store, coordinator, "s")["envelope"]
    second = service.export_envelope(store, coordinator, "s")["envelope"]
    assert first == second
    path = tmp_path / "state.json"
    assert service.save(path, first)["status"] == "saved"
    before = read_pair(store, coordinator)
    loaded = service.load(path)
    validated = service.validate(second)
    assert loaded["status"] == validated["status"] == "load_ready"
    assert loaded["envelope"]["store"]["state"] == before[0]
    assert loaded["envelope"]["store"]["state"] is not store._state
    assert loaded["ledger"] == before[2]
    assert loaded["ledger"]["o1"] is not coordinator._applied["s"]["o1"]
    loaded["envelope"]["store"]["state"]["self_side"]["pokemon"][0]["current_hp"] = 1
    loaded["ledger"]["o1"]["payload"]["changed"] = True
    assert read_pair(store, coordinator) == before


def test_invalid_json_load_is_non_mutating(tmp_path):
    store, coordinator, service = setup(80, 1, {"o1": observation()}); before = read_pair(store, coordinator)
    path = tmp_path / "state.json"; path.write_text("not json", encoding="utf-8")
    assert service.load(path)["status"] == "invalid_json"
    assert read_pair(store, coordinator) == before


def corrupt_non_object(envelope): return []
def corrupt_missing_top_level(envelope): envelope.pop("metadata"); return envelope
def corrupt_unexpected_top_level(envelope): envelope["extra"] = 1; return envelope
def corrupt_unsupported_schema(envelope): envelope["schema_version"] = "future"; return envelope
def corrupt_wrong_top_level_type(envelope): envelope["session_id"] = 1; return envelope
def corrupt_empty_session(envelope): envelope["session_id"] = ""; return envelope
def corrupt_store_shape(envelope):
    envelope["store"]["state"] = {"session_id": "s"}
    envelope["store"]["fingerprint"] = persistence_module.state_fingerprint(envelope["store"]["state"])
    return envelope
def corrupt_store_fingerprint(envelope): envelope["store"]["fingerprint"] = "bad"; return envelope
def corrupt_ledger_container(envelope): envelope["applied_observations"] = {}; return envelope
def corrupt_ledger_entry_shape(envelope): envelope["applied_observations"][0].pop("canonical_fingerprint"); return envelope
def corrupt_observation_id_mismatch(envelope): envelope["applied_observations"][0]["observation_id"] = "other"; return envelope
def corrupt_canonical_shape(envelope):
    envelope["applied_observations"][0]["canonical_observation"].pop("observation_sequence")
    envelope["applied_observations"][0]["canonical_fingerprint"] = persistence_module.canonical_fingerprint(envelope["applied_observations"][0]["canonical_observation"])
    return envelope
def corrupt_canonical_fingerprint(envelope): envelope["applied_observations"][0]["canonical_fingerprint"] = "bad"; return envelope
def corrupt_duplicate_same(envelope): envelope["applied_observations"].append(deepcopy(envelope["applied_observations"][0])); return envelope
def corrupt_duplicate_conflicting(envelope):
    changed = deepcopy(envelope["applied_observations"][0]); changed["canonical_observation"]["turn_number"] = 2; changed["canonical_fingerprint"] = persistence_module.canonical_fingerprint(changed["canonical_observation"]); envelope["applied_observations"].append(changed); return envelope


@pytest.mark.parametrize(("case_id", "corrupt", "status"), [
    ("non_object_root", corrupt_non_object, "invalid_envelope"),
    ("missing_top_level", corrupt_missing_top_level, "invalid_envelope"),
    ("unexpected_top_level", corrupt_unexpected_top_level, "invalid_envelope"),
    ("unsupported_schema", corrupt_unsupported_schema, "unsupported_schema"),
    ("wrong_top_level_type", corrupt_wrong_top_level_type, "invalid_envelope"),
    ("empty_session", corrupt_empty_session, "invalid_envelope"),
    ("store_exact_shape", corrupt_store_shape, "invalid_envelope"),
    ("store_fingerprint", corrupt_store_fingerprint, "fingerprint_mismatch"),
    ("ledger_wrong_container", corrupt_ledger_container, "invalid_envelope"),
    ("ledger_entry_shape", corrupt_ledger_entry_shape, "invalid_envelope"),
    ("observation_id_mismatch", corrupt_observation_id_mismatch, "invalid_envelope"),
    ("canonical_observation_shape", corrupt_canonical_shape, "invalid_envelope"),
    ("canonical_fingerprint", corrupt_canonical_fingerprint, "ledger_fingerprint_mismatch"),
    ("duplicate_same_id_same_content", corrupt_duplicate_same, "ledger_conflict"),
    ("duplicate_same_id_conflicting_content", corrupt_duplicate_conflicting, "ledger_conflict"),
])
def test_corruption_matrix_rejects_each_case_without_runtime_mutation(case_id, corrupt, status):
    store, coordinator, service = setup(80, 1, {"o1": observation()}); envelope = service.export_envelope(store, coordinator, "s")["envelope"]; before = read_pair(store, coordinator)
    assert service.validate(corrupt(deepcopy(envelope)))["status"] == status
    assert read_pair(store, coordinator) == before


def test_save_failures_preserve_existing_target_and_runtime(tmp_path, monkeypatch):
    store, coordinator, service = setup(80, 1, {"o1": observation()}); envelope = service.export_envelope(store, coordinator, "s")["envelope"]; before = read_pair(store, coordinator)
    target = tmp_path / "state.json"; target.write_bytes(b"existing")
    monkeypatch.setattr(Path, "write_text", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("fail")))
    assert service.save(target, envelope)["status"] == "io_error" and target.read_bytes() == b"existing" and read_pair(store, coordinator) == before


def test_serialization_failure_preserves_existing_target_and_runtime(tmp_path, monkeypatch):
    store, coordinator, service = setup(80, 1, {"o1": observation()}); envelope = service.export_envelope(store, coordinator, "s")["envelope"]; before = read_pair(store, coordinator)
    target = tmp_path / "state.json"; target.write_bytes(b"existing")
    validated = service.validate(envelope)
    with monkeypatch.context() as scoped:
        scoped.setattr(service, "validate", lambda _: validated)
        scoped.setattr(persistence_module.json, "dumps", lambda *_args, **_kwargs: (_ for _ in ()).throw(TypeError("fail")))
        result = service.save(target, envelope)
    assert result["status"] == "io_error" and target.read_bytes() == b"existing" and read_pair(store, coordinator) == before


def test_replace_failure_preserves_existing_target_and_cross_session_restore_is_blocked(tmp_path, monkeypatch):
    store, coordinator, service = setup(80, 1, {"o1": observation()}); envelope = service.export_envelope(store, coordinator, "s")["envelope"]; before = read_pair(store, coordinator)
    target = tmp_path / "state.json"; target.write_bytes(b"existing")
    monkeypatch.setattr(persistence_module.os, "replace", lambda *_: (_ for _ in ()).throw(OSError("fail")))
    assert service.save(target, envelope)["status"] == "io_error" and target.read_bytes() == b"existing" and read_pair(store, coordinator) == before
    assert not (tmp_path / "state.json.tmp").exists()
    other_store = BattleStateStore(state(1, 1, "other")); other_coordinator = ObservationReplayCoordinator(other_store); other_before = other_store.read_snapshot()
    candidate = service.validate(envelope)
    assert service.restore(other_store, other_coordinator, candidate, other_before["state_fingerprint"])["status"] == "session_mismatch"
    assert other_store.read_snapshot() == other_before
