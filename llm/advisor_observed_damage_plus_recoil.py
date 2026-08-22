"""Brave Bird-only trusted observed damage followed by exact applied recoil."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_observed_damage_application import apply_exact_observed_damage, apply_exact_observed_recoil, exact_owner
from llm.advisor_transition_preview import fingerprint_transition_preview_state


SCHEMA_VERSION = "observed-damage-plus-recoil-result-v1"
_PROVENANCE = "trusted_observed_damage_plus_recoil_result_v1"
_KEYS = frozenset({"schema_version", "session_id", "source_branch_fingerprint", "user", "target_owner", "move_id", "damage_amount", "damaging_hit_result", "recoil_result", "recoil_amount", "provenance"})


def materialize_observed_brave_bird_recoil(*, branch_state: Mapping[str, Any], source_branch_fingerprint: str, observed_result: Mapping[str, Any]) -> dict[str, Any]:
    """Return one coherent F2 only after exact F0 damage and F1 recoil validate."""
    if fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_observed_brave_bird_branch")
    if not _valid(observed_result, source_branch_fingerprint):
        return _result("rejected", "invalid_observed_brave_bird_result")
    user, target = observed_result["user"], observed_result["target_owner"]
    # Validate required applied recoil on F0 too, so an invalid attacker cannot
    # expose a successful public partial result after target damage.
    active = branch_state.get("active") if isinstance(branch_state, Mapping) else None
    if observed_result["recoil_result"] == "applied" and not _recoil_owner_exact(active, user):
        return _result("rejected", "invalid_observed_recoil_authority")
    damage = apply_exact_observed_damage(branch_state=branch_state, source_branch_fingerprint=source_branch_fingerprint, user=user, target_owner=target, damage_amount=observed_result["damage_amount"])
    if damage.get("status") != "resolved":
        return damage
    f1, f1_fp = damage["next_state"], damage["resulting_branch_fingerprint"]
    if observed_result["recoil_result"] == "not_applied":
        return {**damage, "observed_damage_plus_recoil_result": deepcopy(dict(observed_result)), "f1_branch_fingerprint": f1_fp, "recoil": "not_applied", "secondary_effects": "out_of_scope"}
    recoil_authority = {"schema_version": "observed-brave-bird-recoil-authority-v1", "source_branch_fingerprint": f1_fp,
                        "owner": deepcopy(dict(user)), "recoil_amount": observed_result["recoil_amount"], "provenance": _PROVENANCE}
    recoil = apply_exact_observed_recoil(branch_state=f1, source_branch_fingerprint=f1_fp, recoil_authority=recoil_authority)
    if recoil.get("status") != "resolved":
        return recoil
    return {"status": "resolved", "source_branch_fingerprint": source_branch_fingerprint,
            "f1_branch_fingerprint": f1_fp, "resulting_branch_fingerprint": recoil["resulting_branch_fingerprint"],
            "next_state": recoil["next_state"], "observed_damage_plus_recoil_result": deepcopy(dict(observed_result)), "recoil_authority": recoil_authority,
            "damage_application": {**damage["damage_application"], "provenance": _PROVENANCE},
            "recoil_application": {**recoil["recoil_application"], "provenance": _PROVENANCE},
            "materialization": "pure_idempotent", "secondary_effects": "out_of_scope"}


def _valid(value: Any, fingerprint: str) -> bool:
    if not isinstance(value, Mapping) or set(value) != _KEYS:
        return False
    user, target, damage, recoil = value.get("user"), value.get("target_owner"), value.get("damage_amount"), value.get("recoil_amount")
    status = value.get("recoil_result")
    amount_ok = isinstance(recoil, int) and not isinstance(recoil, bool) and recoil > 0 if status == "applied" else recoil is None
    return (exact_owner(user) and exact_owner(target) and value.get("schema_version") == SCHEMA_VERSION and value.get("provenance") == _PROVENANCE and value.get("move_id") == "brave-bird" and value.get("damaging_hit_result") == "applied" and status in {"applied", "not_applied"} and amount_ok and isinstance(damage, int) and not isinstance(damage, bool) and damage > 0 and value.get("source_branch_fingerprint") == fingerprint and value.get("session_id") == user["session_id"] == target["session_id"] and user["side"] != target["side"])


def _recoil_owner_exact(active: Any, owner: Mapping[str, Any]) -> bool:
    current = active.get(owner["side"]) if isinstance(active, Mapping) else None
    if not isinstance(current, Mapping):
        return False
    hp, maximum = current.get("current_hp"), current.get("max_hp")
    return isinstance(current, Mapping) and all(current.get(key) == owner[key] for key in ("session_id", "side", "slot_index", "pokemon_id")) and isinstance(hp, int) and not isinstance(hp, bool) and isinstance(maximum, int) and not isinstance(maximum, bool) and 0 < hp <= maximum and current.get("fainted") is False


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
