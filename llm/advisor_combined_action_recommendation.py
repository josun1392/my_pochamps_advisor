"""Frozen application-owned action envelope before the move-only provider branch."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from llm.advisor_combined_action_selection import select_combined_self_action
from llm.advisor_cross_action_danger import project_move_cross_action_danger, reduce_switch_cross_action_danger
from llm.advisor_switch_incoming_evaluator import evaluate_switch_incoming_opponent_action
from llm.advisor_switch_entry_effects import evaluate_switch_entry_effects
from llm.advisor_switch_transition import project_authorized_switch_transition
from llm.advisor_shadow_tag_switch_block import aggregate_hard_blockers, derive_arena_trap_block, derive_magnet_pull_block, derive_shadow_tag_block, finalize_switch_candidates


def build_combined_action_envelope(*, prepared_cycle: Mapping[str, Any]) -> dict[str, Any]:
    """Select from one prepared frozen cycle; never construct provider input."""
    evidence = prepared_cycle.get("evidence_bundle") if isinstance(prepared_cycle, Mapping) else None
    snapshot = prepared_cycle.get("_combined_action_turn_snapshot") if isinstance(prepared_cycle, Mapping) else None
    if snapshot is None and isinstance(evidence, Mapping): snapshot = evidence.get("turn_snapshot")
    if not isinstance(evidence, Mapping) or snapshot is None:
        return _failure("insufficient_context")
    if isinstance(evidence, dict):
        evidence["switch_candidates"] = _finalized_switch_candidates(evidence.get("switch_candidates", []), snapshot)
    move_actions = _move_actions(evidence, prepared_cycle.get("candidates"))
    switch_actions = _switch_actions(evidence, snapshot)
    result = select_combined_self_action(move_actions=move_actions, switch_actions=switch_actions)
    selected_id, kind = result.get("selected_candidate_id"), result.get("selected_action_kind")
    if kind == "switch" and selected_id is not None:
        candidate = next((row for row in evidence.get("switch_candidates", []) if isinstance(row, Mapping) and row.get("candidate_id") == selected_id), None)
        if not isinstance(candidate, Mapping) or not _valid_switch(candidate):
            return _failure("validation_failed")
        return {"action_kind": "switch", "candidate_id": selected_id, "selection_status": "resolved", "selection_reason": result["selection_reason"], "supportability": result["selection_supportability"], "switch_candidate_id": selected_id, "target_pokemon_id": candidate["target_pokemon_id"], "target_slot_index": candidate["target_slot_index"], "tied_candidate_ids": [], "danger_tier": _tier_for(selected_id, switch_actions)}
    if kind == "move" and isinstance(selected_id, str):
        return {"action_kind": "move", "candidate_id": selected_id, "selection_status": "resolved", "selection_reason": result["selection_reason"], "supportability": result["selection_supportability"], "move_candidate_id": selected_id, "switch_candidate_id": None, "tied_candidate_ids": [], "danger_tier": _tier_for(selected_id, move_actions)}
    if result.get("selection_supportability") == "unresolved_equal_switches":
        return {"action_kind": None, "candidate_id": None, "selection_status": "unresolved_equal_switches", "selection_reason": "unresolved_switch_tie", "supportability": "unresolved_equal_switches", "move_candidate_id": None, "switch_candidate_id": None, "tied_candidate_ids": deepcopy(result.get("tied_candidate_ids", [])), "danger_tier": None}
    return _failure(result.get("selection_reason", "no_selectable_action"))


def build_combined_action_presentation(*, envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Return bounded deterministic non-move presentation only."""
    if not isinstance(envelope, Mapping): return {"status": "validation_failed", "action_kind": None, "text": None}
    if envelope.get("selection_status") == "resolved" and envelope.get("action_kind") == "switch":
        target = envelope.get("target_pokemon_id")
        if not isinstance(target, str) or not target: return {"status": "validation_failed", "action_kind": None, "text": None}
        reason = envelope.get("selection_reason")
        text = f"교체 추천: {target}"
        if reason == "lower_cross_action_danger": text += "\n현재 확인된 정보에서는 교체 쪽의 즉시 KO 위험이 더 낮습니다."
        elif reason in {"only_selectable_action", "lower_eligibility"}: text += "\n현재 확인된 정보에서 선택 가능한 교체 행동입니다."
        return {"status": "resolved", "action_kind": "switch", "text": text, "envelope": deepcopy(dict(envelope))}
    if envelope.get("selection_status") == "unresolved_equal_switches":
        return {"status": "unresolved_equal_switches", "action_kind": None, "text": "교체 후보가 여러 개이며 현재 계산만으로 우선순위를 정할 수 없습니다.", "envelope": deepcopy(dict(envelope))}
    return {"status": envelope.get("selection_status", "insufficient_context"), "action_kind": None, "text": None, "envelope": deepcopy(dict(envelope))}


def _move_actions(evidence: Mapping[str, Any], candidates: Any) -> list[dict[str, Any]]:
    summaries = evidence.get("known_opponent_threat_summaries", {}).get("threat_summaries", []) if isinstance(evidence.get("known_opponent_threat_summaries"), Mapping) else []
    tiers = {row.get("self_candidate_id"): _move_threat_tier(row) for row in summaries if isinstance(row, Mapping)}
    rows = candidates if isinstance(candidates, Sequence) and not isinstance(candidates, (str, bytes)) else []
    result = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping): continue
        identifier = f"self:{row.get('slot_index')}:{row.get('move')}"
        result.append(project_move_cross_action_danger(candidate_id=identifier, selectable=row.get("availability") == "available", threat_tier=tiers.get(identifier)) | {"native_move_rank": index})
    return result


def _move_threat_tier(summary: Mapping[str, Any]) -> str | None:
    if summary.get("known_executed_guaranteed_ohko_threat_exists") is True: return "executed_guaranteed_ohko"
    if summary.get("known_guaranteed_ohko_capability_exists") is True and summary.get("all_known_actions_preempted") != "true": return "unresolved_guaranteed_ohko_exposure"
    if summary.get("known_executed_possible_ohko_threat_exists") is True: return "executed_possible_ohko"
    return None


def _switch_actions(evidence: Mapping[str, Any], snapshot: Any) -> list[dict[str, Any]]:
    opponent = evidence.get("opponent_action_candidates", [])
    opponent_rows = opponent if isinstance(opponent, list) else opponent.get("candidates", []) if isinstance(opponent, Mapping) else []
    result = []
    for candidate in evidence.get("switch_candidates", []):
        if not isinstance(candidate, Mapping) or not _valid_switch(candidate): continue
        incoming = []
        entry_transition = project_authorized_switch_transition(turn_snapshot=_snapshot_adapter(snapshot), switch_candidate=candidate, switch_authorized=True)
        post = entry_transition.get("post_switch_snapshot") if isinstance(entry_transition, Mapping) else None
        target = post.get("target_roster_mechanics") if isinstance(post, Mapping) else None
        hazards = post.get("switch_hazard_context") if isinstance(post, Mapping) else None
        intimidate_authority = post.get("switch_entry_intimidate_authority") if isinstance(post, Mapping) else None
        download_authority = post.get("switch_entry_download_authority") if isinstance(post, Mapping) else None
        trace_authority = post.get("switch_entry_trace_authority") if isinstance(post, Mapping) else None
        sturdy_authority = post.get("switch_entry_sturdy_authority") if isinstance(post, Mapping) else None
        shared = post.get("side_shared_authority") if isinstance(post, Mapping) else None
        field_state = shared.get("field_state_context") if isinstance(shared, Mapping) else None
        entry_hazard_result = evaluate_switch_entry_effects(hazards=hazards, target=target, intimidate_authority=intimidate_authority, download_authority=download_authority, trace_authority=trace_authority, sturdy_authority=sturdy_authority, field_state_context=field_state) if isinstance(target, Mapping) else None
        # An entry KO is deterministic danger even if no opponent action was
        # supplied. Ordinary chip never creates a favorable ranking signal.
        if isinstance(entry_hazard_result, Mapping) and entry_hazard_result.get("status") == "complete" and entry_hazard_result.get("hazard_ko") is True:
            incoming.append({"entry_hazard_result": entry_hazard_result, "full_switch_outcome_supportability": "unsupported_mechanic"})
        for action in opponent_rows if isinstance(opponent_rows, list) else []:
            transition = project_authorized_switch_transition(turn_snapshot=_snapshot_adapter(snapshot), switch_candidate=candidate, switch_authorized=True, opponent_action=action if isinstance(action, Mapping) else None)
            post = transition.get("post_switch_snapshot") if isinstance(transition, Mapping) else None
            target = post.get("target_roster_mechanics") if isinstance(post, Mapping) else None
            hazards = post.get("switch_hazard_context") if isinstance(post, Mapping) else None
            hazard_result = entry_hazard_result if target is not None and hazards is not None else None
            incoming.append(evaluate_switch_incoming_opponent_action(transition=transition, entry_hazard_result=hazard_result))
        result.append(reduce_switch_cross_action_danger(switch_candidate_id=candidate["candidate_id"], selectable=candidate.get("selectable") is True, incoming_results=incoming))
    return result


def _finalized_switch_candidates(candidates: Any, snapshot: Any) -> list[dict[str, Any]]:
    """Apply frozen-only Shadow Tag veto before any cross-action projection."""
    rows = candidates if isinstance(candidates, Sequence) and not isinstance(candidates, (str, bytes)) else []
    data = snapshot if isinstance(snapshot, Mapping) else snapshot.to_dict() if hasattr(snapshot, "to_dict") else {}
    current = data.get("current_state") if isinstance(data, Mapping) else {}
    battle = data.get("battle_state") if isinstance(data, Mapping) else {}
    authority = current.get("ability_interaction_authority") if isinstance(current, Mapping) else None
    # Legacy/foundation-free frozen requests retain their existing conservative
    # candidate result; only a carried authority activates post-freeze finalization.
    if not isinstance(authority, Mapping):
        return [deepcopy(dict(row)) for row in rows if isinstance(row, Mapping)]
    manual = current.get("switch_candidate_context", {}).get("switch_permission_context", {}) if isinstance(current, Mapping) else {}
    player = battle.get("active_player", {}) if isinstance(battle, Mapping) else {}
    item = {"status": "known" if player.get("item_status") == "user_confirmed" else "known_absent" if player.get("item_status") == "absent" else "unknown", "value": player.get("known_item_id")}
    types = _current_types(current, "self")
    ability = _current_ability(current, "self")
    shadow = derive_shadow_tag_block(authority=authority or {}, self_type=types, self_item=item, self_ability=ability)
    magnet = derive_magnet_pull_block(authority=authority or {}, self_type=types, self_item=item)
    arena = derive_arena_trap_block(authority=authority or {}, groundedness=current.get("identity_groundedness_context", {}) if isinstance(current, Mapping) else {}, self_type=types, self_item=item)
    blocker = aggregate_hard_blockers(shadow, magnet, arena)
    return finalize_switch_candidates(rows, manual_permission=manual, blocker=blocker)


def _current_types(current: Mapping[str, Any], side: str) -> dict[str, Any]:
    entries = current.get("current_type_context", {}).get("current_types", []) if isinstance(current, Mapping) else []
    row = next((x for x in entries if isinstance(x, Mapping) and x.get("side") == side), None)
    return {"status": "known", "types": row.get("types")} if isinstance(row, Mapping) and row.get("state") == "known" and isinstance(row.get("types"), list) else {"status": "unknown"}


def _current_ability(current: Mapping[str, Any], side: str) -> dict[str, Any]:
    entries = current.get("ability_context", {}).get("current_abilities", []) if isinstance(current, Mapping) else []
    row = next((x for x in entries if isinstance(x, Mapping) and x.get("side") == side), None)
    value = row.get("ability") if isinstance(row, Mapping) else None
    return {"status": "known", "value": value} if isinstance(value, str) and value else {"status": "unknown"}


def _valid_switch(candidate: Mapping[str, Any]) -> bool:
    return isinstance(candidate.get("candidate_id"), str) and candidate.get("candidate_id", "").startswith("self-switch:") and candidate.get("action_kind") == "switch" and isinstance(candidate.get("target_pokemon_id"), str) and isinstance(candidate.get("target_slot_index"), int)


def _snapshot_adapter(snapshot: Any) -> Any:
    if isinstance(snapshot, Mapping):
        return _SerializedSnapshot(snapshot)
    return snapshot


class _SerializedSnapshot:
    def __init__(self, value: Mapping[str, Any]): self._value = deepcopy(dict(value))
    def to_dict(self) -> dict[str, Any]: return deepcopy(self._value)


def _tier_for(identifier: str, rows: Sequence[Mapping[str, Any]]) -> str | None:
    row = next((item for item in rows if item.get("action_candidate_id") == identifier), None)
    return row.get("cross_action_danger_tier") if isinstance(row, Mapping) else None


def _failure(reason: str) -> dict[str, Any]:
    return {"action_kind": None, "candidate_id": None, "selection_status": "no_selectable_action", "selection_reason": reason, "supportability": "insufficient_context", "move_candidate_id": None, "switch_candidate_id": None, "tied_candidate_ids": [], "danger_tier": None}
