"""Strict current exact opponent move PP authority from the response-set observation."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness

SCHEMA_VERSION = "runtime-d0-current-opponent-move-pp-state-authority-v1"


def freeze_runtime_d0_current_opponent_move_pp_state_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    base = _base(strategy_d0)
    if base is None:
        return _result("rejected", "invalid_runtime_strategy_d0", {})
    fresh = runtime_strategy_d0_freshness(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
    )
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    pokemon = _active_opponent(state, base["opponent_actor"])
    if pokemon is None:
        return _result("rejected", "runtime_active_opponent_identity_mismatch", base)
    observed = pokemon.get("current_opponent_response_set")
    if observed is None:
        return _result("incomplete", "current_opponent_response_set_unknown", base)
    if not isinstance(observed, Mapping):
        return _result("rejected", "current_opponent_response_set_malformed", base)
    moves = observed.get("move_ids")
    provenance = observed.get("provenance")
    if (
        observed.get("moveset_completeness") != "complete"
        or not isinstance(moves, list) or len(moves) != 4 or len(set(moves)) != 4
        or moves != pokemon.get("known_move_ids")
        or not isinstance(provenance, Mapping)
        or provenance.get("event_kind") != "current_opponent_response_set_observed"
        or provenance.get("trust") != "user_confirmed_observation"
    ):
        return _result("rejected", "current_opponent_response_set_binding_invalid", base)
    source_sequence = provenance.get("source_sequence")
    last_sequence = state.get("last_applied_observation_sequence") if isinstance(state, Mapping) else None
    if not isinstance(source_sequence, int) or isinstance(source_sequence, bool) or source_sequence < 1:
        return _result("rejected", "current_opponent_response_set_sequence_invalid", base)
    if source_sequence != last_sequence:
        return _result("incomplete", "current_opponent_response_set_not_fresh", base)
    pp = observed.get("move_pp_slots")
    if pp is None:
        return _result(
            "incomplete", "current_opponent_move_pp_snapshot_unknown", base,
            response_observation_source_sequence=source_sequence,
            ordered_move_ids=tuple(moves),
        )
    usability = pokemon.get("current_move_usability")
    checked = _validate_pp(moves, usability, pp)
    if isinstance(checked, str):
        return _result("rejected", checked, base)
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        **base,
        "response_observation_source_sequence": source_sequence,
        "ordered_move_ids": tuple(moves),
        "ordered_pp_slots": tuple(deepcopy(checked)),
        "response_set_provenance": deepcopy(provenance),
        "provenance": "strict_current_opponent_move_pp_from_response_set_v1",
    }


def validate_runtime_d0_current_opponent_move_pp_state_authority(value: Any) -> bool:
    if (
        not isinstance(value, Mapping)
        or value.get("status") != "resolved"
        or value.get("schema_version") != SCHEMA_VERSION
    ):
        return False
    moves = value.get("ordered_move_ids")
    slots = value.get("ordered_pp_slots")
    provenance = value.get("response_set_provenance")
    sequence = value.get("response_observation_source_sequence")
    actor = value.get("opponent_actor")
    if (
        not isinstance(moves, tuple) or len(moves) != 4 or len(set(moves)) != 4
        or not all(isinstance(move, str) and bool(move) for move in moves)
        or not isinstance(slots, tuple) or len(slots) != 4
        or not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1
        or not isinstance(provenance, Mapping)
        or provenance.get("event_kind") != "current_opponent_response_set_observed"
        or provenance.get("trust") != "user_confirmed_observation"
        or provenance.get("source_sequence") != sequence
        or not isinstance(actor, Mapping)
        or actor.get("side") != "opponent"
        or any(key not in value for key in (
            "session_id", "source_runtime_fingerprint",
            "source_branch_fingerprint", "decision_owner",
        ))
    ):
        return False
    for index, move in enumerate(moves):
        row = slots[index]
        if not isinstance(row, Mapping) or set(row) != {"slot_index", "move_id", "current_pp", "max_pp"}:
            return False
        current_pp, max_pp = row.get("current_pp"), row.get("max_pp")
        if (
            row.get("slot_index") != index
            or row.get("move_id") != move
            or not isinstance(current_pp, int) or isinstance(current_pp, bool) or current_pp < 0
            or not isinstance(max_pp, int) or isinstance(max_pp, bool) or max_pp <= 0
            or current_pp > max_pp
        ):
            return False
    return True


def _base(d0: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved":
        return None
    opponent = d0.get("active_owners", {}).get("opponent")
    if not isinstance(opponent, Mapping):
        return None
    required = ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint", "decision_owner")
    if any(key not in d0 for key in required):
        return None
    return {
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(d0["decision_owner"]),
        "opponent_actor": deepcopy(opponent),
    }


def _active_opponent(state: Any, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = state.get("opponent_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    row = roster.get(owner.get("slot_index")) if isinstance(roster, Mapping) else None
    if (
        not isinstance(row, Mapping)
        or side.get("active_slot_index") != owner.get("slot_index")
        or row.get("pokemon_id") != owner.get("pokemon_id")
    ):
        return None
    return row


def _validate_pp(moves: list[str], usability: Any, pp: Any) -> list[dict[str, Any]] | str:
    if not isinstance(pp, list) or len(pp) != 4:
        return "opponent_move_pp_snapshot_malformed"
    if not isinstance(usability, Mapping) or set(usability) != set(moves):
        return "opponent_move_pp_usability_binding_invalid"
    rows = []
    seen_slots, seen_moves = set(), set()
    for index, move in enumerate(moves):
        row = pp[index]
        if not isinstance(row, Mapping) or set(row) != {"slot_index", "move_id", "current_pp", "max_pp"}:
            return "opponent_move_pp_snapshot_malformed"
        current_pp, max_pp = row.get("current_pp"), row.get("max_pp")
        if (
            row.get("slot_index") != index or row.get("move_id") != move
            or index in seen_slots or move in seen_moves
            or not isinstance(current_pp, int) or isinstance(current_pp, bool) or current_pp < 0
            or not isinstance(max_pp, int) or isinstance(max_pp, bool) or max_pp <= 0
            or current_pp > max_pp
        ):
            return "opponent_move_pp_snapshot_order_or_value_invalid"
        u = usability.get(move)
        if not isinstance(u, Mapping):
            return "opponent_move_pp_usability_binding_invalid"
        if u.get("status") == "known_usable" and current_pp == 0:
            return "opponent_move_pp_usability_contradiction"
        if u.get("status") == "known_unusable" and u.get("reason") == "no_pp" and current_pp > 0:
            return "opponent_move_pp_usability_contradiction"
        seen_slots.add(index); seen_moves.add(move)
        rows.append({
            "slot_index": index,
            "move_id": move,
            "current_pp": current_pp,
            "max_pp": max_pp,
        })
    return rows


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "status": status,
        "schema_version": SCHEMA_VERSION,
        **deepcopy(dict(base)),
        "reason": reason,
        **deepcopy(extra),
    }
