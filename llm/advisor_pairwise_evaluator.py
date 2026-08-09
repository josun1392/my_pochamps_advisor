"""Read-only self-candidate × known-opponent-action pair evidence."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence


def evaluate_self_opponent_pairs(*, self_candidates: Sequence[Mapping[str, Any]], opponent_evaluation: Mapping[str, Any], turn_snapshot: Any, repositories: Any) -> dict[str, Any]:
    """Build deterministic pairs without damage recalculation, aggregation, or ranking."""
    opponent_rows = opponent_evaluation.get("opponent_action_evaluations") if isinstance(opponent_evaluation, Mapping) else []
    candidate_set_complete = bool(opponent_evaluation.get("candidate_set_complete")) if isinstance(opponent_evaluation, Mapping) else False
    known_state = opponent_evaluation.get("known_move_state", "unknown") if isinstance(opponent_evaluation, Mapping) else "unknown"
    unknown_slots = opponent_evaluation.get("unknown_slots_remaining", 4) if isinstance(opponent_evaluation, Mapping) else 4
    pairs = [
        _evaluate_pair(self_candidate, opponent, turn_snapshot=turn_snapshot, repositories=repositories)
        for self_candidate in self_candidates if isinstance(self_candidate, Mapping)
        for opponent in opponent_rows if isinstance(opponent, Mapping)
    ] if isinstance(opponent_rows, list) else []
    complete = sum(pair["pair_mechanical_completeness"] is True for pair in pairs)
    insufficient = sum(pair["pair_mechanical_completeness"] is False and pair["pair_supportability"] == "insufficient_context" for pair in pairs)
    unsupported = sum(pair["pair_mechanical_completeness"] is False and pair["pair_supportability"] == "unsupported_mechanic" for pair in pairs)
    return {"opponent_known_move_state": known_state, "known_candidate_count": len(opponent_rows) if isinstance(opponent_rows, list) else 0, "opponent_candidate_set_complete": candidate_set_complete, "unknown_slots_remaining": unknown_slots, "pair_count": len(pairs), "mechanically_complete_pair_count": complete, "insufficient_pair_count": insufficient, "unsupported_pair_count": unsupported, "pairs": pairs}


def _evaluate_pair(self_candidate: Mapping[str, Any], opponent: Mapping[str, Any], *, turn_snapshot: Any, repositories: Any) -> dict[str, Any]:
    self_id = _self_id(self_candidate)
    opponent_id = opponent.get("candidate_id")
    session = opponent.get("session_id") if isinstance(opponent.get("session_id"), str) else "unknown"
    identity = {"pair_id": f"pair:{session}:{self_id}:{opponent_id}", "self_candidate_id": self_id, "opponent_candidate_id": opponent_id}
    order = _pair_action_order(self_candidate, opponent, turn_snapshot=turn_snapshot, repositories=repositories)
    self_success = _move_success(self_candidate)
    opponent_success = _move_success(opponent)
    self_mechanics = self_candidate.get("mechanics_result") if isinstance(self_candidate.get("mechanics_result"), Mapping) else {}
    opponent_mechanics = opponent.get("incoming_damage") if isinstance(opponent.get("incoming_damage"), Mapping) else {}
    self_preemption, opponent_preemption = _preemption(order, self_success, opponent_success, self_mechanics, opponent_mechanics)
    layers = [order.get("status"), self_success.get("status"), opponent_success.get("status"), _layer_status(self_mechanics), _layer_status(opponent_mechanics)]
    supportability = "unsupported_mechanic" if "unsupported_mechanic" in layers else "insufficient_context" if "insufficient_context" in layers else "complete"
    return {**identity, "action_order_result": deepcopy(order), "action_order_supportability": supportability if order.get("status") in {"insufficient_context", "unsupported_mechanic"} else "complete", "self_move_success": deepcopy(self_success), "opponent_move_success": deepcopy(opponent_success), "self_damage_supportability": _layer_status(self_mechanics), "opponent_damage_supportability": _layer_status(opponent_mechanics), "self_ko_supportability": _ko_status(self_mechanics), "opponent_ko_supportability": _ko_status(opponent_mechanics), "self_ohko_result": _ohko_result(self_mechanics), "opponent_ohko_result": _ohko_result(opponent_mechanics), "self_action_preemption_status": self_preemption, "opponent_action_preemption_status": opponent_preemption, "pair_supportability": supportability, "pair_mechanical_completeness": supportability == "complete"}


def _pair_action_order(self_candidate: Mapping[str, Any], opponent: Mapping[str, Any], *, turn_snapshot: Any, repositories: Any) -> dict[str, Any]:
    move = self_candidate.get("move")
    metadata = _metadata(repositories, move)
    opponent_metadata = _metadata(repositories, opponent.get("move_id"))
    if not isinstance(move, str) or not isinstance(metadata, Mapping) or not isinstance(opponent_metadata, Mapping):
        return {"status": "unsupported_mechanic", "unsupported_reason": "move_metadata"}
    try:
        serialized = turn_snapshot.to_dict()
        current = serialized.get("current_state")
        if not isinstance(current, Mapping): raise ValueError
        snapshot = {**deepcopy(dict(current)), "opponent_selected_move": {"move_id": opponent.get("move_id")}}
        from llm.advisor_candidate_contract import _action_order_evidence
        return _action_order_evidence(snapshot, move=move, metadata=metadata, repositories=repositories)
    except (AttributeError, TypeError, ValueError):
        return {"status": "insufficient_context", "missing_inputs": ["frozen_turn_snapshot"]}


def _preemption(order: Mapping[str, Any], self_success: Mapping[str, Any], opponent_success: Mapping[str, Any], self_mechanics: Mapping[str, Any], opponent_mechanics: Mapping[str, Any]) -> tuple[str, str]:
    status = order.get("status")
    self_ko = _guaranteed_ohko(self_mechanics)
    opponent_ko = _guaranteed_ohko(opponent_mechanics)
    if status == "acts_first" and self_success.get("status") == "allowed" and self_ko:
        return "executable", "preempted"
    if status == "acts_second" and opponent_success.get("status") == "allowed" and opponent_ko:
        return "preempted", "executable"
    return _execution_status(self_success), _execution_status(opponent_success)


def _guaranteed_ohko(mechanics: Mapping[str, Any]) -> bool:
    ko = mechanics.get("ko_interpretation")
    return isinstance(ko, Mapping) and ko.get("ko_supportability") == "complete" and ko.get("ohko_result") == "guaranteed"


def _execution_status(success: Mapping[str, Any]) -> str:
    status = success.get("status")
    return "blocked" if status == "blocked" else status if status in {"insufficient_context", "unsupported_mechanic", "not_applicable"} else "executable"


def _move_success(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    value = candidate.get("move_success")
    return value if isinstance(value, Mapping) else {"status": "allowed", "move_success_status": "allowed"}


def _layer_status(mechanics: Mapping[str, Any]) -> str:
    status = mechanics.get("status")
    return status if status in {"known", "not_applicable", "insufficient_context", "unsupported_mechanic"} else "insufficient_context"


def _ko_status(mechanics: Mapping[str, Any]) -> str:
    value = mechanics.get("ko_interpretation")
    return value.get("ko_supportability", "not_applicable") if isinstance(value, Mapping) else "not_applicable"


def _ohko_result(mechanics: Mapping[str, Any]) -> str | None:
    value = mechanics.get("ko_interpretation")
    return value.get("ohko_result") if isinstance(value, Mapping) and value.get("ko_supportability") == "complete" else None


def _self_id(candidate: Mapping[str, Any]) -> str:
    return f"self:{candidate.get('slot_index', 'unknown')}:{candidate.get('move', 'unknown')}"


def _metadata(repository: Any, move_id: Any) -> Mapping[str, Any] | None:
    if not isinstance(move_id, str) or not move_id: return None
    try: value = repository.get(move_id) if hasattr(repository, "get") else repository[move_id]
    except Exception: return None
    return value if isinstance(value, Mapping) else None
