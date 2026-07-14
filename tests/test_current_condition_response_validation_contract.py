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
