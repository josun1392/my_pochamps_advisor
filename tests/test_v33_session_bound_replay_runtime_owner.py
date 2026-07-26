from copy import deepcopy
import ast
import inspect

import pytest

import llm.advisor_observation_replay_runtime as runtime_module
from llm.advisor_observation_replay_runtime import ObservationReplayRuntime
from llm.advisor_reducer_state_model import STATE_MODEL_VERSION, state_fingerprint


def state(hp=80, sequence=None, session="s"):
    return {"state_version": STATE_MODEL_VERSION, "session_id": session, "self_side": {"active_slot_index": 0, "pokemon": {0: {"pokemon_id": "pikachu", "current_hp": hp, "max_hp": 100, "fainted": False, "condition": None, "known_item": "berry"}}, "side_conditions": []}, "opponent_side": {"active_slot_index": 0, "pokemon": {}}, "field": {"weather": None, "terrain": None}, "last_applied_observation_sequence": sequence, "q12": {"damage": 99}}


def event(observation_id="hp", sequence=1, hp_after=40):
    return {"event_kind": "exact_hp_transition_observed", "reducer_eligibility": "candidate", "observation_id": observation_id, "observation_sequence": sequence, "session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "pikachu", "hp_before": 80, "hp_after": hp_after, "payload": {"hp_before": 80, "hp_after": hp_after}}


def snapshot(*events, session="s"):
    return {"status": "ready", "session_id": session, "ordered_observations": list(events)}


def runtime(initial=None):
    result = ObservationReplayRuntime.create(state() if initial is None else initial)
    assert result["status"] == "ready"
    return result["runtime"]


def values(owner):
    read = owner.read_state()
    return deepcopy(read["state"]), read["state_fingerprint"], read["state"]["last_applied_observation_sequence"], owner.read_applied_ledger()


def test_runtime_factory_creates_one_detached_same_session_owner():
    initial = state(); expected_fingerprint = state_fingerprint(initial)
    created = ObservationReplayRuntime.create(initial)
    assert created["status"] == "ready" and created["session_id"] == "s"
    owner = created["runtime"]; initial["self_side"]["pokemon"][0]["current_hp"] = 1
    read = owner.read_state(); assert read["state"] == state() and read["state_fingerprint"] == expected_fingerprint
    assert read["state"]["last_applied_observation_sequence"] is None and owner.read_applied_ledger() == {}
    read["state"]["self_side"]["pokemon"][0]["current_hp"] = 2
    assert owner.read_state()["state"] == state() and owner.session_id == "s"


def test_runtime_preview_requires_explicit_apply_and_is_non_mutating():
    owner = runtime(); before = values(owner)
    result = owner.preview(snapshot(event()))
    assert result["status"] == "preview_ready" and result["projected_state"]["self_side"]["pokemon"][0]["current_hp"] == 40
    assert values(owner) == before and "hp" not in owner.read_applied_ledger()


def test_runtime_apply_commits_once_and_duplicate_is_idempotent():
    owner = runtime(); frozen = snapshot(event())
    first = owner.apply(frozen); after_first = values(owner)
    assert first["status"] == "applied" and after_first[0]["self_side"]["pokemon"][0]["current_hp"] == 40
    assert after_first[2] == 1 and after_first[3] == {"hp": event()}
    assert owner.apply(frozen)["status"] == "already_applied"
    assert values(owner) == after_first


def test_runtime_rejects_cross_session_without_retagging():
    owner = runtime(); foreign = snapshot(event(), session="other"); before = values(owner)
    assert owner.preview(foreign)["status"] == "session_mismatch"
    assert owner.apply(foreign)["status"] == "session_mismatch"
    assert foreign["session_id"] == "other" and owner.session_id == "s" and values(owner) == before
    assert set(owner._coordinator._applied) <= {"s"}


def test_runtime_apply_preserves_stale_cas_and_concurrent_writer_protection(monkeypatch):
    owner = runtime(); frozen = snapshot(event()); preview = owner.preview(frozen); assert preview["status"] == "preview_ready"
    before = owner.read_state(); concurrent = deepcopy(before["state"]); concurrent["self_side"]["pokemon"][0]["current_hp"] = 60; concurrent["last_applied_observation_sequence"] = 1
    replaced = owner._store.compare_and_replace(concurrent, expected_session_id="s", expected_base_fingerprint=before["state_fingerprint"])
    assert replaced["status"] == "replaced"; concurrent_values = values(owner)
    monkeypatch.setattr(owner._coordinator, "preview", lambda _: deepcopy(preview))
    assert owner.apply(frozen)["status"] == "cas_conflict"
    assert values(owner) == concurrent_values and owner.read_applied_ledger() == {}


def test_runtime_rejects_conflicting_duplicate_without_partial_mutation():
    owner = runtime(); assert owner.apply(snapshot(event()))["status"] == "applied"; before = values(owner)
    result = owner.apply(snapshot(event(hp_after=1)))
    assert result["status"] == "transition_invalid" and result["conflicts"] == [{"observation_id": "hp", "reason": "conflicting_applied_observation"}]
    assert values(owner) == before and owner.read_applied_ledger() == {"hp": event()}


def test_runtime_returns_detached_read_preview_and_export_results():
    owner = runtime(); frozen = snapshot(event()); preview = owner.preview(frozen); assert owner.apply(frozen)["status"] == "applied"; exported = owner.export_envelope(); before = values(owner)
    state_read = owner.read_state(); ledger = owner.read_applied_ledger()
    state_read["state"]["self_side"]["pokemon"][0]["current_hp"] = 1
    preview["projected_state"]["self_side"]["pokemon"][0]["current_hp"] = 1
    exported["envelope"]["store"]["state"]["self_side"]["pokemon"][0]["current_hp"] = 1
    ledger["hp"]["payload"]["hp_after"] = 1
    assert values(owner) == before


def invalid_non_object(): return []
def invalid_missing_required(): value = state(); value.pop("field"); return value
def invalid_unexpected(): value = state(); value["unexpected"] = True; return value
def invalid_empty_session(): value = state(); value["session_id"] = ""; return value
def invalid_session_type(): value = state(); value["session_id"] = 1; return value
def invalid_sequence_type(): value = state(); value["last_applied_observation_sequence"] = True; return value
def invalid_sequence_negative(): value = state(); value["last_applied_observation_sequence"] = -1; return value
def invalid_nested_shape(): value = state(); value["self_side"] = []; return value


@pytest.mark.parametrize("invalid", [invalid_non_object, invalid_missing_required, invalid_unexpected, invalid_empty_session, invalid_session_type, invalid_sequence_type, invalid_sequence_negative, invalid_nested_shape], ids=["non_object", "missing_required", "unexpected", "empty_session", "session_type", "sequence_type", "sequence_negative", "nested_shape"])
def test_runtime_factory_rejects_invalid_initial_shape_safely(invalid):
    result = ObservationReplayRuntime.create(invalid())
    assert result == {"status": "invalid_initial_state", "runtime": None, "session_id": None}
    assert "Traceback" not in repr(result)


def test_runtime_export_and_validate_are_explicit_non_mutating_persistence_seams():
    owner = runtime(); before = values(owner); exported = owner.export_envelope()
    assert exported["status"] == "ready" and owner.validate_envelope(exported["envelope"])["status"] == "load_ready"
    bad = deepcopy(exported["envelope"]); bad["store"]["fingerprint"] = "bad"
    assert owner.validate_envelope(bad)["status"] == "fingerprint_mismatch"
    assert values(owner) == before


def test_runtime_has_no_ui_worker_provider_or_persistence_command_entry_points():
    public = {name for name in dir(ObservationReplayRuntime) if not name.startswith("_")}
    assert {"create", "session_id", "read_state", "read_applied_ledger", "preview", "apply", "export_envelope", "validate_envelope"} <= public
    assert not ({"save", "load", "restore", "reset", "rollover", "undo", "capture_rollback_snapshot", "compare_and_restore_snapshot"} & public)
    imports = ast.parse(inspect.getsource(runtime_module))
    imported = [alias.name for node in ast.walk(imports) if isinstance(node, ast.Import) for alias in node.names]
    imported += [node.module for node in ast.walk(imports) if isinstance(node, ast.ImportFrom) and node.module]
    assert not any(name == "ui" or name.startswith(("ui.", "llm.advisor_client", "llm.provider")) for name in imported)
