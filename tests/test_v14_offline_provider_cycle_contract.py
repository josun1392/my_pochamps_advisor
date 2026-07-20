from copy import deepcopy
import inspect

from llm.advisor_candidate_contract import run_offline_recommendation_cycle
from llm.advisor_client import run_ui_selected_advice


def _stat(side, stat, value):
    return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}


def _battle_input():
    return {"scenario": {"mode": "advisor"}, "pokemon": {"my_active": {"name_en": "a"}, "opponent_active": {"name_en": "b"}}, "final_stat_context": {"current_final_stats": [_stat("self", "attack", 200), _stat("opponent", "defense", 150), _stat("self", "special-attack", 200), _stat("opponent", "special-defense", 150), _stat("self", "speed", 200), _stat("opponent", "speed", 100)]}}


def _response():
    return {"recommendation_status": "resolved", "recommended_move": "tackle", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": []}


def test_valid_offline_cycle_orders_preparation_provider_and_completion_without_aliases():
    moves = [{"move_id": "tackle"}, {"move_id": "tackle"}]
    battle = _battle_input(); repository = {"tackle": {"category": "physical", "power": 40, "type": "normal"}}
    observed = []
    def fake_provider(payload):
        observed.append(deepcopy(payload)); return _response()
    result = run_offline_recommendation_cycle(selected_moves=moves, battle_input=battle, move_repository=repository, fake_provider=fake_provider)
    moves[0]["move_id"] = "changed"; battle["pokemon"]["my_active"]["name_en"] = "changed"
    assert result["status"] == "resolved" and result["completed_cycle"]["recommendation_result"]["recommended_move"] == "tackle"
    assert [row["slot_index"] for row in result["prepared_cycle"]["candidates"]] == [0, 1]
    assert set(observed[0]) == {"request_version", "battle_snapshot_summary", "candidate_exact_set", "selectable_candidate_exact_set", "candidate_comparisons", "known_limitations", "guardrails"}
    assert "move_repository" not in result and "fake_provider" not in result


def test_legacy_selected_move_runtime_remains_separate_from_new_cycle():
    assert "run_offline_recommendation_cycle" not in inspect.getsource(run_ui_selected_advice)
