"""Strict D0 projection of reducer current persistent effects to a detached branch."""
from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_persistent_effect_authority import materialize_persistent_effect_authority
from llm.advisor_reducer_state_model import STATE_MODEL_VERSION, state_fingerprint, validate_battle_state_unknown_markers
from llm.advisor_runtime_strategy_d0 import PREVIEW_SCHEMA, SCHEMA, runtime_strategy_d0_freshness
from llm.advisor_transition_preview import fingerprint_transition_preview_state


SCHEMA_VERSION = "runtime-d0-persistent-effect-branch-v1"
_FAMILIES = ("aqua_ring", "ingrain", "leech_seed")
_PROVENANCE = "runtime_current_persistent_effect_to_detached_branch_v1"


def project_runtime_d0_persistent_effect_branch(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Attach an unknown-first persistent-effect bundle to a fresh D0 branch."""
    state, session_id, runtime_fingerprint = _runtime_state(runtime_snapshot)
    if state is None:
        return _rejected("invalid_runtime_snapshot")
    if not _valid_strategy_d0(strategy_d0):
        return _rejected("invalid_strategy_d0")
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _rejected(freshness.get("reason", "stale_runtime_d0"))
    if strategy_d0.get("session_id") != session_id or strategy_d0.get("source_runtime_fingerprint") != runtime_fingerprint:
        return _rejected("runtime_d0_fingerprint_or_session_mismatch")
    preview = strategy_d0.get("strategy_state")
    preview_fingerprint = strategy_d0.get("strategy_preview_fingerprint")
    if not isinstance(preview, Mapping) or fingerprint_transition_preview_state(preview) != preview_fingerprint:
        return _rejected("strategy_preview_fingerprint_mismatch")
    owners = _active_owners(state, session_id)
    if owners is None or strategy_d0.get("active_owners") != owners:
        return _rejected("runtime_active_owner_mismatch")
    states = _persistent_states(state, owners)
    bundle = materialize_persistent_effect_authority(
        owners=owners, source_branch_fingerprint=preview_fingerprint, states=states,
    )
    branch = deepcopy(dict(preview))
    branch["branch_persistent_effect_authority"] = deepcopy(bundle)
    resulting_fingerprint = fingerprint_transition_preview_state(branch)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, "session_id": session_id,
        "source_runtime_fingerprint": runtime_fingerprint,
        "source_strategy_preview_fingerprint": preview_fingerprint,
        "resulting_branch_fingerprint": resulting_fingerprint,
        "active_owners": deepcopy(owners),
        "branch_persistent_effect_authority": deepcopy(bundle),
        "branch_state": deepcopy(branch),
        "provenance": _PROVENANCE,
    }


def _runtime_state(snapshot: Any):
    if not isinstance(snapshot, Mapping) or snapshot.get("status") != "runtime_snapshot_ready":
        return None, None, None
    state, session_id, fingerprint = snapshot.get("state"), snapshot.get("session_id"), snapshot.get("state_fingerprint")
    if not isinstance(state, Mapping) or not isinstance(session_id, str) or not session_id or state.get("state_version") != STATE_MODEL_VERSION or state.get("session_id") != session_id or not validate_battle_state_unknown_markers(dict(state)) or not isinstance(fingerprint, str) or fingerprint != state_fingerprint(dict(state)):
        return None, None, None
    return deepcopy(dict(state)), session_id, fingerprint


def _valid_strategy_d0(value: Any) -> bool:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != SCHEMA:
        return False
    preview = value.get("strategy_state")
    return isinstance(preview, Mapping) and preview.get("schema_version") == PREVIEW_SCHEMA and isinstance(value.get("source_runtime_fingerprint"), str) and isinstance(value.get("strategy_preview_fingerprint"), str) and fingerprint_transition_preview_state(preview) == value["strategy_preview_fingerprint"]


def _active_owners(state: Mapping[str, Any], session_id: str):
    owners = {}
    for side in ("self", "opponent"):
        container = state.get(f"{side}_side")
        roster = container.get("pokemon") if isinstance(container, Mapping) else None
        slot = container.get("active_slot_index") if isinstance(container, Mapping) else None
        pokemon = roster.get(slot, roster.get(str(slot))) if isinstance(roster, Mapping) else None
        if not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(pokemon, Mapping) or not isinstance(pokemon.get("pokemon_id"), str) or not pokemon["pokemon_id"]:
            return None
        owners[side] = {"session_id": session_id, "side": side, "slot_index": slot, "pokemon_id": pokemon["pokemon_id"]}
    return owners


def _persistent_states(state: Mapping[str, Any], owners: Mapping[str, Mapping[str, Any]]):
    context = state.get("current_persistent_effect_context")
    rows = context.get("rows") if isinstance(context, Mapping) else []
    result = {side: {} for side in owners}
    for side, owner in owners.items():
        for family in _FAMILIES:
            matched = next((row for row in rows if isinstance(row, Mapping) and row.get("family") == family and row.get("owner") == owner), None)
            status = matched.get("state") if isinstance(matched, Mapping) else None
            projected = {"state": "known_active" if status == "active" else "known_inactive" if status == "inactive" else "unknown"}
            if family == "leech_seed" and projected["state"] == "known_active" and isinstance(matched.get("source_slot"), Mapping):
                projected["source_slot"] = deepcopy(dict(matched["source_slot"]))
            result[side][family] = projected
    return result


def _rejected(reason: str):
    return {"status": "rejected", "reason": reason}
