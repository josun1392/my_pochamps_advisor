from copy import deepcopy
from pathlib import Path

import pytest

import llm.advisor_observation_runtime_session as session_module
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSession, BattleObservationRuntimeSessionManager
from llm.advisor_reducer_state_model import STATE_MODEL_VERSION


def state(session="a", hp=80, sequence=None):
    return {"state_version": STATE_MODEL_VERSION, "session_id": session, "self_side": {"active_slot_index": 0, "pokemon": {0: {"pokemon_id": "pikachu", "current_hp": hp, "max_hp": 100, "fainted": False, "condition": None, "known_item": "berry"}}, "side_conditions": []}, "opponent_side": {"active_slot_index": 0, "pokemon": {}}, "field": {"weather": None, "terrain": None}, "last_applied_observation_sequence": sequence, "q12": {"damage": 99}}


def event(session="a", oid="hp", sequence=1, hp_after=40):
    return {"event_kind": "exact_hp_transition_observed", "reducer_eligibility": "candidate", "observation_id": oid, "observation_sequence": sequence, "session_id": session, "side": "self", "slot_index": 0, "pokemon_id": "pikachu", "hp_before": 80, "hp_after": hp_after, "payload": {"hp_before": 80, "hp_after": hp_after}}


def confirmed(value): return {"status": "confirmed", "observation": value}
def make_manager(session="a", initial=None):
    made = BattleObservationRuntimeSessionManager.create(session, state(session) if initial is None else initial)
    assert made["status"] == "session_ready"
    return made["manager"]
def values(manager):
    read = manager.read_state()
    return (deepcopy(manager.read_collection_snapshot()), deepcopy(read["state"]), read["state_fingerprint"], read["state"]["last_applied_observation_sequence"], manager.last_allocated_sequence, deepcopy(manager.read_applied_ledger()))


def test_session_factory_creates_matching_collection_runtime_and_commands():
    initial = state(); made = BattleObservationRuntimeSession.create("a", initial)
    assert made["status"] == "session_ready" and made["session_id"] == "a"
    owner = made["session"]; current = owner.read_state()
    assert owner.session_id == "a" and owner.read_collection_snapshot()["ordered_observations"] == []
    assert current["state"] == initial and current["state"]["last_applied_observation_sequence"] is None
    assert owner.last_allocated_sequence == 0 and owner.read_applied_ledger() == {}


@pytest.mark.parametrize("session_id,initial", [("", state()), (1, state()), ("a", None), ("a", {"session_id": "a"}), ("a", {**state(), "extra": 1}), ("a", state("other")), ("a", state("a", sequence=-1))])
def test_session_factory_rejects_invalid_initial_state_without_partial_owner(session_id, initial):
    result = BattleObservationRuntimeSession.create(session_id, initial)
    assert result["status"] in {"invalid_initial_state", "creation_failed"} and result["session"] is None and result["session_id"] is None


def test_session_components_are_detached_and_share_exact_session_identity():
    initial = state(); owner = BattleObservationRuntimeSession.create("a", initial)["session"]
    initial["self_side"]["pokemon"][0]["current_hp"] = 1
    collection, current, ledger = owner.read_collection_snapshot(), owner.read_state(), owner.read_applied_ledger()
    collection["ordered_observations"].append({"bad": 1}); current["state"]["self_side"]["pokemon"][0]["current_hp"] = 2; ledger["bad"] = {}
    assert owner.read_state()["state"] == state() and owner.read_collection_snapshot()["ordered_observations"] == [] and owner.read_applied_ledger() == {}


def test_session_factory_performs_no_ui_provider_network_or_filesystem_io():
    source = Path(session_module.__file__).read_text(encoding="utf-8")
    assert not any(value in source for value in ("ui.", "MainWindow", "Worker", "advisor_client", "requests", "Path(", "open(", "autosave", "startup"))
    assert BattleObservationRuntimeSession.create("a", state())["status"] == "session_ready"


def test_explicit_rollover_publishes_new_bundle_atomically():
    manager = make_manager(); old = values(manager)
    assert manager.rollover("b", state("b", hp=60))["status"] == "session_replaced"
    now = values(manager); assert manager.session_id == "b" and now[0]["ordered_observations"] == [] and now[1] == state("b", hp=60)
    assert now[4:] == (0, {}) and old[1] == state() and manager.validate_active_session("a")["status"] == "stale_session"


def test_failed_rollover_preserves_existing_active_session(monkeypatch):
    manager = make_manager(); before = values(manager); identity = id(manager._active_session)
    monkeypatch.setattr(session_module.BattleObservationRuntimeSession, "create", classmethod(lambda *_: {"status": "creation_failed", "session": None, "session_id": None}))
    assert manager.rollover("b", state("b")) == {"status": "creation_failed", "session_id": "a"}
    assert id(manager._active_session) == identity and values(manager) == before


def test_duplicate_same_session_rollover_is_deterministic_and_non_mutating():
    manager = make_manager(); manager.allocate_observation_sequence(); before = values(manager); identity = id(manager._active_session)
    assert manager.rollover("a", {"ignored": True}) == {"status": "session_unchanged", "session_id": "a"}
    assert id(manager._active_session) == identity and values(manager) == before


def test_rollover_never_retags_or_rebinds_old_runtime_and_commands():
    manager = make_manager(); old = manager._active_session; manager.rollover("b", state("b"))
    assert old.session_id == old._runtime.session_id == old._commands.session_id == "a"
    assert old._runtime is not manager._active_session._runtime and old._commands is not manager._active_session._commands


def test_old_session_objects_cannot_be_reactivated_as_current():
    manager = make_manager(); old = manager._active_session; manager.rollover("b", state("b")); before = values(manager)
    public = {name for name in dir(BattleObservationRuntimeSessionManager) if not name.startswith("_")}
    assert manager.validate_active_session(old.session_id)["status"] == "stale_session" and not ({"reactivate", "set_current", "history", "sessions"} & public) and values(manager) == before


def test_new_session_sequence_starts_from_defined_initial_value():
    manager = make_manager(); before = values(manager)
    assert manager.last_allocated_sequence == 0 and manager.allocate_observation_sequence()["observation_sequence"] == 1 and manager.allocate_observation_sequence()["observation_sequence"] == 2
    after = values(manager); assert after[1:4] == before[1:4] and after[5] == before[5] and after[4] == 2


def test_old_session_producer_cannot_advance_new_session_sequence():
    manager = make_manager(); old = manager._active_session; manager.rollover("b", state("b")); before = values(manager)
    assert old.allocate_observation_sequence()["observation_sequence"] == 1 and manager.validate_active_session("a")["status"] == "stale_session" and values(manager) == before


def test_collection_sequence_and_store_last_applied_sequence_remain_session_scoped():
    manager = make_manager(); seq = manager.allocate_observation_sequence()["observation_sequence"]; observed = event(sequence=seq)
    assert manager.admit_confirmation("a", confirmed(observed))["status"] == "added" and manager.read_state()["state"]["last_applied_observation_sequence"] is None
    assert manager.apply("a", manager.read_collection_snapshot())["status"] == "applied" and manager.read_state()["state"]["last_applied_observation_sequence"] == 1
    manager.rollover("b", state("b")); assert manager.allocate_observation_sequence()["observation_sequence"] == 1 and manager.read_state()["state"]["last_applied_observation_sequence"] is None


def test_sequence_regression_is_only_new_namespace_not_same_session_rewind():
    manager = make_manager(); manager.allocate_observation_sequence(); manager.admit_confirmation("a", confirmed(event())); assert manager.apply("a", manager.read_collection_snapshot())["status"] == "applied"
    current = manager.read_state(); lower = deepcopy(current["state"]); lower["last_applied_observation_sequence"] = 0
    result = manager._active_session._runtime._store.compare_and_replace(lower, expected_session_id="a", expected_base_fingerprint=current["state_fingerprint"])
    assert result["status"] == "sequence_regression"; manager.rollover("b", state("b")); assert manager.last_allocated_sequence == 0


def test_old_worker_result_is_rejected_after_session_rollover():
    manager = make_manager(); manager.rollover("b", state("b")); assert manager.validate_worker_result_session("a") == {"status": "stale_worker_result", "session_id": "b"}


def test_stale_worker_result_does_not_mutate_collection_store_or_ledger():
    manager = make_manager(); manager.rollover("b", state("b")); before = values(manager)
    assert manager.validate_worker_result_session("a")["status"] == "stale_worker_result" and values(manager) == before


def test_current_session_worker_result_remains_eligible():
    manager = make_manager(); before = values(manager); assert manager.validate_worker_result_session("a") == {"status": "current_session", "session_id": "a"} and values(manager) == before


def test_worker_result_is_never_retagged_to_active_session():
    manager = make_manager(); captured = "a"; manager.rollover("b", state("b")); result = manager.validate_worker_result_session(captured)
    assert captured == "a" and result == {"status": "stale_worker_result", "session_id": "b"}


def test_active_session_commands_are_bound_to_current_runtime(tmp_path):
    manager = make_manager(); target = tmp_path / "a.json"; assert manager.save("a", target)["status"] == "save_complete"
    loaded = manager.load("a", target); assert loaded["status"] == "load_ready" and loaded["envelope"]["session_id"] == "a"


def test_old_command_owner_is_stale_after_rollover():
    manager = make_manager(); manager.rollover("b", state("b")); before = values(manager)
    assert manager.save("a", "unused.json") == {"status": "stale_session", "session_id": "b"} and values(manager) == before


def test_foreign_loaded_candidate_does_not_trigger_rollover(tmp_path):
    foreign = make_manager("b"); target = tmp_path / "foreign.json"; assert foreign.save("b", target)["status"] == "save_complete"
    manager = make_manager(); before = values(manager); loaded = manager.load("a", target)
    assert loaded["status"] == "load_ready" and loaded["envelope"]["session_id"] == "b" and manager.session_id == "a" and values(manager) == before


def test_restore_cannot_change_active_session_identity(tmp_path):
    foreign = make_manager("b"); target = tmp_path / "foreign.json"; foreign.save("b", target)
    manager = make_manager(); before = values(manager); candidate = manager.load("a", target)
    assert manager.restore("a", candidate, before[2]) == {"status": "session_mismatch"} and manager.session_id == "a" and values(manager) == before


def test_save_load_restore_are_never_invoked_implicitly_by_rollover(monkeypatch):
    manager = make_manager(); calls = []
    for name in ("save", "load", "restore"):
        monkeypatch.setattr(manager._active_session._commands, name, lambda *_a, _name=name, **_k: calls.append(_name))
    assert manager.rollover("b", state("b"))["status"] == "session_replaced" and calls == []


def test_session_owner_does_not_expose_mutable_raw_components():
    for klass in (BattleObservationRuntimeSession, BattleObservationRuntimeSessionManager):
        public = {name for name in dir(klass) if not name.startswith("_")}
        assert not ({"collection", "runtime", "commands", "store", "coordinator", "persistence", "set_sequence", "reset", "rebind", "undo", "redo"} & public)


def test_session_lifecycle_has_no_ui_file_picker_autosave_startup_or_provider_hooks():
    source = Path(session_module.__file__).read_text(encoding="utf-8")
    assert not any(value in source for value in ("ui.", "MainWindow", "Worker", "advisor_client", "QFileDialog", "autosave", "startup", "threading.Timer", "requests"))


def test_lifecycle_results_are_detached_and_sanitized():
    manager = make_manager(); result = manager.read_state(); result["state"]["self_side"]["pokemon"][0]["current_hp"] = 1
    assert manager.read_state()["state"] == state() and "\\" not in repr(manager.validate_worker_result_session("other"))
