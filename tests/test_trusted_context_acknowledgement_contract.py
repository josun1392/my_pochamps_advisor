from __future__ import annotations

import pytest

import llm.advisor_client as advisor_client


EXPECTED = (
    ("current_condition", "self", "burn", None),
    ("current_condition", "opponent", "unknown", None),
    ("observed_item_event", "opponent", "focus-sash", "item_activation_observed"),
)


def _response(lines: str, advice: str = "Choose a cautious action without claiming an exact outcome.") -> str:
    return f"[Trusted Context]\n{lines}\n\n[Advice]\n{advice}"


def test_canonical_and_minor_format_variants_validate_exactly() -> None:
    canonical = _response(
        "- Current condition | self | burn\n"
        "- Current condition | opponent | unknown\n"
        "- Observed item event | opponent | focus-sash | item_activation_observed"
    )
    variation = _response(
        "- current condition | self | burn\n"
        "- Current Condition | opponent | unknown\n"
        "- Observed Item Event | opponent | Focus Sash | item_activation_observed"
    )

    assert advisor_client.validate_trusted_context_acknowledgement(canonical, EXPECTED) is None
    assert advisor_client.validate_trusted_context_acknowledgement(variation, EXPECTED) is None


@pytest.mark.parametrize(
    ("response", "category"),
    [
        ("[Advice]\nAdvice only.", "acknowledgement missing"),
        (_response("- Current condition | self | burn\n- Current condition | opponent | unknown"), "entry mismatch"),
        (_response("- Current condition | self | burn\n- Current condition | opponent | unknown\n- Observed item event | opponent | focus-sash | item_activation_observed\n- Current condition | opponent | paralysis"), "entry mismatch"),
        (_response("- Current condition | self | burn\n- Current condition | opponent | unknown\n- Observed item event | opponent | focus-sash | item_activation_observed\n- Current condition | self | burn"), "duplicate"),
        (_response("- Current condition | opponent | burn\n- Current condition | self | unknown\n- Observed item event | opponent | focus-sash | item_activation_observed"), "entry mismatch"),
        (_response("- Observed item event | self | burn | item_activation_observed\n- Current condition | opponent | unknown\n- Current condition | opponent | focus-sash"), "entry mismatch"),
        (_response("- Current condition | self | burn\n- Current condition | opponent | paralysis\n- Observed item event | opponent | focus-sash | item_activation_observed"), "entry mismatch"),
        (_response("- Current condition | self | burn\n- Current condition | opponent | unknown\n- Observed item event | opponent | focus-sash"), "malformed"),
        (_response("- Current condition / self / burn"), "malformed"),
        (_response("- Current condition | self | burn\n- Current condition | opponent | unknown\n- Observed item event | opponent | focus-sash | item_activation_observed", advice=""), "advice body missing"),
    ],
)
def test_missing_extra_duplicate_swapped_and_malformed_entries_fail(response: str, category: str) -> None:
    failure = advisor_client.validate_trusted_context_acknowledgement(response, EXPECTED)
    assert failure is not None
    assert category in failure


def test_none_condition_remains_exact_identity() -> None:
    expected = (("current_condition", "self", "none", None),)
    good = _response("- Current condition | self | none")
    bad = _response("- Current condition | self | removed")

    assert advisor_client.validate_trusted_context_acknowledgement(good, expected) is None
    assert advisor_client.validate_trusted_context_acknowledgement(bad, expected) == "trusted-context entry mismatch"


def test_empty_expected_context_rejects_a_structured_extra_entry() -> None:
    response = _response(
        "- Current condition | self | burn",
        advice="Choose a cautious action without claiming an exact outcome.",
    )

    assert advisor_client.validate_trusted_context_acknowledgement(response, ()) == "trusted-context entry mismatch"
