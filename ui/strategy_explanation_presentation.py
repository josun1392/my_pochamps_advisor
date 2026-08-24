"""Pure presentation model for detached deterministic strategy explanations.

This module deliberately consumes only ``deterministic-strategy-explanation-v1``.
It neither invokes strategy orchestration nor reaches into battle-state/mechanics data.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


EXPLANATION_SCHEMA = "deterministic-strategy-explanation-v1"
PRESENTATION_SCHEMA = "deterministic-strategy-explanation-presentation-v1"
HORIZON = "immediate_action_consequence"


def present_strategy_explanation(*, explanation: Mapping[str, Any]) -> dict[str, Any]:
    """Return a detached, display-ready model from an orchestration explanation."""
    if not isinstance(explanation, Mapping) or explanation.get("schema_version") != EXPLANATION_SCHEMA:
        return _rejected("invalid_strategy_explanation")
    if explanation.get("status") != "resolved" or explanation.get("horizon") != HORIZON:
        return _rejected("inconsistent_strategy_explanation")
    owner = explanation.get("decision_owner")
    candidates = explanation.get("candidates")
    frontier = explanation.get("preferred_frontier")
    if (
        not isinstance(owner, Mapping)
        or explanation.get("session_id") != owner.get("session_id")
        or not isinstance(explanation.get("decision_branch_fingerprint"), str)
        or not isinstance(candidates, list)
        or not isinstance(frontier, list)
        or any(not isinstance(candidate_id, str) for candidate_id in frontier)
    ):
        return _rejected("inconsistent_strategy_explanation_d0")
    rendered_candidates = []
    for candidate in candidates:
        row = _candidate(candidate, frontier)
        if row is None:
            return _rejected("invalid_strategy_candidate_explanation")
        rendered_candidates.append(row)
    rendered_candidates.sort(key=lambda row: row["candidate_id"])
    overall_status = _overall_status(explanation.get("overall_status"), frontier, rendered_candidates)
    return {
        "status": "resolved",
        "schema_version": PRESENTATION_SCHEMA,
        "session_id": explanation["session_id"],
        "decision_branch_fingerprint": explanation["decision_branch_fingerprint"],
        "decision_owner": deepcopy(dict(owner)),
        "overall_status": overall_status,
        "preferred_frontier": sorted(frontier),
        "horizon": HORIZON,
        "horizon_notice": "범위: 즉시 행동 결과만 (상대 행동 및 턴 종료 효과 제외)",
        "candidates": rendered_candidates,
        "comparison_matrix": deepcopy(explanation.get("comparison_matrix", [])),
        "provenance": "detached_strategy_explanation_presentation_v1",
    }


def render_strategy_explanation(*, presentation: Mapping[str, Any]) -> str:
    """Render deterministic Korean display text from the pure presentation model."""
    if not isinstance(presentation, Mapping) or presentation.get("schema_version") != PRESENTATION_SCHEMA:
        return "결정론적 전략 설명을 표시할 수 없습니다."
    if presentation.get("status") != "resolved":
        return "결정론적 전략 설명을 표시할 수 없습니다."
    candidates = presentation.get("candidates")
    if not isinstance(candidates, list):
        return "결정론적 전략 설명을 표시할 수 없습니다."
    lines = [_status_text(presentation.get("overall_status"), presentation.get("preferred_frontier")), presentation["horizon_notice"]]
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            return "결정론적 전략 설명을 표시할 수 없습니다."
        marker = "★" if candidate.get("preferred_frontier_member") else "-"
        lines.append(f"{marker} {candidate.get('label', candidate.get('candidate_id', '알 수 없는 행동'))} [{_evidence_label(candidate.get('evidence_class'))}]")
        details = candidate.get("fact_labels")
        if isinstance(details, list) and details:
            lines.append("  " + "; ".join(details))
        uncertainty = candidate.get("uncertainty_labels")
        if isinstance(uncertainty, list) and uncertainty:
            lines.append("  " + "; ".join(uncertainty))
        reasons = candidate.get("reason_labels")
        if isinstance(reasons, list) and reasons:
            lines.append("  선호 근거: " + "; ".join(reasons))
        incomplete = candidate.get("incomplete_reason")
        if isinstance(incomplete, str):
            lines.append("  불완전: " + _incomplete_label(incomplete))
    return "\n".join(lines)


def _candidate(candidate: Any, frontier: list[str]) -> dict[str, Any] | None:
    if not isinstance(candidate, Mapping):
        return None
    candidate_id = candidate.get("candidate_id")
    action_type = candidate.get("action_type")
    evidence_class = candidate.get("evidence_class")
    if not isinstance(candidate_id, str) or not isinstance(action_type, str) or not isinstance(evidence_class, str):
        return None
    facts = candidate.get("guaranteed_facts")
    if facts is not None and not isinstance(facts, Mapping):
        return None
    reasons = candidate.get("comparison_reasons")
    if reasons is not None and (not isinstance(reasons, list) or any(not isinstance(reason, str) for reason in reasons)):
        return None
    uncertainty = candidate.get("hit_miss_uncertainty")
    if uncertainty is not None and not _hit_miss_uncertainty(uncertainty, candidate_id):
        return None
    critical = candidate.get("critical_hit_uncertainty")
    if critical is not None and not _critical_hit_uncertainty(critical, candidate_id):
        return None
    secondaries = candidate.get("probabilistic_self_stage_effect_summaries")
    if secondaries is not None and not _probabilistic_self_stage_effect_summaries(secondaries, candidate_id):
        return None
    return {
        "candidate_id": candidate_id,
        "label": _label(candidate_id, action_type),
        "action_type": action_type,
        "evidence_class": evidence_class,
        "execution_readiness": candidate.get("execution_readiness"),
        "preferred_frontier_member": candidate_id in frontier,
        "dominated": bool(frontier) and candidate_id not in frontier,
        "guaranteed_facts": deepcopy(dict(facts)) if isinstance(facts, Mapping) else None,
        "interval": deepcopy(candidate.get("interval")) if isinstance(candidate.get("interval"), Mapping) else None,
        "hit_miss_uncertainty": deepcopy(dict(uncertainty)) if isinstance(uncertainty, Mapping) else None,
        "critical_hit_uncertainty": deepcopy(dict(critical)) if isinstance(critical, Mapping) else None,
        "damage_roll_summaries": deepcopy(candidate.get("damage_roll_summaries", ())),
        "probabilistic_self_stage_effect_summaries": deepcopy(secondaries) if isinstance(secondaries, (tuple, list)) else (),
        "incomplete_reason": candidate.get("incomplete_reason"),
        "provenance": candidate.get("provenance"),
        "fact_labels": _fact_labels(facts),
        "uncertainty_labels": [*_uncertainty_labels(uncertainty), *_critical_uncertainty_labels(critical), *_roll_uncertainty_labels(candidate.get("damage_roll_summaries")), *_probabilistic_self_stage_effect_labels(secondaries)],
        "reason_labels": [_reason_label(reason) for reason in reasons or []],
    }


def _overall_status(status: Any, frontier: list[str], candidates: list[dict[str, Any]]) -> str:
    if status == "selection_incomplete":
        return "selection_incomplete"
    if status == "incomplete_comparison_set":
        return "incomplete_comparison_set"
    if not candidates:
        return "no_selectable_candidates"
    if len(frontier) == 1:
        return "uniquely_preferred"
    return "tied_preferred_set"


def _label(candidate_id: str, action_type: str) -> str:
    _, _, raw = candidate_id.partition(":")
    readable = raw.replace("-", " ").replace("_", " ").title() if raw else candidate_id
    return f"교체: {readable}" if action_type == "manual_switch" else f"기술: {readable}"


def _fact_labels(facts: Any) -> list[str]:
    if not isinstance(facts, Mapping):
        return []
    labels: list[str] = []
    if facts.get("guaranteed_opponent_fainted") is True:
        labels.append("상대 기절 보장")
    elif facts.get("guaranteed_opponent_fainted") is False:
        labels.append("이 행동 결과 범위에서 상대 생존 보장")
    if facts.get("possible_opponent_ko") is True:
        labels.append("상대 기절 가능")
    substitute = facts.get("substitute_facts")
    if isinstance(substitute, Mapping):
        if substitute.get("guaranteed_substitute_break"):
            labels.append("대타 파괴 보장")
        elif substitute.get("guaranteed_substitute_survival"):
            labels.append("대타 생존 보장")
        elif substitute.get("possible_substitute_break"):
            labels.append("대타 파괴 가능")
    if isinstance(facts.get("exact_own_hp"), int):
        labels.append(f"자신의 정확한 HP: {facts['exact_own_hp']}")
    return labels


def _hit_miss_uncertainty(value: Mapping[str, Any], candidate_id: str) -> bool:
    return (
        value.get("status") == "resolved"
        and value.get("schema_version") == "deterministic-predictive-hit-miss-uncertainty-v1"
        and value.get("candidate_id", f"attack:{value.get('move_id')}") == candidate_id
        and isinstance(value.get("probability_percent"), int) and 0 <= value["probability_percent"] <= 100
        and isinstance(value.get("branches"), (tuple, list)) and isinstance(value.get("guaranteed_facts"), Mapping)
    )


def _critical_hit_uncertainty(value: Mapping[str, Any], candidate_id: str) -> bool:
    probability = value.get("critical_probability")
    branches = value.get("branches")
    return (
        value.get("status") == "resolved"
        and value.get("schema_version") == "deterministic-predictive-critical-hit-uncertainty-v1"
        and value.get("move_id") == candidate_id.removeprefix("attack:")
        and isinstance(probability, Mapping)
        and all(isinstance(probability.get(key), int) and not isinstance(probability.get(key), bool) for key in ("numerator", "denominator"))
        and probability["denominator"] > 0 and 0 <= probability["numerator"] <= probability["denominator"]
        and isinstance(branches, (tuple, list)) and all(isinstance(branch, Mapping) and branch.get("branch") in {"non_critical", "critical"} for branch in branches)
    )


def _probabilistic_self_stage_effect_summaries(value: Any, candidate_id: str) -> bool:
    if not isinstance(value, (tuple, list)):
        return False
    for row in value:
        if not isinstance(row, Mapping) or not isinstance(row.get("branch_path"), str) or row.get("conditional_on") != "successful_damaging_hit":
            return False
        uncertainty = row.get("uncertainty")
        probability = uncertainty.get("effect_probability") if isinstance(uncertainty, Mapping) else None
        branches = uncertainty.get("branches") if isinstance(uncertainty, Mapping) else None
        if not isinstance(uncertainty, Mapping) or uncertainty.get("status") != "resolved" or uncertainty.get("schema_version") != "deterministic-predictive-probabilistic-self-stage-effect-uncertainty-v1" or uncertainty.get("move_id") != candidate_id.removeprefix("attack:") or not isinstance(probability, Mapping) or not isinstance(branches, (tuple, list)):
            return False
        numerator, denominator = probability.get("numerator"), probability.get("denominator")
        if not isinstance(numerator, int) or isinstance(numerator, bool) or not isinstance(denominator, int) or isinstance(denominator, bool) or denominator <= 0 or not 0 <= numerator <= denominator:
            return False
    return True


def _uncertainty_labels(value: Any) -> list[str]:
    if not isinstance(value, Mapping):
        return []
    branches = value.get("branches")
    names = [branch.get("branch") for branch in branches if isinstance(branch, Mapping)] if isinstance(branches, (tuple, list)) else []
    probability = value.get("probability_percent")
    if names == ["hit"]:
        return ["명중 판정: 명중 전용"]
    if names == ["miss"]:
        return ["명중 판정: 실패 전용 (0%)"]
    if names == ["hit", "miss"] and isinstance(probability, int):
        return [f"명중 판정: 명중 {probability}% / 실패 {100 - probability}%"]
    return []


def _critical_uncertainty_labels(value: Any) -> list[str]:
    if not isinstance(value, Mapping): return []
    probability, branches = value.get("critical_probability"), value.get("branches")
    if not isinstance(probability, Mapping) or not isinstance(branches, (tuple, list)): return []
    numerator, denominator = probability.get("numerator"), probability.get("denominator")
    if not isinstance(numerator, int) or not isinstance(denominator, int) or denominator <= 0: return []
    names = [branch.get("branch") for branch in branches if isinstance(branch, Mapping)]
    state = "비급소 전용" if names == ["non_critical"] else "급소 전용" if names == ["critical"] else "비급소/급소 분기" if names == ["non_critical", "critical"] else None
    return [f"명중 시 급소 판정: {numerator}/{denominator} ({state})"] if state else []
def _probabilistic_self_stage_effect_labels(values: Any) -> list[str]:
    if not isinstance(values, (tuple, list)):
        return []
    labels = []
    for row in values:
        uncertainty = row.get("uncertainty") if isinstance(row, Mapping) else None
        probability = uncertainty.get("effect_probability") if isinstance(uncertainty, Mapping) else None
        branches = uncertainty.get("branches") if isinstance(uncertainty, Mapping) else None
        if not isinstance(probability, Mapping) or not isinstance(branches, (tuple, list)):
            continue
        numerator, denominator = probability.get("numerator"), probability.get("denominator")
        path = row.get("branch_path") if isinstance(row, Mapping) else None
        if not isinstance(numerator, int) or not isinstance(denominator, int) or denominator <= 0 or not isinstance(path, str):
            continue
        if numerator == 0:
            labels.append(f"{path} 성공 명중 후 Attack +1: 억제됨 (0/{denominator})")
        elif numerator == denominator:
            labels.append(f"{path} 성공 명중 후 Attack +1: 발생 보장 ({numerator}/{denominator})")
        else:
            labels.append(f"{path} 성공 명중 후 Attack +1 가능: {numerator}/{denominator} (미발동 {denominator - numerator}/{denominator})")
    return labels
def _roll_uncertainty_labels(values:Any)->list[str]:
 if not isinstance(values,(tuple,list)):return []
 labels=[]
 for row in values:
  if not isinstance(row,Mapping):continue
  ko=row.get("ko_roll_count");path=row.get("branch_path")
  if isinstance(ko,int) and isinstance(path,str):labels.append(f"{path} 피해 roll: KO {ko}/16" if ko not in {0,16} else f"{path} 피해 roll: {'KO 보장' if ko==16 else 'KO 불가'} (16/16)")
 return labels


def _status_text(status: Any, frontier: Any) -> str:
    if status == "uniquely_preferred" and isinstance(frontier, list) and frontier:
        return "결정론적 전략 분석: 하나의 선호 후보가 있습니다."
    if status == "tied_preferred_set":
        return "결정론적 전략 분석: 동등 선호 후보가 있습니다."
    if status == "selection_incomplete":
        return "결정론적 전략 분석: 선택 가능한 행동 정보가 불완전합니다."
    if status == "no_selectable_candidates":
        return "결정론적 전략 분석: 선택 가능한 행동이 없습니다."
    return "결정론적 전략 분석: 일부 후보 비교가 불완전합니다."


def _evidence_label(evidence_class: Any) -> str:
    return {
        "exact_outcome": "정확 결과",
        "guaranteed_facts": "보장 사실",
        "hit_miss_uncertainty": "명중/실패 분기",
        "incomplete": "불완전",
    }.get(evidence_class, "지원되지 않는 증거")


def _reason_label(reason: str) -> str:
    return {
        "avoids_self_ko": "자신의 확정 기절 회피",
        "causes_opponent_ko": "상대 기절 보장",
        "safer_exact_self_hp": "더 높은 정확한 자신의 HP",
    }.get(reason, reason.replace("_", " "))


def _incomplete_label(reason: str) -> str:
    return {
        "observation_required": "관측 결과 필요",
        "unsupported_predictive_family": "지원되지 않는 예측 기술 계열",
        "incoming_state_unavailable": "교체 대상 현재 상태 없음",
    }.get(reason, reason.replace("_", " "))


def _rejected(reason: str) -> dict[str, Any]:
    return {"status": "rejected", "schema_version": PRESENTATION_SCHEMA, "reason": reason}
