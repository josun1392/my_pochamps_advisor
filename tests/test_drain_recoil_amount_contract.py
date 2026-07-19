from llm.advisor_battle_state_context import build_drain_recoil_assessment


def _hp(self_hp=None):
    entries = [{"side": "opponent", "current_hp": 70, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp"}]
    if self_hp is not None: entries.append({"side": "self", "current_hp": self_hp, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp"})
    return {"current_hp": entries}


def test_drain_uses_actual_damage_and_hp_cap() -> None:
    result = build_drain_recoil_assessment({"calculation_status": "resolved", "damage_rolls": [60, 120] * 8}, {"move_id": "giga-drain", "drain": 50}, _hp(80))
    assert result["actual_damage_range"] == {"minimum": 60, "maximum": 70}
    assert result["effect_amount_range"] == {"minimum": 30, "maximum": 35}
    assert result["actual_restored_hp_range"] == {"minimum": 20, "maximum": 20}
