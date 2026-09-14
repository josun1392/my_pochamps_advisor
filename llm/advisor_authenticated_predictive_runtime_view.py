"""Authenticated sparse state view for the fixed-two-hit second hit.

This is deliberately not a general runtime snapshot replacement.  It binds a
first-hit outcome to the original frozen D0 and exposes only the target HP /
item delta needed to rebase the second normal-formula calculation.  Callers
must use the legacy detached runtime path for any other path-local mutation.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "authenticated-predictive-runtime-view-v1"


def freeze_fixed_two_hit_second_hit_runtime_view(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any],
    first_hit: Mapping[str, Any], normal_formula_input: Mapping[str, Any], native_damage_context: Mapping[str, Any],
    attacker_hp_before: int, attacker_hp_after: int, condition_before: str,
    condition_after: str, focus_sash_consumed: bool,
) -> dict[str, Any]:
    """Bind one supported first-hit delta without constructing a runtime state.

    The first v1 slice supports target HP/faint and the Focus Sash item removal.
    A changed attacker HP or condition is intentionally legacy-only because the
    normal-formula context has additional path-sensitive consumers for them.
    """
    base = _base(strategy_d0, action, attacker, target)
    if base is None or not isinstance(first_hit, Mapping) or not isinstance(normal_formula_input, Mapping) or not isinstance(native_damage_context, Mapping):
        return _result("rejected", "invalid_fixed_two_hit_runtime_view_request", {})
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base)
    if attacker_hp_after != attacker_hp_before or condition_after != condition_before:
        return _result("legacy_required", "fixed_two_hit_runtime_view_unsupported_attacker_overlay", base)
    hp = first_hit.get("post_hp")
    maximum = first_hit.get("target_max_hp")
    if (not isinstance(hp, int) or isinstance(hp, bool) or hp < 1
            or not isinstance(maximum, int) or isinstance(maximum, bool) or hp > maximum):
        return _result("rejected", "fixed_two_hit_runtime_view_first_hit_hp_invalid", base)
    if first_hit.get("hit_index") != 1 or first_hit.get("critical_state") not in {"critical", "non_critical"}:
        return _result("rejected", "fixed_two_hit_runtime_view_source_hit_invalid", base)
    if normal_formula_input.get("status") != "resolved" or normal_formula_input.get("move_id") != base["move_id"]:
        return _result("rejected", "fixed_two_hit_runtime_view_normal_input_mismatch", base)
    overlay = {
        "target": deepcopy(dict(target)),
        "current_hp": hp,
        "fainted": False,
        "known_item": None if focus_sash_consumed else "unchanged",
        "focus_sash_consumed": focus_sash_consumed,
    }
    source = {
        "hit_index": 1,
        "critical_state": first_hit["critical_state"],
        "roll_index": first_hit.get("roll_index"),
        "raw_damage": first_hit.get("raw_damage"),
        "actual_damage": first_hit.get("actual_damage"),
        "post_hp": hp,
    }
    if not all(isinstance(source[key], int) and not isinstance(source[key], bool) and source[key] >= 0 for key in ("roll_index", "raw_damage", "actual_damage")):
        return _result("rejected", "fixed_two_hit_runtime_view_source_hit_identity_invalid", base)
    overlay_fingerprint = _fingerprint({"base": base, "overlay": overlay, "source": source})
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION,
        **base, "source_hit": source, "overlay": overlay,
        "overlay_fingerprint": overlay_fingerprint,
        # The base normal-formula input is already strict and immutable by
        # convention; it is copied only at its producing boundary, not per
        # first-hit terminal branch.
        "base_normal_formula_input": normal_formula_input,
        "base_native_damage_context": native_damage_context,
        "provenance": "fixed_two_hit_first_hit_to_authenticated_runtime_view_v1",
    }


def fixed_two_hit_second_hit_view_inputs(
    *, view: Mapping[str, Any], strategy_d0: Mapping[str, Any], action: Mapping[str, Any],
    attacker: Mapping[str, Any], target: Mapping[str, Any],
) -> dict[str, Any]:
    """Return compact rebased inputs for the existing normal-formula owners."""
    base = _base(strategy_d0, action, attacker, target)
    if base is None or not isinstance(view, Mapping) or view.get("status") != "resolved" or view.get("schema_version") != SCHEMA_VERSION:
        return _result("rejected", "invalid_fixed_two_hit_runtime_view", base or {})
    if any(view.get(key) != value for key, value in base.items()):
        return _result("rejected", "fixed_two_hit_runtime_view_binding_mismatch", base)
    overlay = view.get("overlay")
    source = view.get("source_hit")
    normal = view.get("base_normal_formula_input")
    native = view.get("base_native_damage_context")
    if not isinstance(overlay, Mapping) or not isinstance(source, Mapping) or not isinstance(normal, Mapping) or not isinstance(native, Mapping):
        return _result("rejected", "fixed_two_hit_runtime_view_payload_invalid", base)
    if view.get("overlay_fingerprint") != _fingerprint({"base": base, "overlay": overlay, "source": source}):
        return _result("rejected", "fixed_two_hit_runtime_view_forged_overlay", base)
    if overlay.get("target") != dict(target) or overlay.get("fainted") is not False or not isinstance(overlay.get("current_hp"), int):
        return _result("rejected", "fixed_two_hit_runtime_view_overlay_identity_invalid", base)
    rebased_damage = _rebase_damage_input(normal.get("snapshot_damage_input"), target, overlay["current_hp"], overlay.get("known_item"))
    branch_state = _rebase_branch_state(strategy_d0.get("strategy_state"), target, overlay["current_hp"])
    if rebased_damage is None or branch_state is None:
        return _result("rejected", "fixed_two_hit_runtime_view_rebase_invalid", base)
    return {
        "status": "resolved", **base,
        "snapshot_damage_input": rebased_damage,
        "stat_provenance": normal.get("stat_provenance"),
        "trusted_level": normal.get("trusted_level"),
        "post_hit_authority": normal.get("post_hit_authority"),
        "native_damage_context": native,
        "branch_state": branch_state,
        "source_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint"),
        "provenance": "authenticated_fixed_two_hit_runtime_view_builder_inputs_v1",
    }


def _rebase_damage_input(value: Any, target: Mapping[str, Any], hp: int, known_item: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    # Copy only the native calculation payload, never the reducer runtime.
    result = deepcopy(dict(value))
    try:
        current = result["battle_context"]["current_state"]
        direct = current["direct_mechanics_context"]
        defender = direct["defender"]
    except (KeyError, TypeError):
        return None
    # The native direct-side projection intentionally carries mechanics facts,
    # not roster identity.  Identity was authenticated before this rebase.
    if not isinstance(defender, dict):
        return None
    defender["current_hp"] = hp
    defender["fainted"] = False
    defender["hp_source"] = "detached_path_local_defender_hp_v1"
    if known_item is None:
        defender["item"] = {"status": "known_absent"}
    return result


def _rebase_branch_state(value: Any, target: Mapping[str, Any], hp: int) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    result = deepcopy(dict(value))
    active = result.get("active")
    row = active.get(target.get("side")) if isinstance(active, dict) else None
    if not isinstance(row, dict) or row.get("pokemon_id") != target.get("pokemon_id"):
        return None
    row["current_hp"] = hp
    row["fainted"] = False
    return result


def _base(d0: Any, action: Any, attacker: Any, target: Any) -> dict[str, Any] | None:
    if not all(isinstance(value, Mapping) for value in (d0, action, attacker, target)):
        return None
    owner = d0.get("decision_owner")
    if attacker != owner or target.get("side") == attacker.get("side"):
        return None
    move_id = action.get("identity")
    if not isinstance(move_id, str) or not move_id:
        return None
    keys = ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint")
    if any(not isinstance(d0.get(key), str) or not d0[key] for key in keys):
        return None
    return {
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(owner)), "attacker": deepcopy(dict(attacker)),
        "target": deepcopy(dict(target)), "action_id": action.get("action_id"), "move_id": move_id,
    }


def _fingerprint(value: Mapping[str, Any]) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason, **deepcopy(dict(base))}
