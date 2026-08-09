"""Design-only deterministic DTO contract for threat-aware ranking explanations."""
from __future__ import annotations


_TIER_REASON = {
    "executed_guaranteed_ohko": ("penalty", "opponent_executed_guaranteed_ohko"),
    "unresolved_guaranteed_ohko_exposure": ("penalty", "opponent_unresolved_guaranteed_ohko"),
    "executed_possible_ohko": ("penalty", "opponent_executed_possible_ohko"),
    "neutral_no_positive_threat_evidence": ("neutral", "neutral_partial_or_unknown"),
    "complete_set_no_guaranteed_ohko": ("bounded_reward", "complete_set_no_guaranteed_ohko"),
    "complete_set_all_actions_preempted": ("bounded_reward", "complete_set_all_preempted"),
}
_PENALTY_TIERS = {"executed_guaranteed_ohko", "unresolved_guaranteed_ohko_exposure", "executed_possible_ohko"}


def _project(*, candidate_id, tier, set_state, complete, mechanically_complete, witnesses=()):
    """Fixture-only proposed DTO; production formatting remains unchanged."""
    reason = _TIER_REASON.get(tier)
    if reason is None or (tier.startswith("complete_set_") and not (complete and mechanically_complete)):
        return {"status": "unavailable", "candidate_id": candidate_id}
    witness = next((row for row in witnesses if row.get("tier") == tier), None)
    if tier in _PENALTY_TIERS:
        if not isinstance(witness, dict) or not isinstance(witness.get("move_id"), str):
            return {"status": "unavailable", "candidate_id": candidate_id}
    if tier == "executed_guaranteed_ohko":
        text = f"확인된 상대 기술 {witness['move_id']}에 실행 가능한 확정 1타 위험이 있어 우선순위가 낮아졌습니다."
    elif tier == "unresolved_guaranteed_ohko_exposure":
        text = f"확인된 상대 기술 {witness['move_id']}은 1타 처치가 가능하지만 행동 순서가 확정되지 않아 위험 요소로 반영했습니다."
    elif tier == "executed_possible_ohko":
        text = f"확인된 상대 기술 {witness['move_id']}에 1타 가능성이 있어 순위에 불리하게 반영했습니다."
    elif tier == "complete_set_no_guaranteed_ohko":
        text = "현재 확인된 4개 기술과 지원되는 결정적 계산 범위에서는 확정 1타 위협이 확인되지 않았습니다."
    elif tier == "complete_set_all_actions_preempted":
        text = "현재 확인된 4개 기술 기준으로 이 행동이 모든 상대 행동보다 먼저 확정 1타로 저지할 수 있는 것으로 계산됩니다."
    else:
        text = None
    scope_note = "상대의 아직 확인되지 않은 기술은 이 판단에 포함되지 않습니다." if set_state == "partially_known" and text else None
    return {"status": "available", "candidate_id": candidate_id, "threat_tier": tier, "threat_adjustment_kind": reason[0], "primary_reason_code": reason[1], "supporting_opponent_move_id": witness.get("move_id") if isinstance(witness, dict) else None, "text": text, "scope_note": scope_note}


def test_tier_reason_mapping_is_application_owned_and_partial_witness_uses_frozen_order():
    dto = _project(candidate_id="self:0:slam", tier="executed_guaranteed_ohko", set_state="partially_known", complete=False, mechanically_complete=True, witnesses=(
        {"tier": "executed_guaranteed_ohko", "move_id": "earthquake"},
        {"tier": "executed_guaranteed_ohko", "move_id": "stone-edge"},
    ))
    assert dto["primary_reason_code"] == "opponent_executed_guaranteed_ohko"
    assert dto["supporting_opponent_move_id"] == "earthquake"
    assert dto["scope_note"] == "상대의 아직 확인되지 않은 기술은 이 판단에 포함되지 않습니다."
    assert "확률" not in dto["text"] and "반드시 패배" not in dto["text"]


def test_unresolved_and_possible_wording_do_not_claim_first_action_or_guaranteed_loss():
    unresolved = _project(candidate_id="self:0:move", tier="unresolved_guaranteed_ohko_exposure", set_state="partially_known", complete=False, mechanically_complete=True, witnesses=({"tier": "unresolved_guaranteed_ohko_exposure", "move_id": "earthquake"},))
    possible = _project(candidate_id="self:0:move", tier="executed_possible_ohko", set_state="partially_known", complete=False, mechanically_complete=True, witnesses=({"tier": "executed_possible_ohko", "move_id": "ice-beam"},))
    assert "행동 순서가 확정되지" in unresolved["text"] and "먼저 행동" not in unresolved["text"]
    assert "1타 가능성" in possible["text"] and "확정 1타" not in possible["text"]


def test_partial_neutral_and_preempted_raw_capability_do_not_become_safety_or_danger_copy():
    neutral = _project(candidate_id="self:1:quick", tier="neutral_no_positive_threat_evidence", set_state="partially_known", complete=False, mechanically_complete=True)
    assert neutral["text"] is None and neutral["scope_note"] is None
    assert neutral["threat_adjustment_kind"] == "neutral"


def test_complete_safety_copy_requires_complete_supported_scope_and_never_claims_a_win():
    unavailable = _project(candidate_id="self:0:move", tier="complete_set_all_actions_preempted", set_state="partially_known", complete=False, mechanically_complete=True)
    safety = _project(candidate_id="self:0:move", tier="complete_set_no_guaranteed_ohko", set_state="complete", complete=True, mechanically_complete=True)
    assert unavailable["status"] == "unavailable"
    assert "현재 확인된 4개 기술" in safety["text"]
    assert "안전" not in safety["text"] and "승리" not in safety["text"]


def test_malformed_tier_reason_pair_fails_closed_and_provider_fields_are_not_part_of_dto():
    malformed = _project(candidate_id="self:0:move", tier="unknown-tier", set_state="partial", complete=False, mechanically_complete=False)
    assert malformed == {"status": "unavailable", "candidate_id": "self:0:move"}
    dto = _project(candidate_id="self:0:move", tier="neutral_no_positive_threat_evidence", set_state="unknown", complete=False, mechanically_complete=False)
    assert not ({"recommendation_status", "selected_candidate_id", "explanation_code", "ko_by_1", "exact_damage_rolls"} & set(dto))
