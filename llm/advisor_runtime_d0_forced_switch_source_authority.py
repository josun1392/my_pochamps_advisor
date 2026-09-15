"""Runtime-bound pre-replacement source branch for forced switching."""
from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_reducer_state_model import STATE_MODEL_VERSION, state_fingerprint, validate_battle_state_unknown_markers
from llm.advisor_runtime_d0_persistent_effect_authority import project_runtime_d0_persistent_effect_branch
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0, runtime_strategy_d0_freshness
from llm.advisor_switch_hazard_authority import project_switch_hazard_context
from llm.advisor_transition_preview import fingerprint_transition_preview_state


SCHEMA_VERSION = "runtime-d0-forced-switch-source-authority-v1"
_PROVENANCE = "runtime_d0_forced_switch_source_authority_v1"


def freeze_runtime_d0_forced_switch_source_authority(*, runtime_snapshot: Mapping[str, Any], target_side: str) -> dict[str, Any]:
    """Freeze the exact active forced-switch target into a detached source branch.

    This boundary intentionally stops before replacement selection, entry effects,
    or runtime writeback.
    """
    state, session_id, runtime_fingerprint = _runtime_state(runtime_snapshot)
    if state is None:
        return _rejected("invalid_runtime_snapshot")
    target_owner = _active_owner(state, session_id, target_side)
    if target_owner is None:
        return _rejected("invalid_forced_switch_target_side_or_owner")
    strategy_d0 = freeze_runtime_strategy_d0(runtime_snapshot=runtime_snapshot, decision_owner=target_owner)
    if strategy_d0.get("status") != "resolved":
        return _rejected(strategy_d0.get("reason", "runtime_strategy_d0_unavailable"))
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _rejected(freshness.get("reason", "stale_runtime_d0"))
    if strategy_d0.get("source_runtime_fingerprint") != runtime_fingerprint or strategy_d0.get("active_owners", {}).get(target_side) != target_owner:
        return _rejected("runtime_d0_target_binding_mismatch")
    persistent = project_runtime_d0_persistent_effect_branch(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if persistent.get("status") != "resolved":
        return _rejected(persistent.get("reason", "persistent_effect_branch_unavailable"))
    branch = persistent.get("branch_state")
    persistent_fingerprint = persistent.get("resulting_branch_fingerprint")
    if not isinstance(branch, Mapping) or fingerprint_transition_preview_state(branch) != persistent_fingerprint or persistent.get("active_owners") != strategy_d0.get("active_owners") or branch.get("branch_persistent_effect_authority") != persistent.get("branch_persistent_effect_authority"):
        return _rejected("persistent_effect_branch_binding_mismatch")
    hazards = project_switch_hazard_context(state, affected_side=target_side)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, "session_id": session_id,
        "target_side": target_side, "target_owner": deepcopy(target_owner),
        "source_runtime_fingerprint": runtime_fingerprint,
        "source_strategy_preview_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "persistent_branch_fingerprint": persistent_fingerprint,
        "resulting_source_branch_fingerprint": persistent_fingerprint,
        "active_owners": deepcopy(strategy_d0["active_owners"]),
        "branch_state": deepcopy(dict(branch)),
        "switch_hazard_authority": deepcopy(hazards),
        "provenance": _PROVENANCE,
    }


def _runtime_state(snapshot: Any):
    if not isinstance(snapshot, Mapping) or snapshot.get("status") != "runtime_snapshot_ready":
        return None, None, None
    state, session_id, fingerprint = snapshot.get("state"), snapshot.get("session_id"), snapshot.get("state_fingerprint")
    if not isinstance(state, Mapping) or not isinstance(session_id, str) or not session_id or state.get("state_version") != STATE_MODEL_VERSION or state.get("session_id") != session_id or not validate_battle_state_unknown_markers(dict(state)) or not isinstance(fingerprint, str) or fingerprint != state_fingerprint(dict(state)):
        return None, None, None
    return deepcopy(dict(state)), session_id, fingerprint


def _active_owner(state: Mapping[str, Any], session_id: str, side: str):
    if side not in {"self", "opponent"}:
        return None
    container = state.get(f"{side}_side")
    roster = container.get("pokemon") if isinstance(container, Mapping) else None
    slot = container.get("active_slot_index") if isinstance(container, Mapping) else None
    pokemon = roster.get(slot, roster.get(str(slot))) if isinstance(roster, Mapping) else None
    if not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(pokemon, Mapping) or not isinstance(pokemon.get("pokemon_id"), str) or not pokemon["pokemon_id"]:
        return None
    return {"session_id": session_id, "side": side, "slot_index": slot, "pokemon_id": pokemon["pokemon_id"]}


def _rejected(reason: str):
    return {"status": "rejected", "reason": reason}
