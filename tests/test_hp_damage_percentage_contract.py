from __future__ import annotations

from llm.advisor_battle_state_context import build_hp_ko_assessment


def _damage() -> dict[str, object]:
    return {"attacker_side": "self", "defender_side": "opponent", "move": "tackle", "level": 50, "power": 80, "offensive_stat": 200, "defensive_stat": 150, "calculation_status": "resolved"}


def test_damage_percentage_is_calculated_from_integer_rolls_and_maximum_hp() -> None:
    result = build_hp_ko_assessment(_damage(), {"current_hp": [{"side": "opponent", "current_hp": 90, "maximum_hp": 300, "status": "user_confirmed", "source": "user_confirmed_current_hp"}]})
    assert result is not None
    assert (result["min_damage"], result["max_damage"], result["min_percent"], result["max_percent"]) == (40, 48, 13.3, 16.0)
    assert result["percentage_scope"] == "base_damage_stage_only"
