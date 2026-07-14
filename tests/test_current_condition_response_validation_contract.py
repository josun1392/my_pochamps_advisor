from __future__ import annotations

import re

import pytest


_FORBIDDEN_OUTCOME_CLAIMS = (
    "exact status damage",
    "post-turn hp is",
    "sleep turns remaining",
    "wake-up turn",
    "freeze thaw roll",
    "full paralysis occurred",
    "rng roll",
    "final speed order",
    "resolved condition effect",
    "post-turn condition state",
)


def _evaluate_burn_unknown_response(response: str) -> set[str]:
    """Small fixture-specific evaluator; it is not a generic response parser."""
    text = response.lower()
    failures: set[str] = set()

    if not re.search(r"self[^.]{0,80}\bburn\b[^.]{0,80}user-confirmed[^.]{0,80}current", text):
        failures.add("self_burn_readback_missing_or_mixed")
    if not re.search(r"opponent[^.]{0,80}\bunknown\b", text):
        failures.add("opponent_unknown_readback_missing")
    if re.search(r"opponent[^.]{0,80}\bburn\b", text):
        failures.add("side_mixing")
    if re.search(
        r"opponent[^.]{0,80}\b(paralysis|paralyzed|poison|poisoned|toxic|sleep|asleep|freeze|frozen)\b",
        text,
    ):
        failures.add("unknown_inference")
    if "burn was applied this turn" in text:
        failures.add("application_event_promotion")
    if "burn damage triggered this turn" in text:
        failures.add("trigger_or_resolved_promotion")
    if any(claim in text for claim in _FORBIDDEN_OUTCOME_CLAIMS):
        failures.add("unsupported_outcome_claim")
    return failures


def _evaluate_none_response(response: str) -> set[str]:
    text = response.lower()
    failures: set[str] = set()
    if "self has no current major status" not in text or "user-confirmed" not in text:
        failures.add("none_readback_missing")
    if "condition removal" in text or "was cured" in text:
        failures.add("none_misinterpreted_as_event")
    return failures


def _evaluate_condition_item_event_attribution(response: str) -> set[str]:
    """Fixture-specific attribution contract, not a general language parser."""
    text = response.lower()
    failures = _evaluate_burn_unknown_response(response)
    if not re.search(r"self[^.]{0,100}\bburn\b[^.]{0,100}(current|present-state)", text):
        failures.add("condition_category_missing")
    if not re.search(r"opponent[^.]{0,100}\bunknown\b[^.]{0,100}(current|condition)|opponent[^.]{0,100}(current|condition)[^.]{0,100}\bunknown\b", text):
        failures.add("unknown_current_category_missing")
    if not re.search(r"focus sash[^.]{0,100}(observed|observation|item event)[^.]{0,100}(activation|activated)|focus sash[^.]{0,100}(activation|activated)[^.]{0,100}(observed|observation|item event)", text):
        failures.add("observed_item_event_category_missing")
    if "focus sash activation is the opponent's current condition" in text:
        failures.add("item_event_promoted_to_current_state")
    if "burn was an observed event this turn" in text:
        failures.add("condition_promoted_to_observed_event")
    if "focus sash" in text and "exactly 1 hp" in text:
        failures.add("observed_event_resolved_promotion")
    if "all are confirmed context" in text:
        failures.add("generic_source_collapse")
    return failures


def test_synthetic_good_response_keeps_current_condition_boundary() -> None:
    response = (
        "Self has burn as a user-confirmed current condition. The opponent's "
        "current condition is unknown. The burn application timing and exact "
        "damage are unknown; this does not establish post-turn HP, RNG, or final order."
    )

    assert _evaluate_burn_unknown_response(response) == set()


@pytest.mark.parametrize(
    ("response", "expected_failure"),
    [
        (
            "Opponent has burn as a user-confirmed current condition; their condition is unknown.",
            "self_burn_readback_missing_or_mixed",
        ),
        (
            "Self has burn as a user-confirmed current condition. The opponent is likely paralyzed.",
            "unknown_inference",
        ),
        (
            "Self has burn as a user-confirmed current condition. Opponent condition is unknown. Burn was applied this turn.",
            "application_event_promotion",
        ),
        (
            "Self has burn as a user-confirmed current condition. Opponent condition is unknown. Burn damage triggered this turn.",
            "trigger_or_resolved_promotion",
        ),
        (
            "Self has burn as a user-confirmed current condition. Opponent condition is unknown. The exact status damage is 12.",
            "unsupported_outcome_claim",
        ),
        (
            "Self has burn as a user-confirmed current condition. Opponent condition is unknown. The final speed order is known.",
            "unsupported_outcome_claim",
        ),
        (
            "Use the strongest move because its damage range is favorable.",
            "self_burn_readback_missing_or_mixed",
        ),
    ],
)
def test_synthetic_bad_responses_fail_fixture_specific_boundary(
    response: str,
    expected_failure: str,
) -> None:
    assert expected_failure in _evaluate_burn_unknown_response(response)


def test_synthetic_none_response_is_present_state_not_a_removal_event() -> None:
    good_response = "Self has no current major status as user-confirmed present-state context."
    bad_response = "Self has no current major status because the condition removal was confirmed."

    assert _evaluate_none_response(good_response) == set()
    assert "none_misinterpreted_as_event" in _evaluate_none_response(bad_response)


def test_synthetic_attribution_pass_allows_compact_natural_readback() -> None:
    response = (
        "Self has burn as a user-confirmed current condition, while the opponent's current "
        "major condition is unknown. Separately, the opponent's Focus Sash activation is a "
        "user-confirmed observed item event. Neither context resolves exact HP, damage, or order."
    )

    assert _evaluate_condition_item_event_attribution(response) == set()


@pytest.mark.parametrize(
    ("response", "expected_failure"),
    [
        ("Self burn, opponent unknown, and Focus Sash activation are confirmed context.", "condition_category_missing"),
        ("Self has burn as a user-confirmed current condition. Opponent condition is unknown. Focus Sash activation is the opponent's current condition.", "item_event_promoted_to_current_state"),
        ("Self burn was an observed event this turn. Opponent condition is unknown. Focus Sash activation was observed.", "condition_promoted_to_observed_event"),
        ("Use the strongest move because damage is favorable.", "condition_category_missing"),
        ("Opponent has burn as a user-confirmed current condition. Focus Sash activation was observed.", "self_burn_readback_missing_or_mixed"),
        ("Self has burn as a user-confirmed current condition. Opponent condition is likely paralyzed. Focus Sash activation was observed.", "unknown_inference"),
        ("Self has burn as a user-confirmed current condition. Opponent condition is unknown. Focus Sash activation was observed and left the Pokemon at exactly 1 HP.", "observed_event_resolved_promotion"),
        ("Self has burn as a user-confirmed current condition. Opponent condition is unknown. Focus Sash activation was observed. Burn was applied this turn.", "application_event_promotion"),
        ("Self has burn as a user-confirmed current condition. Opponent condition is unknown.", "observed_item_event_category_missing"),
        ("Self has burn as a user-confirmed current condition. Opponent condition is unknown. Focus Sash activation was observed. All are confirmed context.", "generic_source_collapse"),
    ],
)
def test_synthetic_attribution_failures_remain_distinct(
    response: str,
    expected_failure: str,
) -> None:
    assert expected_failure in _evaluate_condition_item_event_attribution(response)
