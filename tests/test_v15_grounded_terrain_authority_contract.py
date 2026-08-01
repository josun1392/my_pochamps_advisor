from llm.advisor_direct_mechanics import _modifier_context


def _current(terrain, self_status, opponent_status):
    return {"field_state_context": {"current_field": {"weather": "none", "terrain": terrain, "side_effects": []}}, "grounded_context": {"self": {"status": self_status, "provenance": "user_confirmed_current" if self_status != "unknown" else "unknown"}, "opponent": {"status": opponent_status, "provenance": "user_confirmed_current" if opponent_status != "unknown" else "unknown"}}}


def test_electric_and_misty_require_only_the_relevant_explicit_side():
    electric = _modifier_context(current=_current("electric", "known_grounded", "unknown"), direct={}, category="special", move_type="electric")
    assert electric["applied"] == ["terrain_electric_boost"] and electric["attacker_grounded"] is True
    misty = _modifier_context(current=_current("misty", "unknown", "known_ungrounded"), direct={}, category="special", move_type="dragon")
    assert misty["applied"] == [] and misty["defender_grounded"] is False


def test_unknown_or_malformed_grounded_authority_fails_closed_only_when_relevant():
    unknown = _modifier_context(current=_current("grassy", "unknown", "unknown"), direct={}, category="special", move_type="grass")
    assert unknown["missing_inputs"] == ["self.grounded"]
    unrelated = _modifier_context(current=_current("electric", "unknown", "unknown"), direct={}, category="special", move_type="normal")
    assert unrelated["missing_inputs"] == []
    malformed = _current("psychic", "known_grounded", "unknown")
    malformed["grounded_context"]["self"]["provenance"] = "unknown"
    assert _modifier_context(current=malformed, direct={}, category="special", move_type="psychic")["unsupported_reason"] == "grounded_context"
