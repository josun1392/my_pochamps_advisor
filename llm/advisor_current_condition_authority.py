"""Detached strict authority for one Pokemon's current major condition."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


CONDITIONS = frozenset({"none", "burn", "poison", "toxic", "paralysis", "sleep", "freeze"})
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def project_current_condition_authority(
    *, session_id: str, source_runtime_fingerprint: str,
    source_branch_fingerprint: str, owner: Mapping[str, Any],
    current_condition: Any, current_condition_provenance: Any,
) -> dict[str, Any]:
    """Project only an explicit production current-condition observation.

    Reducer legacy condition records deliberately remain unknown here: an
    observed application or fixture-only removal is not evidence that the
    current condition has been freshly observed for this strict consumer.
    """
    if not _binding(session_id, source_runtime_fingerprint, source_branch_fingerprint, owner):
        return {"status": "rejected", "reason": "invalid_current_condition_authority_binding"}
    condition = _exact_condition(current_condition, current_condition_provenance)
    state = (
        {"status": "known_none", "provenance": "runtime_current_condition_observed"}
        if condition == "none" else
        {"status": "known_present", "condition": condition, "provenance": "runtime_current_condition_observed"}
        if condition is not None else
        {"status": "unknown", "reason": "runtime_current_condition_unknown"}
    )
    return {
        "status": "resolved", "schema_version": "runtime-current-condition-authority-v1",
        "session_id": session_id, "source_runtime_fingerprint": source_runtime_fingerprint,
        "source_branch_fingerprint": source_branch_fingerprint, "owner": deepcopy(dict(owner)),
        "condition": state,
        "provenance": "runtime_battle_state_v1_current_condition_projection_v1",
    }


def _exact_condition(value: Any, provenance: Any) -> str | None:
    if not isinstance(provenance, Mapping) or provenance.get("event_kind") != "current_condition_observed" or provenance.get("trust") != "user_confirmed_observation":
        return None
    turn = provenance.get("turn_number")
    if not isinstance(turn, int) or isinstance(turn, bool) or turn < 1:
        return None
    # Reducer-owned current state uses both ``None`` and the canonical string
    # ``"none"`` for an explicitly observed absence.  They are equivalent
    # only when the same trusted current-condition observation says ``none``.
    if (value is None or value == "none") and provenance.get("condition") == "none":
        return "none"
    return value if isinstance(value, str) and value in CONDITIONS - {"none"} and provenance.get("condition") == value else None


def _binding(session: Any, runtime: Any, branch: Any, owner: Any) -> bool:
    return (
        isinstance(session, str) and bool(session) and isinstance(runtime, str) and bool(runtime)
        and isinstance(branch, str) and bool(branch) and isinstance(owner, Mapping)
        and set(owner) == set(_OWNER_KEYS) and owner.get("session_id") == session
        and owner.get("side") in {"self", "opponent"}
        and isinstance(owner.get("slot_index"), int) and not isinstance(owner.get("slot_index"), bool)
        and owner["slot_index"] >= 0 and isinstance(owner.get("pokemon_id"), str) and bool(owner["pokemon_id"])
    )
