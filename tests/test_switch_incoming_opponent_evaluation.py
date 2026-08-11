from copy import deepcopy

from llm.advisor_reducer_state_model import make_unknown_battle_fact
from llm.advisor_roster_mechanics import build_self_roster_mechanics_context_projection
from llm.advisor_switch_candidates import build_switch_candidate_context_projection, build_switch_candidates
from llm.advisor_switch_incoming_evaluator import evaluate_switch_incoming_opponent_action
from llm.advisor_switch_transition import project_authorized_switch_transition
from llm.advisor_turn_snapshot import build_request_start_recommendation_snapshot
from llm.advisor_switch_hazard_authority import build_switch_hazard_context


def _stats(value): return {"hp": value, "attack": value, "defense": value, "special-attack": value, "special-defense": value, "speed": value}


def _state():
    u = make_unknown_battle_fact
    return {"state_version": "battle-state-v1", "session_id": "incoming-s", "last_applied_observation_sequence": None,
            "self_side": {"active_slot_index": 0, "side_conditions": u(), "pokemon": {0: {"pokemon_id": "a", "current_hp": 50, "max_hp": 100, "fainted": False, "condition": u(), "known_item": u()}, 1: {"pokemon_id": "b", "current_hp": 180, "max_hp": 200, "fainted": False, "condition": u(), "known_item": u()}}},
            "opponent_side": {"active_slot_index": 0, "side_conditions": u(), "pokemon": {0: {"pokemon_id": "x", "current_hp": u(), "max_hp": u(), "fainted": False, "condition": u(), "known_item": u()}}}, "field": {"weather": u(), "terrain": u()}}


def _snapshot(state, roster):
    switch = build_switch_candidate_context_projection(state)
    return build_request_start_recommendation_snapshot({"current_state_session_id": state["session_id"], "switch_candidate_context": switch, "self_roster_mechanics_context": roster, "switch_hazard_context": state.get("switch_hazard_context"), "pokemon": {"my_active": {"name_en": "a", "slot_index": 0}, "opponent_active": {"name_en": "x", "slot_index": 0}}, "moves": {"my_available_moves": []}}, selectable_moves=())


def _opponent(target="selected-pokemon", category="physical"):
    metadata = {"move_id": "tackle", "category": category, "power": 40, "type": "normal", "priority": 0, "target": target}
    side = lambda ident, side, types, value: {"pokemon_identity": ident, "side": side, "types": {"available": True, "value": types}, "type_authority": {"status": "known", "basis": "current_type_context"}, "base_stats": {"available": True, "value": _stats(value)}, "final_stats": {"available": True, "value": _stats(value)}}
    return {"candidate_id": "opponent-action:incoming-s:x:tackle:0", "role": "opponent_action", "acting_side": "opponent", "target_side": "self", "session_id": "incoming-s", "pokemon_identity": "x", "move_id": "tackle", "metadata_supportability": "complete", "move_metadata": metadata, "mechanics_snapshot": {"attacker": {"species_id": "x", "slot_index": 0}, "defender": {"species_id": "a", "slot_index": 0}, "move": {"slot_index": 0, "owner_species_id": "x", **metadata}, "battle_context": {"current_state": {"trusted_level_context": {"current_levels": [{"side": "opponent", "value": 50, "provenance": {"pokemon_id": "x", "slot_index": 0}}]}}, "stat_provenance": {"attacker": side("x", "opponent", ["normal"], 100), "defender": side("a", "self", ["fire"], 10)}}}}


def _transition(*, unknown_type=False, target="selected-pokemon"):
    state = _state(); base = build_self_roster_mechanics_context_projection(state); records = deepcopy(base["entries"])
    b = records[1]; b["current_type_authority"] = {"status": "unknown"} if unknown_type else {"status": "known", "value": ["water"]}; b["base_stat_authority"] = {"status": "known", "value": _stats(200)}; b["final_stat_authority"] = {"status": "known", "value": _stats(200)}; b["hp_authority"] = {"status": "known", "current_hp": 180, "maximum_hp": 200, "provenance": "user_confirmed_current_hp"}
    roster = build_self_roster_mechanics_context_projection(state, roster_mechanics_records=records); snapshot = _snapshot(state, roster); candidate = build_switch_candidates(turn_snapshot=snapshot)[0]
    return project_authorized_switch_transition(turn_snapshot=snapshot, switch_candidate=candidate, switch_authorized=True, opponent_action=_opponent(target=target)), candidate, snapshot


def test_authorized_transition_reuses_existing_q12_ko_probability_with_b_defender_only():
    transition, candidate, _snapshot_value = _transition()
    result = evaluate_switch_incoming_opponent_action(transition=transition)
    assert result["switch_candidate_id"] == candidate["candidate_id"]
    assert result["target_pokemon_id"] == "b" and result["direct_incoming_supportability"] == "complete"
    assert result["q12_evidence"]["status"] == "resolved"
    assert result["damage_evidence"]["ko_interpretation"]["ko_supportability"] == "complete"
    assert result["damage_evidence"]["ko_probability"]["ko_probability_supportability"] == "complete"
    assert result["full_switch_outcome_supportability"] == "unsupported_mechanic"


def test_unknown_b_authority_and_unsupported_target_fail_closed_without_a_fallback():
    unknown, _, _ = _transition(unknown_type=True)
    result = evaluate_switch_incoming_opponent_action(transition=unknown)
    assert result["direct_incoming_supportability"] == "insufficient_context"
    assert result["q12_evidence"] is None or result["q12_evidence"]["status"] != "resolved"
    unsupported, _, _ = _transition(target="all-opponents")
    assert evaluate_switch_incoming_opponent_action(transition=unsupported)["incompleteness_reasons"] == ["invalid_switch_transition"]


def test_forged_or_mutated_result_isolated_and_conservative_candidate_is_unchanged():
    transition, candidate, snapshot = _transition(); before = deepcopy(transition)
    result = evaluate_switch_incoming_opponent_action(transition=transition)
    result["damage_evidence"]["status"] = "forged"
    assert transition == before and candidate["selectable"] is False
    forged = deepcopy(transition); forged["post_switch_snapshot"]["target_roster_mechanics"]["pokemon_id"] = "a"
    assert evaluate_switch_incoming_opponent_action(transition=forged)["incompleteness_reasons"] == ["invalid_switch_transition"]
    assert snapshot.to_dict()["current_state"]["self_roster_mechanics_context"]["entries"][1]["pokemon_id"] == "b"


def test_supported_hazard_chip_is_composed_before_direct_incoming_damage():
    state = _state()
    state["switch_hazard_context"] = build_switch_hazard_context(session_id="incoming-s", affected_side="self", stealth_rock="absent", spikes_layers=3)
    state["self_side"]["pokemon"][1]["prospective_groundedness_context"] = {"schema_version": "identity-groundedness-v1", "session_id": "incoming-s", "side": "self", "slot_index": 1, "pokemon_id": "b", "status": "grounded"}
    base = build_self_roster_mechanics_context_projection(state)
    records = deepcopy(base["entries"])
    b = records[1]
    b["current_type_authority"] = {"status": "known", "value": ["water"]}
    b["base_stat_authority"] = {"status": "known", "value": _stats(200)}
    b["final_stat_authority"] = {"status": "known", "value": _stats(200)}
    b["hp_authority"] = {"status": "known", "current_hp": 45, "maximum_hp": 200, "provenance": "user_confirmed_current_hp"}
    b["item_authority"] = {"status": "known", "value": None}
    b["ability_authority"] = {"status": "known", "value": "pressure"}
    roster = build_self_roster_mechanics_context_projection(state, roster_mechanics_records=records)
    snapshot = _snapshot(state, roster)
    candidate = build_switch_candidates(turn_snapshot=snapshot)[0]
    transition = project_authorized_switch_transition(turn_snapshot=snapshot, switch_candidate=candidate, switch_authorized=True, opponent_action=_opponent())
    hazard = transition["post_switch_snapshot"]["switch_hazard_context"]
    target = transition["post_switch_snapshot"]["target_roster_mechanics"]
    from llm.advisor_switch_entry_hazards import evaluate_entry_hazards
    result = evaluate_switch_incoming_opponent_action(transition=transition, entry_hazard_result=evaluate_entry_hazards(hazards=hazard, target=target))
    assert result["entry_hazard_result"]["damage"] == 50
    assert result["entry_hazard_result"]["hazard_ko"] is True
    assert result["direct_incoming_supportability"] == "not_applicable"


def test_entry_ko_reaches_switch_danger_even_without_an_opponent_action():
    state = _state()
    state["switch_hazard_context"] = build_switch_hazard_context(session_id="incoming-s", affected_side="self", stealth_rock="absent", spikes_layers=3)
    state["self_side"]["pokemon"][1]["prospective_groundedness_context"] = {"schema_version": "identity-groundedness-v1", "session_id": "incoming-s", "side": "self", "slot_index": 1, "pokemon_id": "b", "status": "grounded"}
    base = build_self_roster_mechanics_context_projection(state)
    records = deepcopy(base["entries"])
    b = records[1]
    b.update({"item_authority": {"status": "known", "value": None}, "ability_authority": {"status": "known", "value": "pressure"}, "hp_authority": {"status": "known", "current_hp": 40, "maximum_hp": 200, "provenance": "user_confirmed_current_hp"}})
    roster = build_self_roster_mechanics_context_projection(state, roster_mechanics_records=records)
    snapshot = _snapshot(state, roster)
    candidate = build_switch_candidates(turn_snapshot=snapshot)[0]
    from llm.advisor_combined_action_recommendation import _switch_actions
    rows = _switch_actions({"switch_candidates": [candidate], "opponent_action_candidates": []}, snapshot)
    assert rows[0]["cross_action_danger_tier"] == "executed_guaranteed_self_ko"


def test_direct_incoming_uses_b_post_entry_condition_and_speed_stage_not_active_a_values():
    from llm.advisor_switch_incoming_evaluator import _target_after_entry_effects
    target = {
        "hp_authority": {"status": "known", "current_hp": 100, "maximum_hp": 100, "provenance": "user_confirmed_current_hp"},
        "persistent_condition_authority": {"status": "known", "value": None},
        "prospective_speed_stage_authority": {"status": "known", "value": 2},
    }
    result = _target_after_entry_effects(target, {"status": "complete", "post_hazard_hp": 88, "toxic_spikes_result": {"status": "complete", "post_condition": "toxic"}, "sticky_web_result": {"status": "complete", "speed_stage_after": 1}})
    assert result["hp_authority"]["current_hp"] == 88
    assert result["persistent_condition_authority"] == {"status": "known", "value": "toxic"}
    assert result["prospective_speed_stage_authority"] == {"status": "known", "value": 1}


def test_direct_adapter_replaces_active_a_condition_and_speed_stage_with_b_records():
    from llm.advisor_switch_incoming_evaluator import _adapt_opponent_candidate
    action = _opponent()
    action["mechanics_snapshot"]["battle_context"]["current_state"].update({
        "condition_context": {"current_conditions": [{"side": "self", "condition_type": "burn", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"}]},
        "stat_stage_context": {"current_stages": [{"side": "self", "stat": "speed", "stage": 4, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}]},
    })
    target = {"session_id": "incoming-s", "slot_index": 1, "pokemon_id": "b", "persistent_condition_authority": {"status": "known", "value": "toxic"}, "prospective_speed_stage_authority": {"status": "known", "value": -1}, "ability_authority": {"status": "known", "value": "pressure"}, "hp_authority": {"status": "known", "current_hp": 80, "maximum_hp": 100, "provenance": "user_confirmed_current_hp"}}
    adapted = _adapt_opponent_candidate(action, target)
    current = adapted["mechanics_snapshot"]["battle_context"]["current_state"]
    assert current["condition_context"]["current_conditions"] == [{"side": "self", "condition_type": "toxic", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"}]
    assert current["stat_stage_context"]["current_stages"] == [{"side": "self", "stat": "speed", "stage": -1, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}]
