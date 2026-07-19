from llm.advisor_battle_state_context import build_direct_healing_assessment


def _hp(current: int, maximum: int) -> dict[str, object]:
    return {"current_hp": [{"side": "self", "current_hp": current, "maximum_hp": maximum}]}


def test_fifty_percent_uses_maximum_hp() -> None:
    result = build_direct_healing_assessment({"move_id": "recover", "healing": 50}, _hp(100, 300))
    assert result["raw_healing"] == result["actual_healing"] == 150


def test_odd_maximum_hp_uses_floor() -> None:
    assert build_direct_healing_assessment({"move_id": "recover", "healing": 50}, _hp(1, 301))["raw_healing"] == 150


def test_healing_is_capped_by_missing_hp() -> None:
    result = build_direct_healing_assessment({"move_id": "recover", "healing": 50}, _hp(221, 301))
    assert result["actual_healing"] == 80
    assert result["resulting_hp"] == 301


def test_full_hp_is_no_effect() -> None:
    result = build_direct_healing_assessment({"move_id": "recover", "healing": 50}, _hp(100, 100))
    assert result["status"] == "no_effect"
    assert result["reason"] == "already_at_full_hp"
    assert result["actual_healing"] == 0 and result["resulting_hp"] == 100


def test_actual_healing_never_exceeds_missing_hp() -> None:
    result = build_direct_healing_assessment({"move_id": "recover", "healing": 100}, _hp(99, 100))
    assert result["actual_healing"] <= result["maximum_hp"] - result["current_hp"]
