from copy import deepcopy

from llm.advisor_candidate_contract import prepare_ui_recommendation_cycle


def _battle():
    return {"pokemon": {"my_active": {"name_en": "pikachu"}, "opponent_active": {"name_en": "eevee"}}, "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]}, "current_hp_context": {"current_hp": [{"side": "self", "current_hp": 50, "maximum_hp": 100}]}}


def test_preparation_detaches_mutable_battle_and_repository_inputs():
    battle = _battle(); repository = {"tackle": {"category": "physical", "power": 40, "type": "normal"}}
    cycle = prepare_ui_recommendation_cycle(selected_moves=[{"move_id": "tackle"}], battle_input=battle, move_repository=repository)
    frozen = deepcopy(cycle["recommendation_request"])
    battle["pokemon"]["my_active"]["name_en"] = "mew"; battle["moves"]["my_available_moves"][0]["move_id"] = "missing"; repository["tackle"]["power"] = 1
    assert cycle["recommendation_request"] == frozen
    assert frozen["candidate_exact_set"] == [{"slot_index": 0, "move": "tackle"}]
