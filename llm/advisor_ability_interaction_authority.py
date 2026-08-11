"""Frozen trusted ability-applicability and source-target interaction authority.

This module deliberately records prerequisites for a future ability mechanic; it
does not decide any ability effect.  In particular, a raw ability identity is
never enough to make a mechanics claim.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "ability-interaction-authority-v1"
_APPLICABILITY = frozenset({"applicable", "not_applicable", "unknown"})
_INTERACTION = frozenset({"affecting", "not_affecting", "unknown"})


def build_ability_applicability_context(*, session_id: str, source: Mapping[str, Any], ability_id: str, status: str = "unknown") -> dict[str, Any]:
    """Build detached source-owned applicability, independent of interaction."""
    source_identity = _identity(source)
    if not isinstance(session_id, str) or not session_id or not isinstance(ability_id, str) or not ability_id or status not in _APPLICABILITY:
        raise ValueError("invalid_ability_applicability_context")
    return deepcopy({"schema_version": "ability-applicability-context-v1", "session_id": session_id, "source": source_identity, "ability_id": ability_id, "status": status})


def normalize_ability_applicability_context(value: Any, *, session_id: str, source: Mapping[str, Any], ability_id: str) -> dict[str, Any]:
    unknown = build_ability_applicability_context(session_id=session_id, source=source, ability_id=ability_id)
    if not isinstance(value, Mapping):
        return unknown
    try:
        expected = build_ability_applicability_context(session_id=session_id, source=source, ability_id=ability_id, status=value.get("status"))
    except (TypeError, ValueError):
        return unknown
    return deepcopy(expected) if set(value) == set(expected) and all(value[key] == expected[key] for key in expected) else unknown


def build_ability_interaction_context(*, session_id: str, source: Mapping[str, Any], target: Mapping[str, Any], status: str = "unknown") -> dict[str, Any]:
    """Build detached exact source-target interaction, independent of ability identity."""
    source_identity = _identity(source)
    target_identity = _identity(target)
    if not isinstance(session_id, str) or not session_id or status not in _INTERACTION or source_identity["side"] == target_identity["side"]:
        raise ValueError("invalid_ability_interaction_context")
    return deepcopy({"schema_version": "ability-interaction-context-v1", "session_id": session_id, "source": source_identity, "target": target_identity, "status": status})


def normalize_ability_interaction_context(value: Any, *, session_id: str, source: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    unknown = build_ability_interaction_context(session_id=session_id, source=source, target=target)
    if not isinstance(value, Mapping):
        return unknown
    try:
        expected = build_ability_interaction_context(session_id=session_id, source=source, target=target, status=value.get("status"))
    except (TypeError, ValueError):
        return unknown
    return deepcopy(expected) if set(value) == set(expected) and all(value[key] == expected[key] for key in expected) else unknown


def project_ability_interaction_authority(runtime_state: Mapping[str, Any]) -> dict[str, Any]:
    """Combine two canonical reducer facts into one detached mechanic handoff."""
    session_id = runtime_state.get("session_id") if isinstance(runtime_state, Mapping) else None
    source = _active_identity(runtime_state, "opponent")
    target = _active_identity(runtime_state, "self")
    raw_applicability = runtime_state.get("ability_applicability_context") if isinstance(runtime_state, Mapping) else None
    ability_id = raw_applicability.get("ability_id") if isinstance(raw_applicability, Mapping) else None
    if not isinstance(session_id, str) or not session_id or source is None or target is None or not isinstance(ability_id, str) or not ability_id:
        raise ValueError("invalid_ability_interaction_projection")
    applicability = normalize_ability_applicability_context(raw_applicability, session_id=session_id, source=source, ability_id=ability_id)
    interaction = normalize_ability_interaction_context(runtime_state.get("ability_interaction_context"), session_id=session_id, source=source, target=target)
    return build_ability_interaction_authority(session_id=session_id, source=source, target=target, ability_id=ability_id, applicability=applicability["status"], interaction=interaction["status"])


def unknown_ability_interaction_authority(
    *, session_id: str, source: Mapping[str, Any], target: Mapping[str, Any], ability_id: str,
) -> dict[str, Any]:
    """Return detached unknown evidence for one exact source/target pair."""
    return build_ability_interaction_authority(
        session_id=session_id,
        source=source,
        target=target,
        ability_id=ability_id,
        applicability="unknown",
        interaction="unknown",
    )


def build_ability_interaction_authority(
    *,
    session_id: str,
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    ability_id: str,
    applicability: str = "unknown",
    interaction: str = "unknown",
) -> dict[str, Any]:
    """Build detached exact-identity evidence without inferring an ability effect."""
    source_identity = _identity(source)
    target_identity = _identity(target)
    if (
        not isinstance(session_id, str)
        or not session_id
        or not isinstance(ability_id, str)
        or not ability_id
        or applicability not in _APPLICABILITY
        or interaction not in _INTERACTION
        or source_identity["side"] == target_identity["side"]
    ):
        raise ValueError("invalid_ability_interaction_authority")
    return deepcopy(
        {
            "schema_version": SCHEMA_VERSION,
            "session_id": session_id,
            "source": source_identity,
            "target": target_identity,
            "ability_id": ability_id,
            "applicability": applicability,
            "interaction": interaction,
        }
    )


def normalize_ability_interaction_authority(
    value: Any,
    *,
    session_id: str,
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    ability_id: str,
) -> dict[str, Any]:
    """Fail stale, forged, malformed, or legacy evidence closed to exact unknown."""
    unknown = unknown_ability_interaction_authority(
        session_id=session_id, source=source, target=target, ability_id=ability_id,
    )
    if not isinstance(value, Mapping):
        return unknown
    try:
        expected = build_ability_interaction_authority(
            session_id=session_id,
            source=source,
            target=target,
            ability_id=ability_id,
            applicability=value.get("applicability"),
            interaction=value.get("interaction"),
        )
    except (TypeError, ValueError):
        return unknown
    if set(value) != set(expected) or any(value[key] != expected[key] for key in expected):
        return unknown
    return deepcopy(expected)


def ability_mechanic_prerequisite(authority: Any) -> dict[str, str]:
    """State whether a consumer may evaluate its own rule, never that rule's result."""
    if not _is_structurally_valid(authority):
        return {"status": "insufficient_context"}
    if authority.get("applicability") == "applicable" and authority.get("interaction") == "affecting":
        return {"status": "complete"}
    if authority.get("applicability") == "not_applicable" or authority.get("interaction") == "not_affecting":
        return {"status": "not_applicable"}
    return {"status": "insufficient_context"}


def _is_structurally_valid(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    try:
        expected = build_ability_interaction_authority(
            session_id=value.get("session_id"),
            source=value.get("source"),
            target=value.get("target"),
            ability_id=value.get("ability_id"),
            applicability=value.get("applicability"),
            interaction=value.get("interaction"),
        )
    except (TypeError, ValueError):
        return False
    return set(value) == set(expected) and all(value[key] == expected[key] for key in expected)


def _identity(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("invalid_ability_interaction_identity")
    side = value.get("side")
    slot_index = value.get("slot_index")
    pokemon_id = value.get("pokemon_id")
    if (
        side not in {"self", "opponent"}
        or not isinstance(slot_index, int)
        or isinstance(slot_index, bool)
        or slot_index < 0
        or not isinstance(pokemon_id, str)
        or not pokemon_id
    ):
        raise ValueError("invalid_ability_interaction_identity")
    return {"side": side, "slot_index": slot_index, "pokemon_id": pokemon_id}


def _active_identity(state: Mapping[str, Any], side: str) -> dict[str, Any] | None:
    side_state = state.get(f"{side}_side") if isinstance(state, Mapping) else None
    roster = side_state.get("pokemon") if isinstance(side_state, Mapping) else None
    slot = side_state.get("active_slot_index") if isinstance(side_state, Mapping) else None
    pokemon = roster.get(slot, roster.get(str(slot))) if isinstance(roster, Mapping) else None
    pokemon_id = pokemon.get("pokemon_id", pokemon.get("name_en")) if isinstance(pokemon, Mapping) else None
    try:
        return _identity({"side": side, "slot_index": slot, "pokemon_id": pokemon_id})
    except ValueError:
        return None
