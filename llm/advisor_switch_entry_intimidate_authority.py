"""Frozen, identity-bound authority for candidate-B Intimidate on entry."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "switch-entry-intimidate-authority-v1"
_OUTCOMES = frozenset({"lowered", "blocked", "reversed", "unknown"})


def build_switch_entry_intimidate_authority(*, session_id: str, source: Mapping[str, Any], target: Mapping[str, Any], interaction: str = "unknown", target_attack_stage: int | str = "unknown") -> dict[str, Any]:
    """Build one detached source-B to opposing-active mechanics handoff.

    ``target_attack_stage`` is the opposing active's canonical, pre-entry
    Attack stage.  It is deliberately identity-bound so a stale active state
    cannot be applied to another opponent.
    """
    source_identity, target_identity = _identity(source), _identity(target)
    if (not isinstance(session_id, str) or not session_id or source_identity["side"] != "self" or target_identity["side"] != "opponent" or interaction not in _OUTCOMES or (target_attack_stage != "unknown" and (not isinstance(target_attack_stage, int) or isinstance(target_attack_stage, bool) or not -6 <= target_attack_stage <= 6))):
        raise ValueError("invalid_switch_entry_intimidate_authority")
    return deepcopy({"schema_version": SCHEMA_VERSION, "session_id": session_id, "source": source_identity, "target": target_identity, "interaction": interaction, "target_attack_stage": target_attack_stage})


def normalize_switch_entry_intimidate_authority(value: Any, *, session_id: str, target: Mapping[str, Any]) -> dict[str, Any] | None:
    """Accept only exact current-opponent records; malformed data stays absent."""
    if not isinstance(value, Mapping):
        return None
    try:
        expected = build_switch_entry_intimidate_authority(session_id=session_id, source=value.get("source"), target=target, interaction=value.get("interaction"), target_attack_stage=value.get("target_attack_stage"))
    except (TypeError, ValueError):
        return None
    return deepcopy(expected) if set(value) == set(expected) and all(value[key] == expected[key] for key in expected) else None


def _identity(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("invalid_switch_entry_intimidate_identity")
    side, slot, pokemon_id = value.get("side"), value.get("slot_index"), value.get("pokemon_id")
    if side not in {"self", "opponent"} or not isinstance(slot, int) or isinstance(slot, bool) or slot < 0 or not isinstance(pokemon_id, str) or not pokemon_id:
        raise ValueError("invalid_switch_entry_intimidate_identity")
    return {"side": side, "slot_index": slot, "pokemon_id": pokemon_id}
