from copy import deepcopy
import pytest

from llm.advisor_reducer_state_model import execute_atomic_transition, make_unknown_battle_fact
from llm.advisor_switch_candidates import build_switch_candidate_context_projection, build_switch_candidates
from llm.advisor_turn_snapshot import build_request_start_recommendation_snapshot
from llm.advisor_combined_action_selection import select_combined_self_action


def _state(session="s", active=0):
    roster = {0: {"pokemon_id": "pikachu-a", "fainted": False}, 1: {"pokemon_id": "pikachu-b", "fainted": False}, 2: {"pokemon_id": "eevee", "fainted": True}}
    for row in roster.values(): row.update({"current_hp": make_unknown_battle_fact(), "max_hp": make_unknown_battle_fact(), "condition": make_unknown_battle_fact(), "known_item": make_unknown_battle_fact()})
    opponent = {"pokemon_id": "opponent", "current_hp": make_unknown_battle_fact(), "max_hp": make_unknown_battle_fact(), "fainted": make_unknown_battle_fact(), "condition": make_unknown_battle_fact(), "known_item": make_unknown_battle_fact()}
    return {"state_version": "battle-state-v1", "session_id": session, "self_side": {"active_slot_index": active, "pokemon": roster, "side_conditions": make_unknown_battle_fact()}, "opponent_side": {"active_slot_index": 0, "pokemon": {0: opponent}, "side_conditions": make_unknown_battle_fact()}, "field": {"weather": make_unknown_battle_fact(), "terrain": make_unknown_battle_fact()}, "last_applied_observation_sequence": None}


def _event(state, status="permitted", sequence=1):
    active = state["self_side"]["active_slot_index"]; pid = state["self_side"]["pokemon"][active]["pokemon_id"]
    return {"observation_id": f"permission-{sequence}", "observation_sequence": sequence, "planned_effect": "set_switch_permission", "side": "self", "slot_index": active, "pokemon_id": pid, "permission_status": status, "source": "user_confirmed_current_switch_permission", "trust": "user_confirmed_current"}


def _apply(state, event):
    plan = {"session_id": state["session_id"], "status": "planned", "conflicts": [], "accepted_events": [event], "ordered_steps": [event]}
    return execute_atomic_transition(state, plan, expected_session_id=state["session_id"])["committed_state"]


def _candidates(state):
    context = build_switch_candidate_context_projection(state)
    snapshot = build_request_start_recommendation_snapshot({"current_state_session_id": state["session_id"], "switch_candidate_context": context, "pokemon": {"my_active": {"name_en": state["self_side"]["pokemon"][0]["pokemon_id"], "slot_index": 0}, "opponent_active": {"name_en": "opponent", "slot_index": 0}}, "moves": {"my_available_moves": []}}, selectable_moves=())
    return build_switch_candidates(turn_snapshot=snapshot)


def test_unknown_permitted_blocked_and_target_availability_are_separate():
    unknown = {row["target_pokemon_id"]: row for row in _candidates(_state())}
    assert unknown["pikachu-b"]["reason_code"] == "switch_legality_unknown" and not unknown["pikachu-b"]["selectable"]
    permitted = {row["target_pokemon_id"]: row for row in _candidates(_apply(_state(), _event(_state())))}
    assert permitted["pikachu-b"]["selectable"] and permitted["pikachu-b"]["reason_code"] == "switch_available"
    assert not permitted["eevee"]["selectable"] and permitted["eevee"]["reason_code"] == "target_fainted"
    blocked_state = _apply(_state(), _event(_state(), "blocked"))
    assert all(not row["selectable"] and row["reason_code"] in {"switch_blocked", "target_fainted"} for row in _candidates(blocked_state))


def test_permission_is_active_bound_invalidated_and_frozen():
    state = _apply(_state(), _event(_state()))
    frozen = deepcopy(_candidates(state))
    switch = {"observation_id": "switch", "observation_sequence": 2, "planned_effect": "switch_active", "side": "self", "switch_out_slot_index": 0, "switch_out_pokemon_id": "pikachu-a", "switch_in_slot_index": 1, "switch_in_pokemon_id": "pikachu-b"}
    moved = _apply(state, switch)
    assert moved["self_side"]["switch_permission_context"]["status"] == "unknown"
    assert frozen[0]["selectable"] is True


def test_untrusted_or_wrong_active_update_is_rejected():
    state = _state()
    bad = _event(state); bad["source"] = "provider_inference"
    plan = {"session_id": "s", "status": "planned", "conflicts": [], "accepted_events": [bad], "ordered_steps": [bad]}
    assert execute_atomic_transition(state, plan, expected_session_id="s")["status"] == "blocked_by_semantic_conflict"
    wrong = _event(state); wrong["pokemon_id"] = "pikachu-b"
    plan["accepted_events"] = [wrong]; plan["ordered_steps"] = [wrong]
    assert execute_atomic_transition(state, plan, expected_session_id="s")["status"] == "blocked_by_semantic_conflict"


def test_stale_or_malformed_permission_never_authorizes_and_combined_selector_can_use_permitted_switch():
    state = _state(); state["self_side"]["switch_permission_context"] = {"schema_version": "switch-permission-context-v1", "session_id": "old", "side": "self", "active_slot_index": 0, "active_pokemon_id": "pikachu-a", "status": "permitted", "supportability": "complete", "source": "user_confirmed_current_switch_permission", "trust": "user_confirmed_current"}
    with pytest.raises(ValueError, match="invalid_switch_candidate_context"):
        _candidates(state)
    candidate = _candidates(_apply(_state(), _event(_state())))[0]
    result = select_combined_self_action(move_actions=[{"action_candidate_id": "self-move:s:m", "action_kind": "move", "selectable": True, "cross_action_danger_tier": "executed_guaranteed_self_ko"}], switch_actions=[{"action_candidate_id": candidate["candidate_id"], "action_kind": "switch", "selectable": candidate["selectable"], "cross_action_danger_tier": "neutral_no_positive_danger"}])
    assert result["selected_candidate_id"] == candidate["candidate_id"]
