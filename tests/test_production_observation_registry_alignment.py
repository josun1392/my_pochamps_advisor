"""Production collection admission must stay aligned with lifecycle contracts."""
from copy import deepcopy

import llm.advisor_lifecycle_confirmation as lifecycle
import llm.advisor_observation_collection as collection_module
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import LifecycleConfirmationBoundary, USER_TRUST
from llm.advisor_observation_collection import ObservationCollection
from llm.advisor_reducer_state_model import project_atomic_transition
from llm.advisor_replay_policy import _EFFECTS, build_replay_plan


_RUNTIME_COLLECTION_KINDS = {
    "current_healing_prevented_observed",
    "pending_status_action_execution_observed",
    "doubles_active_topology_observed",
    "selected_action_targeting_observed",
    "mat_block_active_entry_eligibility_observed",
    "fake_out_active_entry_eligibility_observed",
    "supreme_overlord_initial_active_observed",
}
_FIXTURE_ONLY_KINDS = {
    "condition_removed_observed", "item_consumption_observed", "item_removed_observed",
    "weather_started_observed", "weather_ended_observed", "terrain_started_observed",
    "side_condition_started_observed", "side_condition_ended_observed",
}


def _state():
    state = create_unknown_bootstrap_battle_state("registry-alignment", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    return state


def _owner(state, side="self"):
    roster = state[f"{side}_side"]
    slot = roster["active_slot_index"]
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": roster["pokemon"][slot]["pokemon_id"]}


def _boundary(state):
    return LifecycleConfirmationBoundary(state["session_id"], {side: _owner(state, side) for side in ("self", "opponent")})


def _confirmation(state, kind, *, boundary=None):
    owner = _owner(state)
    payloads = {
        "current_healing_prevented_observed": {"status": "active"},
        "pending_status_action_execution_observed": {"decision_point": "turn:1", "action_id": "action:sleep", "move_id": "snore", "condition": "sleep", "execution_state": "blocked", "blocker": "sleep", "outcome_class": "blocked_sleep"},
        "doubles_active_topology_observed": {"active_owners": [
            {"side": side, "active_slot_index": slot, "pokemon_id": f"{side}-{slot}", "active": True}
            for side in ("self", "opponent") for slot in (0, 1)
        ]},
        "selected_action_targeting_observed": {"decision_point": "turn:1", "action_id": "action:target", "move_id": "tackle", "selected_target": None},
        "mat_block_active_entry_eligibility_observed": {"decision_point": "turn:1", "action_id": "action:mat", "move_id": "mat-block", "active_entry_token": "entry:1", "eligibility": "eligible"},
        "fake_out_active_entry_eligibility_observed": {"decision_point": "turn:1", "action_id": "action:fake", "move_id": "fake-out", "active_entry_token": "entry:1", "eligibility": "eligible"},
        "supreme_overlord_initial_active_observed": {"entry_token": "entry:1", "cumulative_allied_faint_count": 0},
    }
    sources = {
        "current_healing_prevented_observed": lifecycle.CURRENT_HEALING_PREVENTED_SOURCE,
        "pending_status_action_execution_observed": lifecycle.PENDING_STATUS_ACTION_EXECUTION_SOURCE,
        "doubles_active_topology_observed": lifecycle.DOUBLES_ACTIVE_TOPOLOGY_SOURCE,
        "selected_action_targeting_observed": lifecycle.SELECTED_ACTION_TARGETING_SOURCE,
        "mat_block_active_entry_eligibility_observed": lifecycle.MAT_BLOCK_ACTIVE_ENTRY_ELIGIBILITY_SOURCE,
        "fake_out_active_entry_eligibility_observed": lifecycle.FAKE_OUT_ACTIVE_ENTRY_ELIGIBILITY_SOURCE,
        "supreme_overlord_initial_active_observed": lifecycle.SUPREME_OVERLORD_INITIAL_ACTIVE_SOURCE,
    }
    result = (boundary or _boundary(state)).confirm(
        event_kind=kind, payload=payloads[kind], session_id=state["session_id"], source=sources[kind],
        trust=USER_TRUST, confirmed=True, side=owner["side"], slot_index=owner["slot_index"],
        pokemon_id=owner["pokemon_id"], turn_number=1,
    )
    assert result["status"] == "confirmed", result
    return result


def test_production_ready_runtime_kinds_are_lifecycle_confirmed_and_collectable():
    state = _state()
    for kind in sorted(_RUNTIME_COLLECTION_KINDS):
        confirmation = _confirmation(state, kind)
        collection = ObservationCollection(state["session_id"])
        assert collection.add_confirmation_result(confirmation)["status"] == "added"
        assert collection.snapshot()["ordered_observations"][0]["event_kind"] == kind


def test_registry_contract_keeps_fixture_and_evidence_only_kinds_out_of_normal_admission():
    assert _RUNTIME_COLLECTION_KINDS <= collection_module._KINDS
    assert all(lifecycle._KINDS[kind] == "production_ready" for kind in _RUNTIME_COLLECTION_KINDS)
    assert all(kind in _EFFECTS for kind in _RUNTIME_COLLECTION_KINDS)
    assert all(lifecycle._KINDS[kind] == "fixture_only" and kind not in collection_module._KINDS for kind in _FIXTURE_ONLY_KINDS)
    assert "terrain_ended_observed" not in collection_module._KINDS
    assert "direct_move_damage_observed" in collection_module._KINDS


def test_canonical_lifecycle_collection_replay_reducer_chain_preserves_healing_prevention():
    state = _state()
    collection = ObservationCollection(state["session_id"])
    confirmation = _confirmation(state, "current_healing_prevented_observed")
    assert collection.add_confirmation_result(confirmation)["status"] == "added"
    plan = build_replay_plan(state, collection.snapshot()["ordered_observations"])
    assert plan["status"] == "planned" and plan["ordered_steps"][0]["planned_effect"] == "set_current_healing_prevented"
    projected = project_atomic_transition(state, plan, state["session_id"])
    assert projected["status"] == "ready_with_projected_state", projected
    assert projected["projected_state"]["self_side"]["pokemon"][0]["healing_prevented_status"] == "active"


def test_fake_out_lifecycle_collection_replay_reducer_chain_preserves_eligibility():
    state = _state()
    collection = ObservationCollection(state["session_id"])
    assert collection.add_confirmation_result(_confirmation(state, "fake_out_active_entry_eligibility_observed"))["status"] == "added"
    plan = build_replay_plan(state, collection.snapshot()["ordered_observations"])
    assert plan["ordered_steps"][0]["planned_effect"] == "set_fake_out_active_entry_eligibility"
    assert plan["ordered_steps"][0]["active_entry_token"] == "entry:1"
    projected = project_atomic_transition(state, plan, state["session_id"])
    assert projected["status"] == "ready_with_projected_state", projected
    assert projected["projected_state"]["fake_out_active_entry_eligibility_context"]["eligibility"] == "eligible"


def test_collection_preserves_fail_closed_stale_malformed_and_duplicate_semantics():
    state = _state(); confirmation = _confirmation(state, "fake_out_active_entry_eligibility_observed")
    collection = ObservationCollection(state["session_id"])
    assert collection.add_confirmation_result(confirmation)["status"] == "added"
    assert collection.add_confirmation_result(confirmation)["status"] == "duplicate"
    stale = deepcopy(confirmation); stale["observation"]["session_id"] = "foreign"
    assert collection.add_confirmation_result(stale)["status"] == "stale_session"
    malformed = deepcopy(confirmation); malformed["observation"]["event_kind"] = "condition_removed_observed"
    assert collection.add_confirmation_result(malformed)["status"] == "invalid_observation"
