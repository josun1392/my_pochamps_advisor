from copy import deepcopy

from llm.advisor_ability_interaction_authority import (
    ability_mechanic_prerequisite,
    project_ability_interaction_authority,
)
from llm.advisor_reducer_state_model import execute_atomic_transition, make_unknown_battle_fact
from llm.advisor_turn_snapshot import build_request_start_recommendation_snapshot


def _state():
    def pokemon(pokemon_id):
        return {"pokemon_id": pokemon_id, "current_hp": make_unknown_battle_fact(), "max_hp": make_unknown_battle_fact(), "fainted": make_unknown_battle_fact(), "condition": make_unknown_battle_fact(), "known_item": make_unknown_battle_fact()}
    return {"state_version": "battle-state-v1", "session_id": "s", "self_side": {"active_slot_index": 0, "pokemon": {0: pokemon("self-a"), 1: pokemon("self-b")}, "side_conditions": make_unknown_battle_fact()}, "opponent_side": {"active_slot_index": 0, "pokemon": {0: pokemon("opponent-a"), 1: pokemon("opponent-b")}, "side_conditions": make_unknown_battle_fact()}, "field": {"weather": make_unknown_battle_fact(), "terrain": make_unknown_battle_fact()}, "last_applied_observation_sequence": None}


def _event(effect, sequence, **payload):
    return {"observation_id": f"{effect}-{sequence}", "observation_sequence": sequence, "planned_effect": effect, **payload}


def _apply(state, event):
    plan = {"session_id": "s", "status": "planned", "conflicts": [], "accepted_events": [event], "ordered_steps": [event]}
    result = execute_atomic_transition(state, plan, expected_session_id="s")
    assert result["status"] == "committed"
    return result["committed_state"]


def _authority_events(applicability="applicable", interaction="affecting"):
    return (
        _event("set_ability_applicability", 1, side="opponent", slot_index=0, pokemon_id="opponent-a", ability_id="shadow-tag", applicability_status=applicability),
        _event("set_ability_interaction", 2, source_side="opponent", source_slot_index=0, source_pokemon_id="opponent-a", target_side="self", target_slot_index=0, target_pokemon_id="self-a", interaction_status=interaction),
    )


def _freeze(state):
    authority = project_ability_interaction_authority(state)
    snapshot = build_request_start_recommendation_snapshot({"current_state_session_id": "s", "ability_interaction_authority": authority, "pokemon": {"my_active": {"name_en": "self-a", "slot_index": 0}, "opponent_active": {"name_en": "opponent-a", "slot_index": 0}}, "moves": {"my_available_moves": []}}, selectable_moves=())
    return snapshot.to_dict()["current_state"]["ability_interaction_authority"]


def test_reducer_to_frozen_snapshot_produces_shadow_tag_prerequisite_without_a_blocker():
    state = _state()
    for event in _authority_events(): state = _apply(state, event)
    frozen = _freeze(state)
    assert ability_mechanic_prerequisite(frozen) == {"status": "complete"}
    assert "blocked" not in frozen and "permitted" not in frozen


def test_unknown_and_explicit_negative_production_paths_do_not_assert_an_effect():
    raw = _freeze(_state()) if False else None
    state = _state()
    # Raw ability identity is stored only with explicit applicability; unknown remains incomplete.
    state["ability_applicability_context"] = {"schema_version": "ability-applicability-context-v1", "session_id": "s", "source": {"side": "opponent", "slot_index": 0, "pokemon_id": "opponent-a"}, "ability_id": "shadow-tag", "status": "unknown"}
    assert ability_mechanic_prerequisite(_freeze(state)) == {"status": "insufficient_context"}
    state = _state()
    for event in _authority_events(applicability="not_applicable"): state = _apply(state, event)
    assert ability_mechanic_prerequisite(_freeze(state)) == {"status": "not_applicable"}
    state = _state()
    first, _ = _authority_events(); state = _apply(state, first)
    assert ability_mechanic_prerequisite(_freeze(state)) == {"status": "insufficient_context"}


def test_identity_mismatch_is_rejected_and_frozen_authority_is_detached():
    state = _state()
    bad = _event("set_ability_interaction", 1, source_side="opponent", source_slot_index=0, source_pokemon_id="forged", target_side="self", target_slot_index=0, target_pokemon_id="self-a", interaction_status="affecting")
    plan = {"session_id": "s", "status": "planned", "conflicts": [], "accepted_events": [bad], "ordered_steps": [bad]}
    assert execute_atomic_transition(state, plan, expected_session_id="s")["status"] == "blocked_by_semantic_conflict"
    for event in _authority_events(): state = _apply(state, event)
    frozen = _freeze(state)
    later = deepcopy(state); later["ability_interaction_context"]["status"] = "not_affecting"
    assert frozen["interaction"] == "affecting"
    assert project_ability_interaction_authority(later)["interaction"] == "not_affecting"


def test_active_replacement_invalidates_positive_authority_instead_of_rebinding_same_slot():
    state = _state()
    for event in _authority_events(): state = _apply(state, event)
    switch = _event("switch_active", 3, side="self", switch_out_slot_index=0, switch_out_pokemon_id="self-a", switch_in_slot_index=1, switch_in_pokemon_id="self-b")
    state = _apply(state, switch)
    assert state["ability_interaction_context"]["status"] == "unknown"
