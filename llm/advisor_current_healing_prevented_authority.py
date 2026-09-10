"""Strict projection of one Pokémon\'s observed current Healing Prevented state."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "runtime-d0-current-healing-prevented-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def project_current_healing_prevented_authority(
    *, session_id: str, source_runtime_fingerprint: str,
    source_branch_fingerprint: str, decision_owner: Mapping[str, Any], recipient: Mapping[str, Any],
    healing_prevented_status: Any, healing_prevented_status_provenance: Any,
) -> dict[str, Any]:
    """Freeze an explicit current observation without deriving absence.

    This producer intentionally models only the three current-state facts that
    the detached item-check consumer can safely use.  Lifecycle duration and
    move-origin transitions remain outside this observation boundary.
    """
    base = _base(session_id, source_runtime_fingerprint, source_branch_fingerprint, decision_owner, recipient)
    if base is None:
        return _result("rejected", "invalid_current_healing_prevented_authority_binding", {})
    if not _observed(healing_prevented_status, healing_prevented_status_provenance):
        return _result("incomplete", "current_healing_prevented_unknown", base)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "state": "known_present" if healing_prevented_status == "active" else "known_absent",
        "source_observation_provenance": deepcopy(dict(healing_prevented_status_provenance)),
        "provenance": "runtime_d0_reducer_owned_current_healing_prevented_observation_v1",
    }


def _base(session: Any, runtime: Any, branch: Any, decision_owner: Any, recipient: Any) -> dict[str, Any] | None:
    if not all(isinstance(value, str) and bool(value) for value in (session, runtime, branch)):
        return None
    if not isinstance(decision_owner, Mapping) or set(decision_owner) != set(_OWNER_KEYS):
        return None
    if decision_owner.get("session_id") != session or decision_owner.get("side") not in {"self", "opponent"}:
        return None
    if not isinstance(decision_owner.get("slot_index"), int) or isinstance(decision_owner["slot_index"], bool) or decision_owner["slot_index"] < 0:
        return None
    if not isinstance(decision_owner.get("pokemon_id"), str) or not decision_owner["pokemon_id"]:
        return None
    if not isinstance(recipient, Mapping) or set(recipient) != set(_OWNER_KEYS):
        return None
    if recipient.get("session_id") != session or recipient.get("side") not in {"self", "opponent"}:
        return None
    if not isinstance(recipient.get("slot_index"), int) or isinstance(recipient["slot_index"], bool) or recipient["slot_index"] < 0:
        return None
    if not isinstance(recipient.get("pokemon_id"), str) or not recipient["pokemon_id"]:
        return None
    return {
        "session_id": session, "source_runtime_fingerprint": runtime,
        "source_branch_fingerprint": branch, "decision_owner": deepcopy(dict(decision_owner)),
        "recipient": deepcopy(dict(recipient)),
    }


def _observed(value: Any, provenance: Any) -> bool:
    return (
        isinstance(value, str) and value in {"active", "inactive"}
        and isinstance(provenance, Mapping)
        and provenance.get("event_kind") == "current_healing_prevented_observed"
        and provenance.get("trust") == "user_confirmed_observation"
        and provenance.get("status") == value
        and isinstance(provenance.get("turn_number"), int)
        and not isinstance(provenance["turn_number"], bool) and provenance["turn_number"] >= 1
        and isinstance(provenance.get("source_observation_id"), str)
        and bool(provenance["source_observation_id"])
        and isinstance(provenance.get("source_sequence"), int)
        and not isinstance(provenance["source_sequence"], bool) and provenance["source_sequence"] >= 1
    )


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "state": "unknown", "reason": reason}
