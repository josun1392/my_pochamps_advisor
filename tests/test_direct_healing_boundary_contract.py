import pytest

from llm.advisor_battle_state_context import build_direct_healing_assessment
from llm.advisor_client import _build_ui_selected_prompt


def _move() -> dict[str, object]: return {"move_id": "recover", "healing": 50}
def _hp(entry: dict[str, object]) -> dict[str, object]: return {"current_hp": [{"side": "self", **entry}]}


def test_fainted_user_is_not_applicable() -> None:
    result = build_direct_healing_assessment(_move(), _hp({"current_hp": 0, "maximum_hp": 100}))
    assert result["status"] == "not_applicable" and result["reason"] == "user_already_fainted"
    assert "actual_healing" not in result and "resulting_hp" not in result


@pytest.mark.parametrize("entry", [{"current_hp": 101, "maximum_hp": 100}, {"current_hp": -1, "maximum_hp": 100}, {"current_hp": 1, "maximum_hp": 0}, {"current_hp": True, "maximum_hp": 100}, {"current_hp": 1, "maximum_hp": True}, {"current_hp": "1", "maximum_hp": 100}])
def test_invalid_hp_context_is_rejected(entry: dict[str, object]) -> None:
    assert build_direct_healing_assessment(_move(), _hp(entry))["reason"] == "invalid_attacker_hp_context"


def test_missing_current_hp_is_unavailable() -> None:
    assert build_direct_healing_assessment(_move(), _hp({"maximum_hp": 100}))["reason"] == "missing_attacker_current_hp"


def test_missing_maximum_hp_is_unavailable() -> None:
    assert build_direct_healing_assessment(_move(), _hp({"current_hp": 50}))["reason"] == "missing_attacker_maximum_hp"


def test_gate_off_omits_direct_healing_from_prompt() -> None:
    battle_input = {"moves": {"my_selected_move": _move()}, "current_hp_confirmations": [{"side": "self", "current_hp": 50, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp"}]}
    assert "direct_healing_assessment" not in _build_ui_selected_prompt(battle_input, enable_battle_state_context=False)


def test_gate_on_produces_direct_healing_context_from_ui_payload() -> None:
    battle_input = {"moves": {"my_selected_move": _move()}, "current_hp_confirmations": [{"side": "self", "current_hp": 50, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp"}]}
    assert "direct_healing_assessment" in _build_ui_selected_prompt(battle_input, enable_battle_state_context=True)
