"""Strict D0-bound authority for observed opponent move identities.

This owner deliberately proves only that an active opponent is known to have a
move.  It never promotes that fact into current selectability: PP, Disable,
Choice-lock, Encore, and equivalent restrictions have no current authority.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-opponent-known-move-action-authority-v1"
METADATA_SCHEMA_VERSION = "canonical-normalized-move-metadata-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_STATUSES = frozenset({"resolved", "incomplete", "unsupported", "rejected"})
USABILITY_SCHEMA_VERSION = "runtime-d0-opponent-move-usability-authority-v1"


def freeze_runtime_d0_opponent_known_move_action_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    canonical_move_metadata_authorities: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Freeze known opponent attacks and their metadata at one D0 decision point.

    ``canonical_move_metadata_authorities`` is an authority input, not a
    repository lookup.  A caller must acquire it before this boundary; this
    prevents later pair mechanics from filling D0 omissions from mutable UI or
    repository state.
    """
    base = _base(strategy_d0)
    if base is None or not isinstance(canonical_move_metadata_authorities, Mapping):
        return _result("rejected", "invalid_runtime_d0_or_metadata_authority", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    state = _runtime_state(runtime_snapshot)
    opponent = strategy_d0.get("active_owners", {}).get("opponent")
    target = strategy_d0.get("active_owners", {}).get("self")
    if not _owner(opponent) or not _owner(target):
        return _result("rejected", "runtime_active_owner_unavailable", base)
    raw = _pokemon(state, opponent)
    if raw is None:
        return _result("rejected", "runtime_active_opponent_identity_mismatch", base)
    moves = raw.get("known_move_ids")
    if not isinstance(moves, list):
        return {
            "status": "incomplete", "schema_version": SCHEMA_VERSION, **base,
            "opponent_actor": deepcopy(dict(opponent)), "target_owner": deepcopy(dict(target)),
            "known_moveset_state": "unknown", "unknown_move_slots": 4, "actions": (),
            "reason": "opponent_known_moves_unknown", "provenance": "runtime_reducer_known_move_identity_v1",
        }
    if len(moves) > 4 or len(set(moves)) != len(moves) or any(not _move_id(move) for move in moves):
        return _result("rejected", "runtime_known_move_state_invalid", base)
    state_name = "unknown" if not moves else "complete" if len(moves) == 4 else "partially_known"
    provenance = raw.get("known_move_ids_provenance")
    common = {
        **base,
        "opponent_actor": deepcopy(dict(opponent)),
        "target_owner": deepcopy(dict(target)),
        "known_moveset_state": state_name,
        "unknown_move_slots": 4 - len(moves),
    }
    if not moves:
        return {"status": "incomplete", "schema_version": SCHEMA_VERSION, **common, "actions": (), "reason": "opponent_known_moves_unknown", "provenance": "runtime_reducer_known_move_identity_v1"}
    if not _provenance_map(provenance, moves):
        return {"status": "incomplete", "schema_version": SCHEMA_VERSION, **common, "actions": (), "reason": "opponent_known_move_provenance_unavailable", "provenance": "runtime_reducer_known_move_identity_v1"}
    actions = tuple(
        _action(
            move_id=move, index=index, base=common, actor=opponent, target=target,
            observation=provenance[move], metadata_authority=canonical_move_metadata_authorities.get(move),
        )
        for index, move in enumerate(moves)
    )
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **common,
        "actions": actions, "provenance": "runtime_reducer_known_move_identity_v1",
    }


def compose_runtime_d0_opponent_move_usability(
    *, opponent_action: Mapping[str, Any], usability_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach separately frozen current selectability without re-reading state.

    The known-move action remains an identity authority.  Only a matching
    usability authority may make it selectable; incomplete evidence keeps the
    action known but non-executable for a later pair materializer.
    """
    action = deepcopy(dict(opponent_action)) if isinstance(opponent_action, Mapping) else None
    if not isinstance(action, dict) or action.get("schema_version") != SCHEMA_VERSION:
        return _result("rejected", "invalid_opponent_known_move_action", {})
    if not isinstance(usability_authority, Mapping) or usability_authority.get("schema_version") != USABILITY_SCHEMA_VERSION:
        action["status"] = "rejected"; action["reason"] = "invalid_opponent_move_usability_authority"
        return action
    fields = ("action_id", "move_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "opponent_actor", "target_owner")
    if any(usability_authority.get(field) != action.get(field) for field in fields):
        action["status"] = "rejected"; action["reason"] = "opponent_move_usability_binding_mismatch"
        return action
    usability_status = usability_authority.get("status")
    if usability_status == "rejected":
        action["status"] = "rejected"; action["reason"] = usability_authority.get("reason", "opponent_move_usability_rejected")
        action["usability"] = deepcopy(usability_authority.get("usability", {"status": "unknown"}))
        action["selectability"] = "unknown"
        return action
    if usability_status == "unsupported":
        action["usability"] = deepcopy(usability_authority.get("usability", {"status": "unknown"}))
        action["selectability"] = "unknown"; action["selectability_reason"] = usability_authority.get("reason", "opponent_move_usability_unsupported")
        return action
    if usability_status == "incomplete":
        action["usability"] = deepcopy(usability_authority.get("usability", {"status": "unknown"}))
        action["selectability"] = "unknown"; action["selectability_reason"] = usability_authority.get("reason", "opponent_move_usability_unknown")
        return action
    usage = usability_authority.get("usability")
    if usability_status != "resolved" or not isinstance(usage, Mapping) or usage.get("status") not in {"known_usable", "known_unusable"}:
        action["status"] = "rejected"; action["reason"] = "opponent_move_usability_payload_invalid"
        return action
    action["usability"] = deepcopy(dict(usage))
    action["selectability"] = "selectable" if usage["status"] == "known_usable" else "not_selectable"
    action["selectability_reason"] = usage.get("reason")
    return action


def _action(*, move_id: str, index: int, base: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], observation: Mapping[str, Any], metadata_authority: Any) -> dict[str, Any]:
    action_base = {
        "schema_version": SCHEMA_VERSION,
        "action_id": f"opponent_attack:{move_id}", "action_type": "attack", "move_id": move_id,
        "acting_side": "opponent", "target_side": "self", "opponent_actor": deepcopy(dict(actor)),
        "target_owner": deepcopy(dict(target)), "known_move_index": index,
        "known_move_provenance": deepcopy(dict(observation)),
        "session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"],
        "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": deepcopy(dict(base["decision_owner"])),
        "known_moveset_state": base["known_moveset_state"], "unknown_move_slots": base["unknown_move_slots"],
        "usability": {"status": "incomplete", "reason": "opponent_move_usability_authority_unavailable"},
        "selectability": "unknown",
        "provenance": "runtime_d0_identity_bound_observed_opponent_move_v1",
    }
    metadata = _metadata(move_id, metadata_authority)
    if metadata["status"] != "resolved":
        return {"status": metadata["status"], **action_base, "metadata_authority": metadata, "reason": metadata["reason"]}
    return {"status": "resolved", **action_base, "metadata_authority": metadata}


def _metadata(move_id: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {"status": "incomplete", "reason": "canonical_opponent_move_metadata_missing"}
    status = value.get("status")
    if status not in _STATUSES:
        return {"status": "rejected", "reason": "canonical_opponent_move_metadata_status_invalid"}
    if value.get("schema_version") != METADATA_SCHEMA_VERSION or value.get("move_id") != move_id:
        return {"status": "rejected", "reason": "canonical_opponent_move_metadata_binding_conflict"}
    if status != "resolved":
        return {"status": status, "reason": value.get("reason", "canonical_opponent_move_metadata_unavailable")}
    metadata = value.get("metadata")
    if not isinstance(metadata, Mapping) or metadata.get("move_id") != move_id:
        return {"status": "rejected", "reason": "canonical_opponent_move_metadata_payload_conflict"}
    category, move_type, priority = metadata.get("category"), metadata.get("type"), metadata.get("priority")
    if category not in {"physical", "special", "status"}:
        return {"status": "unsupported", "reason": "canonical_opponent_move_category_unsupported"}
    if not isinstance(move_type, str) or not move_type:
        return {"status": "incomplete", "reason": "canonical_opponent_move_type_missing"}
    if not isinstance(priority, int) or isinstance(priority, bool) or not -7 <= priority <= 7:
        return {"status": "incomplete", "reason": "canonical_opponent_move_priority_missing"}
    if category in {"physical", "special"} and (not isinstance(metadata.get("power"), int) or isinstance(metadata.get("power"), bool) or metadata["power"] < 1):
        return {"status": "incomplete", "reason": "canonical_opponent_move_power_missing"}
    if metadata.get("always_hit") is not True and (not isinstance(metadata.get("accuracy"), int) or isinstance(metadata.get("accuracy"), bool) or not 1 <= metadata["accuracy"] <= 100):
        return {"status": "incomplete", "reason": "canonical_opponent_move_accuracy_missing"}
    return {"status": "resolved", "schema_version": METADATA_SCHEMA_VERSION, "move_id": move_id, "metadata": deepcopy(dict(metadata)), "provenance": deepcopy(value.get("provenance"))}


def _base(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != "deterministic-runtime-strategy-d0-v1":
        return None
    required = ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint", "decision_owner", "active_owners")
    if any(key not in value for key in required) or not _owner(value.get("decision_owner")):
        return None
    return {
        "session_id": value["session_id"], "source_runtime_fingerprint": value["source_runtime_fingerprint"],
        "source_branch_fingerprint": value["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(value["decision_owner"])),
    }


def _runtime_state(snapshot: Any) -> Mapping[str, Any] | None:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
    return state if isinstance(state, Mapping) else None


def _pokemon(state: Mapping[str, Any] | None, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if not isinstance(state, Mapping):
        return None
    side = state.get(f"{owner['side']}_side")
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    value = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    return value if isinstance(value, Mapping) and value.get("pokemon_id") == owner["pokemon_id"] else None


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _move_id(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value == value.lower() and value == value.strip() and " " not in value and "_" not in value


def _provenance_map(value: Any, moves: list[str]) -> bool:
    return isinstance(value, Mapping) and set(value) == set(moves) and all(isinstance(row, Mapping) and row.get("event_kind") == "used_move_observed" and row.get("trust") == "user_confirmed_observation" and isinstance(row.get("source_observation_id"), str) and bool(row["source_observation_id"]) and isinstance(row.get("source_sequence"), int) and not isinstance(row.get("source_sequence"), bool) and row["source_sequence"] >= 1 for row in value.values())


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
