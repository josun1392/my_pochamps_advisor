import inspect

import llm.advisor_candidate_contract as contract
from llm.advisor_client import run_ui_selected_advice


def _stat(side, stat, value):
    return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}


def _input():
    return {"scenario": {"mode": "advisor", "known_limitations": ["known"]}, "pokemon": {"my_active": {"name_en": "a"}, "opponent_active": {"name_en": "b"}}, "final_stat_context": {"current_final_stats": [_stat("self", "attack", 200), _stat("opponent", "defense", 150), _stat("self", "special-attack", 200), _stat("opponent", "special-defense", 150), _stat("self", "speed", 200), _stat("opponent", "speed", 100)]}, "moves": {"my_selected_move_index": 2}}


def test_ui_prepare_builds_ready_existing_deterministic_cycle_with_exact_slots():
    repository = {"tackle": {"category": "physical", "power": 40, "type": "normal"}}
    cycle = contract.prepare_ui_recommendation_cycle(selected_moves=[{"move_id": "tackle"}, None, {"move_id": "tackle"}], battle_input=_input(), move_repository=repository)
    assert cycle["status"] == "ready"
    assert cycle["recommendation_request"]["candidate_exact_set"] == [{"slot_index": 0, "move": "tackle"}, {"slot_index": 2, "move": "tackle"}]
    assert "move_repository" not in cycle and "provider" not in cycle


def test_existing_selected_move_provider_path_does_not_call_offline_adapter():
    assert "prepare_ui_recommendation_cycle" not in inspect.getsource(run_ui_selected_advice)
