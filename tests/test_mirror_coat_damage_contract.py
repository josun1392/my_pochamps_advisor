from llm.advisor_battle_state_context import build_observed_damage_counter_assessment
from llm.advisor_client import normalize_observed_previous_damage_confirmation


def _observed(category):
    return normalize_observed_previous_damage_confirmation({"damage": 60, "damage_category": category, "damage_kind": "direct_move_damage", "source_side": "opponent", "target_side": "self"})


def test_mirror_coat_returns_double_special_damage():
    assert build_observed_damage_counter_assessment({"move_id": "mirror-coat"}, _observed("special"), None)["returned_damage"] == 120


def test_mirror_coat_physical_no_effect_and_dark_immunity():
    no_effect = build_observed_damage_counter_assessment({"move_id": "mirror-coat"}, _observed("physical"), None)
    immune = build_observed_damage_counter_assessment({"move_id": "mirror-coat"}, _observed("special"), None, {"opponent_active": {"types": ["dark"]}})
    assert no_effect["reason"] == "previous_damage_not_special" and immune["reason"] == "type_immunity"
