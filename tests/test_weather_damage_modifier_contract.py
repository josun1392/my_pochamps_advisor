from llm.advisor_battle_state_context import build_context_modified_damage_estimate


def test_rain_boosts_water_and_reduces_fire() -> None:
    field = {"current_field": {"weather": "rain", "side_effects": []}}
    common = {"calculation_status": "resolved", "damage_class": "special", "level": 50, "power": 80, "offensive_stat": 200, "defensive_stat": 150, "damage_rolls": [100] * 16}
    assert build_context_modified_damage_estimate({**common, "move_type": "water"}, None, field)["damage_rolls"] == [150] * 16
    assert build_context_modified_damage_estimate({**common, "move_type": "fire"}, None, field)["damage_rolls"] == [50] * 16
