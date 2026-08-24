"""Detached, bounded current authority for crit-relevant reducer state."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


CRIT_VOLATILES = ("focus-energy", "lansat", "dragon-cheer")
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def project_current_crit_volatile_authority(*, session_id: str, source_runtime_fingerprint: str,
    source_branch_fingerprint: str, owner: Mapping[str, Any], current_crit_volatiles: Any,
) -> dict[str, Any]:
    """Project one exact bounded volatile observation without neutral defaults."""
    if not _owner_binding(session_id, source_runtime_fingerprint, source_branch_fingerprint, owner):
        return {"status": "rejected", "reason": "invalid_current_crit_volatile_authority_binding"}
    values = set(current_crit_volatiles) if _volatile_snapshot(current_crit_volatiles) else None
    states = {
        value: ({"status": "known_present", "provenance": "runtime_battle_state_v1"}
                if values is not None and value in values else
                {"status": "known_absent", "provenance": "runtime_battle_state_v1"}
                if values is not None else
                {"status": "unknown", "reason": "runtime_crit_volatile_unknown"})
        for value in CRIT_VOLATILES
    }
    return {
        "status": "resolved", "schema_version": "runtime-current-crit-volatile-authority-v1",
        "session_id": session_id, "source_runtime_fingerprint": source_runtime_fingerprint,
        "source_branch_fingerprint": source_branch_fingerprint, "owner": deepcopy(dict(owner)),
        "volatiles": states, "provenance": "runtime_battle_state_v1_current_crit_volatile_projection_v1",
    }


def project_current_lucky_chant_authority(*, session_id: str, source_runtime_fingerprint: str,
    source_branch_fingerprint: str, side: str, current_side_conditions: Any,
) -> dict[str, Any]:
    """Project the exact target-side Lucky Chant state, if observed as a full list."""
    if not _side_binding(session_id, source_runtime_fingerprint, source_branch_fingerprint, side):
        return {"status": "rejected", "reason": "invalid_current_lucky_chant_authority_binding"}
    exact = _side_snapshot(current_side_conditions)
    state = ({"status": "known_present", "provenance": "runtime_battle_state_v1"}
             if exact and "lucky-chant" in current_side_conditions else
             {"status": "known_absent", "provenance": "runtime_battle_state_v1"}
             if exact else
             {"status": "unknown", "reason": "runtime_side_conditions_unknown"})
    return {
        "status": "resolved", "schema_version": "runtime-current-lucky-chant-authority-v1",
        "session_id": session_id, "source_runtime_fingerprint": source_runtime_fingerprint,
        "source_branch_fingerprint": source_branch_fingerprint, "side": side,
        "lucky_chant": state, "provenance": "runtime_battle_state_v1_current_lucky_chant_projection_v1",
    }


def _volatile_snapshot(value: Any) -> bool:
    return isinstance(value, list) and len(value) == len(set(value)) and all(item in CRIT_VOLATILES for item in value)


def _side_snapshot(value: Any) -> bool:
    return isinstance(value, list) and len(value) == len(set(value)) and all(isinstance(item, str) and item for item in value)


def _owner_binding(session: Any, runtime: Any, branch: Any, owner: Any) -> bool:
    return _shared_binding(session, runtime, branch) and isinstance(owner, Mapping) and set(owner) == set(_OWNER_KEYS) and owner.get("session_id") == session and owner.get("side") in {"self", "opponent"} and isinstance(owner.get("slot_index"), int) and not isinstance(owner.get("slot_index"), bool) and owner["slot_index"] >= 0 and isinstance(owner.get("pokemon_id"), str) and bool(owner["pokemon_id"])


def _side_binding(session: Any, runtime: Any, branch: Any, side: Any) -> bool:
    return _shared_binding(session, runtime, branch) and side in {"self", "opponent"}


def _shared_binding(session: Any, runtime: Any, branch: Any) -> bool:
    return isinstance(session, str) and bool(session) and isinstance(runtime, str) and bool(runtime) and isinstance(branch, str) and bool(branch)
