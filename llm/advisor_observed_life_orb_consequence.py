"""F1-bound trusted observed Life Orb post-hit authority and application."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.damage.recoil import HitResult, RecoilMove, RecoilPokemon, compute_life_orb_recoil
from llm.advisor_observed_damage_application import (
    apply_exact_observed_life_orb_consequence,
    exact_owner,
)
from llm.advisor_transition_preview import fingerprint_transition_preview_state


SCHEMA_VERSION = "observed-life-orb-post-hit-result-v1"
_PROVENANCE = "trusted_observed_life_orb_post_hit_v1"
_KEYS = frozenset({
    "schema_version", "session_id", "source_branch_fingerprint", "user", "target_owner",
    "move_id", "move_category", "qualifying_hit_result", "provenance",
})


def materialize_observed_life_orb_post_hit(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str,
    observed_result: Mapping[str, Any], preceding_damage_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve one exact F1 Life Orb consequence without calculating move damage."""
    if fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_observed_life_orb_branch")
    if not _valid_observation(observed_result, source_branch_fingerprint, preceding_damage_result):
        return _result("rejected", "invalid_observed_life_orb_result")
    user, target = observed_result["user"], observed_result["target_owner"]
    active = branch_state.get("active") if isinstance(branch_state, Mapping) else None
    if not isinstance(active, Mapping) or not _current_owner(active, user) or not _current_owner(active, target):
        return _result("rejected", "stale_or_foreign_life_orb_owner")
    item = _current_item(branch_state, user["side"])
    if item is None:
        return _result("incomplete", "life_orb_current_item_unknown")
    if item != "life-orb":
        return _non_trigger(branch_state, observed_result, "known_non_life_orb")
    ability = _current_ability(branch_state, user["side"])
    if ability is None:
        return _result("incomplete", "life_orb_current_ability_unknown")
    target_ability = _current_ability(branch_state, target["side"])
    if ability in {"magic-guard", "sheer-force"} and target_ability is None:
        return _result("incomplete", "life_orb_target_ability_unknown")
    if observed_result["qualifying_hit_result"] == "not_qualifying":
        return _non_trigger(branch_state, observed_result, "exact_not_qualifying")
    attacker = active[user["side"]]
    if not _exact_hp(attacker):
        return _result("incomplete", "life_orb_attacker_hp_unknown")
    effective_ability = None if target_ability == "neutralizing-gas" else ability
    recoil = compute_life_orb_recoil(
        RecoilPokemon(max_hp=active[user["side"]].get("max_hp"), item=item, ability=effective_ability),
        RecoilMove(move_id=observed_result["move_id"], category=observed_result["move_category"]),
        HitResult(targets_hit=1),
    )
    if recoil == 0:
        reason = "suppressed_by_magic_guard" if effective_ability == "magic-guard" else "suppressed_by_sheer_force"
        return _non_trigger(branch_state, observed_result, reason)
    authority = {
        "schema_version": "life-orb-post-hit-authority-v1", "source_branch_fingerprint": source_branch_fingerprint,
        "owner": deepcopy(dict(user)), "target_owner": deepcopy(dict(target)), "recoil_amount": recoil,
        "provenance": _PROVENANCE,
    }
    applied = apply_exact_observed_life_orb_consequence(
        branch_state=branch_state, source_branch_fingerprint=source_branch_fingerprint,
        life_orb_authority=authority,
    )
    if applied.get("status") != "resolved":
        return applied
    return {
        "status": "resolved", "source_branch_fingerprint": source_branch_fingerprint,
        "resulting_branch_fingerprint": applied["resulting_branch_fingerprint"], "next_state": applied["next_state"],
        "observed_life_orb_post_hit_result": deepcopy(dict(observed_result)),
        "life_orb_authority": authority, "life_orb_application": applied["life_orb_application"],
        "materialization": "pure_idempotent",
    }


def _valid_observation(value: Any, fingerprint: str, damage_result: Any) -> bool:
    if not isinstance(value, Mapping) or set(value) != _KEYS:
        return False
    user, target = value.get("user"), value.get("target_owner")
    source = damage_result.get("observed_direct_damage_result") if isinstance(damage_result, Mapping) else None
    return (
        exact_owner(user) and exact_owner(target) and value.get("schema_version") == SCHEMA_VERSION
        and value.get("provenance") == _PROVENANCE and value.get("source_branch_fingerprint") == fingerprint
        and value.get("session_id") == user["session_id"] == target["session_id"] and user["side"] != target["side"]
        and isinstance(value.get("move_id"), str) and bool(value["move_id"])
        and value.get("move_category") in {"physical", "special"}
        and value.get("qualifying_hit_result") in {"qualifying", "not_qualifying"}
        and isinstance(source, Mapping) and source.get("schema_version") == "observed-direct-damage-result-v1"
        and source.get("provenance") == "trusted_observed_direct_damage_result_v1"
        and source.get("move_id") == value.get("move_id")
        and source.get("user") == user and source.get("target_owner") == target
        and damage_result.get("status") == "resolved"
        and damage_result.get("resulting_branch_fingerprint") == fingerprint
    )


def _current_owner(active: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    current = active.get(owner["side"])
    return isinstance(current, Mapping) and all(current.get(key) == owner.get(key) for key in ("session_id", "side", "slot_index", "pokemon_id"))


def _current_item(state: Mapping[str, Any], side: str) -> str | None:
    direct = state.get("current_state", {}).get("direct_mechanics_context") if isinstance(state.get("current_state"), Mapping) else None
    role = "attacker" if side == "self" else "defender"
    item = direct.get(role, {}).get("item") if isinstance(direct, Mapping) and isinstance(direct.get(role), Mapping) else None
    if isinstance(item, Mapping) and item.get("status") == "known" and isinstance(item.get("value"), str):
        return item["value"]
    if isinstance(item, Mapping) and item.get("status") == "known_absent":
        return ""
    return None


def _current_ability(state: Mapping[str, Any], side: str) -> str | None:
    current = state.get("current_state") if isinstance(state, Mapping) else None
    rows = current.get("ability_context", {}).get("current_abilities") if isinstance(current, Mapping) else None
    entry = next((row for row in rows if isinstance(row, Mapping) and row.get("side") == side and row.get("status") == "user_confirmed" and row.get("source") == "user_confirmed_current_ability" and isinstance(row.get("ability"), str)), None) if isinstance(rows, list) else None
    return entry["ability"] if entry is not None else None


def _non_trigger(branch_state: Mapping[str, Any], observed_result: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        "status": "resolved", "source_branch_fingerprint": observed_result["source_branch_fingerprint"],
        "resulting_branch_fingerprint": observed_result["source_branch_fingerprint"],
        "next_state": deepcopy(dict(branch_state)),
        "observed_life_orb_post_hit_result": deepcopy(dict(observed_result)),
        "life_orb": "not_triggered", "reason": reason, "materialization": "pure_idempotent",
    }


def _exact_hp(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("current_hp"), int) and not isinstance(value.get("current_hp"), bool)
        and isinstance(value.get("max_hp"), int) and not isinstance(value.get("max_hp"), bool)
        and value["max_hp"] > 0 and 0 < value["current_hp"] <= value["max_hp"]
        and value.get("fainted") is False
    )


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
