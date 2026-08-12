"""Danger-only cross-action ranking evidence; no cross-kind winner selection."""
from typing import Any, Mapping, Sequence

_ORDINAL = {"executed_guaranteed_self_ko": 0, "unresolved_guaranteed_self_ko_exposure": 1, "possible_self_ko_exposure": 2, "neutral_no_positive_danger": 3}

def project_move_cross_action_danger(*, candidate_id: str, selectable: bool, threat_tier: str | None) -> dict[str, Any]:
    mapping = {"executed_guaranteed_ohko": "executed_guaranteed_self_ko", "unresolved_guaranteed_ohko_exposure": "unresolved_guaranteed_self_ko_exposure", "executed_possible_ohko": "possible_self_ko_exposure"}
    tier = mapping.get(threat_tier, "neutral_no_positive_danger")
    return _result(candidate_id, "move", selectable, tier)

def reduce_switch_cross_action_danger(*, switch_candidate_id: str, selectable: bool, incoming_results: Sequence[Mapping[str, Any]] | None) -> dict[str, Any]:
    rows = incoming_results if isinstance(incoming_results, Sequence) and not isinstance(incoming_results, (str, bytes)) else []
    tier = "neutral_no_positive_danger"
    for row in rows:
        hazard = row.get("entry_hazard_result") if isinstance(row, Mapping) else None
        if isinstance(hazard, Mapping) and hazard.get("status") == "complete" and hazard.get("hazard_ko") is True:
            tier = "executed_guaranteed_self_ko"; break
        residual = row.get("post_turn_residual_evidence") if isinstance(row, Mapping) else None
        if isinstance(residual, Mapping) and residual.get("status") == "complete" and residual.get("guaranteed_ko") is True:
            tier = "executed_guaranteed_self_ko"; break
        damage = row.get("damage_evidence") if isinstance(row, Mapping) else None
        ko = damage.get("ko_interpretation") if isinstance(damage, Mapping) else None
        label = ko.get("primary_ko_label") if isinstance(ko, Mapping) and ko.get("ko_supportability") == "complete" else None
        if label == "guaranteed_ohko": tier = "executed_guaranteed_self_ko"; break
        if label == "possible_ohko": tier = "possible_self_ko_exposure"
    result = _result(switch_candidate_id, "switch", selectable, tier)
    result["cross_action_supportability"] = "complete" if rows else "insufficient_context"
    result["full_switch_outcome_supportability"] = "unsupported_mechanic" if any(isinstance(row, Mapping) and row.get("full_switch_outcome_supportability") == "unsupported_mechanic" for row in rows) else "insufficient_context"
    return result

def compare_cross_action_danger(left: Mapping[str, Any], right: Mapping[str, Any]) -> str:
    if left.get("selectable") is True and right.get("selectable") is not True: return "left_better_eligibility"
    if right.get("selectable") is True and left.get("selectable") is not True: return "right_better_eligibility"
    a, b = left.get("cross_action_danger_tier"), right.get("cross_action_danger_tier")
    if a not in _ORDINAL or b not in _ORDINAL: return "malformed_unresolved"
    if _ORDINAL[a] < _ORDINAL[b]: return "left_better_danger"
    if _ORDINAL[b] < _ORDINAL[a]: return "right_better_danger"
    if left.get("action_kind") != right.get("action_kind"): return "tied_cross_kind_unresolved"
    return "tied_same_kind_native_resolvable" if left.get("action_kind") == "move" else "tied_same_kind_switch_unresolved"

def _result(candidate_id: str, kind: str, selectable: bool, tier: str) -> dict[str, Any]:
    return {"action_candidate_id": candidate_id, "action_kind": kind, "selectable": selectable is True, "cross_action_danger_tier": tier, "cross_action_danger_ordinal": _ORDINAL[tier], "cross_action_supportability": "complete"}
