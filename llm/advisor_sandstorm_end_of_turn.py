"""Sandstorm-only detached EOT adapter for the deterministic Turn Engine."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_battle_state_context import normalize_current_type_authority, normalize_user_confirmed_current_ability
from llm.advisor_sandstorm_residual_core import evaluate_sandstorm_residual
from llm.advisor_transition_preview import fingerprint_transition_preview_state


def project_sandstorm_end_of_turn(*, pre_end_of_turn: Mapping[str, Any]) -> dict[str, Any]:
    """Apply exact Sandstorm residuals only when no poison/Toxic order is needed."""
    if not isinstance(pre_end_of_turn, Mapping) or pre_end_of_turn.get("status") != "resolved" or pre_end_of_turn.get("boundary", {}).get("phase") != "pre_end_of_turn":
        return _result("rejected", "pre_end_of_turn_boundary_required")
    source = pre_end_of_turn.get("next_state")
    source_fp = fingerprint_transition_preview_state(source) if isinstance(source, Mapping) else None
    if source_fp is None:
        return _result("rejected", "invalid_pre_end_of_turn_branch")
    state = deepcopy(dict(source))
    owners = _owners(state)
    if owners is None:
        return _result("rejected", "invalid_active_owner")
    if not _sandstorm_field_authority(state, source_fp, owners["self"]["session_id"]):
        return _result("rejected", "stale_or_invalid_branch_sandstorm_authority")
    if _requires_residual_ordering(state):
        return _result("incomplete", "sandstorm_residual_ordering_unresolved")
    types = {side: _types(state, side) for side in ("self", "opponent")}
    abilities = {side: _ability(state, side) for side in ("self", "opponent")}
    items = {side: _item(state, side) for side in ("self", "opponent")}
    if any(value is None for value in types.values()):
        return _result("incomplete", "sandstorm_current_type_authority")
    if any(value is None for value in abilities.values()):
        return _result("incomplete", "sandstorm_current_ability_authority")
    if any(value is _UNKNOWN for value in items.values()):
        return _result("incomplete", "sandstorm_current_item_authority")
    trace: list[dict[str, Any]] = []
    for side in ("self", "opponent"):
        active = state["active"][side]
        if active["fainted"]:
            continue
        residual = evaluate_sandstorm_residual(current_type=types[side], item=items[side], active_abilities=abilities, target_side=side, current_hp=active["current_hp"], maximum_hp=active["max_hp"])
        if residual.get("status") != "complete":
            return _result("incomplete", "canonical_sandstorm_residual_authority")
        active["current_hp"], active["fainted"] = residual["post_hp"], residual["post_hp"] == 0
        _sync_hp(state, side, residual["post_hp"], residual["max_hp"])
        trace.append({"sequence": len(trace) + 1, "effect": "sandstorm_residual", "owner": deepcopy(owners[side]), "weather": "sandstorm", "execution_status": "prevented" if residual["residual_damage"] == 0 else "executed", "provenance": "detached_branch_sandstorm_residual_v1", **deepcopy(residual)})
    return {"status": "resolved", "source_pre_end_of_turn_fingerprint": source_fp, "resulting_branch_fingerprint": fingerprint_transition_preview_state(state), "eot_consequence_trace": trace, "next_state": state, "boundary": {"phase": "end_of_turn"}, "limitations": ["sandstorm_residual_only", "poison_or_toxic_ordering_fails_closed", "no_reducer_or_runtime_writeback"]}


_UNKNOWN = object()


def _owners(state: Mapping[str, Any]) -> dict[str, dict[str, Any]] | None:
    active = state.get("active") if isinstance(state, Mapping) else None
    owners: dict[str, dict[str, Any]] = {}
    for side in ("self", "opponent"):
        row = active.get(side) if isinstance(active, Mapping) else None
        if not isinstance(row, Mapping) or row.get("side") != side or not isinstance(row.get("session_id"), str) or not row["session_id"] or isinstance(row.get("slot_index"), bool) or not isinstance(row.get("slot_index"), int) or row["slot_index"] < 0 or not isinstance(row.get("pokemon_id"), str) or not row["pokemon_id"] or any(isinstance(row.get(key), bool) or not isinstance(row.get(key), int) for key in ("current_hp", "max_hp")) or row["max_hp"] < 1 or not 0 <= row["current_hp"] <= row["max_hp"] or row.get("fainted") is not (row["current_hp"] == 0):
            return None
        owners[side] = {key: row[key] for key in ("session_id", "side", "slot_index", "pokemon_id")}
    return owners if owners["self"]["session_id"] == owners["opponent"]["session_id"] else None


def _sandstorm_field_authority(state: Mapping[str, Any], source_fp: str, session: str) -> bool:
    context = state.get("branch_field_weather_context")
    current = state.get("current_state") if isinstance(state, Mapping) else None
    field = current.get("field_state_context", {}).get("current_field") if isinstance(current, Mapping) and isinstance(current.get("field_state_context"), Mapping) else None
    required = {"schema_version", "session_id", "scope", "source_branch_fingerprint", "provenance", "weather"}
    return isinstance(context, Mapping) and set(context) == required and context.get("schema_version") == "detached-field-weather-v1" and context.get("session_id") == session and context.get("scope") == "battle_field" and isinstance(context.get("source_branch_fingerprint"), str) and bool(context["source_branch_fingerprint"]) and context.get("provenance") == "frozen_field_state_context" and context.get("weather") == "sandstorm" and isinstance(field, Mapping) and field.get("weather") == "sandstorm" and source_fp == fingerprint_transition_preview_state(state)


def _requires_residual_ordering(state: Mapping[str, Any]) -> bool:
    predicted = state.get("predicted_condition_context")
    if isinstance(predicted, Mapping) and predicted.get("condition_type") in {"poison", "toxic"}:
        return True
    current = state.get("current_state") if isinstance(state, Mapping) else None
    rows = current.get("condition_context", {}).get("current_conditions") if isinstance(current, Mapping) and isinstance(current.get("condition_context"), Mapping) else None
    return any(isinstance(row, Mapping) and row.get("condition_type") in {"poison", "toxic"} for row in rows) if isinstance(rows, list) else False


def _types(state: Mapping[str, Any], side: str) -> list[str] | None:
    current = state.get("current_state") if isinstance(state, Mapping) else None
    rows = current.get("current_type_context", {}).get("current_types") if isinstance(current, Mapping) and isinstance(current.get("current_type_context"), Mapping) else None
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("side") == side] if isinstance(rows, list) else []
    if len(matches) != 1:
        return None
    try:
        normalized = normalize_current_type_authority(matches[0])
    except ValueError:
        return None
    return normalized["types"] if normalized.get("state") == "known" else None


def _ability(state: Mapping[str, Any], side: str) -> str | None:
    current = state.get("current_state") if isinstance(state, Mapping) else None
    rows = current.get("ability_context", {}).get("current_abilities") if isinstance(current, Mapping) and isinstance(current.get("ability_context"), Mapping) else None
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("side") == side] if isinstance(rows, list) else []
    if len(matches) != 1:
        return None
    try:
        return normalize_user_confirmed_current_ability(matches[0])["ability"]
    except ValueError:
        return None


def _item(state: Mapping[str, Any], side: str) -> str | None | object:
    current = state.get("current_state") if isinstance(state, Mapping) else None
    direct = current.get("direct_mechanics_context") if isinstance(current, Mapping) else None
    record = direct.get("attacker" if side == "self" else "defender") if isinstance(direct, Mapping) else None
    item = record.get("item") if isinstance(record, Mapping) else None
    if item == {"status": "known_absent"}:
        return None
    if isinstance(item, Mapping) and item.get("status") == "known" and set(item) == {"status", "value"} and (item.get("value") is None or isinstance(item.get("value"), str)):
        return item["value"]
    return _UNKNOWN


def _sync_hp(state: Mapping[str, Any], side: str, hp: int, maximum: int) -> None:
    current = state.get("current_state") if isinstance(state, Mapping) else None
    rows = current.get("current_hp_context", {}).get("current_hp") if isinstance(current, Mapping) and isinstance(current.get("current_hp_context"), Mapping) else None
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("side") == side:
                row["current_hp"], row["maximum_hp"] = hp, maximum
    direct = current.get("direct_mechanics_context") if isinstance(current, Mapping) else None
    record = direct.get("attacker" if side == "self" else "defender") if isinstance(direct, Mapping) else None
    if isinstance(record, dict):
        record["current_hp"], record["max_hp"] = hp, maximum


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
