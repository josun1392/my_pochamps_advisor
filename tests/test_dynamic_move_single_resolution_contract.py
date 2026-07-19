from llm.advisor_battle_state_context import resolve_registered_dynamic_move


def test_each_registered_move_selects_only_its_family():
    result = resolve_registered_dynamic_move({"move_id": "fury-cutter"}, limited_context_enabled=True, consecutive_use_context={"fury_cutter_consecutive_uses": 2})
    assert result["assessment_key"] == "consecutive_use_power_assessment"


def test_gate_off_omits_resolution():
    assert resolve_registered_dynamic_move({"move_id": "fury-cutter"}, limited_context_enabled=False, consecutive_use_context={"fury_cutter_consecutive_uses": 2}) is None
