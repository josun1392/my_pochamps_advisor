"""Acid Spray-only trusted observed damage plus target-stage result."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_observed_damage_application import (
    apply_exact_observed_damage,
    apply_exact_observed_target_stage_consequence,
    exact_owner,
)
from llm.advisor_transition_preview import fingerprint_transition_preview_state


SCHEMA_VERSION = "observed-damage-plus-target-stage-result-v1"
_PROVENANCE = "trusted_observed_damage_plus_target_stage_result_v1"
_KEYS = frozenset({
    "schema_version", "session_id", "source_branch_fingerprint", "user", "target_owner",
    "move_id", "damage_amount", "damaging_hit_result", "target_stage_result", "stat",
    "stage_delta", "provenance",
})


def materialize_observed_acid_spray(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str,
    observed_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Materialize exact Acid Spray damage, then its F1-bound target SpD drop."""
    if fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_observed_acid_spray_branch")
    if not _valid(observed_result, source_branch_fingerprint):
        return _result("rejected", "invalid_observed_acid_spray_result")
    user, target = observed_result["user"], observed_result["target_owner"]
    damage = apply_exact_observed_damage(
        branch_state=branch_state, source_branch_fingerprint=source_branch_fingerprint,
        user=user, target_owner=target, damage_amount=observed_result["damage_amount"],
    )
    if damage.get("status") != "resolved":
        return damage
    f1, f1_fingerprint = damage["next_state"], damage["resulting_branch_fingerprint"]
    if observed_result["target_stage_result"] == "not_applied":
        return {
            **damage, "f1_branch_fingerprint": f1_fingerprint,
            "observed_damage_plus_target_stage_result": deepcopy(dict(observed_result)),
            "target_stage": "not_applied",
        }
    if damage["damage_application"].get("target_hit_substitute"):
        return _result("rejected", "target_stage_blocked_by_substitute")
    if damage["damage_application"]["target_fainted"]:
        return _result("rejected", "target_stage_after_terminal_damage")
    authority = {
        "schema_version": "observed-acid-spray-target-stage-authority-v1",
        "source_branch_fingerprint": f1_fingerprint, "owner": deepcopy(dict(target)),
        "stat": "special-defense", "delta": -2, "provenance": _PROVENANCE,
    }
    stage = apply_exact_observed_target_stage_consequence(
        branch_state=f1, source_branch_fingerprint=f1_fingerprint, stage_authority=authority,
    )
    if stage.get("status") != "resolved":
        return stage
    return {
        "status": "resolved", "source_branch_fingerprint": source_branch_fingerprint,
        "f1_branch_fingerprint": f1_fingerprint,
        "resulting_branch_fingerprint": stage["resulting_branch_fingerprint"],
        "next_state": stage["next_state"],
        "observed_damage_plus_target_stage_result": deepcopy(dict(observed_result)),
        "target_stage_authority": authority, "damage_application": damage["damage_application"],
        "target_stage_application": stage["target_stage_application"],
        "materialization": "pure_idempotent",
    }


def _valid(value: Any, fingerprint: str) -> bool:
    if not isinstance(value, Mapping) or set(value) != _KEYS:
        return False
    user, target, damage, result = (
        value.get("user"), value.get("target_owner"), value.get("damage_amount"),
        value.get("target_stage_result"),
    )
    stage_ok = (
        result == "applied" and value.get("stat") == "special-defense" and value.get("stage_delta") == -2
    ) or (result == "not_applied" and value.get("stat") is None and value.get("stage_delta") is None)
    return (
        exact_owner(user) and exact_owner(target) and value.get("schema_version") == SCHEMA_VERSION
        and value.get("provenance") == _PROVENANCE and value.get("move_id") == "acid-spray"
        and value.get("damaging_hit_result") == "applied" and isinstance(damage, int)
        and not isinstance(damage, bool) and damage > 0 and stage_ok
        and value.get("source_branch_fingerprint") == fingerprint
        and value.get("session_id") == user["session_id"] == target["session_id"] and user["side"] != target["side"]
    )


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
