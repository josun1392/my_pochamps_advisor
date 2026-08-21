"""Bounded executable switch-first transition for detached Turn Engine branches."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_hypothetical_direct_mechanics import evaluate_hypothetical_direct_mechanics
from llm.advisor_incoming_active_materialization import materialize_incoming_active_branch
from llm.advisor_switch_entry_effects import evaluate_switch_entry_effects
from llm.advisor_switch_transition import project_authorized_switch_transition
from llm.advisor_transition_preview import fingerprint_transition_preview_state, project_exact_direct_action_on_branch
from llm.advisor_branch_hazard_context import project_side_hazards, remove_absorbed_toxic_spikes
from llm.advisor_branch_weather_context import apply_supported_switch_entry_weather, project_field_weather
from llm.advisor_toxic_spikes_condition_adapter import apply_toxic_spikes_condition


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
    if not _incoming_matches_authorized_switch(switch, incoming_authority):
        return _result("rejected", "switch_candidate_incoming_authority_mismatch")
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
    entry = evaluate_switch_entry_effects(hazards=hazards, target=target, intimidate_authority=post.get("switch_entry_intimidate_authority"), download_authority=post.get("switch_entry_download_authority"), field_state_context=post.get("side_shared_authority", {}).get("field_state_context") if isinstance(post.get("side_shared_authority"), Mapping) else None)
    if entry.get("entry_effects_supportability") != "complete" or entry.get("status") != "complete":
        return _result("incomplete", "switch_entry_authority")
    state = deepcopy(post_switch)
    projected = project_side_hazards(branch_state=state, source_fingerprint=post_switch_fp, frozen_hazards=hazards)
    if projected.get("status") != "resolved": return projected
    state = projected["next_state"]
    active = state["active"]["self"]
    damage = entry["damage"]
    active["current_hp"] = max(0, active["current_hp"] - damage)
    active["fainted"] = active["current_hp"] == 0
    _sync_self_hp(state, active["current_hp"], active["max_hp"])
    entry_fp = fingerprint_transition_preview_state(state)
    trace = [*materialized["materialization_trace"], {"sequence": 2, "event": "switch_entry_hazards", "execution_status": "executed", "damage": damage, "post_hp": active["current_hp"], "hazards": {"stealth_rock": hazards.get("stealth_rock"), "spikes_layers": hazards.get("spikes_layers"), "sticky_web": entry.get("sticky_web_result")}}]
    if active["fainted"]:
        return {"status": "unsupported", "reason": "replacement_required_after_entry_hazard_ko", "source_branch_fingerprint": source_branch_fingerprint, "post_switch_branch_fingerprint": post_switch_fp, "post_entry_branch_fingerprint": entry_fp, "next_state": state, "consequence_trace": trace, "boundary": {"phase": "pre_end_of_turn"}}
    intimidate = entry.get("intimidate_result")
    if not isinstance(intimidate, Mapping) or intimidate.get("status") != "complete":
        return _result("incomplete", "intimidate_entry_authority")
    if intimidate.get("outcome") in {"attack_stage_lowered", "attack_stage_minimum"}:
        if not _materialized_self_has_ability(state, "intimidate") or not _sync_opponent_attack_stage(state, intimidate.get("opponent_identity"), intimidate.get("attack_stage_before"), intimidate.get("attack_stage_after")):
            return _result("incomplete", "opponent_exact_attack_stage_authority")
        trace.append({"sequence": 3, "event": "switch_entry_intimidate", "execution_status": "executed", "source_owner": {key: active[key] for key in ("session_id", "side", "slot_index", "pokemon_id")}, "target_owner": deepcopy(dict(intimidate["opponent_identity"])), "attack_stage_before": intimidate["attack_stage_before"], "attack_stage_after": intimidate["attack_stage_after"], "provenance": "switch-entry-intimidate-authority-v1"})
    elif intimidate.get("outcome") == "attack_drop_prevented":
        trace.append({"sequence": 3, "event": "switch_entry_intimidate", "execution_status": "prevented", "provenance": "switch-entry-intimidate-authority-v1"})
    elif intimidate.get("outcome") != "not_applicable":
        return _result("unsupported", "intimidate_entry_outcome")
    download = entry.get("download_result")
    if not isinstance(download, Mapping) or download.get("status") != "complete":
        return _result("incomplete", "download_entry_authority")
    if download.get("outcome") in {"attack_stage_raised", "attack_stage_maximum", "special-attack_stage_raised", "special-attack_stage_maximum"}:
        if not _materialized_self_has_ability(state, "download") or not _sync_self_offensive_stage(state, download.get("boosted_stat"), download.get("stage_before"), download.get("stage_after")):
            return _result("incomplete", "incoming_exact_download_stage_authority")
        trace.append({"sequence": len(trace) + 1, "event": "switch_entry_download", "execution_status": "executed", "source_owner": {key: active[key] for key in ("session_id", "side", "slot_index", "pokemon_id")}, "target_owner": deepcopy(dict(download["opponent_identity"])), "boosted_stat": download["boosted_stat"], "stage_before": download["stage_before"], "stage_after": download["stage_after"], "provenance": "switch-entry-download-authority-v1"})
    elif download.get("outcome") == "ability_suppressed":
        trace.append({"sequence": len(trace) + 1, "event": "switch_entry_download", "execution_status": "prevented", "provenance": "switch-entry-download-authority-v1"})
    elif download.get("outcome") != "not_applicable":
        return _result("unsupported", "download_entry_outcome")
    weather = entry.get("weather_result")
    if not isinstance(weather, Mapping) or weather.get("status") != "complete":
        return _result("incomplete", "weather_entry_authority")
    if weather.get("outcome") in {"weather_set", "weather_already_active"}:
        weather_after = weather.get("weather_after")
        ability = {"rain": "drizzle", "sun": "drought", "sandstorm": "sand-stream", "snow": "snow-warning"}.get(weather_after)
        if ability is None or not _materialized_self_has_ability(state, ability):
            return _result("unsupported", "weather_entry_outcome")
        field_state = post.get("side_shared_authority", {}).get("field_state_context") if isinstance(post.get("side_shared_authority"), Mapping) else None
        projected_weather = project_field_weather(branch_state=state, source_fingerprint=fingerprint_transition_preview_state(state), frozen_field_state=field_state)
        if projected_weather.get("status") != "resolved": return projected_weather
        state = projected_weather["next_state"]
        if weather.get("outcome") == "weather_set":
            changed_weather = apply_supported_switch_entry_weather(branch_state=state, source_fingerprint=projected_weather["resulting_branch_fingerprint"], weather_result=weather)
            if changed_weather.get("status") != "resolved": return changed_weather
            state = changed_weather["next_state"]
        trace.append({"sequence": len(trace) + 1, "event": f"switch_entry_{ability.replace('-', '_')}", "execution_status": "executed" if weather.get("outcome") == "weather_set" else "already_active", "source_owner": {key: active[key] for key in ("session_id", "side", "slot_index", "pokemon_id")}, "weather_before": weather["weather_before"], "weather_after": weather_after, "provenance": "canonical_switch_entry_weather"})
    elif weather.get("outcome") != "not_applicable":
        return _result("unsupported", "weather_entry_outcome")
    sticky = entry.get("sticky_web_result")
    if not isinstance(sticky, Mapping) or sticky.get("status") != "complete":
        return _result("incomplete", "sticky_web_entry_authority")
    if sticky.get("outcome") in {"speed_stage_lowered", "speed_stage_minimum"}:
        if not _sync_self_speed_stage(state, sticky.get("speed_stage_after")):
            return _result("incomplete", "incoming_exact_speed_stage_authority")
    toxic = entry.get("toxic_spikes_result")
    entry_fp = fingerprint_transition_preview_state(state)
    if not isinstance(toxic, Mapping) or toxic.get("status") != "complete": return _result("incomplete", "toxic_spikes_entry_authority")
    if toxic.get("outcome") == "absorbed":
        changed = remove_absorbed_toxic_spikes(branch_state=state, source_fingerprint=entry_fp, absorption=toxic)
    elif toxic.get("outcome") == "status_applied":
        changed = apply_toxic_spikes_condition(branch_state=state, branch_fingerprint=entry_fp, owner=state["active"]["self"], evaluator_result=toxic)
    elif toxic.get("outcome") in {"absent", "ungrounded", "status_immune", "already_statused", "prevented_by_heavy_duty_boots", "status_prevented"}:
        changed = {"status": "resolved", "next_state": state, "resulting_branch_fingerprint": entry_fp}
    else: return _result("unsupported", "toxic_spikes_entry_outcome")
    if changed.get("status") != "resolved": return changed
    state, entry_fp = changed["next_state"], changed["resulting_branch_fingerprint"]
    evaluated = evaluate_hypothetical_direct_mechanics(branch_state=state, source_snapshot_fingerprint=source_branch_fingerprint, action=opponent_action, expected_owner=state["active"]["opponent"], direct_evaluation_input=opponent_direct_evaluation_input)
    if evaluated.get("status") != "known" or evaluated.get("branch_state_fingerprint") != entry_fp:
        status = "unsupported" if evaluated.get("status") == "unsupported_mechanic" else "rejected" if evaluated.get("status") == "rejected" else "incomplete"
        return {"status": status, "reason": str(evaluated.get("reason") or "post_entry_direct_mechanics"), "post_entry_branch_fingerprint": entry_fp}
    candidate = {"slot_index": opponent_action["move"]["slot_index"], "move": opponent_action["move"]["move_id"], "accuracy_evidence": {"status": "always_hits"}, "mechanics_result": evaluated["mechanics_result"]}
    direct = project_exact_direct_action_on_branch(branch_state=state, source_snapshot_fingerprint=source_branch_fingerprint, action=opponent_action, candidate=candidate)
    if direct.get("status") != "resolved":
        return direct
    return {"status": "resolved", "source_snapshot_fingerprint": source_branch_fingerprint, "source_branch_fingerprint": source_branch_fingerprint, "post_switch_branch_fingerprint": post_switch_fp, "post_entry_branch_fingerprint": entry_fp, "resulting_branch_fingerprint": fingerprint_transition_preview_state(direct["next_state"]), "switch_transition": deepcopy(switch), "entry_effect_result": deepcopy(entry), "direct_evaluation": deepcopy(evaluated), "consequence_trace": trace + deepcopy(direct["consequence_trace"]), "next_state": deepcopy(direct["next_state"]), "boundary": {"phase": "pre_end_of_turn"}, "limitations": ["switch_first_only", "bounded_switch_entry_effects_only", "no_reducer_or_runtime_writeback"]}


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


def _sync_self_speed_stage(state: Mapping[str, Any], stage: Any) -> bool:
    if isinstance(stage, bool) or not isinstance(stage, int) or not -6 <= stage <= 6: return False
    current = state.get("current_state") if isinstance(state, Mapping) else None
    rows = current.get("stat_stage_context", {}).get("current_stages") if isinstance(current, Mapping) else None
    match = next((row for row in rows if isinstance(row, dict) and row.get("side") == "self" and row.get("stat") == "speed" and row.get("status") == "user_confirmed" and row.get("source") == "user_confirmed_current_stat_stage" and row.get("confidence") == "known"), None) if isinstance(rows, list) else None
    if match is None: return False
    match["stage"] = stage
    attacker = current.get("direct_mechanics_context", {}).get("attacker") if isinstance(current, Mapping) and isinstance(current.get("direct_mechanics_context"), Mapping) else None
    if isinstance(attacker, dict) and isinstance(attacker.get("boosts"), dict): attacker["boosts"]["speed"] = stage
    return True


def _materialized_self_has_ability(state: Mapping[str, Any], ability: str) -> bool:
    current = state.get("current_state") if isinstance(state, Mapping) else None
    rows = current.get("ability_context", {}).get("current_abilities") if isinstance(current, Mapping) else None
    return any(isinstance(row, Mapping) and row.get("side") == "self" and row.get("ability") == ability and row.get("status") == "user_confirmed" and row.get("source") == "user_confirmed_current_ability" for row in rows) if isinstance(rows, list) else False


def _sync_opponent_attack_stage(state: Mapping[str, Any], target: Any, before: Any, after: Any) -> bool:
    opponent = state.get("active", {}).get("opponent") if isinstance(state.get("active"), Mapping) else None
    if not isinstance(opponent, Mapping) or not isinstance(target, Mapping) or any(opponent.get(key) != target.get(key) for key in ("side", "slot_index", "pokemon_id")):
        return False
    if any(isinstance(value, bool) or not isinstance(value, int) or not -6 <= value <= 6 for value in (before, after)):
        return False
    current = state.get("current_state") if isinstance(state, Mapping) else None
    rows = current.get("stat_stage_context", {}).get("current_stages") if isinstance(current, Mapping) else None
    match = next((row for row in rows if isinstance(row, dict) and row.get("side") == "opponent" and row.get("stat") == "attack" and row.get("status") == "user_confirmed" and row.get("source") == "user_confirmed_current_stat_stage" and row.get("confidence") == "known"), None) if isinstance(rows, list) else None
    if match is None or match.get("stage") != before:
        return False
    match["stage"] = after
    return True


def _sync_self_offensive_stage(state: Mapping[str, Any], stat: Any, before: Any, after: Any) -> bool:
    if stat not in {"attack", "special-attack"} or any(isinstance(value, bool) or not isinstance(value, int) or not -6 <= value <= 6 for value in (before, after)):
        return False
    current = state.get("current_state") if isinstance(state, Mapping) else None
    rows = current.get("stat_stage_context", {}).get("current_stages") if isinstance(current, Mapping) else None
    match = next((row for row in rows if isinstance(row, dict) and row.get("side") == "self" and row.get("stat") == stat and row.get("status") == "user_confirmed" and row.get("source") == "user_confirmed_current_stat_stage" and row.get("confidence") == "known"), None) if isinstance(rows, list) else None
    if match is None or match.get("stage") != before:
        return False
    match["stage"] = after
    return True


def _incoming_matches_authorized_switch(switch: Mapping[str, Any], incoming_authority: Mapping[str, Any]) -> bool:
    """Keep the finalized candidate and materialized identity inseparable."""
    action = switch.get("self_action")
    owner = incoming_authority.get("owner") if isinstance(incoming_authority, Mapping) else None
    return (
        isinstance(action, Mapping)
        and isinstance(owner, Mapping)
        and owner.get("session_id") == action.get("session_id")
        and owner.get("side") == "self"
        and owner.get("slot_index") == action.get("target_slot_index")
        and owner.get("pokemon_id") == action.get("target_pokemon_id")
    )


def _result(status: str, reason: str) -> dict[str, Any]: return {"status": status, "reason": reason}
