from copy import deepcopy
from llm.advisor_switch_entry_mechanics_derived_observation import (
    DERIVED_KINDS, MECHANICS_DERIVED_TRUST, SWITCH_ENTRY_MECHANICS_SOURCE,
)
from llm.advisor_champions_status_action_lifecycle_derived_observation import (
    DERIVED_KINDS as STATUS_ACTION_DERIVED_KINDS,
)
from llm.advisor_champions_confusion_action_lifecycle_derived_observation import (
    DERIVED_KINDS as CONFUSION_ACTION_DERIVED_KINDS,
    MECHANICS_DERIVED_TRUST as CONFUSION_ACTION_TRUST,
    CHAMPIONS_CONFUSION_ACTION_LIFECYCLE_SOURCE,
)

REPLAY_POLICY_VERSION = "v1"
_EFFECTS = {"exact_hp_transition_observed":"apply_exact_hp_transition","exact_hp_recovery_observed":"apply_exact_hp_recovery","current_type_observed":"set_current_type","current_condition_observed":"set_current_condition","current_healing_prevented_observed":"set_current_healing_prevented","pending_status_action_execution_observed":"set_pending_status_action_execution","pending_confusion_action_execution_observed":"record_pending_confusion_action_execution","doubles_active_topology_observed":"set_doubles_active_topology","selected_action_targeting_observed":"set_selected_action_targeting","current_weather_observed":"set_current_weather","current_ability_observed":"set_current_ability","current_item_observed":"set_current_item","current_terrain_observed":"set_current_terrain","current_side_conditions_observed":"set_current_side_conditions","current_battle_format_observed":"set_current_battle_format","current_level_observed":"set_current_level","current_final_combat_stat_observed":"set_current_final_combat_stat","current_opponent_response_set_observed":"set_current_opponent_response_set","current_opponent_switch_response_set_observed":"set_current_opponent_switch_response_set","current_opponent_switch_target_combat_observed":"set_current_opponent_switch_target_combat","substitute_state_observed":"set_current_substitute","used_move_observed":"record_known_move","condition_applied_observed":"set_condition","stat_stage_observed":"set_current_stat_stage","switch_hazards_observed":"set_switch_hazards","tailwind_side_condition_observed":"set_observed_tailwind","trick_room_field_observed":"set_observed_trick_room","magic_room_field_observed":"set_observed_magic_room","gravity_field_observed":"set_observed_gravity","current_locked_on_state_observed":"set_current_locked_on_state","same_turn_event_observed":"set_same_turn_event","first_end_of_turn_reached_observed":"mark_first_end_of_turn_reached","condition_removed_observed":"clear_condition","item_consumption_observed":"consume_item","item_removed_observed":"remove_item","weather_started_observed":"start_weather","weather_ended_observed":"end_weather","terrain_started_observed":"start_terrain","terrain_ended_observed":"end_terrain","side_condition_started_observed":"start_side_condition","side_condition_ended_observed":"end_side_condition","pokemon_switch_observed":"switch_active","pokemon_faint_observed":"mark_fainted"}
_EFFECTS["mat_block_active_entry_eligibility_observed"] = "set_mat_block_active_entry_eligibility"
_EFFECTS["fake_out_active_entry_eligibility_observed"] = "set_fake_out_active_entry_eligibility"
_EFFECTS["supreme_overlord_initial_active_observed"] = "initialize_supreme_overlord_active_entry"
_EFFECTS["berry_eaten_state_observed"] = "set_berry_eaten_state"
_EFFECTS["executed_move_observed"] = "record_executed_move"
_EFFECTS["previous_action_result_observed"] = "record_previous_action_result"
_EFFECTS.update({"current_aqua_ring_state_observed":"set_current_aqua_ring_state", "current_ingrain_state_observed":"set_current_ingrain_state", "current_leech_seed_state_observed":"set_current_leech_seed_state"})
_EFFECTS.update({"current_confusion_state_observed":"set_current_confusion_state", "champions_confusion_progression_observed":"record_champions_confusion_progression", "champions_status_progression_observed":"record_champions_status_progression"})
_EFFECTS.update({"taunt_restriction_applied_observed":"apply_taunt_restriction", "encore_restriction_applied_observed":"apply_encore_restriction", "disable_restriction_applied_observed":"apply_disable_restriction", "taunt_restricted_turn_completed_observed":"complete_restricted_active_turn", "encore_restricted_turn_completed_observed":"complete_encore_restricted_active_turn", "disable_restricted_turn_completed_observed":"complete_disable_restricted_active_turn"})
_EFFECTS.update({"switch_entry_hp_transition_derived":"apply_exact_hp_transition", "switch_entry_condition_applied_derived":"set_condition", "switch_entry_stat_stage_transition_derived":"set_current_stat_stage", "switch_entry_weather_transition_derived":"set_current_weather", "switch_entry_hazard_transition_derived":"set_switch_hazards", "switch_entry_faint_derived":"mark_fainted", "switch_entry_ability_transition_derived":"set_switch_entry_trace_ability"})
_EFFECTS.update({"champions_status_progression_derived":"advance_champions_status_progression", "champions_status_condition_cleared_derived":"clear_champions_status_condition"})
_EFFECTS.update({"champions_confusion_progression_derived":"advance_champions_confusion_progression", "champions_confusion_cleared_derived":"clear_champions_confusion"})

def build_replay_plan(base_state, ordered_observations, *, canonical_move_resolver=None):
    """Pure, non-mutating future-reducer planning only."""
    state=deepcopy(base_state) if isinstance(base_state,dict) else {}
    session=state.get("session_id")
    accepted=[]; evidence=[]; unsupported=[]; excluded=[]; conflicts=[]; seen={}; canonical_moves={}
    values=ordered_observations if isinstance(ordered_observations,list) else []
    for raw in values:
        if not isinstance(raw,dict): excluded.append({"reason":"invalid_observation"}); continue
        event=deepcopy(raw); oid=event.get("observation_id"); seq=event.get("observation_sequence")
        if event.get("session_id")!=session or not isinstance(oid,str) or not isinstance(seq,int) or isinstance(seq,bool) or seq<1: excluded.append({"observation_id":oid,"reason":"invalid_session_or_sequence"}); continue
        old=seen.get(oid)
        if old is not None:
            if old==event: excluded.append({"observation_id":oid,"reason":"duplicate"})
            else: conflicts.append({"observation_id":oid,"reason":"conflicting_duplicate"})
            continue
        seen[oid]=event; eligibility=event.get("reducer_eligibility")
        if eligibility=="candidate" and event.get("event_kind") in _EFFECTS:
            if event.get("event_kind") == "used_move_observed":
                canonical_move_id = _resolve_canonical_move(event.get("move_id"), canonical_move_resolver)
                if canonical_move_id is None:
                    unsupported.append(event)
                    continue
                canonical_moves[oid] = canonical_move_id
            accepted.append(event)
        elif eligibility=="evidence_only": evidence.append(event)
        else: unsupported.append(event)
    accepted.sort(key=lambda e:(e["observation_sequence"],e["observation_id"]))
    switches = {e.get("observation_id"): e for e in accepted if e.get("event_kind") == "pokemon_switch_observed"}
    dependency_verified = []
    for event in accepted:
        if event.get("event_kind") in DERIVED_KINDS:
            source = switches.get(event.get("payload", {}).get("source_switch_observation_id"))
            payload = event.get("payload", {})
            incoming = source.get("payload", {}) if isinstance(source, dict) else {}
            if (source is None or source.get("session_id") != event.get("session_id")
                    or source.get("turn_number") != event.get("turn_number")
                    or source.get("observation_sequence", 0) >= event.get("observation_sequence", 0)
                    or event.get("trust") != MECHANICS_DERIVED_TRUST or event.get("source") != SWITCH_ENTRY_MECHANICS_SOURCE
                    or event.get("scope") != "switch_entry"
                    or not _derived_owner_matches(event, source, incoming)):
                unsupported.append(event); conflicts.append({"observation_id": event.get("observation_id"), "reason": "invalid_switch_entry_derived_binding"}); continue
        dependency_verified.append(event)
    accepted = dependency_verified
    confusion_sources = {e.get("observation_id"): e for e in accepted if e.get("event_kind") == "pending_confusion_action_execution_observed"}
    confusion_verified=[]
    for event in accepted:
        if event.get("event_kind") in CONFUSION_ACTION_DERIVED_KINDS:
            source=confusion_sources.get(event.get("payload",{}).get("source_pending_observation_id"))
            if (source is None or source.get("session_id")!=event.get("session_id")
                    or source.get("turn_number")!=event.get("turn_number")
                    or source.get("observation_sequence",0)>=event.get("observation_sequence",0)
                    or event.get("trust")!=CONFUSION_ACTION_TRUST
                    or event.get("source")!=CHAMPIONS_CONFUSION_ACTION_LIFECYCLE_SOURCE
                    or event.get("scope")!="champions_confusion_action_lifecycle"):
                unsupported.append(event); conflicts.append({"observation_id":event.get("observation_id"),"reason":"invalid_confusion_action_derived_binding"}); continue
        confusion_verified.append(event)
    accepted=confusion_verified
    exact_executions = {}
    verified = []
    for event in accepted:
        if event.get("event_kind") == "executed_move_observed":
            key = (event.get("side"), event.get("slot_index"), event.get("pokemon_id"), event.get("payload", {}).get("source_action_id"), event.get("payload", {}).get("move_id"))
            exact_executions[key] = event
        elif event.get("event_kind") == "previous_action_result_observed":
            payload = event.get("payload", {})
            key = (event.get("side"), event.get("slot_index"), event.get("pokemon_id"), payload.get("previous_action_id"), payload.get("execution_move_id"))
            prior = exact_executions.get(key)
            if prior is None or prior.get("observation_sequence") >= event.get("observation_sequence"):
                unsupported.append(event)
                continue
        verified.append(event)
    accepted = verified
    steps=[{"observation_id":e["observation_id"],"observation_sequence":e["observation_sequence"],"event_kind":e.get("event_kind"),"turn_number":e.get("turn_number"),"source":e.get("source"),"trust":e.get("trust"),"scope":e.get("scope"),"eligibility":"candidate","planned_effect":_EFFECTS[e["event_kind"]], **({"side":e.get("side"),"slot_index":e.get("slot_index"),"pokemon_id":e.get("pokemon_id"),"canonical_move_id":canonical_moves.get(e["observation_id"])} if e.get("event_kind")=="used_move_observed" else {"side":e.get("side"),"slot_index":e.get("slot_index"),"pokemon_id":e.get("pokemon_id"),"hp_before":e.get("payload",{}).get("hp_before"),"hp_after":e.get("payload",{}).get("hp_after")} if e.get("event_kind") in {"exact_hp_transition_observed","exact_hp_recovery_observed"} else {"side":e.get("side"),"slot_index":e.get("slot_index"),"pokemon_id":e.get("pokemon_id"),"types":deepcopy(e.get("payload",{}).get("types"))} if e.get("event_kind")=="current_type_observed" else {"side":e.get("side"),"slot_index":e.get("slot_index"),"pokemon_id":e.get("pokemon_id"), **deepcopy(e.get("payload",{}))} if e.get("event_kind") in {"current_condition_observed","current_locked_on_state_observed","current_healing_prevented_observed","pending_confusion_action_execution_observed","champions_confusion_progression_derived","champions_confusion_cleared_derived","current_level_observed","current_final_combat_stat_observed","substitute_state_observed","same_turn_event_observed","current_aqua_ring_state_observed","current_ingrain_state_observed","current_leech_seed_state_observed"} else {"side":e.get("side"),"slot_index":e.get("slot_index"),"pokemon_id":e.get("pokemon_id"),"condition":e.get("payload",{}).get("condition")} if e.get("event_kind")=="condition_applied_observed" else {"side":e.get("side"),"slot_index":e.get("slot_index"),"pokemon_id":e.get("pokemon_id"),"stat":e.get("payload",{}).get("stat"),"stage":e.get("payload",{}).get("stage")} if e.get("event_kind")=="stat_stage_observed" else {"side":e.get("side"), **deepcopy(e.get("payload",{}))} if e.get("event_kind")=="switch_hazards_observed" else {"side":e.get("side"),"tailwind_status":e.get("payload",{}).get("status")} if e.get("event_kind")=="tailwind_side_condition_observed" else {"trick_room_status":e.get("payload",{}).get("status")} if e.get("event_kind")=="trick_room_field_observed" else {"magic_room_status":e.get("payload",{}).get("status")} if e.get("event_kind")=="magic_room_field_observed" else {"gravity_status":e.get("payload",{}).get("status")} if e.get("event_kind")=="gravity_field_observed" else {})} for e in accepted]
    for step, event in zip(steps, accepted):
        if event.get("event_kind") in STATUS_ACTION_DERIVED_KINDS:
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), **deepcopy(event.get("payload", {})))
        if event.get("event_kind") in DERIVED_KINDS:
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), **deepcopy(event.get("payload", {})))
            if event.get("event_kind") == "switch_entry_weather_transition_derived": step["weather"] = event.get("payload", {}).get("weather_after")
            if event.get("event_kind") == "switch_entry_hazard_transition_derived": step.update(**deepcopy(event.get("payload", {}).get("hazards_after", {})))
            if event.get("event_kind") == "switch_entry_stat_stage_transition_derived": step["stage"] = event.get("payload", {}).get("stage_after")
            if event.get("event_kind") == "switch_entry_ability_transition_derived": step["ability"] = event.get("payload", {}).get("ability_after")
        if event.get("event_kind") == "pokemon_switch_observed":
            step.update(side=event.get("side"), **deepcopy(event.get("payload", {})))
        elif event.get("event_kind").endswith("restriction_applied_observed") or event.get("event_kind").endswith("restricted_turn_completed_observed"):
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), **deepcopy(event.get("payload", {})))
        elif event.get("event_kind") == "executed_move_observed":
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), move_id=event.get("payload", {}).get("move_id"), source_action_id=event.get("payload", {}).get("source_action_id"))
        elif event.get("event_kind") == "previous_action_result_observed":
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), **deepcopy(event.get("payload", {})))
        elif event.get("event_kind") == "current_weather_observed":
            step["weather"] = deepcopy(event.get("payload", {}).get("weather"))
        elif event.get("event_kind") == "current_ability_observed":
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), ability=deepcopy(event.get("payload", {}).get("ability")))
        elif event.get("event_kind") == "current_opponent_response_set_observed":
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), move_ids=deepcopy(event.get("payload", {}).get("move_ids")), move_usability=deepcopy(event.get("payload", {}).get("move_usability")))
        elif event.get("event_kind") == "current_opponent_switch_response_set_observed":
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), permission=deepcopy(event.get("payload", {}).get("permission")), targets=deepcopy(event.get("payload", {}).get("targets")))
        elif event.get("event_kind") == "current_opponent_switch_target_combat_observed":
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), **deepcopy(event.get("payload", {})))
        elif event.get("event_kind") == "pending_status_action_execution_observed":
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), **deepcopy(event.get("payload", {})))
        elif event.get("event_kind") == "mat_block_active_entry_eligibility_observed":
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), **deepcopy(event.get("payload", {})))
        elif event.get("event_kind") == "fake_out_active_entry_eligibility_observed":
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), **deepcopy(event.get("payload", {})))
        elif event.get("event_kind") == "doubles_active_topology_observed":
            step.update(**deepcopy(event.get("payload", {})))
        elif event.get("event_kind") == "supreme_overlord_initial_active_observed":
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), **deepcopy(event.get("payload", {})))
        elif event.get("event_kind") == "berry_eaten_state_observed":
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), **deepcopy(event.get("payload", {})))
        elif event.get("event_kind") == "selected_action_targeting_observed":
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), **deepcopy(event.get("payload", {})))
        elif event.get("event_kind") == "current_confusion_state_observed":
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), confusion_state=event.get("payload", {}).get("state"))
        elif event.get("event_kind") in {"champions_confusion_progression_observed", "champions_status_progression_observed"}:
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), **deepcopy(event.get("payload", {})))
        elif event.get("event_kind") in {"current_item_observed", "current_terrain_observed", "current_side_conditions_observed", "current_battle_format_observed"}:
            step.update(**deepcopy(event.get("payload", {})))
    return {"status":"blocked_by_conflict" if conflicts else "planned","session_id":session,"accepted_events":accepted,"evidence_only_events":evidence,"unsupported_events":unsupported,"excluded_events":excluded,"conflicts":conflicts,"ordered_steps":steps,"limitations":["full_atomic_validation_before_mutation","no_state_mutation","no_q12_or_modifier_application"],"replay_policy_version":REPLAY_POLICY_VERSION}


def _derived_owner_matches(event, source, incoming):
    owner = (event.get("side"), event.get("slot_index"), event.get("pokemon_id"))
    incoming_owner = (source.get("side"), incoming.get("switch_in_slot_index"), incoming.get("switch_in_pokemon_id"))
    kind = event.get("event_kind")
    if kind == "switch_entry_hazard_transition_derived":
        return owner == (incoming_owner[0], None, None)
    if kind == "switch_entry_stat_stage_transition_derived" and event.get("payload", {}).get("mechanic") in {"intimidate", "intimidate_reversed"}:
        return owner[0] in {"self", "opponent"} and owner[0] != incoming_owner[0]
    return owner == incoming_owner


def _resolve_canonical_move(move_id, resolver):
    if not isinstance(move_id, str) or not move_id or resolver is None:
        return None
    try:
        resolved = resolver(move_id)
    except Exception:
        return None
    canonical = resolved.get("move_id") if isinstance(resolved, dict) else getattr(resolved, "move_id", None)
    return canonical if canonical == move_id and move_id == move_id.lower() and " " not in move_id and "_" not in move_id else None
