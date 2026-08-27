"""Frozen identity-bound opposing-ability authority for candidate-B Trace."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "switch-entry-trace-authority-v1"
_TRACEABILITY = frozenset({"traceable", "untraceable", "unknown"})


def build_switch_entry_trace_authority(*, session_id: str, source: Mapping[str, Any], target: Mapping[str, Any], target_ability: str = "unknown", traceability: str = "unknown") -> dict[str, Any]:
    source_identity, target_identity = _identity(source), _identity(target)
    if (not isinstance(session_id, str) or not session_id or source_identity["side"] == target_identity["side"] or not isinstance(target_ability, str) or not target_ability or traceability not in _TRACEABILITY or (traceability != "unknown" and target_ability == "unknown")):
        raise ValueError("invalid_switch_entry_trace_authority")
    return deepcopy({"schema_version": SCHEMA_VERSION, "session_id": session_id, "source": source_identity, "target": target_identity, "target_ability": target_ability, "traceability": traceability})


def normalize_switch_entry_trace_authority(value: Any, *, session_id: str, target: Mapping[str, Any]) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    try:
        expected = build_switch_entry_trace_authority(session_id=session_id, source=value.get("source"), target=target, target_ability=value.get("target_ability"), traceability=value.get("traceability"))
    except (TypeError, ValueError):
        return None
    return deepcopy(expected) if set(value) == set(expected) and all(value[key] == expected[key] for key in expected) else None


def _identity(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("invalid_switch_entry_trace_identity")
    side, slot, pokemon_id = value.get("side"), value.get("slot_index"), value.get("pokemon_id")
    if side not in {"self", "opponent"} or not isinstance(slot, int) or isinstance(slot, bool) or slot < 0 or not isinstance(pokemon_id, str) or not pokemon_id:
        raise ValueError("invalid_switch_entry_trace_identity")
    return {"side": side, "slot_index": slot, "pokemon_id": pokemon_id}
