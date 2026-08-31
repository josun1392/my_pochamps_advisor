"""Exact terminal-leaf adapter for authoritative deterministic fixed damage."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_focus_sash_survival import apply_focus_sash_to_hit


SCHEMA_VERSION = "detached-deterministic-fixed-damage-attack-leaf-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def materialize_detached_deterministic_fixed_damage_attack_leaf(
    *, strategy_d0: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any],
    move_id: str, predictive_authority: Mapping[str, Any],
    sturdy_survival_authority: Mapping[str, Any] | None = None,
    focus_sash_survival_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project one already-exact fixed-damage result into one ``1/1`` leaf.

    This is deliberately only a terminal-leaf projection.  Fixed-damage
    mechanics, type immunity, Substitute routing, and HP arithmetic remain
    owned by the existing predictive fixed-damage authority.
    """
    base = _base(strategy_d0, attacker, target, move_id)
    if base is None:
        return _result("rejected", "invalid_fixed_damage_leaf_request", {})
    parsed = _authority(predictive_authority, base)
    if isinstance(parsed, str):
        return _result("rejected", parsed, base)
    if predictive_authority.get("completeness") != "exact_complete":
        return _result("incomplete", predictive_authority.get("reason", "fixed_damage_authority_incomplete"), base)
    result = predictive_authority.get("predicted_result")
    if not isinstance(result, Mapping):
        return _result("rejected", "fixed_damage_predicted_result_missing", base)
    sturdy = _sturdy(sturdy_survival_authority, base)
    if isinstance(sturdy, Mapping):
        return _result(sturdy["status"], sturdy["reason"], base)
    focus = _focus(focus_sash_survival_authority, base)
    if isinstance(focus, Mapping):
        return _result(focus["status"], focus["reason"], base)
    if sturdy and focus:
        return _result("unsupported", "simultaneous_sturdy_focus_sash_survival_precedence_unsupported", base)
    projected = _consequences(strategy_d0, attacker, target, result, sturdy, focus_sash_survival_authority if focus else None)
    if isinstance(projected, str):
        return _result("rejected", projected, base)
    leaf = {
        "leaf_id": "fixed_damage:deterministic",
        "candidate_id": f"attack:{move_id}",
        "action_type": "attack",
        "branch_path": ("fixed_damage", "deterministic"),
        "probability": {"numerator": 1, "denominator": 1},
        "hit_state": "deterministic_exact",
        "critical_state": "not_applicable",
        "consequences": projected,
        "provenance": {
            **base,
            "provenance": "strict_d0_predictive_fixed_damage_authority_v1",
        },
    }
    return {
        "status": "evaluable", "schema_version": SCHEMA_VERSION,
        "terminal_leaves": (leaf,),
        "terminal_probability_mass": {"numerator": 1, "denominator": 1},
        "component_manifest": {
            "accuracy": {"status": "not_applicable", "reason": "authoritative_deterministic_fixed_damage_result"},
            "critical": {"status": "not_applicable", "reason": "fixed_damage_no_critical_branch"},
            "damage_roll": {"status": "not_applicable", "reason": "fixed_damage_no_roll_branch"},
            "secondary": {"status": "not_applicable"},
        },
        **base,
        "provenance": "strict_predictive_fixed_damage_to_exact_deterministic_terminal_leaf_v1",
    }


def _base(d0: Any, attacker: Any, target: Any, move_id: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(attacker) or not _owner(target) or attacker["side"] == target["side"] or move_id != "seismic-toss":
        return None
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or d0.get("decision_owner") != dict(attacker) or active.get(attacker["side"]) != dict(attacker) or active.get(target["side"]) != dict(target):
        return None
    return {
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(d0["decision_owner"])),
        "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)), "move_id": move_id,
    }


def _authority(value: Any, base: Mapping[str, Any]) -> str | None:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != "deterministic-predictive-attack-authority-v1" or value.get("authority_class") != "current_predictive_execution_authority":
        return "fixed_damage_predictive_authority_invalid"
    for key in ("session_id", "source_branch_fingerprint", "decision_owner", "attacker", "target", "move_id"):
        if value.get(key) != base.get(key):
            return "fixed_damage_predictive_authority_binding_mismatch"
    return None


def _consequences(d0: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any], result: Mapping[str, Any], sturdy: bool, focus_sash: Mapping[str, Any] | None) -> dict[str, Any] | str:
    damage = result.get("damage")
    active = d0.get("strategy_state", {}).get("active", {})
    own = active.get(attacker["side"]) if isinstance(active, Mapping) else None
    defender = active.get(target["side"]) if isinstance(active, Mapping) else None
    if not isinstance(damage, int) or isinstance(damage, bool) or damage < 0 or not _hp(own) or not _hp(defender):
        return "fixed_damage_result_or_current_hp_invalid"
    route = result.get("damage_route")
    if route == "target":
        before, after, fainted = result.get("target_hp_before"), result.get("target_hp_after"), result.get("target_fainted")
        if before != defender["current_hp"] or not isinstance(after, int) or isinstance(after, bool) or after != max(0, before - damage) or fainted is not (after == 0):
            return "fixed_damage_target_result_mismatch"
        sturdy_applied = sturdy and damage >= before
        actual_damage = before - 1 if sturdy_applied else damage
        focus_row = apply_focus_sash_to_hit(authority=focus_sash, consumed=False, hp_before=before, raw_damage=damage, actual_damage=actual_damage, source_hit={"move_id": "seismic-toss", "damage_route": "target"})
        if isinstance(focus_row, Mapping) and focus_row.get("status") in {"incomplete", "unsupported", "rejected"}:
            return str(focus_row["reason"])
        focus_applied = isinstance(focus_row, Mapping) and focus_row.get("activated") is True
        if focus_applied:
            actual_damage = focus_row["actual_damage"]
        target_hp, target_ko = max(0, before - actual_damage), not sturdy_applied and fainted
        if focus_applied:
            target_ko = False
    elif route == "substitute":
        before, after, fainted = result.get("substitute_hp_before"), result.get("substitute_hp_after"), result.get("target_fainted")
        if not isinstance(before, int) or isinstance(before, bool) or not isinstance(after, int) or isinstance(after, bool) or after != max(0, before - damage) or fainted is not False:
            return "fixed_damage_substitute_result_mismatch"
        target_hp, target_ko, actual_damage, sturdy_applied = defender["current_hp"], False, damage, False
    else:
        return "fixed_damage_route_unsupported"
    return {
        "damage": actual_damage, "own_final_hp": own["current_hp"], "target_final_hp": target_hp,
        "target_ko": target_ko, "self_fainted": False, "secondary": None,
        "sturdy_survival": (
            {"outcome": "applied", "target_final_hp": 1, "provenance": "exact_detached_opponent_switch_in_sturdy_survival_v1"}
            if sturdy_applied else
            {"outcome": "not_triggered"} if sturdy else {"outcome": "not_applicable"}
        ),
        "focus_sash_survival": deepcopy(focus_row["survival"]) if isinstance(focus_row, Mapping) else {"outcome": "not_applicable"},
        "deterministic_fixed_damage": {
            "damage_route": route, "raw_damage": damage, "actual_damage": actual_damage,
            "predicted_result": deepcopy(dict(result)),
        },
    }


def _sturdy(value: Mapping[str, Any] | None, base: Mapping[str, Any]) -> bool | dict[str, str]:
    if value is None:
        return False
    if not isinstance(value, Mapping):
        return {"status": "rejected", "reason": "sturdy_survival_authority_invalid"}
    status = value.get("status")
    if status == "not_applicable":
        return False
    if status in {"incomplete", "unsupported", "rejected"}:
        return {"status": status, "reason": value.get("reason", "sturdy_survival_authority_unavailable")}
    required = {"schema_version", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "defender", "attacker", "status", "post_entry_hp", "maximum_hp", "provenance"}
    if status != "ready" or set(value) != required or value.get("schema_version") != "detached-switch-in-sturdy-survival-authority-v1":
        return {"status": "rejected", "reason": "sturdy_survival_authority_invalid"}
    # The fixed-damage authority is rebuilt from the detached post-switch
    # predictive view, so only its stable source session/decision owner and
    # explicit actor identities can match the frozen switch-in authority.
    if any(value.get(key) != base.get(key) for key in ("session_id", "decision_owner")) or value.get("defender") != base["target"] or value.get("attacker") != base["attacker"]:
        return {"status": "rejected", "reason": "sturdy_survival_authority_binding_mismatch"}
    hp, maximum = value.get("post_entry_hp"), value.get("maximum_hp")
    if not isinstance(hp, int) or isinstance(hp, bool) or not isinstance(maximum, int) or isinstance(maximum, bool) or hp != maximum or hp <= 1:
        return {"status": "rejected", "reason": "sturdy_post_entry_hp_invalid"}
    return True


def _focus(value: Mapping[str, Any] | None, base: Mapping[str, Any]) -> bool | dict[str, str]:
    if value is None:
        return False
    if not isinstance(value, Mapping):
        return {"status": "rejected", "reason": "focus_sash_survival_authority_invalid"}
    if value.get("status") == "resolved" and value.get("outcome") == "known_no_effect":
        return False
    if value.get("status") in {"incomplete", "unsupported", "rejected"}:
        return {"status": value["status"], "reason": value.get("reason", "focus_sash_survival_authority_unavailable")}
    if value.get("status") != "ready" or value.get("schema_version") != "runtime-d0-focus-sash-survival-authority-v1":
        return {"status": "rejected", "reason": "focus_sash_survival_authority_invalid"}
    if any(value.get(key) != base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "move_id")) or value.get("holder") != base["target"]:
        return {"status": "rejected", "reason": "focus_sash_survival_authority_binding_mismatch"}
    return True


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _hp(value: Any) -> bool:
    return isinstance(value, Mapping) and isinstance(value.get("current_hp"), int) and not isinstance(value.get("current_hp"), bool) and value["current_hp"] >= 0 and value.get("fainted") is (value["current_hp"] == 0)


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
