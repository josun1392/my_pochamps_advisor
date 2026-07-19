import pytest
from llm.advisor_battle_state_context import build_environment_based_move_assessment
@pytest.mark.parametrize("weather,type_,power",[("none","normal",50),("sun","fire",100),("rain","water",100),("sandstorm","rock",100),("snow","ice",100)])
def test_weather_mapping(weather,type_,power):
 r=build_environment_based_move_assessment({"move_id":"weather-ball"},{"current_field":{"weather":weather}})
 assert (r["effective_type"],r["effective_power"])==(type_,power)
