from llm.advisor_battle_state_context import resolve_registered_dynamic_move


def test_power_and_environment_type_overrides_are_distinct():
    power = resolve_registered_dynamic_move({"move_id": "fury-cutter"}, limited_context_enabled=True, consecutive_use_context={"fury_cutter_consecutive_uses": 2})
    environment = resolve_registered_dynamic_move({"move_id": "weather-ball"}, limited_context_enabled=True, field_state_context={"current_field": {"weather": "rain"}})
    assert power["effective_power_override"] == 80 and "effective_type_override" not in power
    assert environment["effective_power_override"] == 100 and environment["effective_type_override"] == "water"
