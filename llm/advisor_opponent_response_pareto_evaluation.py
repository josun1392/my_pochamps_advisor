"""Conservative response-wise Pareto comparison over detached pair metrics.

This owner deliberately has no live frontier integration.  It can only refine
an exact stable own-attack tie after the existing guaranteed-first evaluator
has completed, using every member of one complete, known opponent response
set.  Response selection remains explicitly non-probabilistic.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_probability_aware_strategy_evaluation import (
    compare_own_action_probability_aware_candidates,
)


SCHEMA_VERSION = "opponent-response-wise-pareto-evaluation-v1"
PROFILE_SCHEMA = "detached-opponent-response-profile-v1"
PAIR_LEDGER_SCHEMA = "exact-immediate-action-pair-outcome-ledger-v1"
PAIR_METRICS_SCHEMA = "exact-immediate-action-pair-descriptive-metrics-v1"
PAIR_HORIZON = "immediate_action_pair"


def compare_opponent_response_wise_pareto_candidates(*, left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    """Refine only an exact own-action tie; never assign response utility."""
    base = compare_own_action_probability_aware_candidates(left=left, right=right)
    if base.get("status") != "resolved":
        return _result(base.get("status", "rejected"), base.get("reason", "own_action_comparison_unavailable"), base_comparison=base)
    if base.get("comparison") != "tied" or base.get("reason") != "exact_probability_metrics_tie":
        return _result("resolved", "own_action_comparison_not_an_exact_attack_tie", comparison=base.get("comparison"), preference_source=base.get("preference_source"), base_comparison=base)
    if not _attack(left) or not _attack(right):
        return _result("resolved", "opponent_response_policy_attack_pair_required", comparison="tied", preference_source="stable_own_action_tie", base_comparison=base)

    left_profile, right_profile = _profile(left.get("opponent_response_profile"), left), _profile(right.get("opponent_response_profile"), right)
    if left_profile["status"] == "rejected" or right_profile["status"] == "rejected":
        bad = left_profile if left_profile["status"] == "rejected" else right_profile
        return _result("rejected", bad["reason"], base_comparison=base)
    if left_profile["status"] != "evaluable" or right_profile["status"] != "evaluable":
        unavailable = left_profile if left_profile["status"] != "evaluable" else right_profile
        return _result("resolved", "opponent_response_profile_not_applicable", comparison="tied", preference_source="stable_own_action_tie", base_comparison=base, response_policy={"status": unavailable["status"], "reason": unavailable["reason"]})
    if left_profile["bindings"] != right_profile["bindings"]:
        return _result("rejected", "opponent_response_profile_comparison_basis_mismatch", base_comparison=base)
    if left_profile["response_ids"] != right_profile["response_ids"]:
        return _result("rejected", "opponent_response_action_id_set_mismatch", base_comparison=base)

    rows = []
    left_dominates = right_dominates = True
    left_strict = right_strict = False
    for action_id in left_profile["response_ids"]:
        first, second = left_profile["responses"][action_id], right_profile["responses"][action_id]
        left_weak = first["opponent_ko"] >= second["opponent_ko"] and first["own_ko"] <= second["own_ko"]
        right_weak = second["opponent_ko"] >= first["opponent_ko"] and second["own_ko"] <= first["own_ko"]
        left_dominates &= left_weak; right_dominates &= right_weak
        left_strict |= first["opponent_ko"] > second["opponent_ko"] or first["own_ko"] < second["own_ko"]
        right_strict |= second["opponent_ko"] > first["opponent_ko"] or second["own_ko"] < first["own_ko"]
        rows.append({"opponent_response_action_id": action_id, "left_opponent_ko_probability": _fd(first["opponent_ko"]), "right_opponent_ko_probability": _fd(second["opponent_ko"]), "left_own_ko_probability": _fd(first["own_ko"]), "right_own_ko_probability": _fd(second["own_ko"]), "left_weakly_dominates": left_weak, "right_weakly_dominates": right_weak})
    policy = {"status": "eligible", "response_action_ids": tuple(left_profile["response_ids"]), "response_comparisons": tuple(rows), "bindings": deepcopy(left_profile["bindings"]), "response_probability": "not_modeled", "ranking_influence": "none"}
    if left_dominates and left_strict:
        return _result("resolved", "response_wise_pareto_dominance", comparison="left_preferred", preference_source="opponent_response_wise_pareto", base_comparison=base, response_policy=policy)
    if right_dominates and right_strict:
        return _result("resolved", "response_wise_pareto_dominance", comparison="right_preferred", preference_source="opponent_response_wise_pareto", base_comparison=base, response_policy=policy)
    return _result("resolved", "response_wise_pareto_tradeoff_or_exact_tie", comparison="tied", preference_source="stable_own_action_tie", base_comparison=base, response_policy=policy)


def _attack(record: Any) -> bool:
    return isinstance(record, Mapping) and record.get("action_type") == "attack" and isinstance(record.get("candidate_id"), str)


def _profile(value: Any, record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {"status": "incomplete", "reason": "opponent_response_profile_unavailable"}
    status = value.get("status")
    if status in {"incomplete", "unsupported"}:
        return {"status": status, "reason": value.get("reason", "opponent_response_profile_unavailable")}
    if status == "rejected":
        return {"status": "rejected", "reason": value.get("reason", "opponent_response_profile_rejected")}
    bindings = _bindings(value, record)
    if status != "evaluable" or value.get("schema_version") != PROFILE_SCHEMA or value.get("horizon") != PAIR_HORIZON or bindings is None:
        return {"status": "rejected", "reason": "invalid_evaluable_opponent_response_profile"}
    ids = value.get("selectable_response_action_ids")
    entries = value.get("response_entries")
    if not isinstance(ids, tuple) or not ids or not all(isinstance(item, str) and item for item in ids) or len(ids) != len(set(ids)) or not isinstance(entries, tuple):
        return {"status": "rejected", "reason": "opponent_response_profile_response_set_invalid"}
    response_rows: dict[str, dict[str, Fraction]] = {}
    for entry in entries:
        parsed = _entry(entry, bindings)
        if isinstance(parsed, str): return {"status": "rejected", "reason": parsed}
        action_id, row = parsed
        if action_id in response_rows: return {"status": "rejected", "reason": "duplicate_opponent_response_action_id"}
        response_rows[action_id] = row
    if set(response_rows) != set(ids):
        return {"status": "rejected", "reason": "opponent_response_profile_entry_set_mismatch"}
    return {"status": "evaluable", "bindings": bindings, "response_ids": tuple(ids), "responses": response_rows}


def _bindings(profile: Mapping[str, Any], record: Mapping[str, Any]) -> dict[str, Any] | None:
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "opponent_actor", "target_owner")
    if profile.get("own_action_id") != record.get("candidate_id") or any(key not in profile for key in keys): return None
    bindings = {key: deepcopy(profile[key]) for key in keys}
    if not all(isinstance(bindings[key], str) and bindings[key] for key in keys[:3]) or not all(isinstance(bindings[key], Mapping) for key in keys[3:]): return None
    ledger = record.get("exact_outcome_ledger")
    if not isinstance(ledger, Mapping) or not isinstance(ledger.get("bindings"), Mapping): return None
    own = ledger["bindings"]
    if any(own.get(key) != bindings[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")): return None
    if own.get("attacker") != bindings["target_owner"] or own.get("target") != bindings["opponent_actor"]: return None
    return bindings


def _entry(value: Any, bindings: Mapping[str, Any]) -> tuple[str, dict[str, Fraction]] | str:
    if not isinstance(value, Mapping) or not isinstance(value.get("opponent_response_action_id"), str): return "invalid_opponent_response_profile_entry"
    pair, ledger, metrics = value.get("pair"), value.get("exact_pair_outcome_ledger"), value.get("descriptive_metrics")
    if not isinstance(pair, Mapping) or pair.get("status") != "evaluable" or not isinstance(ledger, Mapping) or ledger.get("status") != "evaluable" or not isinstance(metrics, Mapping) or metrics.get("status") != "resolved": return "required_response_pair_not_evaluable"
    if ledger.get("schema_version") != PAIR_LEDGER_SCHEMA or ledger.get("horizon") != PAIR_HORIZON or metrics.get("schema_version") != PAIR_METRICS_SCHEMA or metrics.get("horizon") != PAIR_HORIZON or metrics.get("source_ledger_status") != "evaluable": return "invalid_response_pair_ledger_or_metrics"
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_action_id", "opponent_action_id", "own_actor", "opponent_actor")
    if any(pair.get(key) != ledger.get(key) or ledger.get(key) != metrics.get(key) for key in keys): return "response_pair_artifact_binding_mismatch"
    if pair.get("session_id") != bindings["session_id"] or pair.get("source_runtime_fingerprint") != bindings["source_runtime_fingerprint"] or pair.get("source_branch_fingerprint") != bindings["source_branch_fingerprint"] or pair.get("decision_owner") != bindings["decision_owner"] or pair.get("opponent_actor") != bindings["opponent_actor"] or pair.get("own_actor") != bindings["target_owner"] or pair.get("opponent_action_id") != value["opponent_response_action_id"]: return "response_pair_profile_binding_mismatch"
    if _fraction(ledger.get("terminal_probability_mass")) != Fraction(1, 1) or _fraction(metrics.get("terminal_probability_mass")) != Fraction(1, 1): return "response_pair_probability_mass_not_one"
    own, opponent = metrics.get("own"), metrics.get("opponent")
    if not isinstance(own, Mapping) or not isinstance(opponent, Mapping) or own.get("status") != "resolved" or opponent.get("status") != "resolved": return "response_pair_ko_metric_unavailable"
    own_ko, own_survival = _fraction(own.get("ko_probability")), _fraction(own.get("survival_probability"))
    opponent_ko, opponent_survival = _fraction(opponent.get("ko_probability")), _fraction(opponent.get("survival_probability"))
    if None in {own_ko, own_survival, opponent_ko, opponent_survival} or own_ko + own_survival != 1 or opponent_ko + opponent_survival != 1: return "response_pair_ko_metric_invalid"
    return value["opponent_response_action_id"], {"own_ko": own_ko, "opponent_ko": opponent_ko}


def _fraction(value: Any) -> Fraction | None:
    if not isinstance(value, Mapping) or not isinstance(value.get("numerator"), int) or isinstance(value.get("numerator"), bool) or not isinstance(value.get("denominator"), int) or isinstance(value.get("denominator"), bool) or value["numerator"] < 0 or value["denominator"] <= 0: return None
    return Fraction(value["numerator"], value["denominator"])


def _fd(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _result(status: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason, **deepcopy(extra)}
