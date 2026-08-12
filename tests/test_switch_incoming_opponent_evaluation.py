from copy import deepcopy

from llm.advisor_reducer_state_model import make_unknown_battle_fact
from llm.advisor_roster_mechanics import build_self_roster_mechanics_context_projection
from llm.advisor_switch_candidates import build_switch_candidate_context_projection, build_switch_candidates
from llm.advisor_switch_incoming_evaluator import evaluate_switch_incoming_opponent_action
from llm.advisor_switch_transition import project_authorized_switch_transition
from llm.advisor_turn_snapshot import build_request_start_recommendation_snapshot
from llm.advisor_switch_hazard_authority import build_switch_hazard_context
from llm.advisor_switch_entry_intimidate_authority import build_switch_entry_intimidate_authority
from llm.advisor_switch_entry_sturdy_authority import build_switch_entry_sturdy_authority


def _stats(value): return {"hp": value, "attack": value, "defense": value, "special-attack": value, "special-defense": value, "speed": value}


def _state():
    u = make_unknown_battle_fact
    return {"state_version": "battle-state-v1", "session_id": "incoming-s", "last_applied_observation_sequence": None,
            "self_side": {"active_slot_index": 0, "side_conditions": u(), "pokemon": {0: {"pokemon_id": "a", "current_hp": 50, "max_hp": 100, "fainted": False, "condition": u(), "known_item": u()}, 1: {"pokemon_id": "b", "current_hp": 180, "max_hp": 200, "fainted": False, "condition": u(), "known_item": u()}}},
            "opponent_side": {"active_slot_index": 0, "side_conditions": u(), "pokemon": {0: {"pokemon_id": "x", "current_hp": u(), "max_hp": u(), "fainted": False, "condition": u(), "known_item": u()}}}, "field": {"weather": u(), "terrain": u()}}


def _snapshot(state, roster):
    switch = build_switch_candidate_context_projection(state)
    return build_request_start_recommendation_snapshot({"current_state_session_id": state["session_id"], "switch_candidate_context": switch, "self_roster_mechanics_context": roster, "switch_hazard_context": state.get("switch_hazard_context"), "switch_entry_intimidate_authority": state.get("switch_entry_intimidate_authority"), "switch_entry_sturdy_authority": state.get("switch_entry_sturdy_authority"), "pokemon": {"my_active": {"name_en": "a", "slot_index": 0}, "opponent_active": {"name_en": "x", "slot_index": 0}}, "moves": {"my_available_moves": []}}, selectable_moves=())


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


def test_direct_incoming_uses_b_owned_trace_copy_not_the_opponent_authority_object():
    from llm.advisor_switch_incoming_evaluator import _target_after_entry_effects
    target = {"ability_authority": {"status": "known", "value": "trace"}}
    result = _target_after_entry_effects(target, {"trace_result": {"status": "complete", "copied_ability": "water-absorb"}})
    assert result["ability_authority"] == {"status": "known", "value": "water-absorb"}
    assert result["ability_authority"] is not target["ability_authority"]


def test_direct_adapter_uses_post_entry_weather_for_existing_weather_consumers():
    from llm.advisor_switch_incoming_evaluator import _adapt_opponent_candidate
    action = _opponent()
    action["mechanics_snapshot"]["battle_context"]["current_state"]["field_state_context"] = {"current_field": {"weather": "none"}}
    target = {"session_id": "incoming-s", "slot_index": 1, "pokemon_id": "b"}
    for weather in ("rain", "sandstorm", "snow"):
        current = _adapt_opponent_candidate(action, target, entry_effect_result={"weather_result": {"status": "complete", "weather_after": weather}})["mechanics_snapshot"]["battle_context"]["current_state"]
        assert current["field_state_context"]["current_field"]["weather"] == weather


def test_direct_adapter_preserves_exact_b_owned_defender_item_authority():
    from llm.advisor_switch_incoming_evaluator import _defender_provenance
    target = {"session_id": "incoming-s", "slot_index": 1, "pokemon_id": "b", "item_authority": {"status": "known", "value": "assault-vest"}}
    assert _defender_provenance(target)["known_item"] == {"available": True, "status": "known", "value": "assault-vest", "profile_source": "frozen_candidate_item_authority"}


def test_exact_full_hp_focus_sash_refines_only_supported_single_hit_guaranteed_ohko():
    from llm.advisor_switch_incoming_evaluator import _apply_focus_sash_survival
    damage = {"status": "known", "ko_interpretation": {"ko_supportability": "complete", "ohko_result": "guaranteed", "primary_ko_label": "guaranteed_ohko"}}
    target = {"item_authority": {"status": "known", "value": "focus-sash"}, "hp_authority": {"status": "known", "current_hp": 100, "maximum_hp": 100}}
    action = {"move_metadata": {"min_hits": 1, "max_hits": 1}}
    result = _apply_focus_sash_survival(damage, target, action, {"status": "complete"})
    assert result["ko_interpretation"]["primary_ko_label"] == "no_ko_within_supported_horizon"
    assert result["ko_interpretation"]["focus_sash_survival"] == "applied"
    assert _apply_focus_sash_survival(damage, target, {"move_metadata": {"min_hits": None, "max_hits": None}}, {"status": "complete"})["ko_interpretation"]["focus_sash_survival"] == "applied"
    assert _apply_focus_sash_survival(damage, target, {"move_metadata": {"min_hits": 2, "max_hits": 2}}, {"status": "complete"})["ko_interpretation"]["primary_ko_label"] == "guaranteed_ohko"
    assert _apply_focus_sash_survival(damage, {**target, "hp_authority": {**target["hp_authority"], "current_hp": 99}}, action, {"status": "complete"})["ko_interpretation"]["primary_ko_label"] == "guaranteed_ohko"
    assert _apply_focus_sash_survival(damage, target, action, {"status": "incomplete"})["ko_interpretation"]["primary_ko_label"] == "guaranteed_ohko"


def test_exact_sturdy_readiness_refines_only_matching_single_hit_guaranteed_ohko():
    from llm.advisor_switch_incoming_evaluator import _apply_sturdy_survival
    damage = {"status": "known", "ko_interpretation": {"ko_supportability": "complete", "ohko_result": "guaranteed", "primary_ko_label": "guaranteed_ohko"}}
    action = _opponent()
    effect = {"sturdy_result": {"status": "complete", "outcome": "survival_ready", "opponent_identity": {"side": "opponent", "slot_index": 0, "pokemon_id": "x"}}}
    result = _apply_sturdy_survival(damage, {}, action, effect)
    assert result["ko_interpretation"]["primary_ko_label"] == "no_ko_within_supported_horizon"
    assert result["ko_interpretation"]["sturdy_survival"] == "applied"
    assert _apply_sturdy_survival(damage, {}, action, {"sturdy_result": {**effect["sturdy_result"], "outcome": "ability_suppressed"}})["ko_interpretation"]["primary_ko_label"] == "guaranteed_ohko"
    assert _apply_sturdy_survival(damage, {}, action, {"sturdy_result": {**effect["sturdy_result"], "opponent_identity": {"side": "opponent", "slot_index": 1, "pokemon_id": "other"}}})["ko_interpretation"]["primary_ko_label"] == "guaranteed_ohko"
    action["move_metadata"]["min_hits"] = 2
    assert _apply_sturdy_survival(damage, {}, action, effect)["ko_interpretation"]["primary_ko_label"] == "guaranteed_ohko"


def test_frozen_transition_carries_identity_bound_sturdy_authority_to_entry_evaluation():
    from llm.advisor_switch_entry_effects import evaluate_switch_entry_effects
    state = _state()
    state["switch_hazard_context"] = build_switch_hazard_context(session_id="incoming-s", affected_side="self", stealth_rock="absent", spikes_layers=0)
    state["switch_entry_sturdy_authority"] = build_switch_entry_sturdy_authority(session_id="incoming-s", source={"side": "self", "slot_index": 1, "pokemon_id": "b"}, target={"side": "opponent", "slot_index": 0, "pokemon_id": "x"}, applicability="applicable")
    records = deepcopy(build_self_roster_mechanics_context_projection(state)["entries"])
    records[1].update({"current_type_authority": {"status": "known", "value": ["water"]}, "base_stat_authority": {"status": "known", "value": _stats(200)}, "final_stat_authority": {"status": "known", "value": _stats(200)}, "ability_authority": {"status": "known", "value": "sturdy"}, "item_authority": {"status": "known", "value": None}, "hp_authority": {"status": "known", "current_hp": 200, "maximum_hp": 200, "provenance": "user_confirmed_current_hp"}})
    snapshot = _snapshot(state, build_self_roster_mechanics_context_projection(state, roster_mechanics_records=records))
    transition = project_authorized_switch_transition(turn_snapshot=snapshot, switch_candidate=build_switch_candidates(turn_snapshot=snapshot)[0], switch_authorized=True, opponent_action=_opponent())
    post = transition["post_switch_snapshot"]
    result = evaluate_switch_entry_effects(hazards=post["switch_hazard_context"], target=post["target_roster_mechanics"], sturdy_authority=post["switch_entry_sturdy_authority"])
    assert result["sturdy_result"]["outcome"] == "survival_ready"


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


def test_direct_adapter_replaces_only_exact_opposing_attack_stage_after_intimidate():
    from llm.advisor_switch_incoming_evaluator import _adapt_opponent_candidate
    action = _opponent()
    action["mechanics_snapshot"]["battle_context"]["current_state"]["stat_stage_context"] = {"current_stages": [{"side": "opponent", "stat": "attack", "stage": 3, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}]}
    target = {"session_id": "incoming-s", "slot_index": 1, "pokemon_id": "b"}
    effect = {"intimidate_result": {"status": "complete", "opponent_identity": {"side": "opponent", "slot_index": 0, "pokemon_id": "x"}, "attack_stage_after": -1}}
    current = _adapt_opponent_candidate(action, target, entry_effect_result=effect)["mechanics_snapshot"]["battle_context"]["current_state"]
    assert current["stat_stage_context"]["current_stages"] == [{"side": "opponent", "stat": "attack", "stage": -1, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}]
    stale = {"intimidate_result": {"status": "complete", "opponent_identity": {"side": "opponent", "slot_index": 1, "pokemon_id": "other"}, "attack_stage_after": -1}}
    unchanged = _adapt_opponent_candidate(action, target, entry_effect_result=stale)["mechanics_snapshot"]["battle_context"]["current_state"]
    assert unchanged["stat_stage_context"]["current_stages"][0]["stage"] == 3


def test_frozen_transition_carries_b_to_exact_opponent_intimidate_authority_before_direct_incoming():
    from llm.advisor_switch_entry_effects import evaluate_switch_entry_effects
    state = _state()
    state["switch_hazard_context"] = build_switch_hazard_context(session_id="incoming-s", affected_side="self", stealth_rock="absent", spikes_layers=0)
    state["switch_entry_intimidate_authority"] = build_switch_entry_intimidate_authority(session_id="incoming-s", source={"side": "self", "slot_index": 1, "pokemon_id": "b"}, target={"side": "opponent", "slot_index": 0, "pokemon_id": "x"}, interaction="lowered", target_attack_stage=0)
    records = deepcopy(build_self_roster_mechanics_context_projection(state)["entries"])
    records[1]["ability_authority"] = {"status": "known", "value": "intimidate"}
    records[1]["item_authority"] = {"status": "known", "value": None}
    roster = build_self_roster_mechanics_context_projection(state, roster_mechanics_records=records)
    snapshot = _snapshot(state, roster); candidate = build_switch_candidates(turn_snapshot=snapshot)[0]
    transition = project_authorized_switch_transition(turn_snapshot=snapshot, switch_candidate=candidate, switch_authorized=True, opponent_action=_opponent())
    post = transition["post_switch_snapshot"]
    effect = evaluate_switch_entry_effects(hazards=post["switch_hazard_context"], target=post["target_roster_mechanics"], intimidate_authority=post["switch_entry_intimidate_authority"])
    assert effect["intimidate_result"]["attack_stage_after"] == -1
    result = evaluate_switch_incoming_opponent_action(transition=transition, entry_hazard_result=effect)
    assert result["entry_hazard_result"]["intimidate_result"]["attack_stage_after"] == -1
