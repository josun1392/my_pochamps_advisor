"""Private frozen, identity-bound self-roster mechanics authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from llm.advisor_reducer_state_model import is_unknown_battle_fact, validate_battle_state_unknown_markers
from llm.advisor_identity_groundedness import normalize_groundedness


SCHEMA_VERSION = "self-roster-mechanics-context-v1"
_AUTHORITY_KEYS = (
    "current_type_authority", "base_stat_authority", "final_stat_authority", "ability_authority",
    "item_authority", "hp_authority", "fainted_authority", "persistent_condition_authority",
    "prospective_groundedness_authority",
)


def build_self_roster_mechanics_context_projection(
    runtime_state: Mapping[str, Any], *, roster_mechanics_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Freeze runtime roster facts plus optional already identity-bound mechanics.

    Optional records are validation-only handoffs for facts captured elsewhere;
    they never borrow a fact from another slot or from species metadata.
    """
    if not isinstance(runtime_state, Mapping) or not validate_battle_state_unknown_markers(dict(runtime_state)):
        raise ValueError("invalid_roster_mechanics_context")
    session, side = runtime_state.get("session_id"), runtime_state.get("self_side")
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    if not isinstance(session, str) or not session or not isinstance(roster, Mapping):
        raise ValueError("invalid_roster_mechanics_context")
    supplied = _records_by_identity(roster_mechanics_records, session=session)
    entries = []
    for slot in sorted(roster):
        pokemon = roster[slot]
        if not isinstance(slot, int) or isinstance(slot, bool) or slot < 0 or not isinstance(pokemon, Mapping):
            raise ValueError("invalid_roster_mechanics_context")
        pokemon_id = pokemon.get("pokemon_id")
        if not isinstance(pokemon_id, str) or not pokemon_id:
            raise ValueError("invalid_roster_mechanics_context")
        identity = (slot, pokemon_id)
        record = _base_record(session, slot, pokemon_id, pokemon)
        if identity in supplied:
            record.update(supplied[identity])
        entries.append(record)
    return {"schema_version": SCHEMA_VERSION, "session_id": session, "side": "self", "entries": entries}


def normalize_self_roster_mechanics_context_projection(value: Any, *, session_id: str, active_slot_index: int, active_pokemon_id: str) -> dict[str, Any]:
    """Validate a bounded frozen handoff against the selected active identity."""
    if not isinstance(value, Mapping) or value.get("schema_version") != SCHEMA_VERSION or value.get("session_id") != session_id or value.get("side") != "self":
        raise ValueError("invalid_roster_mechanics_context")
    entries = value.get("entries")
    if not isinstance(entries, list):
        raise ValueError("invalid_roster_mechanics_context")
    result, seen = [], set()
    for raw in entries:
        normalized = _normalize_record(raw, session_id=session_id)
        identity = (normalized["slot_index"], normalized["pokemon_id"])
        if identity in seen:
            raise ValueError("invalid_roster_mechanics_context")
        seen.add(identity); result.append(normalized)
    active = next((row for row in result if row["slot_index"] == active_slot_index and row["pokemon_id"] == active_pokemon_id), None)
    if active is None:
        raise ValueError("invalid_roster_mechanics_context")
    return {"schema_version": SCHEMA_VERSION, "session_id": session_id, "side": "self", "entries": sorted(result, key=lambda row: row["slot_index"])}


def active_self_roster_mechanics_view(context: Mapping[str, Any], *, slot_index: int, pokemon_id: str) -> dict[str, Any] | None:
    """Return a detached active view from one roster source of truth."""
    if not isinstance(context, Mapping) or context.get("side") != "self":
        return None
    entries = context.get("entries")
    if not isinstance(entries, list):
        return None
    match = next((row for row in entries if isinstance(row, Mapping) and row.get("slot_index") == slot_index and row.get("pokemon_id") == pokemon_id), None)
    return deepcopy(dict(match)) if isinstance(match, Mapping) else None


def _base_record(session: str, slot: int, pokemon_id: str, pokemon: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "session_id": session, "side": "self", "slot_index": slot, "pokemon_id": pokemon_id,
        "current_type_authority": _unknown_authority(),
        "base_stat_authority": _unknown_authority(),
        "final_stat_authority": _unknown_authority(),
        "ability_authority": _unknown_authority(),
        "item_authority": _fact_authority(pokemon.get("known_item")),
        "hp_authority": {
            "status": "unknown" if is_unknown_battle_fact(pokemon.get("current_hp")) or is_unknown_battle_fact(pokemon.get("max_hp")) else "known",
            "current_hp": None if is_unknown_battle_fact(pokemon.get("current_hp")) else deepcopy(pokemon.get("current_hp")),
            "maximum_hp": None if is_unknown_battle_fact(pokemon.get("max_hp")) else deepcopy(pokemon.get("max_hp")),
            "provenance": "unqualified_runtime_state",
        },
        "fainted_authority": _fact_authority(pokemon.get("fainted")),
        "persistent_condition_authority": _fact_authority(pokemon.get("condition")),
        # B-owned observation only.  Unknown is intentional; active A's
        # groundedness is never projected into another roster identity.
        "prospective_groundedness_authority": _prospective_groundedness(
            pokemon.get("prospective_groundedness_context"),
            session=session,
            slot=slot,
            pokemon_id=pokemon_id,
        ),
    }


def _records_by_identity(records: Sequence[Mapping[str, Any]] | None, *, session: str) -> dict[tuple[int, str], dict[str, Any]]:
    if records is None:
        return {}
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise ValueError("invalid_roster_mechanics_context")
    result = {}
    for raw in records:
        normalized = _normalize_record(raw, session_id=session)
        identity = (normalized["slot_index"], normalized["pokemon_id"])
        if identity in result:
            raise ValueError("invalid_roster_mechanics_context")
        result[identity] = normalized
    return result


def _normalize_record(raw: Any, *, session_id: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or raw.get("session_id") != session_id or raw.get("side") != "self":
        raise ValueError("invalid_roster_mechanics_context")
    slot, pokemon_id = raw.get("slot_index"), raw.get("pokemon_id")
    if not isinstance(slot, int) or isinstance(slot, bool) or slot < 0 or not isinstance(pokemon_id, str) or not pokemon_id:
        raise ValueError("invalid_roster_mechanics_context")
    if set(raw) != {"session_id", "side", "slot_index", "pokemon_id", *_AUTHORITY_KEYS}:
        raise ValueError("invalid_roster_mechanics_context")
    return {"session_id": session_id, "side": "self", "slot_index": slot, "pokemon_id": pokemon_id, **{key: _normalize_authority(raw[key], key=key) for key in _AUTHORITY_KEYS}}


def _unknown_authority() -> dict[str, Any]:
    return {"status": "unknown"}


def _fact_authority(value: Any) -> dict[str, Any]:
    return _unknown_authority() if is_unknown_battle_fact(value) else {"status": "known", "value": deepcopy(value)}


def _normalize_authority(value: Any, *, key: str) -> dict[str, Any]:
    if key == "prospective_groundedness_authority":
        if not isinstance(value, Mapping) or value.get("status") not in {"grounded", "ungrounded", "unknown"}:
            raise ValueError("invalid_roster_mechanics_context")
        if set(value) != {"status"}:
            raise ValueError("invalid_roster_mechanics_context")
        return deepcopy(dict(value))
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "unknown", "unsupported_mechanic", "malformed", "omitted_legacy"}:
        raise ValueError("invalid_roster_mechanics_context")
    status = value["status"]
    if key == "hp_authority":
        allowed = {"status", "current_hp", "maximum_hp", "provenance"}
        if set(value) != allowed or not isinstance(value.get("provenance"), str):
            raise ValueError("invalid_roster_mechanics_context")
        if status == "known" and (not isinstance(value.get("current_hp"), int) or isinstance(value.get("current_hp"), bool) or not isinstance(value.get("maximum_hp"), int) or isinstance(value.get("maximum_hp"), bool)):
            raise ValueError("invalid_roster_mechanics_context")
        return deepcopy(dict(value))
    if status == "known":
        if set(value) != {"status", "value"}:
            raise ValueError("invalid_roster_mechanics_context")
    elif set(value) != {"status"}:
        raise ValueError("invalid_roster_mechanics_context")
    return deepcopy(dict(value))


def _prospective_groundedness(value: Any, *, session: str, slot: int, pokemon_id: str) -> dict[str, Any]:
    """Project only a record owned by this exact prospective roster identity."""
    normalized = normalize_groundedness(
        value, session_id=session, side="self", slot_index=slot, pokemon_id=pokemon_id,
    )
    return {"status": normalized["status"]}
