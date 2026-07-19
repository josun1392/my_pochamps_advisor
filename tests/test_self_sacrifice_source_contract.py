import pytest
from llm.advisor_battle_state_context import build_self_consequence_assessment


@pytest.mark.parametrize("move", ["explosion", "self-destruct", "misty-explosion", "memento", "healing-wish", "lunar-dance"])
def test_explicit_sacrifice_moves_guarantee_user_faint(move):
    result = build_self_consequence_assessment({"move_id": move}, None)
    assert result["status"] == "resolved" and result["self_resulting_hp"] == 0 and result["self_faint_status"] == "guaranteed_self_faint"


def test_non_allowlisted_move_has_no_self_consequence():
    assert build_self_consequence_assessment({"move_id": "tackle"}, None) is None
