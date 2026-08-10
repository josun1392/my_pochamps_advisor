from copy import deepcopy

from llm.advisor_combined_action_selection import select_combined_self_action


def _action(kind, identifier, tier, *, selectable=True, rank=None):
    result = {
        "action_candidate_id": identifier,
        "action_kind": kind,
        "selectable": selectable,
        "cross_action_danger_tier": tier,
    }
    if rank is not None:
        result["native_move_rank"] = rank
    return result


def test_no_selectable_switch_preserves_existing_move_native_order():
    result = select_combined_self_action(
        move_actions=[_action("move", "self-move:s:m1", "neutral_no_positive_danger", rank=2), _action("move", "self-move:s:m2", "neutral_no_positive_danger", rank=1)],
        switch_actions=[_action("switch", "self-switch:s:b", "neutral_no_positive_danger", selectable=False)],
    )
    assert result["selected_candidate_id"] == "self-move:s:m2"
    assert result["selection_reason"] == "move_native_rank"


def test_lower_proven_danger_wins_before_move_native_rank():
    result = select_combined_self_action(
        move_actions=[_action("move", "self-move:s:ko", "executed_guaranteed_self_ko", rank=0)],
        switch_actions=[_action("switch", "self-switch:s:b", "neutral_no_positive_danger")],
    )
    assert result["selected_candidate_id"] == "self-switch:s:b"


def test_same_danger_cross_kind_prefers_move_without_probability_or_damage_fields():
    move = _action("move", "self-move:s:m", "possible_self_ko_exposure", rank=99)
    switch = _action("switch", "self-switch:s:b", "possible_self_ko_exposure")
    result = select_combined_self_action(move_actions=[move], switch_actions=[switch])
    assert result["selected_candidate_id"] == move["action_candidate_id"]
    assert result["selection_reason"] == "same_tier_move_preference"


def test_selectability_precedes_danger_and_never_changes_candidate_input():
    switch = _action("switch", "self-switch:s:b", "neutral_no_positive_danger", selectable=False)
    original = deepcopy(switch)
    result = select_combined_self_action(
        move_actions=[_action("move", "self-move:s:m", "executed_guaranteed_self_ko")], switch_actions=[switch]
    )
    assert result["selected_candidate_id"] == "self-move:s:m"
    assert switch == original
    selectable_switch = _action("switch", "self-switch:s:c", "neutral_no_positive_danger")
    result = select_combined_self_action(
        move_actions=[_action("move", "self-move:s:m", "executed_guaranteed_self_ko", selectable=False)], switch_actions=[selectable_switch]
    )
    assert result["selected_candidate_id"] == selectable_switch["action_candidate_id"]


def test_same_tier_switches_stay_strategically_unresolved():
    result = select_combined_self_action(
        move_actions=[_action("move", "self-move:s:m", "executed_guaranteed_self_ko")],
        switch_actions=[_action("switch", "self-switch:s:b", "neutral_no_positive_danger"), _action("switch", "self-switch:s:c", "neutral_no_positive_danger")],
    )
    assert result["selected_action_kind"] == "switch"
    assert result["selected_candidate_id"] is None
    assert result["selection_supportability"] == "unresolved_equal_switches"
    assert result["tied_candidate_ids"] == ["self-switch:s:b", "self-switch:s:c"]


def test_malformed_switch_cannot_outrank_valid_move_and_result_is_detached():
    actions = [_action("move", "self-move:s:m", "neutral_no_positive_danger")]
    malformed = [{"action_candidate_id": "self-switch:s:b", "action_kind": "switch", "selectable": True, "cross_action_danger_tier": "safe"}]
    result = select_combined_self_action(move_actions=actions, switch_actions=malformed)
    assert result["selected_candidate_id"] == "self-move:s:m"
    assert result["malformed_candidate_ids"] == ["self-switch:s:b"]
    result["malformed_candidate_ids"].append("mutated")
    assert actions[0]["action_candidate_id"] == "self-move:s:m"
