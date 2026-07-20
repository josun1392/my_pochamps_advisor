import pytest
from llm.advisor_candidate_contract import build_recommendation_request, evaluate_move_candidate, serialize_recommendation_request, validate_recommendation_selection


def _stat(side, stat, value): return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}
def _snapshot(**extra):
    result={"final_stat_context":{"current_final_stats":[_stat("self","attack",200),_stat("opponent","defense",150),_stat("self","special-attack",200),_stat("opponent","special-defense",150),_stat("self","speed",200),_stat("opponent","speed",100)]}}
    result.update(extra); return result


@pytest.mark.parametrize(("move", "metadata", "snapshot", "family", "key", "power", "type_"), [
    ("eruption", {"category":"special","power":150,"type":"fire"}, _snapshot(current_hp_context={"current_hp":[{"side":"self","current_hp":100,"maximum_hp":100}]}), "current_hp_based_power", "current_hp_based_power_assessment", 150, None),
    ("electro-ball", {"category":"special","power":1,"type":"electric"}, _snapshot(), "speed_based_power", "speed_based_power_assessment", 80, None),
    ("heavy-slam", {"category":"physical","power":1,"type":"steel"}, _snapshot(weight_context={"self_weight":1000,"opponent_weight":100}), "weight_based_power", "weight_based_power_assessment", 120, None),
    ("stored-power", {"category":"special","power":20,"type":"psychic"}, _snapshot(stat_stage_context={"current_stages":[{"side":"self","stat":"attack","stage":2,"status":"user_confirmed","source":"user_confirmed_current_stat_stage","confidence":"known"}]}), "stat_stage_based_power", "stat_stage_based_power_assessment", 60, None),
    ("crush-grip", {"category":"physical","power":120,"type":"normal"}, _snapshot(current_hp_context={"current_hp":[{"side":"opponent","current_hp":100,"maximum_hp":100}]}), "target_hp_based_power", "target_hp_based_power_assessment", 121, None),
    ("weather-ball", {"category":"special","power":50,"type":"normal"}, _snapshot(field_state_context={"current_field":{"weather":"rain"}}), "environment_based_move", "environment_based_move_assessment", 100, "water"),
    ("facade", {"category":"physical","power":70,"type":"normal"}, _snapshot(condition_context={"current_conditions":[{"side":"self","condition_type":"burn"}]}), "binary_condition_power", "binary_condition_power_assessment", 140, None),
    ("avalanche", {"category":"physical","power":60,"type":"ice"}, _snapshot(turn_event_context={"received_target_direct_damage":True}), "turn_event_power", "turn_event_power_assessment", 120, None),
    ("rage-fist", {"category":"physical","power":50,"type":"ghost"}, _snapshot(battle_counter_context={"rage_fist_hits_received":1}), "battle_counter_power", "battle_counter_power_assessment", 100, None),
    ("fury-cutter", {"category":"physical","power":40,"type":"bug"}, _snapshot(consecutive_use_context={"fury_cutter_consecutive_uses":2}), "consecutive_use_power", "consecutive_use_power_assessment", 80, None),
])
def test_ten_family_candidates_copy_production_dynamic_results(move, metadata, snapshot, family, key, power, type_):
    candidate=evaluate_move_candidate(slot_index=0, move=move, battle_snapshot=snapshot, repositories={move:metadata})
    assert candidate["dynamic_move"] == {"family":family,"assessment_key":key,"status":"resolved","effective_power":power,"effective_type":type_}
    assert candidate["damage"]["status"] in {"resolved", "unavailable"}
    if candidate["damage"]["status"] == "unavailable": assert "minimum" not in candidate["damage"] and "maximum" not in candidate["damage"]


@pytest.mark.parametrize(("move", "metadata"), [("eruption",{"category":"special","power":150,"type":"fire"}), ("electro-ball",{"category":"special","power":1,"type":"electric"}), ("heavy-slam",{"category":"physical","power":1,"type":"steel"}), ("stored-power",{"category":"special","power":20,"type":"psychic"}), ("crush-grip",{"category":"physical","power":120,"type":"normal"}), ("weather-ball",{"category":"special","power":50,"type":"normal"}), ("facade",{"category":"physical","power":70,"type":"normal"}), ("avalanche",{"category":"physical","power":60,"type":"ice"}), ("rage-fist",{"category":"physical","power":50,"type":"ghost"}), ("fury-cutter",{"category":"physical","power":40,"type":"bug"})])
def test_ten_family_missing_context_never_uses_metadata_damage(move, metadata):
    candidate=evaluate_move_candidate(slot_index=0, move=move, battle_snapshot={}, repositories={move:metadata})
    assert candidate["dynamic_move"]["status"] == "unavailable"
    assert candidate["dynamic_move"]["effective_power"] is None and candidate["dynamic_move"]["effective_type"] is None
    assert candidate["damage"]["status"] != "resolved"
    assert candidate["status"] in {"partial","unavailable"} and candidate["unavailable_reasons"]


def test_v143_partial_functions_remain_importable():
    assert all(callable(value) for value in (build_recommendation_request, validate_recommendation_selection, serialize_recommendation_request))
