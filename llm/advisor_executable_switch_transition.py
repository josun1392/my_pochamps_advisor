"""Bounded executable switch-first transition for detached Turn Engine branches."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_hypothetical_direct_mechanics import evaluate_hypothetical_direct_mechanics
from llm.advisor_incoming_active_materialization import materialize_incoming_active_branch
from llm.advisor_switch_entry_effects import evaluate_switch_entry_effects
from llm.advisor_switch_transition import project_authorized_switch_transition
from llm.advisor_transition_preview import fingerprint_transition_preview_state, project_exact_direct_action_on_branch


class _FrozenSnapshot:
    def __init__(self, value: Mapping[str, Any]): self._value = deepcopy(dict(value))
    def to_dict(self) -> dict[str, Any]: return deepcopy(self._value)


def execute_manual_switch_then_direct(
    *, source_branch: Mapping[str, Any], source_branch_fingerprint: str, switch_snapshot: Mapping[str, Any],
    switch_candidate: Mapping[str, Any], incoming_authority: Mapping[str, Any], opponent_action: Mapping[str, Any],
    opponent_direct_evaluation_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute only canonical self-switch-first, SR/Spikes, then one direct move."""
    if fingerprint_transition_preview_state(source_branch) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_source_branch_fingerprint")
    # The candidate is finalized by the existing manual-permission/blocker
    # pipeline; this executor never grants permission itself.
    if switch_candidate.get("selectable") is not True or switch_candidate.get("reason_code") != "switch_available":
        return _result("incomplete", "switch_legality_unknown_or_blocked")
    switch = project_authorized_switch_transition(turn_snapshot=_FrozenSnapshot(switch_snapshot), switch_candidate=switch_candidate, switch_authorized=True, opponent_action={"role": "opponent_action", "acting_side": "opponent", "target_side": "self", "move_id": opponent_action.get("move", {}).get("move_id"), "move_metadata": {"target": "selected-pokemon"}})
    if switch.get("supportability") != "complete" or switch.get("order_result") != "self_switch_first":
        return _result("unsupported", str(switch.get("unsupported_reason") or switch.get("reason") or "switch_order_unsupported"))
    materialized = materialize_incoming_active_branch(source_branch=source_branch, source_branch_fingerprint=source_branch_fingerprint, incoming_authority=incoming_authority)
    if materialized.get("status") != "resolved":
        return materialized
    post_switch = materialized["next_state"]
    post_switch_fp = materialized["resulting_branch_fingerprint"]
    post = switch.get("post_switch_snapshot")
    target = post.get("target_roster_mechanics") if isinstance(post, Mapping) else None
    hazards = post.get("switch_hazard_context") if isinstance(post, Mapping) else None
    if not isinstance(target, Mapping) or not isinstance(hazards, Mapping):
        return _result("incomplete", "switch_entry_authority")
    if hazards.get("toxic_spikes_layers") != 0 or hazards.get("sticky_web") != "absent":
        return _result("unsupported", "unsupported_material_switch_entry_effect")
    entry = evaluate_switch_entry_effects(hazards=hazards, target=target, field_state_context=post.get("side_shared_authority", {}).get("field_state_context") if isinstance(post.get("side_shared_authority"), Mapping) else None)
    if entry.get("entry_effects_supportability") != "complete" or entry.get("status") != "complete":
        return _result("incomplete", "switch_entry_authority")
    state = deepcopy(post_switch)
    active = state["active"]["self"]
    damage = entry["damage"]
    active["current_hp"] = max(0, active["current_hp"] - damage)
    active["fainted"] = active["current_hp"] == 0
    _sync_self_hp(state, active["current_hp"], active["max_hp"])
    entry_fp = fingerprint_transition_preview_state(state)
    trace = [*materialized["materialization_trace"], {"sequence": 2, "event": "switch_entry_hazards", "execution_status": "executed", "damage": damage, "post_hp": active["current_hp"], "hazards": {"stealth_rock": hazards.get("stealth_rock"), "spikes_layers": hazards.get("spikes_layers")}}]
    if active["fainted"]:
        return {"status": "unsupported", "reason": "replacement_required_after_entry_hazard_ko", "source_branch_fingerprint": source_branch_fingerprint, "post_switch_branch_fingerprint": post_switch_fp, "post_entry_branch_fingerprint": entry_fp, "next_state": state, "consequence_trace": trace, "boundary": {"phase": "pre_end_of_turn"}}
    evaluated = evaluate_hypothetical_direct_mechanics(branch_state=state, source_snapshot_fingerprint=source_branch_fingerprint, action=opponent_action, expected_owner=state["active"]["opponent"], direct_evaluation_input=opponent_direct_evaluation_input)
    if evaluated.get("status") != "known" or evaluated.get("branch_state_fingerprint") != entry_fp:
        status = "unsupported" if evaluated.get("status") == "unsupported_mechanic" else "rejected" if evaluated.get("status") == "rejected" else "incomplete"
        return {"status": status, "reason": str(evaluated.get("reason") or "post_entry_direct_mechanics"), "post_entry_branch_fingerprint": entry_fp}
    candidate = {"slot_index": opponent_action["move"]["slot_index"], "move": opponent_action["move"]["move_id"], "accuracy_evidence": {"status": "always_hits"}, "mechanics_result": evaluated["mechanics_result"]}
    direct = project_exact_direct_action_on_branch(branch_state=state, source_snapshot_fingerprint=source_branch_fingerprint, action=opponent_action, candidate=candidate)
    if direct.get("status") != "resolved":
        return direct
    return {"status": "resolved", "source_branch_fingerprint": source_branch_fingerprint, "post_switch_branch_fingerprint": post_switch_fp, "post_entry_branch_fingerprint": entry_fp, "resulting_branch_fingerprint": fingerprint_transition_preview_state(direct["next_state"]), "switch_transition": deepcopy(switch), "entry_effect_result": deepcopy(entry), "direct_evaluation": deepcopy(evaluated), "consequence_trace": trace + deepcopy(direct["consequence_trace"]), "next_state": deepcopy(direct["next_state"]), "boundary": {"phase": "pre_end_of_turn"}, "limitations": ["switch_first_only", "stealth_rock_and_spikes_only", "no_reducer_or_runtime_writeback"]}


def _sync_self_hp(state: Mapping[str, Any], hp: int, maximum: int) -> None:
    current = state.get("current_state") if isinstance(state, Mapping) else None
    rows = current.get("current_hp_context", {}).get("current_hp") if isinstance(current, Mapping) else None
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("side") == "self": row["current_hp"], row["maximum_hp"] = hp, maximum
    direct = current.get("direct_mechanics_context") if isinstance(current, Mapping) else None
    attacker = direct.get("attacker") if isinstance(direct, Mapping) else None
    if isinstance(attacker, dict):
        attacker["current_hp"], attacker["max_hp"] = hp, maximum


def _result(status: str, reason: str) -> dict[str, Any]: return {"status": status, "reason": reason}
