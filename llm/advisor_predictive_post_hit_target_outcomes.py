"""Strict per-roll target outcomes after already-composed post-hit mechanics."""
from __future__ import annotations

from typing import Any, Mapping


def resolve_predictive_post_hit_target_outcomes(*, interval: Mapping[str, Any], post_hit: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return exact per-roll actual damage and survival without changing raw rolls.

    This is deliberately a structural adapter: post-hit mechanics (including
    detached Sturdy survival) remain owned by their existing composer.
    """
    target_hp = interval.get("target_hp_before") if isinstance(interval, Mapping) else None
    rolls = interval.get("exact_damage_rolls") if isinstance(interval, Mapping) else None
    if not isinstance(target_hp, int) or isinstance(target_hp, bool) or target_hp < 1 or not isinstance(rolls, tuple) or len(rolls) != 16:
        return _result("incomplete", "target_hp_or_roll_authority_incomplete")
    if post_hit is None:
        return _resolved(tuple({"raw_damage": damage, "actual_damage": min(damage, target_hp), "target_post_hit_hp": max(0, target_hp - damage), "target_survived": damage < target_hp} for damage in rolls))
    if not isinstance(post_hit, Mapping) or post_hit.get("status") != "resolved" or post_hit.get("schema_version") != "deterministic-predictive-normal-formula-post-hit-v1":
        return _result("rejected", "post_hit_target_outcome_authority_invalid")
    if any(post_hit.get(key) != interval.get(key) for key in ("session_id", "source_branch_fingerprint", "decision_owner", "move_id")):
        return _result("rejected", "post_hit_target_outcome_binding_mismatch")
    branches = post_hit.get("branches")
    if not isinstance(branches, (tuple, list)) or len(branches) != 16:
        return _result("rejected", "post_hit_target_outcome_roll_identity_missing")
    outcomes = []
    for raw, branch in zip(rolls, branches, strict=True):
        actual = branch.get("actual_damage") if isinstance(branch, Mapping) else None
        if not isinstance(branch, Mapping) or branch.get("raw_damage") != raw or not isinstance(actual, int) or isinstance(actual, bool) or not 0 <= actual <= target_hp:
            return _result("rejected", "post_hit_target_outcome_roll_identity_mismatch")
        outcomes.append({"raw_damage": raw, "actual_damage": actual, "target_post_hit_hp": target_hp - actual, "target_survived": actual < target_hp})
    return _resolved(tuple(outcomes))


def _resolved(outcomes: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    return {"status": "resolved", "outcomes": outcomes, "provenance": "exact_post_hit_actual_damage_target_survival_adapter_v1"}


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
