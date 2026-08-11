"""Frozen identity-bound authorities required by non-damaging entry effects."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


_INTERACTION_STATUSES = frozenset({"applicable", "blocked", "unknown"})


def build_prospective_speed_stage(*, session_id: str, side: str, slot_index: int, pokemon_id: str, stage: int | str = "unknown") -> dict[str, Any]:
    identity = _identity(session_id=session_id, side=side, slot_index=slot_index, pokemon_id=pokemon_id)
    if stage != "unknown" and (not isinstance(stage, int) or isinstance(stage, bool) or not -6 <= stage <= 6):
        raise ValueError("invalid_prospective_speed_stage")
    return deepcopy({"schema_version": "prospective-speed-stage-v1", **identity, "stage": stage})


def normalize_prospective_speed_stage(value: Any, *, session_id: str, side: str, slot_index: int, pokemon_id: str) -> dict[str, Any]:
    unknown = build_prospective_speed_stage(session_id=session_id, side=side, slot_index=slot_index, pokemon_id=pokemon_id)
    if not isinstance(value, Mapping):
        return unknown
    try:
        expected = build_prospective_speed_stage(session_id=session_id, side=side, slot_index=slot_index, pokemon_id=pokemon_id, stage=value.get("stage"))
    except (TypeError, ValueError):
        return unknown
    return deepcopy(expected) if set(value) == set(expected) and all(value[key] == expected[key] for key in expected) else unknown


def build_prospective_entry_interactions(*, session_id: str, side: str, slot_index: int, pokemon_id: str, toxic_spikes: str = "unknown", sticky_web: str = "unknown") -> dict[str, Any]:
    identity = _identity(session_id=session_id, side=side, slot_index=slot_index, pokemon_id=pokemon_id)
    if toxic_spikes not in _INTERACTION_STATUSES or sticky_web not in _INTERACTION_STATUSES:
        raise ValueError("invalid_prospective_entry_interactions")
    return deepcopy({"schema_version": "prospective-entry-interactions-v1", **identity, "toxic_spikes": toxic_spikes, "sticky_web": sticky_web})


def normalize_prospective_entry_interactions(value: Any, *, session_id: str, side: str, slot_index: int, pokemon_id: str) -> dict[str, Any]:
    unknown = build_prospective_entry_interactions(session_id=session_id, side=side, slot_index=slot_index, pokemon_id=pokemon_id)
    if not isinstance(value, Mapping):
        return unknown
    try:
        expected = build_prospective_entry_interactions(session_id=session_id, side=side, slot_index=slot_index, pokemon_id=pokemon_id, toxic_spikes=value.get("toxic_spikes"), sticky_web=value.get("sticky_web"))
    except (TypeError, ValueError):
        return unknown
    return deepcopy(expected) if set(value) == set(expected) and all(value[key] == expected[key] for key in expected) else unknown


def _identity(*, session_id: str, side: str, slot_index: int, pokemon_id: str) -> dict[str, Any]:
    if not isinstance(session_id, str) or not session_id or side not in {"self", "opponent"} or not isinstance(slot_index, int) or isinstance(slot_index, bool) or slot_index < 0 or not isinstance(pokemon_id, str) or not pokemon_id:
        raise ValueError("invalid_prospective_entry_identity")
    return {"session_id": session_id, "side": side, "slot_index": slot_index, "pokemon_id": pokemon_id}
