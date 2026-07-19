import pytest

from core.move_repository import MoveView
from llm.advisor_battle_state_context import build_direct_healing_assessment


def test_move_view_exposes_metadata_healing() -> None:
    assert MoveView("recover", "Recover", None, "normal", "status", None, None, 10, healing=50).healing == 50


def test_missing_healing_has_no_result() -> None:
    assert build_direct_healing_assessment({"move_id": "recover"}, None) is None


def test_zero_healing_has_no_result() -> None:
    assert build_direct_healing_assessment({"move_id": "recover", "healing": 0}, None) is None


@pytest.mark.parametrize("healing", [-1, 101, True, 50.0, "50"])
def test_invalid_healing_metadata_is_rejected(healing: object) -> None:
    result = build_direct_healing_assessment({"move_id": "recover", "healing": healing}, None)
    assert result == {"move": "recover", "scope": "direct-max-hp-proportional-healing-only", "status": "unavailable", "reason": "invalid_healing_metadata"}


@pytest.mark.parametrize("move", ["synthesis", "morning-sun", "moonlight", "shore-up", "rest", "strength-sap", "pain-split", "wish", "aqua-ring", "ingrain", "floral-healing", "life-dew", "jungle-healing"])
def test_unsupported_direct_healing_moves_are_unavailable(move: str) -> None:
    result = build_direct_healing_assessment({"move_id": move, "healing": 50}, {"current_hp": [{"side": "self", "current_hp": 50, "maximum_hp": 100}]})
    assert result["status"] == "unavailable"
    assert result["reason"] == "unsupported_direct_healing_rule"
