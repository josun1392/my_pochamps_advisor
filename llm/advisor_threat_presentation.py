"""Application-owned, selected-only projection for threat-ranking explanations."""
from __future__ import annotations

from typing import Any, Mapping

from llm.advisor_threat_ranking import project_threat_ranking_tier


_TIER_REASONS = {
    "executed_guaranteed_ohko": ("penalty", "opponent_executed_guaranteed_ohko"),
    "unresolved_guaranteed_ohko_exposure": ("penalty", "opponent_unresolved_guaranteed_ohko"),
    "executed_possible_ohko": ("penalty", "opponent_executed_possible_ohko"),
    "complete_set_no_guaranteed_ohko": ("bounded_reward", "complete_set_no_guaranteed_ohko"),
    "complete_set_all_actions_preempted": ("bounded_reward", "complete_set_all_actions_preempted"),
}


def project_selected_threat_presentation(
    *, selected_candidate_id: str, evidence_bundle: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Project existing frozen evidence only; malformed or neutral data is silent."""
    unavailable = {"presentation_status": "unavailable", "selected_candidate_id": selected_candidate_id}
    if not isinstance(selected_candidate_id, str) or not isinstance(evidence_bundle, Mapping):
        return unavailable
    summaries = _mapping(evidence_bundle.get("known_opponent_threat_summaries"))
    rows = summaries.get("threat_summaries")
    if not isinstance(rows, list):
        return unavailable
    summary = next(
        (row for row in rows if isinstance(row, Mapping) and row.get("self_candidate_id") == selected_candidate_id),
        None,
    )
    if summary is None:
        return unavailable
    try:
        tier, _ = project_threat_ranking_tier(summary)
    except ValueError:
        return unavailable
    if tier == "neutral_no_positive_threat_evidence":
        return unavailable
    reason = _TIER_REASONS.get(tier)
    if reason is None:
        return unavailable
    pairs = _pairs_for(selected_candidate_id, evidence_bundle)
    witness = _witness_for(tier, pairs)
    if tier.startswith("executed_") or tier.startswith("unresolved_"):
        if witness is None:
            return unavailable
    elif not _complete_scope(summary):
        return unavailable
    text = _text_for(tier, witness)
    if text is None:
        return unavailable
    partial = summary.get("opponent_known_move_state") == "partially_known"
    return {
        "presentation_status": "available",
        "selected_candidate_id": selected_candidate_id,
        "threat_tier": tier,
        "adjustment_kind": reason[0],
        "reason_code": reason[1],
        "witness_move_id": witness.get("move_id") if witness else None,
        "text": text,
        "scope_note": "아직 확인되지 않은 상대 기술은 이 판단에 포함되지 않습니다." if partial else None,
    }


def _pairs_for(selected_candidate_id: str, evidence_bundle: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    pair_set = _mapping(evidence_bundle.get("self_opponent_pairs"))
    pairs = pair_set.get("pairs")
    return [pair for pair in pairs if isinstance(pair, Mapping) and pair.get("self_candidate_id") == selected_candidate_id] if isinstance(pairs, list) else []


def _witness_for(tier: str, pairs: list[Mapping[str, Any]]) -> dict[str, str] | None:
    expected = "possible" if tier == "executed_possible_ohko" else "guaranteed"
    for pair in pairs:
        success = _mapping(pair.get("opponent_move_success"))
        if (
            pair.get("pair_mechanical_completeness") is True
            and success.get("status") == "allowed"
            and pair.get("opponent_action_preemption_status") != "preempted"
            and pair.get("opponent_ohko_result") == expected
        ):
            move_id = _move_id(pair.get("opponent_candidate_id"))
            if move_id:
                order = _mapping(pair.get("action_order_result")).get("status")
                return {"move_id": move_id, "order": order if isinstance(order, str) else ""}
    return None


def _complete_scope(summary: Mapping[str, Any]) -> bool:
    return (
        summary.get("candidate_set_complete") is True
        and summary.get("known_candidate_count") == 4
        and summary.get("unknown_slots_remaining") == 0
        and summary.get("known_threat_evaluation_complete") is True
        and summary.get("global_threat_complete") is True
    )


def _text_for(tier: str, witness: Mapping[str, str] | None) -> str | None:
    move = witness.get("move_id") if isinstance(witness, Mapping) else None
    if tier == "executed_guaranteed_ohko" and isinstance(move, str):
        if witness.get("order") == "acts_second":
            return f"상대가 먼저 행동하는 것으로 계산되는 {move}의 확정 1타 위험 때문에 우선순위가 낮아졌습니다."
        return f"확인된 상대 기술 {move}의 확정 1타 위험 때문에 우선순위가 낮아졌습니다."
    if tier == "unresolved_guaranteed_ohko_exposure" and isinstance(move, str):
        return f"확인된 상대 기술 {move}은 1타 처치가 가능한 것으로 계산되지만 행동 순서가 확정되지 않아 위험 요소로 반영되었습니다."
    if tier == "executed_possible_ohko" and isinstance(move, str):
        return f"확인된 상대 기술 {move}에 1타 가능성이 있어 우선순위에 불리하게 반영되었습니다."
    if tier == "complete_set_no_guaranteed_ohko":
        return "현재 확인된 4개 기술과 지원되는 결정적 계산 범위에서는 확정 1타 위협이 확인되지 않았습니다."
    if tier == "complete_set_all_actions_preempted":
        return "현재 확인된 4개 기술 기준으로는 이 행동이 상대의 모든 행동보다 먼저 확정 1타로 저지할 수 있는 것으로 계산됩니다."
    return None


def _move_id(candidate_id: Any) -> str | None:
    if not isinstance(candidate_id, str):
        return None
    parts = candidate_id.rsplit(":", 2)
    return parts[-2] if len(parts) == 3 and parts[-2] else None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
