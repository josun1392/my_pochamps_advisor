"""Bounded trusted observed direct damage for the plain Water Gun fixture."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_observed_damage_application import apply_exact_observed_damage, exact_owner
from llm.advisor_transition_preview import fingerprint_transition_preview_state


OBSERVED_DIRECT_DAMAGE_SCHEMA_VERSION = "observed-direct-damage-result-v1"
_PROVENANCE = "trusted_observed_direct_damage_result_v1"
_REQUIRED = frozenset({
    "schema_version", "session_id", "source_branch_fingerprint", "user", "target_owner",
    "move_id", "damage_amount", "damaging_hit_result", "provenance",
})
_SUPPORTED = frozenset({"water-gun"})


def materialize_observed_direct_damage_result(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str,
    observed_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Materialize one trusted observed Water Gun hit through the shared F0→F1 core."""
    if fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_observed_direct_damage_branch")
    if not _valid_observation(observed_result, source_branch_fingerprint):
        return _result("rejected", "invalid_observed_direct_damage_result")
    applied = apply_exact_observed_damage(
        branch_state=branch_state, source_branch_fingerprint=source_branch_fingerprint,
        user=observed_result["user"], target_owner=observed_result["target_owner"],
        damage_amount=observed_result["damage_amount"],
    )
    if applied.get("status") != "resolved":
        return applied
    return {
        **applied,
        "observed_direct_damage_result": deepcopy(dict(observed_result)),
        "damage_application": {**applied["damage_application"], "provenance": _PROVENANCE},
        "secondary_effects": "out_of_scope",
    }


def _valid_observation(value: Any, fingerprint: str) -> bool:
    if not isinstance(value, Mapping) or set(value) != _REQUIRED:
        return False
    user, target = value.get("user"), value.get("target_owner")
    damage = value.get("damage_amount")
    return (
        exact_owner(user) and exact_owner(target)
        and value.get("schema_version") == OBSERVED_DIRECT_DAMAGE_SCHEMA_VERSION
        and value.get("provenance") == _PROVENANCE
        and value.get("move_id") in _SUPPORTED
        and value.get("damaging_hit_result") == "applied"
        and isinstance(damage, int) and not isinstance(damage, bool) and damage > 0
        and value.get("source_branch_fingerprint") == fingerprint
        and value.get("session_id") == user["session_id"] == target["session_id"]
        and user["side"] != target["side"]
    )


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
