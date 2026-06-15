from __future__ import annotations

from llm.advisor_turn_order_context import (
    TURN_ORDER_CONTEXT_ORDER_HINT_VALUES,
    TURN_ORDER_CONTEXT_PRIORITY_RELATION_VALUES,
    TURN_ORDER_CONTEXT_SPEED_RELATION_VALUES,
    build_deterministic_turn_order_context,
)


def test_base_speed_own_faster_context_is_limited_and_non_resolved() -> None:
    context = build_deterministic_turn_order_context(
        own_move_priority=0,
        opponent_move_priority=0,
        own_base_speed=100,
        opponent_base_speed=80,
    )

    assert context["kind"] == "deterministic_turn_order_context"
    assert context["confidence"] == "limited"
    assert context["priority"]["priority_relation"] == "same_priority"
    assert context["speed"]["basis"] == "base_species_stats_only"
    assert context["speed"]["speed_relation"] == "own_faster_by_base_speed"
    assert context["speed"]["final_speed_known"] is False
    assert context["order_hint"] == "own_likely_before_opponent_if_same_priority"
    assert context["tie_or_unknown"] is False
    _assert_no_forbidden_fields(context)


def test_base_speed_opponent_faster_context() -> None:
    context = build_deterministic_turn_order_context(
        own_move_priority=0,
        opponent_move_priority=0,
        own_base_speed=60,
        opponent_base_speed=95,
    )

    assert context["speed"]["speed_relation"] == "opponent_faster_by_base_speed"
    assert context["order_hint"] == "opponent_likely_before_own_if_same_priority"
    assert context["tie_or_unknown"] is False


def test_equal_base_speed_is_tie_candidate_not_resolved() -> None:
    context = build_deterministic_turn_order_context(
        own_move_priority=0,
        opponent_move_priority=0,
        own_base_speed=90,
        opponent_base_speed=90,
    )

    assert context["speed"]["speed_relation"] == "equal_base_speed_tie_candidate"
    assert context["order_hint"] == "tie_or_unknown"
    assert context["tie_or_unknown"] is True
    _assert_required_unsupported_boundaries(context)


def test_confirmed_final_speed_overrides_base_speed_relation() -> None:
    context = build_deterministic_turn_order_context(
        own_move_priority=0,
        opponent_move_priority=0,
        own_base_speed=100,
        opponent_base_speed=80,
        own_confirmed_final_speed=90,
        opponent_confirmed_final_speed=120,
    )

    assert context["speed"]["basis"] == "confirmed_final_speed"
    assert context["speed"]["speed_relation"] == "opponent_faster_by_confirmed_final_speed"
    assert context["speed"]["final_speed_known"] is True
    assert context["order_hint"] == "opponent_likely_before_own_if_same_priority"


def test_known_different_priority_uses_priority_relation_without_final_order() -> None:
    context = build_deterministic_turn_order_context(
        own_move_priority=1,
        opponent_move_priority=0,
        own_base_speed=40,
        opponent_base_speed=120,
    )

    assert context["priority"]["priority_relation"] == "own_higher_priority"
    assert context["order_hint"] == "priority_overrides_speed"
    assert "final_order_resolved" not in context
    _assert_no_forbidden_fields(context)


def test_unknown_priority_keeps_order_hint_unknown() -> None:
    context = build_deterministic_turn_order_context(
        own_move_priority=0,
        opponent_move_priority=None,
        own_base_speed=100,
        opponent_base_speed=80,
    )

    assert context["priority"]["opponent_move_priority"] == "unknown"
    assert context["priority"]["priority_relation"] == "unknown"
    assert context["order_hint"] == "unknown"
    assert context["tie_or_unknown"] is True


def test_missing_speed_data_sets_unknown_confidence_when_priority_unknown() -> None:
    context = build_deterministic_turn_order_context(
        own_move_priority=None,
        opponent_move_priority=None,
        own_base_speed=None,
        opponent_base_speed=None,
    )

    assert context["confidence"] == "unknown"
    assert context["speed"]["basis"] == "unknown"
    assert context["speed"]["speed_relation"] == "unknown_due_to_missing_speed_data"
    assert context["order_hint"] == "unknown"
    assert context["tie_or_unknown"] is True


def test_quick_claw_candidate_modifier_is_never_resolved() -> None:
    context = build_deterministic_turn_order_context(
        own_move_priority=0,
        opponent_move_priority=0,
        own_base_speed=50,
        opponent_base_speed=80,
        candidate_modifiers=[
            {
                "source": "Quick Claw",
                "effect": "may alter move order",
                "resolved": True,
                "activated": True,
            }
        ],
    )

    assert context["candidate_modifiers"] == [
        {
            "source": "Quick Claw",
            "effect": "may alter move order",
            "resolved": False,
        }
    ]
    _assert_no_forbidden_fields(context)


def test_context_values_stay_within_v7_2_contract_allowed_values() -> None:
    context = build_deterministic_turn_order_context(
        own_move_priority=0,
        opponent_move_priority=0,
        own_base_speed=100,
        opponent_base_speed=80,
    )

    assert context["priority"]["priority_relation"] in TURN_ORDER_CONTEXT_PRIORITY_RELATION_VALUES
    assert context["speed"]["speed_relation"] in TURN_ORDER_CONTEXT_SPEED_RELATION_VALUES
    assert context["order_hint"] in TURN_ORDER_CONTEXT_ORDER_HINT_VALUES


def test_context_includes_required_unsupported_boundaries() -> None:
    context = build_deterministic_turn_order_context(
        own_move_priority=0,
        opponent_move_priority=0,
        own_base_speed=100,
        opponent_base_speed=80,
    )

    _assert_required_unsupported_boundaries(context)


def _assert_required_unsupported_boundaries(context: dict) -> None:
    assert "speed tie resolution" in context["unsupported"]
    assert "RNG item activation" in context["unsupported"]
    assert "exact final order" in context["unsupported"]
    assert "item consumption" in context["unsupported"]
    assert "post-turn HP update" in context["unsupported"]


def _assert_no_forbidden_fields(value: object) -> None:
    forbidden = {
        "final_order_resolved",
        "item_consumed",
        "post_turn_hp",
        "speed_tie_resolved",
        "rng_item_activated",
        "activated",
    }
    if isinstance(value, dict):
        for key, child_value in value.items():
            assert key not in forbidden
            _assert_no_forbidden_fields(child_value)
    elif isinstance(value, list):
        for child_value in value:
            _assert_no_forbidden_fields(child_value)
