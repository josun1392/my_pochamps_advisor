"""Frozen identity-bound opponent-defense authority for candidate-B Download."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "switch-entry-download-authority-v1"
_APPLICABILITY = frozenset({"applicable", "blocked", "unknown"})


def build_switch_entry_download_authority(*, session_id: str, source: Mapping[str, Any], target: Mapping[str, Any], applicability: str = "unknown", target_defense: int | str = "unknown", target_special_defense: int | str = "unknown") -> dict[str, Any]:
    source_identity, target_identity = _identity(source), _identity(target)
    if (not isinstance(session_id, str) or not session_id or target_identity["side"] != ("opponent" if source_identity["side"] == "self" else "self") or applicability not in _APPLICABILITY or any(value != "unknown" and (not isinstance(value, int) or isinstance(value, bool) or value <= 0) for value in (target_defense, target_special_defense))):
        raise ValueError("invalid_switch_entry_download_authority")
    return deepcopy({"schema_version": SCHEMA_VERSION, "session_id": session_id, "source": source_identity, "target": target_identity, "applicability": applicability, "target_defense": target_defense, "target_special_defense": target_special_defense})


def normalize_switch_entry_download_authority(value: Any, *, session_id: str, target: Mapping[str, Any]) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    try:
        expected = build_switch_entry_download_authority(session_id=session_id, source=value.get("source"), target=target, applicability=value.get("applicability"), target_defense=value.get("target_defense"), target_special_defense=value.get("target_special_defense"))
    except (TypeError, ValueError):
        return None
    return deepcopy(expected) if set(value) == set(expected) and all(value[key] == expected[key] for key in expected) else None


def _identity(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("invalid_switch_entry_download_identity")
    side, slot, pokemon_id = value.get("side"), value.get("slot_index"), value.get("pokemon_id")
    if side not in {"self", "opponent"} or not isinstance(slot, int) or isinstance(slot, bool) or slot < 0 or not isinstance(pokemon_id, str) or not pokemon_id:
        raise ValueError("invalid_switch_entry_download_identity")
    return {"side": side, "slot_index": slot, "pokemon_id": pokemon_id}
