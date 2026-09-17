"""Shared authoritative admission for explicit current-state UI facts."""
from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_lifecycle_confirmation import (
    CURRENT_ABILITY_SOURCE, CURRENT_BATTLE_FORMAT_SOURCE, CURRENT_ITEM_SOURCE,
    CURRENT_LEVEL_SOURCE, CURRENT_SIDE_CONDITIONS_SOURCE, CURRENT_TERRAIN_SOURCE, CURRENT_TYPE_SOURCE,
    CURRENT_WEATHER_SOURCE, FINAL_COMBAT_STAT_SOURCE, HP_RECOVERY_SOURCE, HP_TRANSITION_SOURCE,
    STAT_STAGE_SOURCE, TAILWIND_SOURCE, TRICK_ROOM_SOURCE, USER_TRUST, LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager


_SOURCES = {
    "current_type_observed": CURRENT_TYPE_SOURCE,
    "current_ability_observed": CURRENT_ABILITY_SOURCE,
    "current_item_observed": CURRENT_ITEM_SOURCE,
    "stat_stage_observed": STAT_STAGE_SOURCE,
    "current_final_combat_stat_observed": FINAL_COMBAT_STAT_SOURCE,
    "current_level_observed": CURRENT_LEVEL_SOURCE,
    "exact_hp_transition_observed": HP_TRANSITION_SOURCE,
    "exact_hp_recovery_observed": HP_RECOVERY_SOURCE,
    "current_weather_observed": CURRENT_WEATHER_SOURCE,
    "current_terrain_observed": CURRENT_TERRAIN_SOURCE,
    "current_side_conditions_observed": CURRENT_SIDE_CONDITIONS_SOURCE,
    "current_battle_format_observed": CURRENT_BATTLE_FORMAT_SOURCE,
    "trick_room_field_observed": TRICK_ROOM_SOURCE,
    "tailwind_side_condition_observed": TAILWIND_SOURCE,
}
_GLOBAL = {"current_weather_observed", "current_terrain_observed", "current_battle_format_observed", "trick_room_field_observed"}


def admit_current_state_observation(*, runtime_session_manager: Any, captured_session_id: Any,
                                    event_kind: str, payload: Mapping[str, Any], turn_number: Any,
                                    side: str | None = None) -> dict[str, Any]:
    """Preview and commit one UI fact against the exact current runtime owner.

    The caller deliberately receives no mutable runtime object.  UI mirrors are
    updated only after this function returns ``resolved``.
    """
    result = admit_current_state_observations(
        runtime_session_manager=runtime_session_manager,
        captured_session_id=captured_session_id,
        observations=({"event_kind": event_kind, "payload": payload, "side": side},),
        turn_number=turn_number,
    )
    if result.get("status") != "resolved":
        return result
    return {
        **result,
        "owner": result["owners"][0],
        "observation": result["observations"][0],
    }


def admit_current_state_observations(*, runtime_session_manager: Any, captured_session_id: Any,
                                     observations: Any, turn_number: Any) -> dict[str, Any]:
    """Atomically admit one or more exact current-state facts.

    Field-state UI submits a coherent weather/terrain/side-condition snapshot.
    It must never commit an early row and then leave later rows rejected.
    """
    if not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager):
        return _result("invalid_runtime_manager")
    if not isinstance(captured_session_id, str) or not captured_session_id:
        return _result("invalid_admission_request")
    if not isinstance(observations, (tuple, list)) or not observations:
        return _result("invalid_admission_request")
    if not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _result("invalid_payload_or_turn")
    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready":
        return _result("runtime_snapshot_unavailable")
    owners = _active_owners(snapshot.get("state"), captured_session_id)
    if owners is None:
        return _result("active_owner_unavailable")
    confirmations, admitted_owners, confirmed_observations = [], [], []
    boundary = LifecycleConfirmationBoundary(captured_session_id, owners)
    for row in observations:
        if not isinstance(row, Mapping):
            return _result("invalid_admission_request")
        event_kind, payload, side = row.get("event_kind"), row.get("payload"), row.get("side")
        if event_kind not in _SOURCES or not isinstance(payload, Mapping):
            return _result("invalid_admission_request")
        owner = None if event_kind in _GLOBAL else owners.get(side)
        if event_kind not in _GLOBAL and owner is None:
            return _result("invalid_current_owner")
        allocated = runtime_session_manager.allocate_observation_sequence()
        if allocated.get("status") != "allocated" or allocated.get("session_id") != captured_session_id:
            return _result("sequence_binding_mismatch")
        sequence = allocated["observation_sequence"]
        confirmation = boundary.confirm(
            event_kind=event_kind, payload=deepcopy(dict(payload)), session_id=captured_session_id,
            source=_SOURCES[event_kind], trust=USER_TRUST, confirmed=True,
            side=owner.get("side") if owner else side,
            slot_index=owner.get("slot_index") if owner else None,
            pokemon_id=owner.get("pokemon_id") if owner else None,
            observation_id=f"{captured_session_id}:current-state:{event_kind}:{sequence}",
            turn_number=turn_number,
        )
        if confirmation.get("status") != "confirmed":
            return _result(str(confirmation.get("excluded_reason") or "lifecycle_rejected"))
        observation = confirmation["observation"]
        observation["observation_sequence"] = sequence
        confirmations.append(confirmation)
        admitted_owners.append(deepcopy(owner))
        confirmed_observations.append(deepcopy(observation))
    collection = runtime_session_manager.read_collection_snapshot()
    rows = [*collection.get("ordered_observations", []), *deepcopy(confirmed_observations)]
    rows.sort(key=lambda row: (row["observation_sequence"], row["observation_id"]))
    preview = runtime_session_manager.preview(captured_session_id, {**collection, "ordered_observations": rows})
    if preview.get("status") != "preview_ready":
        return _result("reducer_preview_rejected")
    admitted = runtime_session_manager.admit_confirmations_atomically(captured_session_id, confirmations)
    if admitted.get("status") not in {"added", "duplicate"}:
        return _result("observation_admission_rejected")
    applied = runtime_session_manager.apply(captured_session_id, runtime_session_manager.read_collection_snapshot())
    if applied.get("status") not in {"applied", "already_applied"}:
        return _result("reducer_application_rejected")
    committed = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if committed.get("status") != "runtime_snapshot_ready":
        return _result("committed_runtime_unavailable")
    return {"status": "resolved", "reason": None, "owners": admitted_owners,
            "observations": confirmed_observations,
            "runtime_fingerprint": committed.get("state_fingerprint")}


def _active_owners(state: Any, session_id: str) -> dict[str, dict[str, Any]] | None:
    if not isinstance(state, Mapping) or state.get("session_id") != session_id:
        return None
    result = {}
    for side in ("self", "opponent"):
        side_state = state.get(f"{side}_side")
        roster = side_state.get("pokemon") if isinstance(side_state, Mapping) else None
        slot = side_state.get("active_slot_index") if isinstance(side_state, Mapping) else None
        pokemon = roster.get(slot, roster.get(str(slot))) if isinstance(roster, Mapping) and isinstance(slot, int) and not isinstance(slot, bool) else None
        pokemon_id = pokemon.get("pokemon_id") if isinstance(pokemon, Mapping) else None
        if not isinstance(slot, int) or isinstance(slot, bool) or slot < 0 or not isinstance(pokemon_id, str) or not pokemon_id or pokemon.get("fainted") is True:
            return None
        result[side] = {"session_id": session_id, "side": side, "slot_index": slot, "pokemon_id": pokemon_id}
    return result


def _result(reason: str) -> dict[str, Any]:
    return {"status": "rejected", "reason": reason, "owner": None, "observation": None,
            "owners": [], "observations": []}
