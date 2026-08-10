"""Frozen Conservative projection of trusted self switch targets; no transition or ranking."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_reducer_state_model import is_unknown_battle_fact, validate_battle_state_unknown_markers
from llm.advisor_switch_permission import project_switch_permission_context, normalize_switch_permission_context


SCHEMA_VERSION = "switch-candidate-context-v2"
_TARGET_STATE_FACTS = ("current_hp", "max_hp", "condition", "known_item")


def build_switch_candidate_context_projection(runtime_state: Mapping[str, Any]) -> dict[str, Any]:
    """Project frozen roster identity and already-trusted target-owned facts."""
    if not isinstance(runtime_state, Mapping) or not validate_battle_state_unknown_markers(dict(runtime_state)):
        raise ValueError("invalid_switch_candidate_context")
    session_id, side = runtime_state.get("session_id"), runtime_state.get("self_side")
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    active = side.get("active_slot_index") if isinstance(side, Mapping) else None
    if not isinstance(session_id, str) or not session_id or not isinstance(active, int) or isinstance(active, bool) or not isinstance(roster, Mapping):
        raise ValueError("invalid_switch_candidate_context")
    entries = []
    for slot in sorted(roster):
        pokemon = roster[slot]
        if not isinstance(slot, int) or isinstance(slot, bool) or slot < 0 or not isinstance(pokemon, Mapping):
            raise ValueError("invalid_switch_candidate_context")
        pokemon_id = pokemon.get("pokemon_id")
        if not isinstance(pokemon_id, str) or not pokemon_id:
            raise ValueError("invalid_switch_candidate_context")
        fainted = pokemon.get("fainted")
        if is_unknown_battle_fact(fainted):
            fact = {"status": "unknown"}
        elif isinstance(fainted, bool):
            fact = {"status": "known", "value": fainted}
        else:
            raise ValueError("invalid_switch_candidate_context")
        entry = {"slot_index": slot, "pokemon_id": pokemon_id, "fainted": fact}
        for key in _TARGET_STATE_FACTS:
            entry[key] = _project_fact(pokemon.get(key))
        entries.append(entry)
    if active not in roster:
        raise ValueError("invalid_switch_candidate_context")
    return {"schema_version": SCHEMA_VERSION, "session_id": session_id, "self_active_slot_index": active, "self_pokemon": entries, "switch_permission_context": project_switch_permission_context(runtime_state)}


def normalize_switch_candidate_context_projection(value: Any, *, battle_input: Mapping[str, Any], session_id: str) -> dict[str, Any]:
    """Validate the frozen roster handoff against the UI-selected active identity."""
    if not isinstance(value, Mapping) or value.get("schema_version") != SCHEMA_VERSION or value.get("session_id") != session_id:
        raise ValueError("invalid_switch_candidate_context")
    entries, active = value.get("self_pokemon"), value.get("self_active_slot_index")
    pokemon = battle_input.get("pokemon") if isinstance(battle_input, Mapping) else None
    ui_active = pokemon.get("my_active") if isinstance(pokemon, Mapping) else None
    if not isinstance(entries, list) or not isinstance(active, int) or isinstance(active, bool) or not isinstance(ui_active, Mapping):
        raise ValueError("invalid_switch_candidate_context")
    if ui_active.get("slot_index") != active:
        raise ValueError("invalid_switch_candidate_context")
    result, slots = [], set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("invalid_switch_candidate_context")
        slot, pokemon_id, fainted = entry.get("slot_index"), entry.get("pokemon_id"), entry.get("fainted")
        if not isinstance(slot, int) or isinstance(slot, bool) or slot < 0 or slot in slots or not isinstance(pokemon_id, str) or not pokemon_id:
            raise ValueError("invalid_switch_candidate_context")
        if not isinstance(fainted, Mapping) or set(fainted) not in ({"status"}, {"status", "value"}):
            raise ValueError("invalid_switch_candidate_context")
        if fainted.get("status") == "unknown" and set(fainted) == {"status"}:
            fact = {"status": "unknown"}
        elif fainted.get("status") == "known" and set(fainted) == {"status", "value"} and isinstance(fainted.get("value"), bool):
            fact = {"status": "known", "value": fainted["value"]}
        else:
            raise ValueError("invalid_switch_candidate_context")
        normalized = {"slot_index": slot, "pokemon_id": pokemon_id, "fainted": fact}
        for key in _TARGET_STATE_FACTS:
            normalized[key] = _normalize_fact(entry.get(key))
        slots.add(slot); result.append(normalized)
    active_entry = next((entry for entry in result if entry["slot_index"] == active), None)
    if active_entry is None or active_entry["pokemon_id"] != ui_active.get("name_en"):
        raise ValueError("invalid_switch_candidate_context")
    permission = normalize_switch_permission_context(value.get("switch_permission_context"), session_id=session_id, active_slot_index=active, active_pokemon_id=ui_active.get("name_en"))
    return {"schema_version": SCHEMA_VERSION, "session_id": session_id, "self_active_slot_index": active, "self_pokemon": sorted(result, key=lambda entry: entry["slot_index"]), "switch_permission_context": permission}


def _project_fact(value: Any) -> dict[str, Any]:
    if is_unknown_battle_fact(value):
        return {"status": "unknown"}
    return {"status": "known", "value": deepcopy(value)}


def _normalize_fact(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) not in ({"status"}, {"status", "value"}):
        raise ValueError("invalid_switch_candidate_context")
    if value.get("status") == "unknown" and set(value) == {"status"}:
        return {"status": "unknown"}
    if value.get("status") == "known" and set(value) == {"status", "value"}:
        return {"status": "known", "value": deepcopy(value["value"])}
    raise ValueError("invalid_switch_candidate_context")


def build_switch_candidates(*, turn_snapshot: Any) -> list[dict[str, Any]]:
    """Enumerate potential bench targets from one frozen snapshot, never live state."""
    try:
        serialized = turn_snapshot.to_dict()
        current = serialized.get("current_state")
        context = current.get("switch_candidate_context") if isinstance(current, Mapping) else None
        if not isinstance(context, Mapping):
            return []
        session, active, entries = context.get("session_id"), context.get("self_active_slot_index"), context.get("self_pokemon")
        if not isinstance(session, str) or not isinstance(active, int) or not isinstance(entries, list):
            return []
    except (AttributeError, TypeError, ValueError):
        return []
    candidates = []
    for entry in entries:
        if not isinstance(entry, Mapping) or entry.get("slot_index") == active:
            continue
        slot, pokemon_id, fainted = entry.get("slot_index"), entry.get("pokemon_id"), entry.get("fainted")
        if not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(pokemon_id, str) or not pokemon_id or not isinstance(fainted, Mapping):
            continue
        permission = context.get("switch_permission_context")
        availability, legality, reason, selectable = "complete", "insufficient_context", "switch_legality_unknown", False
        if fainted.get("status") == "unknown":
            availability, legality, reason = "insufficient_context", "not_applicable", "target_availability_unknown"
        elif fainted.get("status") == "known" and fainted.get("value") is True:
            legality, reason = "not_applicable", "target_fainted"
        elif not (fainted.get("status") == "known" and fainted.get("value") is False):
            continue
        elif isinstance(permission, Mapping) and permission.get("status") == "permitted" and permission.get("supportability") == "complete":
            legality, reason, selectable = "complete", "switch_available", True
        elif isinstance(permission, Mapping) and permission.get("status") == "blocked" and permission.get("supportability") == "complete":
            legality, reason = "complete", "switch_blocked"
        candidates.append({
            "candidate_id": f"self-switch:{session}:{slot}:{pokemon_id}",
            "action_kind": "switch",
            "session_id": session,
            "target_pokemon_id": pokemon_id,
            "target_slot_index": slot,
            "identity_supportability": "complete",
            "availability_supportability": availability,
            "legality_supportability": legality,
            "selectable": selectable,
            "reason_code": reason,
        })
    return deepcopy(candidates)
