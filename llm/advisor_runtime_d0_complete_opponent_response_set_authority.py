"""Strict D0-bound complete opponent selectable-response-set authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_d0_opponent_action_authority import (
    SCHEMA_VERSION as ACTION_SCHEMA_VERSION,
    compose_runtime_d0_opponent_move_usability,
)
from llm.advisor_runtime_d0_opponent_move_usability_authority import (
    freeze_runtime_d0_opponent_move_usability_authority,
)
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-complete-opponent-response-set-authority-v1"


def freeze_runtime_d0_complete_opponent_response_set_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    opponent_known_move_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze only an explicitly observed complete, currently usable response set.

    Four identities alone are deliberately insufficient.  The reducer must hold
    the dedicated current response-set observation, and every exact move must
    have current usability from that same decision basis.
    """
    base = _base(strategy_d0, opponent_known_move_authority)
    if base is None:
        return _result("rejected", "invalid_runtime_d0_or_opponent_action_authority", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    pokemon = _active_opponent(state, base["opponent_actor"])
    if pokemon is None:
        return _result("rejected", "runtime_active_opponent_identity_mismatch", base)
    observed = pokemon.get("current_opponent_response_set")
    checked = _observed_complete_set(observed, state, pokemon)
    if checked is None:
        return _result("incomplete", "opponent_moveset_completeness_unknown", base)
    if isinstance(checked, str):
        return _result("rejected", checked, base)
    actions = opponent_known_move_authority.get("actions")
    if opponent_known_move_authority.get("status") != "resolved" or not isinstance(actions, (tuple, list)):
        return _result(_status(opponent_known_move_authority), opponent_known_move_authority.get("reason", "opponent_known_move_authority_unavailable"), base)
    if opponent_known_move_authority.get("known_moveset_state") != "complete" or tuple(action.get("move_id") for action in actions if isinstance(action, Mapping)) != tuple(checked["move_ids"]):
        return _result("rejected", "opponent_known_move_set_binding_mismatch", base)
    composed = []
    for action in actions:
        if not isinstance(action, Mapping) or action.get("status") != "resolved":
            return _result(_status(action), action.get("reason", "opponent_move_action_unavailable") if isinstance(action, Mapping) else "opponent_move_action_invalid", base)
        usability = freeze_runtime_d0_opponent_move_usability_authority(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, opponent_action=action,
        )
        if usability.get("status") != "resolved":
            return _result(_status(usability), usability.get("reason", "opponent_move_usability_unavailable"), base)
        bound = compose_runtime_d0_opponent_move_usability(opponent_action=action, usability_authority=usability)
        if bound.get("status") != "resolved" or bound.get("selectability") not in {"selectable", "not_selectable"}:
            return _result(_status(bound), bound.get("reason", "opponent_move_selectability_unavailable"), base)
        composed.append(bound)
    selectable = tuple(action["action_id"] for action in composed if action["selectability"] == "selectable")
    if not selectable:
        return _result("incomplete", "no_currently_selectable_opponent_response", base, known_actions=tuple(composed))
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "moveset_completeness": "complete", "known_action_ids": tuple(action["action_id"] for action in composed),
        "selectable_response_action_ids": selectable, "actions": tuple(deepcopy(composed)),
        "response_set_provenance": deepcopy(checked["provenance"]),
        "provenance": "runtime_d0_explicit_complete_opponent_response_set_v1",
    }


def _base(d0: Any, actions: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(actions, Mapping) or actions.get("schema_version") != ACTION_SCHEMA_VERSION:
        return None
    opponent, target = d0.get("active_owners", {}).get("opponent"), d0.get("active_owners", {}).get("self")
    required = ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint", "decision_owner")
    if not isinstance(opponent, Mapping) or not isinstance(target, Mapping) or any(key not in d0 for key in required):
        return None
    expected = {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "opponent_actor": opponent, "target_owner": target}
    if any(actions.get(key) != value for key, value in expected.items()):
        return None
    return {key: deepcopy(value) if isinstance(value, Mapping) else value for key, value in expected.items()}


def _active_opponent(state: Any, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = state.get("opponent_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    value = roster.get(owner.get("slot_index")) if isinstance(roster, Mapping) else None
    return value if isinstance(value, Mapping) and side.get("active_slot_index") == owner.get("slot_index") and value.get("pokemon_id") == owner.get("pokemon_id") else None


def _observed_complete_set(value: Any, state: Any, pokemon: Mapping[str, Any]) -> Mapping[str, Any] | str | None:
    if value is None:
        return None
    if not isinstance(value, Mapping) or set(value) != {"moveset_completeness", "move_ids", "provenance"}:
        return "opponent_moveset_completeness_record_invalid"
    provenance, moves = value.get("provenance"), value.get("move_ids")
    if value.get("moveset_completeness") != "complete" or not isinstance(moves, list) or len(moves) != 4 or len(set(moves)) != 4 or moves != pokemon.get("known_move_ids"):
        return "opponent_moveset_completeness_record_invalid"
    if not isinstance(provenance, Mapping) or provenance.get("event_kind") != "current_opponent_response_set_observed" or provenance.get("trust") != "user_confirmed_observation" or provenance.get("source_sequence") != (state.get("last_applied_observation_sequence") if isinstance(state, Mapping) else None):
        return None
    return value


def _status(value: Any) -> str:
    return value.get("status") if isinstance(value, Mapping) and value.get("status") in {"incomplete", "unsupported", "rejected"} else "rejected"


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
