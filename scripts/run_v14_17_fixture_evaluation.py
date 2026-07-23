"""v14.17 suspended CLI with a single, narrowly approved one-shot entry point."""
from __future__ import annotations

import argparse
import json

from llm.structured_fixture_evaluation import (
    AUTHORIZED_ACTUAL_FIXTURE_IDS,
    _CLEAR_RESOLVED_PREDECESSOR,
    execute_single_authorized_fixture,
    prepare_single_authorized_fixture,
    suspended_fixture_report,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", action="append", choices=AUTHORIZED_ACTUAL_FIXTURE_IDS)
    parser.add_argument("--actual-provider-approved", action="store_true")
    parser.add_argument("--budget", type=int)
    parser.add_argument("--execute-t1-clear-resolved-once", action="store_true")
    parser.add_argument("--execute-t1-insufficient-context-once", action="store_true")
    return parser.parse_args(argv)


def _terminal_report(result):
    keys = ("fixture_id", "preparation_status", "provider_eligible", "provider_invoked", "actual_call_count", "completion_status", "presentation_status", "recommended_move", "recommended_slot_index", "failure_codes", "remaining_call_budget")
    report = {key: result.get(key) for key in keys if key in result}
    completion = result.get("completion_status")
    report["schema_validation"] = completion not in {"provider_response_validation_failed", "provider_unavailable", "timeout_uncertain"}
    report["semantic_validation"] = completion == "insufficient_context"
    report["fixture_evaluation"] = completion == "insufficient_context"
    report["resolved_recommendation_present"] = result.get("recommended_move") is not None
    report["invalid_claim_present"] = "invalid_claim" in result.get("failure_codes", [])
    return report


def run_t1_clear_resolved_once(*, provider_factory, model: str) -> dict:
    preflight = prepare_single_authorized_fixture(fixture_id="clear_resolved", completed_fixture_ids=())
    if not preflight["provider_eligible"]:
        return {**preflight, "provider_invoked": False, "actual_call_count": 0, "completion_status": "preparation_blocked"}
    return execute_single_authorized_fixture(
        fixture_id="clear_resolved", completed_fixture_ids=(), actual_provider_approved=True,
        provider_evaluation_state="ACTIVE", provider_factory=provider_factory, model=model,
    )


def run_t1_insufficient_context_once(*, provider_factory, model: str) -> dict:
    """Run only the T1-approved final fixture after fixed predecessor proof."""
    preflight = prepare_single_authorized_fixture(
        fixture_id="insufficient_context",
        completed_fixture_ids=("clear_resolved",),
        predecessor_evidence=_CLEAR_RESOLVED_PREDECESSOR,
    )
    if not preflight["provider_eligible"]:
        return {**preflight, "provider_invoked": False, "actual_call_count": 0, "completion_status": "preparation_blocked"}
    return execute_single_authorized_fixture(
        fixture_id="insufficient_context", completed_fixture_ids=("clear_resolved",),
        predecessor_evidence=_CLEAR_RESOLVED_PREDECESSOR, actual_provider_approved=True,
        provider_evaluation_state="ACTIVE", provider_factory=provider_factory, model=model,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.fixture is not None and len(args.fixture) != 1:
        print(json.dumps({"status": "multiple_fixtures_rejected", "actual_call_count": 0}, ensure_ascii=True))
        return 2
    if args.budget is not None:
        print(json.dumps({"status": "budget_override_rejected", "actual_call_count": 0}, ensure_ascii=True))
        return 2
    if args.execute_t1_clear_resolved_once:
        print(json.dumps({"status": "fixture_already_consumed", "actual_call_count": 0}, ensure_ascii=True))
        return 2
    if args.execute_t1_insufficient_context_once:
        if args.fixture is not None or args.actual_provider_approved:
            print(json.dumps({"status": "one_shot_argument_rejected", "actual_call_count": 0}, ensure_ascii=True))
            return 2
        preflight = prepare_single_authorized_fixture(
            fixture_id="insufficient_context", completed_fixture_ids=("clear_resolved",),
            predecessor_evidence=_CLEAR_RESOLVED_PREDECESSOR,
        )
        if not preflight["provider_eligible"]:
            print(json.dumps({**preflight, "status": "preparation_blocked", "actual_call_count": 0}, ensure_ascii=True, sort_keys=True))
            return 0
        from llm.advisor_client import call_structured_recommendation_provider
        from scripts.spike_advisor import DEFAULT_MODEL
        result = run_t1_insufficient_context_once(
            provider_factory=lambda: call_structured_recommendation_provider, model=DEFAULT_MODEL,
        )
        print(json.dumps(_terminal_report(result), ensure_ascii=True, sort_keys=True))
        return 0
    if args.actual_provider_approved:
        print(json.dumps({"status": "provider_evaluation_suspended", "actual_call_count": 0}, ensure_ascii=True))
        return 2
    fixture_id = args.fixture[0] if args.fixture else None
    print(json.dumps(suspended_fixture_report(fixture_id=fixture_id), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
