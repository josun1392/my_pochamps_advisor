"""D0-bound envelope for special damage families outside the formula engine."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_fractional_target_hp_damage_family import resolve_canonical_fractional_target_hp_damage_move
from advisor.damage.types import type_effectiveness_multiplier
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
from llm.advisor_substitute import substitute_state


SCHEMA_VERSION = "runtime-d0-special-damage-execution-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def freeze_runtime_d0_fractional_target_hp_damage_execution_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any], target: Mapping[str, Any], move_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze current, identity-bound routing facts; never calculate damage."""
    base = _base(strategy_d0, attacker, target, move_metadata)
    if base is None:
        return _result("rejected", "fractional_special_damage_identity_or_metadata_invalid", {})
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base)
    canonical = resolve_canonical_fractional_target_hp_damage_move(move=move_metadata)
    if canonical.get("status") != "resolved":
        return _result(canonical.get("status", "rejected"), canonical.get("reason", "fractional_catalog_unavailable"), base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    raw_target = _roster_row(state, target)
    preview = strategy_d0.get("strategy_state", {}).get("active", {}).get(target["side"])
    if not isinstance(raw_target, Mapping) or not _hp(preview):
        return _result("incomplete", "fractional_execution_target_hp_unknown", base)
    types = raw_target.get("current_type")
    if not isinstance(types, list) or not types or not all(isinstance(value, str) and value for value in types):
        return _result("incomplete", "fractional_execution_target_type_unknown", base)
    substitute = substitute_state(strategy_d0["strategy_state"], target)
    if substitute.get("state") in {"unknown", "legacy_untracked"}:
        return _result("incomplete", "fractional_execution_substitute_state_unknown", base)
    route = "substitute" if substitute.get("state") == "known_active" else "target"
    hp = substitute.get("substitute_hp") if route == "substitute" else preview["current_hp"]
    if not isinstance(hp, int) or isinstance(hp, bool) or hp < 1:
        return _result("incomplete", "fractional_execution_route_hp_unknown", base)
    immune = type_effectiveness_multiplier(canonical["effect"]["type"], tuple(types)) == 0.0
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "special_damage_family": "current_hp_fraction_damage",
        "special_damage_rule_authority": deepcopy(canonical["effect"]),
        "target_type_authority": {"status": "known", "values": deepcopy(types), "provenance": "runtime_battle_state_v1"},
        "applicability": "immune" if immune else "applicable",
        "target_route": route,
        "execution_target_hp": hp,
        "target_hp_authority": {"status": "known", "current_hp": preview["current_hp"], "max_hp": preview["max_hp"]},
        "substitute_authority": {"status": "known", "state": substitute["state"], **({"substitute_hp": substitute["substitute_hp"]} if route == "substitute" else {})},
        "provenance": "runtime_d0_fractional_target_hp_special_damage_execution_envelope_v1",
    }


def _base(d0: Any, attacker: Any, target: Any, move: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(attacker) or not _owner(target) or not isinstance(move, Mapping):
        return None
    active = d0.get("active_owners")
    if attacker["side"] == target["side"] or not isinstance(active, Mapping) or d0.get("decision_owner") != dict(attacker) or active.get(attacker["side"]) != dict(attacker) or active.get(target["side"]) != dict(target):
        return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)), "move_id": move.get("move_id"), "canonical_move_metadata": deepcopy(dict(move))}


def _roster_row(state: Any, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None
    rows = side.get("pokemon") if isinstance(side, Mapping) else None
    row = rows.get(owner["slot_index"]) if isinstance(rows, Mapping) else rows[owner["slot_index"]] if isinstance(rows, list) and owner["slot_index"] < len(rows) else None
    return row if isinstance(row, Mapping) and row.get("pokemon_id") == owner["pokemon_id"] else None


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _hp(value: Any) -> bool:
    return isinstance(value, Mapping) and isinstance(value.get("current_hp"), int) and not isinstance(value.get("current_hp"), bool) and isinstance(value.get("max_hp"), int) and not isinstance(value.get("max_hp"), bool) and 0 < value["current_hp"] <= value["max_hp"]


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
