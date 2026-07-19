import pytest
from llm.advisor_battle_state_context import build_environment_based_move_assessment
@pytest.mark.parametrize("terrain,type_",[("electric","electric"),("grassy","grass"),("misty","fairy"),("psychic","psychic")])
def test_grounded_terrain_mapping(terrain,type_): assert build_environment_based_move_assessment({"move_id":"terrain-pulse"},{"current_field":{"terrain":terrain}},True)["effective_type"]==type_
def test_missing_grounded_is_unavailable(): assert build_environment_based_move_assessment({"move_id":"terrain-pulse"},{"current_field":{"terrain":"electric"}})["reason"]=="missing_grounded_state"
