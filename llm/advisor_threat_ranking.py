"""Application-owned categorical threat tier projection; no score or probability."""
from __future__ import annotations

from typing import Any, Mapping

_TIERS = {
    "executed_guaranteed_ohko": 0,
    "unresolved_guaranteed_ohko_exposure": 1,
    "executed_possible_ohko": 2,
    "neutral_no_positive_threat_evidence": 3,
    "complete_set_no_guaranteed_ohko": 4,
    "complete_set_all_actions_preempted": 5,
}

_REQUIRED_SUMMARY_FIELDS = {
    "known_guaranteed_ohko_capability_exists",
    "known_executed_guaranteed_ohko_threat_exists",
    "known_executed_possible_ohko_threat_exists",
    "candidate_set_complete",
    "known_candidate_count",
    "unknown_slots_remaining",
    "known_threat_evaluation_complete",
    "global_threat_complete",
    "all_known_actions_preempted",
    "no_known_guaranteed_ohko",
}

def project_threat_ranking_tier(summary: Mapping[str, Any] | None) -> tuple[str, int]:
    if summary is None:
        return "neutral_no_positive_threat_evidence", _TIERS["neutral_no_positive_threat_evidence"]
    if not isinstance(summary, Mapping) or not _REQUIRED_SUMMARY_FIELDS <= set(summary):
        raise ValueError("malformed_threat_summary")
    if summary["known_executed_guaranteed_ohko_threat_exists"] is True:
        return "executed_guaranteed_ohko", _TIERS["executed_guaranteed_ohko"]
    if summary["known_guaranteed_ohko_capability_exists"] is True:
        return "unresolved_guaranteed_ohko_exposure", _TIERS["unresolved_guaranteed_ohko_exposure"]
    if summary["known_executed_possible_ohko_threat_exists"] is True:
        return "executed_possible_ohko", _TIERS["executed_possible_ohko"]

    complete = (
        summary["candidate_set_complete"] is True
        and summary["known_candidate_count"] == 4
        and summary["unknown_slots_remaining"] == 0
        and summary["known_threat_evaluation_complete"] is True
        and summary["global_threat_complete"] is True
    )
    if complete and summary["all_known_actions_preempted"] == "true":
        return "complete_set_all_actions_preempted", _TIERS["complete_set_all_actions_preempted"]
    if complete and summary["no_known_guaranteed_ohko"] == "true":
        return "complete_set_no_guaranteed_ohko", _TIERS["complete_set_no_guaranteed_ohko"]
    return "neutral_no_positive_threat_evidence", _TIERS["neutral_no_positive_threat_evidence"]
