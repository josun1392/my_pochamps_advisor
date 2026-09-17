"""Composition coverage for the session-owned observation sequence allocator."""
from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager


def _state(session="sequence-owner"):
    state = create_unknown_bootstrap_battle_state(session, "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    return state


def _manager(state=None):
    state = _state() if state is None else state
    result = BattleObservationRuntimeSessionManager.create(state["session_id"], state)
    assert result["status"] == "session_ready"
    return result["manager"]


def _commit_hp(manager, after):
    read = manager.read_state(); state = read["state"]; pokemon = state["self_side"]["pokemon"][0]
    sequence = manager.allocate_observation_sequence()["observation_sequence"]
    observation = {
        "event_kind": "exact_hp_transition_observed", "reducer_eligibility": "candidate",
        "observation_id": f"{state['session_id']}:hp:{sequence}", "observation_sequence": sequence,
        "session_id": state["session_id"], "side": "self", "slot_index": 0,
        "pokemon_id": pokemon["pokemon_id"], "payload": {"hp_before": pokemon["current_hp"], "hp_after": after},
    }
    assert manager.admit_confirmation(state["session_id"], {"status": "confirmed", "observation": observation})["status"] == "added"
    assert manager.apply(state["session_id"], manager.read_collection_snapshot())["status"] == "applied"
    return sequence


def test_switch_permission_commit_advances_session_owned_sequence_for_next_canonical_observation():
    manager = _manager(); state = manager.read_state()["state"]; owner = state["self_side"]["pokemon"][0]
    captured = manager.capture_switch_permission(state["session_id"], active_slot_index=0, active_pokemon_id=owner["pokemon_id"], permission="permitted")
    assert captured["status"] == "captured"
    assert manager.read_state()["state"]["last_applied_observation_sequence"] == manager.last_allocated_sequence == 1
    assert _commit_hp(manager, 90) == 2
    assert manager.read_state()["state"]["last_applied_observation_sequence"] == manager.last_allocated_sequence == 2


def test_failed_switch_permission_does_not_reserve_or_commit_a_sequence():
    manager = _manager(); before = deepcopy(manager.read_state())
    result = manager.capture_switch_permission("sequence-owner", active_slot_index=0, active_pokemon_id="wrong", permission="permitted")
    assert result["status"] == "active_identity_mismatch"
    assert manager.last_allocated_sequence == 0 and manager.read_state() == before


def test_restore_resynchronizes_allocator_before_next_canonical_observation(tmp_path):
    source = _manager(); assert _commit_hp(source, 90) == 1 and _commit_hp(source, 80) == 2
    target = _manager(); path = tmp_path / "newer-state.json"
    assert source.save("sequence-owner", path)["status"] == "save_complete"
    candidate = target.load("sequence-owner", path); before = target.read_state()
    assert target.restore("sequence-owner", candidate, before["state_fingerprint"])["status"] == "restore_complete"
    assert target.read_state()["state"]["last_applied_observation_sequence"] == target.last_allocated_sequence == 2
    assert _commit_hp(target, 70) == 3


def test_failed_restore_preserves_allocator_and_committed_state(tmp_path):
    manager = _manager(); _commit_hp(manager, 90); before = deepcopy(manager.read_state()); sequence = manager.last_allocated_sequence
    assert manager.restore("sequence-owner", {"status": "invalid"}, before["state_fingerprint"])["status"] == "invalid_envelope"
    assert manager.last_allocated_sequence == sequence and manager.read_state() == before


def test_session_seeds_and_preserves_strict_duplicate_protection_from_committed_history():
    state = _state(); state["last_applied_observation_sequence"] = 4
    manager = _manager(state)
    assert manager.last_allocated_sequence == 4 and manager.allocate_observation_sequence()["observation_sequence"] == 5
    assert manager.admit_confirmation("sequence-owner", {"status": "confirmed", "observation": {"observation_id": "duplicate", "observation_sequence": 5, "event_kind": "exact_hp_transition_observed", "session_id": "sequence-owner"}})["status"] == "added"
    assert manager.admit_confirmation("sequence-owner", {"status": "confirmed", "observation": {"observation_id": "duplicate", "observation_sequence": 5, "event_kind": "exact_hp_transition_observed", "session_id": "sequence-owner"}})["status"] == "duplicate"
