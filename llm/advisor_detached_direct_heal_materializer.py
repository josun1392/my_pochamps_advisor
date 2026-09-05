"""Exact detached terminal leaf for the plain half-max self-heal family."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

SCHEMA_VERSION = "detached-direct-heal-materialization-v1"


def materialize_detached_direct_heal(*, execution_authority: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(execution_authority, Mapping) or execution_authority.get("status") != "resolved":
        return _result(execution_authority.get("status", "rejected") if isinstance(execution_authority, Mapping) else "rejected", execution_authority.get("reason", "direct_heal_execution_unavailable") if isinstance(execution_authority, Mapping) else "direct_heal_execution_unavailable", {})
    base = {key: deepcopy(execution_authority[key]) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "actor", "action_id", "move_id") if key in execution_authority}
    if len(base) != 7 or not _hp(execution_authority.get("current_hp"), execution_authority.get("max_hp"), execution_authority.get("fainted")):
        return _result("rejected", "direct_heal_execution_authority_shape_invalid", base)
    effect = execution_authority.get("canonical_effect", {}).get("effect") if isinstance(execution_authority.get("canonical_effect"), Mapping) else None
    if not isinstance(effect, Mapping) or effect.get("consequence_family") != "plain_half_max_hp_self_heal": return _result("rejected", "direct_heal_canonical_effect_invalid", base)
    current, maximum = execution_authority["current_hp"], execution_authority["max_hp"]
    if execution_authority["fainted"]:
        return _result("not_applicable", "user_already_fainted", base)
    nominal = (maximum + 1) // 2
    actual = min(nominal, maximum - current)
    outcome = "no_effect_full_hp" if actual == 0 else "healed"
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "outcome": outcome,
            "probability": {"numerator": 1, "denominator": 1}, "hit_state": "not_applicable", "critical_state": "not_applicable", "damage_roll": "not_applicable", "damage": "not_applicable",
            "heal": {"pre_hp": current, "max_hp": maximum, "nominal_heal": nominal, "actual_heal": actual, "post_hp": current + actual},
            "execution_authority": deepcopy(dict(execution_authority)), "provenance": "strict_detached_direct_heal_materialization_v1"}


def _hp(current: Any, maximum: Any, fainted: Any) -> bool:
    return isinstance(current, int) and not isinstance(current, bool) and isinstance(maximum, int) and not isinstance(maximum, bool) and maximum > 0 and 0 <= current <= maximum and fainted is (current == 0)
def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
