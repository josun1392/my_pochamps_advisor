"""Strict current selectability authority for an already-known opponent move."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-opponent-move-usability-authority-v1"
ACTION_SCHEMA_VERSION = "runtime-d0-opponent-known-move-action-authority-v1"
_BINDINGS = (
    "session_id", "source_runtime_fingerprint", "source_branch_fingerprint",
    "decision_owner", "opponent_actor", "target_owner",
)


def freeze_runtime_d0_opponent_move_usability_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    opponent_action: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze one current usability observation without inferring neutrality.

    A record is current only if it is the reducer's latest applied observation.
    This intentionally conservative lifecycle rule invalidates it after any
    subsequent event, turn transition, or active-identity change.
    """
    base = _base(opponent_action)
    if base is None:
        return _result("rejected", "invalid_opponent_action_authority", {})
    if not isinstance(strategy_d0, Mapping) or strategy_d0.get("status") != "resolved":
        return _result("rejected", "invalid_runtime_d0", base)
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    if not _matches_d0(base, strategy_d0):
        return _result("rejected", "opponent_action_runtime_d0_binding_mismatch", base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    pokemon = _pokemon(state, base["opponent_actor"])
    if pokemon is None:
        return _result("rejected", "runtime_active_opponent_identity_mismatch", base)
    record = pokemon.get("current_move_usability", {}).get(base["move_id"]) if isinstance(pokemon.get("current_move_usability"), Mapping) else None
    if record is None:
        return _unknown(base, "opponent_move_usability_unknown")
    if not _record(record):
        return _result("rejected", "opponent_move_usability_record_invalid", base)
    if record["provenance"]["source_sequence"] != state.get("last_applied_observation_sequence"):
        return _unknown(base, "opponent_move_usability_observation_not_current", record)
    selectability = "selectable" if record["status"] == "known_usable" else "not_selectable"
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "usability": deepcopy(dict(record)), "selectability": selectability,
        "provenance": "runtime_reducer_current_opponent_move_usability_v1",
    }


def _base(action: Any) -> dict[str, Any] | None:
    if not isinstance(action, Mapping) or action.get("schema_version") != ACTION_SCHEMA_VERSION:
        return None
    if action.get("action_type") != "attack" or action.get("acting_side") != "opponent" or action.get("target_side") != "self":
        return None
    if not isinstance(action.get("action_id"), str) or not isinstance(action.get("move_id"), str) or not action["move_id"] or action["action_id"] != f"opponent_attack:{action['move_id']}":
        return None
    if any(key not in action for key in _BINDINGS) or not _owner(action.get("decision_owner")) or not _owner(action.get("opponent_actor")) or not _owner(action.get("target_owner")):
        return None
    actor, target = action["opponent_actor"], action["target_owner"]
    if actor["side"] != "opponent" or target["side"] != "self" or actor["session_id"] != action["session_id"] or target["session_id"] != action["session_id"]:
        return None
    return {
        key: deepcopy(dict(action[key])) if key in {"decision_owner", "opponent_actor", "target_owner"} else action[key]
        for key in _BINDINGS
    } | {"action_id": action["action_id"], "move_id": action["move_id"]}


def _matches_d0(base: Mapping[str, Any], d0: Mapping[str, Any]) -> bool:
    owners = d0.get("active_owners")
    return (
        base["session_id"] == d0.get("session_id")
        and base["source_runtime_fingerprint"] == d0.get("source_runtime_fingerprint")
        and base["source_branch_fingerprint"] == d0.get("strategy_preview_fingerprint")
        and base["decision_owner"] == d0.get("decision_owner")
        and isinstance(owners, Mapping)
        and base["opponent_actor"] == owners.get("opponent")
        and base["target_owner"] == owners.get("self")
    )


def _pokemon(state: Any, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if not isinstance(state, Mapping):
        return None
    side = state.get("opponent_side")
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    value = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    active = side.get("active_slot_index") if isinstance(side, Mapping) else None
    if active != owner["slot_index"]:
        return None
    return value if isinstance(value, Mapping) and value.get("pokemon_id") == owner["pokemon_id"] else None


def _record(value: Any) -> bool:
    if not isinstance(value, Mapping) or set(value) != {"status", "reason", "provenance"} or value.get("status") not in {"known_usable", "known_unusable"}:
        return False
    if value["status"] == "known_usable" and value.get("reason") is not None:
        return False
    if value["status"] == "known_unusable" and value.get("reason") not in {"no_pp", "disabled", "choice_lock", "encore_restriction", "other_supported_restriction", "observed_unclassified"}:
        return False
    provenance = value.get("provenance")
    return isinstance(provenance, Mapping) and provenance.get("event_kind") == "current_move_usability_observed" and provenance.get("trust") == "user_confirmed_observation" and isinstance(provenance.get("turn_number"), int) and not isinstance(provenance.get("turn_number"), bool) and provenance["turn_number"] >= 1 and isinstance(provenance.get("source_sequence"), int) and not isinstance(provenance.get("source_sequence"), bool) and provenance["source_sequence"] >= 1


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == {"session_id", "side", "slot_index", "pokemon_id"} and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _unknown(base: Mapping[str, Any], reason: str, record: Mapping[str, Any] | None = None) -> dict[str, Any]:
    result = {"status": "incomplete", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "usability": {"status": "unknown", "reason": reason}, "selectability": "unknown", "reason": reason, "provenance": "runtime_reducer_current_opponent_move_usability_v1"}
    if record is not None:
        result["stale_observation"] = deepcopy(dict(record))
    return result


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
