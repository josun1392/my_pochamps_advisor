from copy import deepcopy

from llm.advisor_reducer_state_model import make_unknown_battle_fact
from llm.advisor_switch_candidates import build_switch_candidate_context_projection, build_switch_candidates
from llm.advisor_switch_transition import project_authorized_switch_transition
from llm.advisor_turn_snapshot import build_request_start_recommendation_snapshot


def _state():
    unknown = make_unknown_battle_fact
    return {
        "state_version": "battle-state-v1", "session_id": "switch-transition", "last_applied_observation_sequence": None,
        "self_side": {"active_slot_index": 0, "side_conditions": unknown(), "pokemon": {
            0: {"pokemon_id": "a", "current_hp": unknown(), "max_hp": unknown(), "fainted": False, "condition": unknown(), "known_item": unknown()},
            1: {"pokemon_id": "b", "current_hp": unknown(), "max_hp": unknown(), "fainted": False, "condition": unknown(), "known_item": unknown()},
        }},
        "opponent_side": {"active_slot_index": 0, "side_conditions": unknown(), "pokemon": {0: {"pokemon_id": "x", "current_hp": unknown(), "max_hp": unknown(), "fainted": False, "condition": unknown(), "known_item": unknown()}}},
        "field": {"weather": unknown(), "terrain": unknown()},
    }


def _snapshot():
    context = build_switch_candidate_context_projection(_state())
    return build_request_start_recommendation_snapshot(
        {"current_state_session_id": "switch-transition", "switch_candidate_context": context,
         "pokemon": {"my_active": {"name_en": "a", "slot_index": 0}, "opponent_active": {"name_en": "x", "slot_index": 0}},
         "moves": {"my_available_moves": []}}, selectable_moves=(),
    )


def _opponent(*, priority=0, target="selected-pokemon"):
    return {"candidate_id": "opponent-action:s:x:test:0", "role": "opponent_action", "acting_side": "opponent", "target_side": "self", "move_id": "test", "move_metadata": {"move_id": "test", "priority": priority, "target": target}}


def test_manual_switch_precedes_all_move_priorities_and_ignores_speed_context():
    snapshot = _snapshot(); candidate = build_switch_candidates(turn_snapshot=snapshot)[0]
    for priority in (-1, 0, 1):
        result = project_authorized_switch_transition(turn_snapshot=snapshot, switch_candidate=candidate, switch_authorized=True, opponent_action=_opponent(priority=priority))
        assert (result["first_actor"], result["order_result"], result["order_supportability"]) == ("self", "self_switch_first", "complete")
        assert result["move_priority_supportability"] == result["speed_order_supportability"] == "not_applicable"


def test_transition_is_detached_redirects_only_supported_target_and_keeps_candidate_conservative():
    snapshot = _snapshot(); candidate = build_switch_candidates(turn_snapshot=snapshot)[0]; before = deepcopy(snapshot.to_dict())
    result = project_authorized_switch_transition(turn_snapshot=snapshot, switch_candidate=candidate, switch_authorized=True, opponent_action=_opponent())
    assert result["post_switch_snapshot"]["self_active"]["pokemon_id"] == "b"
    assert [row["pokemon_id"] for row in result["post_switch_snapshot"]["self_roster"]] == ["a", "b"]
    assert result["post_switch_snapshot"]["self_active"]["fainted"] == {"status": "known", "value": False}
    assert result["post_switch_snapshot"]["target_pokemon_state"]["current_hp"] == {"status": "unknown"}
    assert result["post_switch_snapshot"]["target_pokemon_state"]["condition"] == {"status": "unknown"}
    assert result["post_switch_snapshot"]["entry_effects_supportability"] == "unsupported_mechanic"
    assert result["redirected_opponent_action"]["redirected_target"]["pokemon_id"] == "b"
    assert snapshot.to_dict() == before and candidate["selectable"] is False
    result["post_switch_snapshot"]["self_active"]["pokemon_id"] = "forged"
    assert snapshot.to_dict() == before
    unsupported = project_authorized_switch_transition(turn_snapshot=snapshot, switch_candidate=candidate, switch_authorized=True, opponent_action=_opponent(target="all-opponents"))
    assert unsupported["transition_supportability"] == "complete"
    assert unsupported["target_redirection_supportability"] == "unsupported_mechanic"


def test_stale_forged_and_switch_vs_switch_inputs_fail_closed_without_changing_move_path():
    snapshot = _snapshot(); candidate = build_switch_candidates(turn_snapshot=snapshot)[0]
    stale = {**candidate, "session_id": "other"}
    assert project_authorized_switch_transition(turn_snapshot=snapshot, switch_candidate=stale, switch_authorized=True)["reason"] == "invalid_or_stale_switch_candidate"
    forged = {**candidate, "target_pokemon_id": "forged"}
    assert project_authorized_switch_transition(turn_snapshot=snapshot, switch_candidate=forged, switch_authorized=True)["reason"] == "invalid_or_stale_switch_candidate"
    switch_opponent = {"action_kind": "switch"}
    result = project_authorized_switch_transition(turn_snapshot=snapshot, switch_candidate=candidate, switch_authorized=True, opponent_action=switch_opponent)
    assert result["order_supportability"] == "unsupported_mechanic" and result["unsupported_reason"] == "switch_vs_switch"
    assert project_authorized_switch_transition(turn_snapshot=snapshot, switch_candidate=candidate, switch_authorized=False)["reason"] == "switch_not_authorized"
