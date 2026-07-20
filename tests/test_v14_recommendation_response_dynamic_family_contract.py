from copy import deepcopy

import pytest

from llm.advisor_candidate_contract import build_recommendation_request, evaluate_move_candidate, parse_recommendation_response


def _stat(side, stat, value):
    return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}


def _snapshot(**extra):
    snapshot = {"final_stat_context": {"current_final_stats": [_stat("self", "attack", 200), _stat("opponent", "defense", 150), _stat("self", "special-attack", 200), _stat("opponent", "special-defense", 150), _stat("self", "speed", 200), _stat("opponent", "speed", 100)]}}
    snapshot.update(extra); return snapshot


@pytest.mark.parametrize(("move", "metadata", "snapshot"), [
    ("eruption", {"category": "special", "power": 150, "type": "fire"}, _snapshot(current_hp_context={"current_hp": [{"side": "self", "current_hp": 100, "maximum_hp": 100}]})),
    ("electro-ball", {"category": "special", "power": 1, "type": "electric"}, _snapshot()),
    ("heavy-slam", {"category": "physical", "power": 1, "type": "steel"}, _snapshot(weight_context={"self_weight": 1000, "opponent_weight": 100})),
    ("stored-power", {"category": "special", "power": 20, "type": "psychic"}, _snapshot(stat_stage_context={"current_stages": [{"side": "self", "stat": "attack", "stage": 2, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}]})),
    ("crush-grip", {"category": "physical", "power": 120, "type": "normal"}, _snapshot(current_hp_context={"current_hp": [{"side": "opponent", "current_hp": 100, "maximum_hp": 100}]})),
    ("weather-ball", {"category": "special", "power": 50, "type": "normal"}, _snapshot(field_state_context={"current_field": {"weather": "rain"}})),
    ("facade", {"category": "physical", "power": 70, "type": "normal"}, _snapshot(condition_context={"current_conditions": [{"side": "self", "condition_type": "burn"}]})),
    ("avalanche", {"category": "physical", "power": 60, "type": "ice"}, _snapshot(turn_event_context={"received_target_direct_damage": True})),
    ("rage-fist", {"category": "physical", "power": 50, "type": "ghost"}, _snapshot(battle_counter_context={"rage_fist_hits_received": 1})),
    ("fury-cutter", {"category": "physical", "power": 40, "type": "bug"}, _snapshot(consecutive_use_context={"fury_cutter_consecutive_uses": 2})),
])
def test_actual_ten_family_candidate_summaries_support_exact_dynamic_claims(move, metadata, snapshot):
    candidate = evaluate_move_candidate(slot_index=0, move=move, battle_snapshot=snapshot, repositories={move: metadata})
    request = build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": [candidate], "known_limitations": []})
    before = deepcopy(request)
    payload = {"recommendation_status": "resolved", "recommended_move": move, "recommended_slot_index": 0, "primary_reasons": [{"kind": "dynamic_mechanic", "claim": "emitted_dynamic_summary"}], "risks": [], "alternatives": []}
    assert parse_recommendation_response(request=request, response_payload=payload)["status"] == "resolved"
    assert request == before
