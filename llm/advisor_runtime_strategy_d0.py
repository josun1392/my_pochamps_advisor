"""Runtime-owned, one-way D0 authority for detached strategy previews.

``battle-state-v1`` remains the mutable runtime source of truth.  This module
only freezes a detached ``deterministic-transition-preview-v1`` view and keeps
the originating reducer fingerprint alongside its preview fingerprint.  It
does not make UI/recommendation projections into battle-state owners.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from llm.advisor_current_action_authority import freeze_current_action_authority
from llm.advisor_reducer_state_model import (
    STATE_MODEL_VERSION,
    is_unknown_battle_fact,
    state_fingerprint,
    validate_battle_state_unknown_markers,
)
from llm.advisor_transition_preview import fingerprint_transition_preview_state


SCHEMA = "deterministic-runtime-strategy-d0-v1"
PREVIEW_SCHEMA = "deterministic-transition-preview-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def freeze_runtime_strategy_d0(*, runtime_snapshot: Mapping[str, Any], decision_owner: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze a detached strategy D0 from one exact runtime snapshot.

    Unknown reducer facts are deliberately not replaced with strategy defaults.
    They remain untracked in the preview and cause downstream mechanics to fail
    closed when those mechanics require exact state.
    """
    state, session_id, runtime_fingerprint = _runtime_snapshot(runtime_snapshot)
    if state is None or not _owner(decision_owner) or decision_owner.get("session_id") != session_id:
        return _result("rejected", "invalid_runtime_d0_authority")
    owners = _active_owners(state, session_id)
    if owners is None or owners.get(decision_owner["side"]) != dict(decision_owner):
        return _result("rejected", "runtime_decision_owner_mismatch")
    preview = {
        "schema_version": PREVIEW_SCHEMA,
        "active": {
            side: _preview_active(state, side, owner)
            for side, owner in owners.items()
        },
        "current_state": {
            "current_state_session_id": session_id,
            # This is provenance only.  Existing mechanics do not consume it as
            # exact current-state authority, so missing conversion adapters stay
            # unknown instead of becoming neutral defaults.
            "runtime_strategy_d0_authority": _runtime_authority_summary(state),
        },
    }
    preview_fingerprint = fingerprint_transition_preview_state(preview)
    if not isinstance(preview_fingerprint, str):
        return _result("rejected", "unserializable_strategy_d0")
    return {
        "status": "resolved",
        "schema_version": SCHEMA,
        "session_id": session_id,
        "source_runtime_fingerprint": runtime_fingerprint,
        "strategy_preview_fingerprint": preview_fingerprint,
        "decision_owner": deepcopy(dict(decision_owner)),
        "active_owners": deepcopy(owners),
        "strategy_state": deepcopy(preview),
        "provenance": "runtime_battle_state_v1_to_detached_strategy_d0_v1",
    }


def runtime_strategy_d0_freshness(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Check reducer-fingerprint freshness without inspecting UI state."""
    if not _valid_d0(strategy_d0):
        return _result("rejected", "invalid_strategy_d0")
    _state, session_id, fingerprint = _runtime_snapshot(runtime_snapshot)
    if session_id is None or fingerprint is None:
        return _result("rejected", "invalid_runtime_snapshot")
    if session_id != strategy_d0["session_id"]:
        return _result("stale", "runtime_session_mismatch")
    if fingerprint != strategy_d0["source_runtime_fingerprint"]:
        return _result("stale", "runtime_fingerprint_changed")
    return {"status": "current", "source_runtime_fingerprint": fingerprint}


def freeze_runtime_strategy_selection_authority(*, strategy_d0: Mapping[str, Any], selection_projection: Mapping[str, Any]) -> dict[str, Any]:
    """Join already-validated structured selectability to one exact runtime D0.

    The projection provides selection facts only.  This adapter intentionally
    drops any execution-shaped payload rather than promoting it across the
    selection boundary.
    """
    if not _valid_d0(strategy_d0) or not isinstance(selection_projection, Mapping):
        return _result("rejected", "invalid_strategy_d0_or_selection_projection")
    owner = strategy_d0["decision_owner"]
    expected = {
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "decision_owner": owner,
        "active_owner": owner,
    }
    if any(selection_projection.get(key) != value for key, value in expected.items()):
        return _result("rejected", "selection_projection_runtime_d0_mismatch")
    moves, switches = selection_projection.get("moves"), selection_projection.get("switches")
    if not _selection_entries(moves, "move_id") or not _selection_entries(switches, "pokemon_id"):
        return _result("rejected", "invalid_selection_projection_records")
    fingerprint = strategy_d0["strategy_preview_fingerprint"]
    frozen_moves = [
        {"owner": deepcopy(owner), "source_branch_fingerprint": fingerprint, "move_id": row["move_id"], "selection": row["selection"]}
        for row in moves
    ]
    frozen_switches = [
        {"owner": deepcopy(owner), "source_branch_fingerprint": fingerprint, "pokemon_id": row["pokemon_id"], "selection": row["selection"]}
        for row in switches
    ]
    return freeze_current_action_authority(
        decision_state=strategy_d0["strategy_state"], decision_owner=owner,
        moves=frozen_moves, switches=frozen_switches,
    )


def freeze_runtime_incoming_authority_boundary(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], incoming_owner: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a runtime bench identity without fabricating strict incoming state.

    ``identity_bound_incoming_current_state_v1`` remains unavailable until a
    dedicated runtime-owned converter can supply its complete current-state
    shape (including material persistent and Substitute authority).  Returning
    an explicit incomplete boundary keeps a selectable switch selectable while
    preventing false execution readiness.
    """
    if not _valid_d0(strategy_d0) or not _owner(incoming_owner):
        return _result("rejected", "invalid_strategy_d0_or_incoming_owner")
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"))
    state, _session, _fingerprint = _runtime_snapshot(runtime_snapshot)
    owner = strategy_d0["decision_owner"]
    if incoming_owner.get("session_id") != owner["session_id"] or incoming_owner.get("side") != owner["side"] or incoming_owner == owner:
        return _result("rejected", "foreign_or_active_incoming_owner")
    roster = _roster(state, owner["side"])
    current = roster.get(incoming_owner.get("slot_index")) if isinstance(roster, Mapping) else None
    if not isinstance(current, Mapping) or current.get("pokemon_id") != incoming_owner.get("pokemon_id"):
        return _result("rejected", "incoming_owner_not_in_runtime_roster")
    return {
        "status": "resolved",
        "schema_version": "deterministic-runtime-incoming-authority-boundary-v1",
        "session_id": owner["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(owner),
        "outgoing_owner": deepcopy(owner),
        "incoming_owner": deepcopy(dict(incoming_owner)),
        "execution_readiness": "execution_incomplete",
        "reason": "runtime_incoming_current_state_adapter_unavailable",
        "provenance": "runtime_roster_identity_boundary_v1",
    }


def _runtime_snapshot(value: Any) -> tuple[dict[str, Any] | None, str | None, str | None]:
    if not isinstance(value, Mapping) or value.get("status") != "runtime_snapshot_ready":
        return None, None, None
    state = value.get("state")
    session_id = value.get("session_id")
    fingerprint = value.get("state_fingerprint")
    if (
        not isinstance(state, Mapping) or not isinstance(session_id, str) or not session_id
        or state.get("state_version") != STATE_MODEL_VERSION or state.get("session_id") != session_id
        or not validate_battle_state_unknown_markers(dict(state))
        or not isinstance(fingerprint, str) or fingerprint != state_fingerprint(dict(state))
    ):
        return None, None, None
    return deepcopy(dict(state)), session_id, fingerprint


def _active_owners(state: Mapping[str, Any], session_id: str) -> dict[str, dict[str, Any]] | None:
    owners: dict[str, dict[str, Any]] = {}
    for side, side_key in (("self", "self_side"), ("opponent", "opponent_side")):
        container = state.get(side_key)
        roster = container.get("pokemon") if isinstance(container, Mapping) else None
        slot = container.get("active_slot_index") if isinstance(container, Mapping) else None
        active = roster.get(slot) if isinstance(roster, Mapping) else None
        if not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(active, Mapping) or not isinstance(active.get("pokemon_id"), str) or not active["pokemon_id"]:
            return None
        owners[side] = {"session_id": session_id, "side": side, "slot_index": slot, "pokemon_id": active["pokemon_id"]}
    return owners


def _preview_active(state: Mapping[str, Any], side: str, owner: Mapping[str, Any]) -> dict[str, Any]:
    raw = _roster(state, side).get(owner["slot_index"])
    result = deepcopy(dict(owner))
    if not isinstance(raw, Mapping):
        return result
    hp, maximum, fainted = raw.get("current_hp"), raw.get("max_hp"), raw.get("fainted")
    if _exact_hp(hp, maximum, fainted):
        result.update(current_hp=hp, max_hp=maximum, fainted=fainted)
    return result


def _runtime_authority_summary(state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "runtime-strategy-current-authority-summary-v1",
        "active": {
            side: _fact_summary(_roster(state, side).get(_side_active_slot(state, side)))
            for side in ("self", "opponent")
        },
        "field": _fact_summary(state.get("field")),
        "unknown_first": True,
    }


def _fact_summary(value: Any) -> Any:
    if is_unknown_battle_fact(value):
        return {"status": "unknown"}
    if isinstance(value, Mapping):
        return {
            key: _fact_summary(item)
            for key, item in value.items()
            if key in {"current_hp", "max_hp", "fainted", "condition", "known_item", "current_type", "current_ability", "stat_stages", "weather", "terrain", "side_conditions"}
        }
    return deepcopy(value)


def _side_active_slot(state: Mapping[str, Any], side: str) -> Any:
    container = state.get(f"{side}_side")
    return container.get("active_slot_index") if isinstance(container, Mapping) else None


def _roster(state: Mapping[str, Any], side: str) -> Mapping[str, Any]:
    container = state.get(f"{side}_side")
    roster = container.get("pokemon") if isinstance(container, Mapping) else None
    return roster if isinstance(roster, Mapping) else {}


def _exact_hp(hp: Any, maximum: Any, fainted: Any) -> bool:
    return (
        isinstance(hp, int) and not isinstance(hp, bool)
        and isinstance(maximum, int) and not isinstance(maximum, bool)
        and maximum > 0 and 0 <= hp <= maximum and isinstance(fainted, bool)
        and fainted is (hp == 0)
    )


def _selection_entries(entries: Any, identity_key: str) -> bool:
    return (
        isinstance(entries, Sequence) and not isinstance(entries, (str, bytes))
        and all(isinstance(row, Mapping) and isinstance(row.get(identity_key), str) and bool(row[identity_key]) and row.get("selection") in {"selectable", "not_selectable", "selection_unknown"} for row in entries)
    )


def _owner(value: Any) -> bool:
    return (
        isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS)
        and isinstance(value.get("session_id"), str) and bool(value["session_id"])
        and value.get("side") in {"self", "opponent"}
        and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
    )


def _valid_d0(value: Any) -> bool:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != SCHEMA:
        return False
    state = value.get("strategy_state")
    owner = value.get("decision_owner")
    return (
        _owner(owner) and value.get("session_id") == owner["session_id"]
        and isinstance(value.get("source_runtime_fingerprint"), str)
        and isinstance(value.get("strategy_preview_fingerprint"), str)
        and isinstance(state, Mapping) and state.get("schema_version") == PREVIEW_SCHEMA
        and fingerprint_transition_preview_state(state) == value["strategy_preview_fingerprint"]
    )


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
