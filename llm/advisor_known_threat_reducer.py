"""Read-only categorical summaries of frozen known-opponent pair evidence."""
from __future__ import annotations

from typing import Any, Mapping, Sequence


def reduce_known_opponent_threats(*, pair_set: Mapping[str, Any], self_candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Group existing pairs only; never recalculate or rank mechanics."""
    pairs = pair_set.get("pairs") if isinstance(pair_set, Mapping) else []
    pairs = [pair for pair in pairs if isinstance(pair, Mapping)] if isinstance(pairs, list) else []
    identities = [_self_id(candidate) for candidate in self_candidates if isinstance(candidate, Mapping)]
    return {"threat_summaries": [_summary(identity, [pair for pair in pairs if pair.get("self_candidate_id") == identity], pair_set) for identity in identities]}


def _summary(self_id: str, pairs: list[Mapping[str, Any]], pair_set: Mapping[str, Any]) -> dict[str, Any]:
    complete_pairs = [pair for pair in pairs if pair.get("pair_mechanical_completeness") is True]
    incomplete = len(pairs) - len(complete_pairs)
    raw_guaranteed = [pair for pair in complete_pairs if pair.get("opponent_ohko_result") == "guaranteed"]
    raw_possible = [pair for pair in complete_pairs if pair.get("opponent_ohko_result") == "possible"]
    executable = [pair for pair in complete_pairs if _allowed(pair) and pair.get("opponent_action_preemption_status") != "preempted"]
    executed_guaranteed = [pair for pair in executable if pair.get("opponent_ohko_result") == "guaranteed"]
    executed_possible = [pair for pair in executable if pair.get("opponent_ohko_result") == "possible"]
    all_complete = bool(pairs) and incomplete == 0
    all_preempted = _universal(pairs, all_complete, lambda pair: pair.get("opponent_action_preemption_status") == "preempted")
    no_guaranteed = "false" if raw_guaranteed else _universal(pairs, all_complete, lambda pair: pair.get("opponent_ohko_result") != "guaranteed")
    set_complete = pair_set.get("opponent_candidate_set_complete") is True
    known_count = pair_set.get("known_candidate_count") if isinstance(pair_set.get("known_candidate_count"), int) else len(pairs)
    return {
        "self_candidate_id": self_id,
        "opponent_known_move_state": pair_set.get("opponent_known_move_state", "unknown"),
        "known_candidate_count": known_count,
        "unknown_slots_remaining": pair_set.get("unknown_slots_remaining", 4),
        "candidate_set_complete": set_complete,
        "known_pair_count": len(pairs),
        "mechanically_complete_pair_count": len(complete_pairs),
        "incomplete_pair_count": incomplete,
        "unsupported_pair_count": sum(pair.get("pair_supportability") == "unsupported_mechanic" for pair in pairs),
        "known_guaranteed_ohko_capability_exists": bool(raw_guaranteed),
        "known_possible_ohko_capability_exists": bool(raw_possible),
        "known_executed_guaranteed_ohko_threat_exists": bool(executed_guaranteed),
        "known_executed_possible_ohko_threat_exists": bool(executed_possible),
        "known_opponent_first_action_exists": any(pair.get("action_order_result", {}).get("status") == "acts_second" and _allowed(pair) for pair in complete_pairs if isinstance(pair.get("action_order_result"), Mapping)),
        "self_preempts_count": sum(pair.get("opponent_action_preemption_status") == "preempted" for pair in complete_pairs),
        "opponent_preempts_count": sum(pair.get("self_action_preemption_status") == "preempted" for pair in complete_pairs),
        "guaranteed_ohko_pair_count": len(executed_guaranteed), "possible_ohko_pair_count": len(executed_possible),
        "all_known_actions_preempted": all_preempted, "no_known_guaranteed_ohko": no_guaranteed,
        "known_threat_evaluation_complete": all_complete,
        "global_threat_complete": bool(set_complete and known_count == 4 and all_complete and pair_set.get("unknown_slots_remaining") == 0),
    }


def _allowed(pair: Mapping[str, Any]) -> bool:
    success = pair.get("opponent_move_success")
    return isinstance(success, Mapping) and success.get("status") == "allowed"


def _universal(pairs: list[Mapping[str, Any]], all_complete: bool, predicate: Any) -> str:
    if not pairs or not all_complete: return "unresolved"
    return "true" if all(predicate(pair) for pair in pairs) else "false"


def _self_id(candidate: Mapping[str, Any]) -> str:
    return f"self:{candidate.get('slot_index', 'unknown')}:{candidate.get('move', 'unknown')}"
