"""Pure arithmetic owner for canonical Endeavor."""
from __future__ import annotations
from typing import Any, Mapping
from advisor.canonical_endeavor_hp_difference_damage_family import resolve_canonical_endeavor_hp_difference_damage_move


def materialize_detached_endeavor_hp_difference_damage(*, move: Mapping[str, Any], attacker_hp: Mapping[str, Any], target_hp: Mapping[str, Any], hit_state: str, applicability: str) -> dict[str, Any]:
    canonical = resolve_canonical_endeavor_hp_difference_damage_move(move=move)
    if canonical.get("status") != "resolved": return {"status": canonical.get("status", "rejected"), "reason": canonical.get("reason", "catalog_unavailable")}
    attacker, target = _hp(attacker_hp), _hp(target_hp)
    if attacker is None or target is None or attacker < 1: return {"status": "incomplete", "reason": "endeavor_execution_hp_unknown"}
    if hit_state not in {"hit", "miss"} or applicability not in {"applicable", "immune", "blocked"}: return {"status": "rejected", "reason": "endeavor_hit_or_applicability_invalid"}
    success = hit_state == "hit" and applicability == "applicable" and target > attacker
    failure = "endeavor_target_hp_not_above_attacker_hp" if hit_state == "hit" and applicability == "applicable" and target <= attacker else None
    damage = target - attacker if success else 0
    return {"status": "resolved", "family": canonical["effect"], "attacker_execution_hp": attacker, "target_execution_hp": target, "hit_state": hit_state, "applicability": applicability, "relation": "target_hp_above_attacker_hp" if target > attacker else "target_hp_not_above_attacker_hp", "outcome": "success" if success else "failure" if failure else applicability if hit_state == "hit" else "miss", "reason": failure, "damage": damage, "derived_damage": damage, "target_post_hp": target - damage, "target_fainted": False, "critical_state": "not_applicable", "damage_roll": "not_applicable", "provenance": "strict_detached_endeavor_hp_difference_damage_v1"}


def _hp(value: Any) -> int | None:
    if not isinstance(value, Mapping): return None
    current, maximum, fainted = value.get("current_hp"), value.get("max_hp"), value.get("fainted")
    return current if isinstance(current, int) and not isinstance(current, bool) and isinstance(maximum, int) and not isinstance(maximum, bool) and 0 <= current <= maximum and fainted is (current == 0) else None
