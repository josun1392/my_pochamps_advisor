from __future__ import annotations

import pytest

from llm.advisor_battle_state_context import build_hp_ko_assessment


def _damage() -> dict[str, object]: return {"attacker_side": "self", "defender_side": "opponent", "move": "tackle", "level": 50, "power": 80, "offensive_stat": 200, "defensive_stat": 150, "calculation_status": "resolved"}
def _hp(current: int) -> dict[str, object]: return {"current_hp": [{"side": "opponent", "current_hp": current, "maximum_hp": 300, "status": "user_confirmed", "source": "user_confirmed_current_hp"}]}


@pytest.mark.parametrize(("current", "ohko", "two"), [(40, "guaranteed", "guaranteed"), (45, "possible", "guaranteed"), (90, "impossible", "possible"), (97, "impossible", "impossible")])
def test_ohko_and_within_two_hits_use_16_and_256_independent_rolls(current: int, ohko: str, two: str) -> None:
    result = build_hp_ko_assessment(_damage(), _hp(current)); assert result is not None
    assert result["ohko"]["status"] == ohko and result["ohko"]["total_rolls"] == 16
    assert result["two_hit_ko"]["status"] == two and result["two_hit_ko"]["total_combinations"] == 256
    assert result["two_hit_ko"]["scope"] == "two-hit-independent-rolls-no-between-turn-effects"


def test_zero_current_hp_keeps_percentage_but_makes_ko_assessment_not_applicable() -> None:
    result = build_hp_ko_assessment(_damage(), _hp(0)); assert result is not None
    assert result["current_hp"] == 0 and result["assessment_status"] == "not_applicable"
    assert result["reason"] == "target_already_fainted"
    assert result["min_percent"] == 13.3 and result["max_percent"] == 16.0
    assert "ohko" not in result and "two_hit_ko" not in result
