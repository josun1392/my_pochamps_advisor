from copy import deepcopy
from pathlib import Path

import pytest

import llm.advisor_observation_replay_persistence as persistence_module
import llm.advisor_observation_replay_persistence_commands as commands_module
from llm.advisor_observation_replay_persistence_commands import ObservationReplayPersistenceCommands
from llm.advisor_observation_replay_runtime import ObservationReplayRuntime
from llm.advisor_reducer_state_model import STATE_MODEL_VERSION


def state(hp=80, sequence=None, session="s"):
    return {"state_version": STATE_MODEL_VERSION, "session_id": session, "self_side": {"active_slot_index": 0, "pokemon": {0: {"pokemon_id": "pikachu", "current_hp": hp, "max_hp": 100, "fainted": False, "condition": None, "known_item": "berry"}}, "side_conditions": []}, "opponent_side": {"active_slot_index": 0, "pokemon": {}}, "field": {"weather": None, "terrain": None}, "last_applied_observation_sequence": sequence, "q12": {"damage": 99}}


def event(observation_id="hp", sequence=1, hp_after=40):
    return {"event_kind": "exact_hp_transition_observed", "reducer_eligibility": "candidate", "observation_id": observation_id, "observation_sequence": sequence, "session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "pikachu", "hp_before": 80, "hp_after": hp_after, "payload": {"hp_before": 80, "hp_after": hp_after}}


def snapshot(*events, session="s"): return {"status": "ready", "session_id": session, "ordered_observations": list(events)}


def setup(initial=None):
    created = ObservationReplayRuntime.create(state() if initial is None else initial); assert created["status"] == "ready"
    commands = ObservationReplayPersistenceCommands.create(created["runtime"]); assert commands["status"] == "ready"
    return created["runtime"], commands["commands"]


def values(runtime):
    read = runtime.read_state(); return deepcopy(read["state"]), read["state_fingerprint"], read["state"]["last_applied_observation_sequence"], runtime.read_applied_ledger()


def test_command_owner_binds_to_one_runtime_without_exposing_raw_components():
    runtime, commands = setup(); public = {name for name in dir(ObservationReplayPersistenceCommands) if not name.startswith("_")}
    assert commands.session_id == runtime.session_id == "s"
    assert {"create", "session_id", "save", "load", "restore"} <= public
    assert not ({"store", "coordinator", "persistence", "rebind", "undo", "reset", "rollover", "capture_rollback_snapshot"} & public)


def test_explicit_save_writes_deterministic_snapshot_without_runtime_mutation(tmp_path):
    runtime, commands = setup(); before = values(runtime); target = tmp_path / "state.json"
    assert commands.save(target) == {"status": "save_complete"}
    loaded = commands.load(target)
    assert loaded["status"] == "load_ready" and loaded["envelope"]["store"]["state"] == before[0]
    assert loaded["envelope"]["store"]["fingerprint"] == before[1] and loaded["ledger"] == before[3]
    assert values(runtime) == before


def test_save_uses_command_start_snapshot_when_runtime_changes_concurrently(tmp_path, monkeypatch):
    runtime, commands = setup(); target = tmp_path / "state.json"; original = runtime._persistence.save
    def save_after_apply(path, envelope):
        assert runtime.apply(snapshot(event()))["status"] == "applied"
        return original(path, envelope)
    monkeypatch.setattr(runtime._persistence, "save", save_after_apply)
    assert commands.save(target)["status"] == "save_complete"
    assert commands.load(target)["envelope"]["store"]["state"]["last_applied_observation_sequence"] is None
    assert runtime.read_state()["state"]["last_applied_observation_sequence"] == 1


def test_save_failure_preserves_existing_target_and_runtime(tmp_path, monkeypatch):
    runtime, commands = setup(); before = values(runtime); target = tmp_path / "state.json"; target.write_bytes(b"old")
    monkeypatch.setattr(Path, "write_text", lambda *_a, **_k: (_ for _ in ()).throw(OSError("fail")))
    assert commands.save(target) == {"status": "io_error"} and target.read_bytes() == b"old" and values(runtime) == before


def test_save_replace_failure_cleans_temp_and_preserves_target(tmp_path, monkeypatch):
    runtime, commands = setup(); before = values(runtime); target = tmp_path / "state.json"; target.write_bytes(b"old")
    monkeypatch.setattr(persistence_module.os, "replace", lambda *_: (_ for _ in ()).throw(OSError("fail")))
    assert commands.save(target) == {"status": "io_error"} and target.read_bytes() == b"old" and not (tmp_path / "state.json.tmp").exists() and values(runtime) == before


@pytest.mark.parametrize("path", [None, "", object()], ids=["none", "empty", "object"])
def test_save_rejects_invalid_path_without_runtime_mutation(path, tmp_path):
    runtime, commands = setup(); before = values(runtime)
    assert commands.save(path) == {"status": "invalid_path"} and values(runtime) == before
    assert commands.save(tmp_path) == {"status": "invalid_path"}
    assert commands.save(tmp_path / "missing" / "state.json") == {"status": "invalid_path"}


def test_save_is_never_invoked_implicitly_by_runtime_creation_preview_or_apply(tmp_path):
    runtime, commands = setup(); target = tmp_path / "never.json"
    runtime.preview(snapshot(event())); runtime.apply(snapshot(event()))
    assert not target.exists() and commands.session_id == "s"


def test_load_returns_detached_validated_envelope_without_runtime_mutation(tmp_path):
    source, source_commands = setup(); target = tmp_path / "state.json"; assert source_commands.save(target)["status"] == "save_complete"
    runtime, commands = setup(state(60, 1)); before = values(runtime); loaded = commands.load(target)
    assert loaded["status"] == "load_ready" and values(runtime) == before
    loaded["envelope"]["store"]["state"]["self_side"]["pokemon"][0]["current_hp"] = 1
    assert values(runtime) == before


@pytest.mark.parametrize("mutate,status", [
    (lambda e: "not json", "invalid_json"),
    (lambda e: [], "invalid_envelope"),
    (lambda e: {key: value for key, value in e.items() if key != "metadata"}, "invalid_envelope"),
    (lambda e: {**e, "extra": 1}, "invalid_envelope"),
    (lambda e: {**e, "schema_version": "future"}, "unsupported_schema"),
    (lambda e: {**e, "session_id": 1}, "invalid_envelope"),
    (lambda e: {**e, "store": {**e["store"], "fingerprint": "bad"}}, "fingerprint_mismatch"),
    (lambda e: {**e, "applied_observations": e["applied_observations"] + [deepcopy(e["applied_observations"][0])]}, "ledger_conflict"),
], ids=["json", "root", "missing", "extra", "schema", "type", "fingerprint", "ledger_conflict"])
def test_load_corruption_matrix_is_non_mutating(tmp_path, mutate, status):
    source, source_commands = setup(); assert source.apply(snapshot(event()))["status"] == "applied"; envelope = source.export_envelope()["envelope"]; value = mutate(deepcopy(envelope)); path = tmp_path / "state.json"
    path.write_text(value if isinstance(value, str) else __import__("json").dumps(value), encoding="utf-8")
    runtime, commands = setup(); before = values(runtime)
    assert commands.load(path)["status"] == status and values(runtime) == before


def test_load_missing_or_unreadable_file_returns_sanitized_status(tmp_path, monkeypatch):
    runtime, commands = setup(); before = values(runtime)
    assert commands.load(tmp_path / "missing.json") == {"status": "not_found"}
    monkeypatch.setattr(Path, "read_text", lambda *_a, **_k: (_ for _ in ()).throw(OSError("fail")))
    assert commands.load(tmp_path / "unreadable.json") == {"status": "io_error"} and values(runtime) == before


def test_load_foreign_session_envelope_is_detached_and_does_not_restore(tmp_path):
    foreign, foreign_commands = setup(state(session="other")); target = tmp_path / "foreign.json"; assert foreign_commands.save(target)["status"] == "save_complete"
    runtime, commands = setup(); before = values(runtime); loaded = commands.load(target)
    assert loaded["status"] == "load_ready" and loaded["envelope"]["session_id"] == "other" and values(runtime) == before
    assert commands.restore(loaded, before[1]) == {"status": "session_mismatch"} and values(runtime) == before


def test_mutating_loaded_envelope_does_not_alias_runtime_or_file_state(tmp_path):
    source, source_commands = setup(); target = tmp_path / "state.json"; assert source_commands.save(target)["status"] == "save_complete"; bytes_before = target.read_bytes()
    runtime, commands = setup(); before = values(runtime); loaded = commands.load(target); loaded["ledger"]["x"] = event("x", 2)
    assert target.read_bytes() == bytes_before and values(runtime) == before


def target_candidate():
    target, _ = setup(state(40, 2)); assert target._coordinator.replace_applied_ledger("s", {"hp": event()}); return target.export_envelope()["envelope"]


def test_explicit_restore_applies_same_session_recovery_unit():
    runtime, commands = setup(state(80, 1)); before = runtime.read_state(); candidate = target_candidate()
    assert commands.restore(candidate, before["state_fingerprint"]) == {"status": "restore_complete"}
    assert runtime.read_state()["state"] == candidate["store"]["state"] and runtime.read_applied_ledger() == {"hp": event()}


def test_restore_rejects_stale_expected_runtime_fingerprint(monkeypatch):
    runtime, commands = setup(state(80, 1)); before = values(runtime); called = []
    monkeypatch.setattr(runtime._persistence, "restore", lambda *_: called.append(True))
    assert commands.restore(target_candidate(), "stale") == {"status": "stale_runtime"} and not called and values(runtime) == before


def test_restore_ledger_failure_rolls_store_back(monkeypatch):
    runtime, commands = setup(state(80, 1)); runtime._coordinator.replace_applied_ledger("s", {"old": event("old")}); before = values(runtime)
    monkeypatch.setattr(runtime._coordinator, "replace_applied_ledger", lambda *_: False)
    assert commands.restore(target_candidate(), before[1]) == {"status": "restore_rolled_back"} and values(runtime) == before


def test_restore_concurrent_writer_conflict_preserves_writer(monkeypatch):
    runtime, commands = setup(state(80, 1)); runtime._coordinator.replace_applied_ledger("s", {"old": event("old")}); expected = runtime.read_state()["state_fingerprint"]
    def fail_after_writer(*_):
        current = runtime.read_state(); changed = deepcopy(current["state"]); changed["self_side"]["pokemon"][0]["current_hp"] = 10; changed["last_applied_observation_sequence"] = 3
        runtime._store.compare_and_replace(changed, expected_session_id="s", expected_base_fingerprint=current["state_fingerprint"]); return False
    monkeypatch.setattr(runtime._coordinator, "replace_applied_ledger", fail_after_writer)
    assert commands.restore(target_candidate(), expected) == {"status": "critical_restore_inconsistency"}
    assert runtime.read_state()["state"] == state(10, 3) and runtime.read_applied_ledger() == {"old": event("old")}


def test_restore_critical_inconsistency_is_not_reported_as_success(monkeypatch):
    runtime, commands = setup(state(80, 1)); expected = runtime.read_state()["state_fingerprint"]
    monkeypatch.setattr(runtime._persistence, "restore", lambda *_: {"status": "critical_restore_inconsistency"})
    assert commands.restore(target_candidate(), expected) == {"status": "critical_restore_inconsistency"}


def test_restore_duplicate_ledger_semantics_survive_command_boundary():
    runtime, commands = setup(state(80, 1)); assert commands.restore(target_candidate(), runtime.read_state()["state_fingerprint"])["status"] == "restore_complete"; before = values(runtime)
    assert runtime.apply(snapshot(event()))["status"] == "already_applied"
    assert runtime.apply(snapshot(event(hp_after=1)))["status"] == "transition_invalid" and values(runtime) == before


def test_restore_is_not_available_as_undo_or_arbitrary_history_api():
    public = {name for name in dir(ObservationReplayPersistenceCommands) if not name.startswith("_")}
    assert not ({"undo", "redo", "history", "unapply", "reset", "rollover", "capture_rollback_snapshot", "compare_and_restore_snapshot"} & public)


def test_command_boundary_has_no_ui_worker_provider_autosave_or_startup_hooks():
    source = Path(commands_module.__file__).read_text(encoding="utf-8")
    assert not any(value in source for value in ("ui.", "MainWindow", "Worker", "advisor_client", "autosave", "startup", "threading.Timer"))


def test_command_results_are_detached_and_sanitized(tmp_path):
    runtime, commands = setup(); target = tmp_path / "state.json"; assert commands.save(target)["status"] == "save_complete"; result = commands.load(target); before = values(runtime)
    result["envelope"]["store"]["state"]["self_side"]["pokemon"][0]["current_hp"] = 1
    assert values(runtime) == before and "\\" not in repr(result)
