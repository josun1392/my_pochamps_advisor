from llm.advisor_battle_state_context import resolve_registered_dynamic_move


def test_missing_context_is_unavailable_without_metadata_override():
    result = resolve_registered_dynamic_move({"move_id": "eruption"}, limited_context_enabled=True)
    assert result["assessment_payload"]["status"] == "unavailable"
    assert "effective_power_override" not in result
