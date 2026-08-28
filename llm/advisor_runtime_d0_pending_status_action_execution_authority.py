"""Strict D0 reader for an explicitly observed sleep/freeze action result.

The authority never derives execution from the major-condition label.  It only
freezes a user-confirmed, reducer-owned result for one current pending attack.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-pending-status-action-execution-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def freeze_runtime_d0_pending_status_action_execution_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    pending_actor: Mapping[str, Any], pending_action: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze one exact observed pending-action execution state.

    ``pending_action`` must provide ``decision_point``, ``action_id``, and
    ``move_id``.  Its selection or mechanics are deliberately out of scope.
    """
    base = _base(strategy_d0, pending_actor, pending_action)
    if base is None:
        return _result("rejected", "invalid_runtime_d0_or_pending_action", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    if not isinstance(state, Mapping) or state.get("session_id") != strategy_d0.get("session_id"):
        return _result("rejected", "runtime_snapshot_session_mismatch", base)
    context = state.get("pending_status_action_execution_context")
    if context is None:
        return _result("incomplete", "pending_status_action_execution_observation_missing", base)
    if not isinstance(context, Mapping):
        return _result("rejected", "pending_status_action_execution_context_malformed", base)
    if not _matches_context(strategy_d0, context, pending_actor, pending_action):
        return _result("rejected", "pending_status_action_execution_binding_mismatch", base)
    if not _context_is_current(state, context):
        return _result("rejected", "stale_pending_status_action_execution_observation", base)
    if not _current_condition_matches(state, pending_actor, context.get("condition")):
        return _result("rejected", "pending_status_action_execution_condition_mismatch", base)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "condition": context["condition"], "execution_state": context["execution_state"],
        "blocker": context["blocker"], "observation_sequence": context["provenance"]["source_sequence"],
        "trusted_provenance": deepcopy(dict(context["provenance"])),
        "provenance": "runtime_d0_explicit_pending_status_action_execution_observation_v1",
    }


def _base(d0: Mapping[str, Any], actor: Mapping[str, Any], action: Mapping[str, Any]) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(actor) or not isinstance(action, Mapping):
        return None
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(actor.get("side")) != dict(actor):
        return None
    if not all(isinstance(d0.get(key), str) and bool(d0[key]) for key in ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint")):
        return None
    if not all(isinstance(action.get(key), str) and bool(action[key]) for key in ("decision_point", "action_id", "move_id")):
        return None
    return {
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0.get("decision_owner")),
        "pending_actor": deepcopy(dict(actor)), "decision_point": action["decision_point"],
        "pending_action_id": action["action_id"], "pending_move_id": action["move_id"],
    }


def _matches_context(d0: Mapping[str, Any], context: Mapping[str, Any], actor: Mapping[str, Any], action: Mapping[str, Any]) -> bool:
    provenance = context.get("provenance")
    return (
        context.get("schema_version") == "pending-status-action-execution-context-v1"
        and context.get("session_id") == d0.get("session_id")
        and context.get("actor") == dict(actor)
        and all(context.get(key) == action.get(key) for key in ("decision_point", "action_id", "move_id"))
        and context.get("condition") in {"sleep", "freeze"}
        and context.get("execution_state") in {"executable", "blocked"}
        and ((context.get("execution_state") == "executable" and context.get("blocker") is None) or (context.get("execution_state") == "blocked" and context.get("blocker") == context.get("condition")))
        and isinstance(provenance, Mapping) and provenance.get("event_kind") == "pending_status_action_execution_observed"
        and provenance.get("trust") == "user_confirmed_observation"
        and isinstance(provenance.get("source_sequence"), int) and not isinstance(provenance.get("source_sequence"), bool)
    )


def _context_is_current(state: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    last = state.get("last_applied_observation_sequence")
    sequence = context.get("provenance", {}).get("source_sequence") if isinstance(context.get("provenance"), Mapping) else None
    return isinstance(last, int) and not isinstance(last, bool) and isinstance(sequence, int) and not isinstance(sequence, bool) and last == sequence


def _current_condition_matches(state: Mapping[str, Any], actor: Mapping[str, Any], condition: Any) -> bool:
    side = state.get(f"{actor.get('side')}_side") if isinstance(actor, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    pokemon = roster.get(actor.get("slot_index")) if isinstance(roster, Mapping) else None
    provenance = pokemon.get("condition_provenance") if isinstance(pokemon, Mapping) else None
    return (
        isinstance(pokemon, Mapping) and pokemon.get("pokemon_id") == actor.get("pokemon_id")
        and pokemon.get("condition") == condition
        and isinstance(provenance, Mapping) and provenance.get("event_kind") == "current_condition_observed"
        and provenance.get("trust") == "user_confirmed_observation" and provenance.get("condition") == condition
    )


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
