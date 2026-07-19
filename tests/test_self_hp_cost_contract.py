import pytest
from llm.advisor_battle_state_context import build_self_consequence_assessment


def _hp(current=80, maximum=160): return {"current_hp": [{"side": "self", "current_hp": current, "maximum_hp": maximum}]}


@pytest.mark.parametrize("move", ["steel-beam", "mind-blown", "chloroblast"])
def test_maximum_hp_half_cost_is_supported(move):
    result = build_self_consequence_assessment({"move_id": move}, _hp())
    assert (result["self_damage"], result["self_resulting_hp"], result["self_faint_status"]) == (80, 0, "guaranteed_self_faint")


def test_odd_maximum_hp_floors_and_can_leave_user_alive():
    result = build_self_consequence_assessment({"move_id": "steel-beam"}, _hp(100, 161))
    assert (result["self_damage"], result["self_resulting_hp"], result["self_faint_status"]) == (80, 20, "no_self_faint")


@pytest.mark.parametrize("hp,reason", [(None, "missing_self_current_hp"), ({"current_hp": 80}, "missing_self_maximum_hp"), ({"current_hp": 90, "maximum_hp": 80}, "invalid_self_hp_context")])
def test_hp_cost_requires_valid_trusted_self_hp(hp, reason):
    context = None if hp is None else {"current_hp": [{"side": "self", **hp}]}
    assert build_self_consequence_assessment({"move_id": "steel-beam"}, context)["reason"] == reason


def test_fainted_user_and_struggle_are_not_resolved():
    assert build_self_consequence_assessment({"move_id": "steel-beam"}, _hp(0, 100))["reason"] == "user_already_fainted"
    assert build_self_consequence_assessment({"move_id": "struggle"}, _hp())["reason"] == "unsupported_self_damage_rule"
