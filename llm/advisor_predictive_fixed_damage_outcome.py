"""Detached outcome adapter for exact-complete predictive Seismic Toss only."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_substitute import route_exact_damage_to_substitute, substitute_state
from llm.advisor_transition_preview import fingerprint_transition_preview_state


_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_CANDIDATE_SCHEMA = "deterministic-action-candidate-v1"
_PREDICTIVE_SCHEMA = "deterministic-predictive-attack-authority-v1"


def enrich_predictive_attack_candidate(
    *, candidate: Mapping[str, Any], predictive_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach present-tense predictive authority without executing it."""
    if not _candidate_matches_authority(candidate, predictive_authority):
        return _result("rejected", "stale_or_mismatched_predictive_authority")
    row = deepcopy(dict(candidate))
    row["action_authority"] = deepcopy(dict(predictive_authority))
    row["execution_readiness"] = "predictive_execution_ready" if predictive_authority.get("completeness") == "exact_complete" else "execution_incomplete"
    row["execution_reason"] = predictive_authority.get("reason")
    return {"status": "resolved", "candidate": row}


def materialize_predictive_fixed_damage_outcome(
    *, decision_state: Mapping[str, Any], decision_owner: Mapping[str, Any],
    candidate: Mapping[str, Any], predictive_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Convert one exact predictive Seismic Toss result to a detached outcome.

    This consumes predictive authority directly; it creates no observed result
    and does not call the observed candidate materializer.
    """
    fingerprint = fingerprint_transition_preview_state(decision_state)
    if not isinstance(fingerprint, str) or not _candidate_matches_authority(candidate, predictive_authority):
        return _result("rejected", "stale_or_mismatched_predictive_authority")
    if candidate.get("decision_owner") != dict(decision_owner) or candidate.get("source_branch_fingerprint") != fingerprint:
        return _result("rejected", "stale_or_invalid_candidate_authority")
    if predictive_authority.get("source_branch_fingerprint") != fingerprint or predictive_authority.get("decision_owner") != dict(decision_owner):
        return _result("rejected", "predictive_authority_d0_mismatch")
    if predictive_authority.get("completeness") != "exact_complete":
        return _result("incomplete", predictive_authority.get("reason", "predictive_execution_incomplete"))
    result = predictive_authority.get("predicted_result")
    if not _valid_result(result):
        return _result("rejected", "invalid_predictive_result")
    target = predictive_authority["target"]
    active = decision_state.get("active") if isinstance(decision_state, Mapping) else None
    current_target = active.get(target["side"]) if isinstance(active, Mapping) else None
    if not _same_owner(current_target, target):
        return _result("rejected", "foreign_predictive_target")

    if result["damage_route"] == "substitute":
        routed = _apply_predicted_substitute_damage(decision_state, fingerprint, target, result)
        if routed.get("status") != "resolved":
            return routed
        state, result_fingerprint = routed["next_state"], routed["resulting_branch_fingerprint"]
    else:
        applied = _apply_predicted_target_damage(decision_state, target, result)
        if applied is None:
            return _result("rejected", "predictive_result_target_state_mismatch")
        state = applied
        result_fingerprint = fingerprint_transition_preview_state(state)
        if not isinstance(result_fingerprint, str):
            return _result("rejected", "unserializable_predictive_outcome")
    return {
        "status": "complete",
        "outcome": {
            "schema_version": "deterministic-candidate-outcome-v1",
            "candidate_id": candidate["candidate_id"],
            "action_type": candidate["action_type"],
            "source_branch_fingerprint": fingerprint,
            "outcome_state": state,
            "outcome_branch_fingerprint": result_fingerprint,
            "completeness": "complete",
            "execution_provenance": "current_predictive_fixed_damage_v1",
        },
    }


def _candidate_matches_authority(candidate: Any, authority: Any) -> bool:
    return isinstance(candidate, Mapping) and isinstance(authority, Mapping) and candidate.get("schema_version") == _CANDIDATE_SCHEMA and candidate.get("action_type") == "attack" and candidate.get("candidate_id") == "attack:seismic-toss" and authority.get("status") == "resolved" and authority.get("schema_version") == _PREDICTIVE_SCHEMA and authority.get("authority_class") == "current_predictive_execution_authority" and authority.get("move_id") == "seismic-toss" and candidate.get("decision_owner") == authority.get("decision_owner") and candidate.get("source_branch_fingerprint") == authority.get("source_branch_fingerprint") and candidate["decision_owner"] == authority.get("attacker")


def _valid_result(value: Any) -> bool:
    if not isinstance(value, Mapping) or not isinstance(value.get("damage"), int) or isinstance(value.get("damage"), bool) or value["damage"] < 0:
        return False
    if value.get("damage_route") == "target":
        return all(isinstance(value.get(key), int) and not isinstance(value.get(key), bool) and value[key] >= 0 for key in ("target_hp_before", "target_hp_after")) and value.get("target_fainted") is (value["target_hp_after"] == 0) and value["target_hp_after"] == max(0, value["target_hp_before"] - value["damage"])
    if value.get("damage_route") == "substitute":
        return all(isinstance(value.get(key), int) and not isinstance(value.get(key), bool) and value[key] >= 0 for key in ("substitute_hp_before", "substitute_hp_after")) and value.get("substitute_broken") is (value["substitute_hp_after"] == 0) and value.get("target_fainted") is False and value["substitute_hp_after"] == max(0, value["substitute_hp_before"] - value["damage"])
    return False


def _apply_predicted_target_damage(state: Mapping[str, Any], target: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any] | None:
    active_target = state.get("active", {}).get(target["side"]) if isinstance(state.get("active"), Mapping) else None
    if not _exact_hp(active_target) or active_target["current_hp"] != result["target_hp_before"]:
        return None
    copy = deepcopy(dict(state)); current = copy["active"][target["side"]]
    current["current_hp"] = result["target_hp_after"]
    current["fainted"] = result["target_fainted"]
    _sync_hp(copy, target["side"], current["current_hp"], current["max_hp"])
    return copy


def _apply_predicted_substitute_damage(state: Mapping[str, Any], fingerprint: str, target: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    substitute = substitute_state(state, target)
    if substitute.get("state") != "known_active" or substitute.get("substitute_hp") != result["substitute_hp_before"]:
        return _result("rejected", "predictive_result_substitute_state_mismatch")
    routed = route_exact_damage_to_substitute(branch_state=state, target_owner=target, damage_amount=result["damage"], source_branch_fingerprint=fingerprint)
    if not isinstance(routed, Mapping) or routed.get("status") != "resolved" or routed.get("damage_application", {}).get("substitute_hp_after") != result["substitute_hp_after"]:
        return _result("rejected", "predictive_result_substitute_state_mismatch")
    return dict(routed)


def _same_owner(value: Any, owner: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and dict(owner) == {key: value.get(key) for key in _OWNER_KEYS}


def _exact_hp(value: Any) -> bool:
    return isinstance(value, Mapping) and isinstance(value.get("current_hp"), int) and not isinstance(value.get("current_hp"), bool) and isinstance(value.get("max_hp"), int) and not isinstance(value.get("max_hp"), bool) and 0 <= value["current_hp"] <= value["max_hp"] and value["max_hp"] > 0 and value.get("fainted") is (value["current_hp"] == 0)


def _sync_hp(state: Mapping[str, Any], side: str, hp: int, maximum: int) -> None:
    current = state.get("current_state") if isinstance(state, Mapping) else None
    rows = current.get("current_hp_context", {}).get("current_hp") if isinstance(current, Mapping) else None
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("side") == side:
                row["current_hp"], row["maximum_hp"] = hp, maximum


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
