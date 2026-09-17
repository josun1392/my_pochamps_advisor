from llm.advisor_battle_state_context import build_direct_healing_assessment
from advisor.canonical_direct_heal_move_family import plain_half_max_hp_self_heal_amount
from llm.advisor_detached_direct_heal_materializer import materialize_detached_direct_heal


def _hp(current: int, maximum: int) -> dict[str, object]:
    return {"current_hp": [{"side": "self", "current_hp": current, "maximum_hp": maximum}]}


def test_fifty_percent_uses_maximum_hp() -> None:
    result = build_direct_healing_assessment({"move_id": "recover", "healing": 50}, _hp(100, 300))
    assert result["raw_healing"] == result["actual_healing"] == 150


def _detached(current: int, maximum: int) -> dict[str, object]:
    return materialize_detached_direct_heal(execution_authority={
        "status": "resolved", "session_id": "s", "source_runtime_fingerprint": "runtime",
        "source_branch_fingerprint": "branch", "decision_owner": {"side": "self"},
        "actor": {"side": "self"}, "action_id": "recover", "move_id": "recover",
        "current_hp": current, "max_hp": maximum, "fainted": current == 0,
        "canonical_effect": {"effect": {"consequence_family": "plain_half_max_hp_self_heal"}},
    })


def test_odd_maximum_hp_uses_half_up_across_context_and_detached_owners() -> None:
    legacy = build_direct_healing_assessment({"move_id": "recover", "healing": 50}, _hp(1, 301))
    detached = _detached(1, 301)
    assert plain_half_max_hp_self_heal_amount(301) == legacy["raw_healing"] == detached["heal"]["nominal_heal"] == 151
    assert legacy["actual_healing"] == detached["heal"]["actual_heal"] == 151


def test_even_and_small_maximum_half_heal_use_canonical_half_up_amount() -> None:
    assert plain_half_max_hp_self_heal_amount(300) == 150
    assert plain_half_max_hp_self_heal_amount(1) == 1
    assert build_direct_healing_assessment({"move_id": "slack-off", "healing": 50}, _hp(1, 300))["raw_healing"] == 150
    assert _detached(0, 1)["status"] == "not_applicable"


def test_plain_direct_heal_family_moves_share_half_up_context_rule() -> None:
    for move_id in ("recover", "slack-off", "soft-boiled"):
        assert build_direct_healing_assessment({"move_id": move_id, "healing": 50}, _hp(1, 301))["raw_healing"] == 151


def test_healing_is_capped_by_missing_hp() -> None:
    result = build_direct_healing_assessment({"move_id": "recover", "healing": 50}, _hp(250, 301))
    assert result["raw_healing"] == 151 and result["actual_healing"] == 51
    assert result["resulting_hp"] == 301


def test_full_hp_is_no_effect() -> None:
    result = build_direct_healing_assessment({"move_id": "recover", "healing": 50}, _hp(100, 100))
    assert result["status"] == "no_effect"
    assert result["reason"] == "already_at_full_hp"
    assert result["actual_healing"] == 0 and result["resulting_hp"] == 100


def test_actual_healing_never_exceeds_missing_hp() -> None:
    result = build_direct_healing_assessment({"move_id": "recover", "healing": 100}, _hp(99, 100))
    assert result["actual_healing"] <= result["maximum_hp"] - result["current_hp"]
