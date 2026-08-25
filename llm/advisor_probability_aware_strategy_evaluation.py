"""Conservative own-action probability tie-breaks over detached evidence.

The existing guaranteed-fact comparator remains primary.  Exact probability is
consulted only after it returns a genuine tie, and only for fully comparable
evaluable attack candidates.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping, Sequence

from llm.advisor_guaranteed_fact_comparison import compare_guaranteed_candidates


SCHEMA_VERSION = "own-action-probability-aware-strategy-evaluation-v1"
HORIZON = "immediate_action_consequence"


def compare_own_action_probability_aware_candidates(*, left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    """Compare one pair without reading mutable state or assigning utility."""
    facts_left, facts_right = _facts(left), _facts(right)
    if facts_left is None or facts_right is None:
        return _result("incomplete", "guaranteed_facts_unavailable")
    guaranteed = compare_guaranteed_candidates(candidate_a=facts_left, candidate_b=facts_right)
    if guaranteed.get("status") != "resolved":
        return _result(guaranteed.get("status", "rejected"), guaranteed.get("reason", "guaranteed_comparison_unavailable"), guaranteed=guaranteed)
    if guaranteed.get("comparison") == "preferred":
        preferred = "left" if guaranteed.get("preferred_candidate") == "a" else "right"
        return _result("resolved", guaranteed["reason"], comparison=f"{preferred}_preferred", preference_source="guaranteed_facts", guaranteed=guaranteed)
    if guaranteed.get("comparison") != "tied_on_supported_facts":
        return _result("rejected", "invalid_guaranteed_comparison_result", guaranteed=guaranteed)

    eligibility = _eligibility(left, right)
    if eligibility["status"] == "rejected":
        return _result("rejected", eligibility["reason"], guaranteed=guaranteed)
    if eligibility["status"] != "eligible":
        return _result("resolved", "probability_tie_break_not_applicable", comparison="tied", preference_source="stable_guaranteed_tie", guaranteed=guaranteed, probability_policy=eligibility)

    left_ko, right_ko = eligibility["left_ko"], eligibility["right_ko"]
    if left_ko != right_ko:
        preferred = "left" if left_ko > right_ko else "right"
        return _result("resolved", "higher_exact_target_ko_probability", comparison=f"{preferred}_preferred", preference_source="target_ko_probability", guaranteed=guaranteed, probability_policy=_policy(eligibility))
    left_faint, right_faint = eligibility["left_faint"], eligibility["right_faint"]
    if left_faint != right_faint:
        preferred = "left" if left_faint < right_faint else "right"
        return _result("resolved", "lower_exact_self_faint_probability", comparison=f"{preferred}_preferred", preference_source="self_faint_probability", guaranteed=guaranteed, probability_policy=_policy(eligibility))
    return _result("resolved", "exact_probability_metrics_tie", comparison="tied", preference_source="stable_guaranteed_tie", guaranteed=guaranteed, probability_policy=_policy(eligibility))


def rank_own_action_probability_aware_candidates(*, candidates: Sequence[Mapping[str, Any]], opponent_response_profiles: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Use the existing frontier shape with only the approved pairwise wrapper."""
    ids = [row.get("candidate_id") if isinstance(row, Mapping) else None for row in candidates]
    if len(candidates) < 2 or not all(isinstance(value, str) and value for value in ids) or len(set(ids)) != len(ids):
        return _result("rejected", "invalid_candidate_set")
    dominated: set[str] = set(); matrix = []; incomplete = False
    for index, left in enumerate(candidates):
        for right in candidates[index + 1:]:
            comparison = compare_own_action_probability_aware_candidates(left=left, right=right)
            if _exact_stable_attack_tie(comparison):
                from llm.advisor_opponent_response_pareto_evaluation import (
                    compare_opponent_response_wise_pareto_candidates,
                )
                comparison = compare_opponent_response_wise_pareto_candidates(
                    left=_with_response_profile(left, opponent_response_profiles),
                    right=_with_response_profile(right, opponent_response_profiles),
                )
            comparison = {
                **comparison,
                "left_candidate_id": left["candidate_id"],
                "right_candidate_id": right["candidate_id"],
            }
            matrix.append(comparison)
            if comparison.get("status") != "resolved":
                incomplete = True
            elif comparison.get("comparison") == "left_preferred":
                dominated.add(right["candidate_id"])
            elif comparison.get("comparison") == "right_preferred":
                dominated.add(left["candidate_id"])
    return {"status": "incomplete_comparison_set" if incomplete else "resolved", "schema_version": SCHEMA_VERSION, "preferred_frontier": sorted(set(ids) - dominated), "pairwise_matrix": tuple(matrix), "provenance": "guaranteed_primary_exact_probability_tie_break_v1"}


def _facts(record: Any) -> Mapping[str, Any] | None:
    value = record.get("guaranteed_facts") if isinstance(record, Mapping) else None
    return value if isinstance(value, Mapping) else None


def _exact_stable_attack_tie(comparison: Mapping[str, Any]) -> bool:
    return comparison.get("status") == "resolved" and comparison.get("comparison") == "tied" and comparison.get("reason") == "exact_probability_metrics_tie" and comparison.get("preference_source") == "stable_guaranteed_tie"


def _with_response_profile(record: Mapping[str, Any], profiles: Mapping[str, Mapping[str, Any]] | None) -> dict[str, Any]:
    result = deepcopy(dict(record))
    candidate_id = result.get("candidate_id")
    if isinstance(profiles, Mapping) and isinstance(candidate_id, str) and isinstance(profiles.get(candidate_id), Mapping):
        result["opponent_response_profile"] = deepcopy(dict(profiles[candidate_id]))
    return result


def _eligibility(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    first, second = _candidate(left), _candidate(right)
    if first["status"] == "rejected" or second["status"] == "rejected":
        return {"status": "rejected", "reason": first.get("reason") if first["status"] == "rejected" else second["reason"]}
    if first["status"] != "eligible" or second["status"] != "eligible":
        return {"status": "not_applicable", "reason": first.get("reason") if first["status"] != "eligible" else second.get("reason")}
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target")
    if any(first["bindings"].get(key) != second["bindings"].get(key) for key in keys):
        return {"status": "rejected", "reason": "probability_comparison_basis_mismatch"}
    return {"status": "eligible", "left_ko": first["ko"], "right_ko": second["ko"], "left_faint": first["faint"], "right_faint": second["faint"], "bindings": deepcopy(dict(first["bindings"]))}


def _candidate(record: Any) -> dict[str, Any]:
    if not isinstance(record, Mapping) or record.get("action_type") != "attack" or not isinstance(record.get("candidate_id"), str):
        return {"status": "not_applicable", "reason": "probability_policy_attack_pair_required"}
    facts, ledger, metrics = record.get("guaranteed_facts"), record.get("exact_outcome_ledger"), record.get("descriptive_metrics")
    if not isinstance(facts, Mapping) or facts.get("candidate_id") != record["candidate_id"]:
        return {"status": "rejected", "reason": "candidate_guaranteed_fact_binding_invalid"}
    if not isinstance(ledger, Mapping) or ledger.get("status") in {"incomplete", "unsupported"}:
        return {"status": "not_applicable", "reason": "exact_outcome_ledger_not_evaluable"}
    if ledger.get("status") == "rejected":
        return {"status": "rejected", "reason": ledger.get("reason", "exact_outcome_ledger_rejected")}
    if ledger.get("status") != "evaluable" or ledger.get("schema_version") != "exact-predictive-outcome-ledger-v1" or ledger.get("horizon") != HORIZON:
        return {"status": "rejected", "reason": "invalid_evaluable_exact_outcome_ledger"}
    if _fraction(ledger.get("terminal_probability_mass")) != Fraction(1, 1):
        return {"status": "rejected", "reason": "exact_outcome_ledger_mass_not_one"}
    if not isinstance(metrics, Mapping) or metrics.get("status") in {"incomplete", "unsupported"}:
        return {"status": "not_applicable", "reason": "descriptive_metrics_not_resolved"}
    if metrics.get("status") == "rejected":
        return {"status": "rejected", "reason": metrics.get("reason", "descriptive_metrics_rejected")}
    if metrics.get("status") != "resolved" or metrics.get("schema_version") != "exact-outcome-descriptive-metrics-v1" or metrics.get("source_ledger_status") != "evaluable" or metrics.get("horizon") != HORIZON or metrics.get("candidate_id") != record["candidate_id"]:
        return {"status": "rejected", "reason": "invalid_resolved_descriptive_metrics"}
    bindings = ledger.get("bindings")
    if not isinstance(bindings, Mapping) or metrics.get("bindings") != bindings or ledger.get("candidate_id") != record["candidate_id"] or ledger.get("action_type") != "attack" or metrics.get("action_type") != "attack" or metrics.get("terminal_probability_mass") != ledger.get("terminal_probability_mass"):
        return {"status": "rejected", "reason": "ledger_metrics_binding_mismatch"}
    target, own = metrics.get("target"), metrics.get("own")
    if not isinstance(target, Mapping) or target.get("status") != "resolved" or not isinstance(own, Mapping) or own.get("status") != "resolved":
        return {"status": "not_applicable", "reason": "ko_or_self_faint_metric_not_applicable"}
    ko, survival, faint = _fraction(target.get("ko_probability")), _fraction(target.get("survival_probability")), _fraction(own.get("self_faint_probability"))
    if ko is None or survival is None or faint is None or ko + survival != 1:
        return {"status": "rejected", "reason": "exact_probability_metric_invalid"}
    return {"status": "eligible", "bindings": bindings, "ko": ko, "faint": faint}


def _policy(value: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": "eligible", "left_target_ko_probability": _fraction_dict(value["left_ko"]), "right_target_ko_probability": _fraction_dict(value["right_ko"]), "left_self_faint_probability": _fraction_dict(value["left_faint"]), "right_self_faint_probability": _fraction_dict(value["right_faint"]), "bindings": deepcopy(dict(value["bindings"]))}


def _fraction(value: Any) -> Fraction | None:
    if not isinstance(value, Mapping) or not isinstance(value.get("numerator"), int) or isinstance(value.get("numerator"), bool) or not isinstance(value.get("denominator"), int) or isinstance(value.get("denominator"), bool) or value["numerator"] < 0 or value["denominator"] <= 0:
        return None
    return Fraction(value["numerator"], value["denominator"])


def _fraction_dict(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _result(status: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason, **extra}
