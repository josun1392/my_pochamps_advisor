from copy import deepcopy

REPLAY_POLICY_VERSION = "v1"
_EFFECTS = {"exact_hp_transition_observed":"apply_exact_hp_transition","exact_hp_recovery_observed":"apply_exact_hp_recovery","current_type_observed":"set_current_type","current_condition_observed":"set_current_condition","current_weather_observed":"set_current_weather","current_ability_observed":"set_current_ability","current_item_observed":"set_current_item","current_terrain_observed":"set_current_terrain","current_side_conditions_observed":"set_current_side_conditions","current_battle_format_observed":"set_current_battle_format","current_level_observed":"set_current_level","current_final_combat_stat_observed":"set_current_final_combat_stat","substitute_state_observed":"set_current_substitute","used_move_observed":"record_known_move","condition_applied_observed":"set_condition","stat_stage_observed":"set_current_stat_stage","switch_hazards_observed":"set_switch_hazards","tailwind_side_condition_observed":"set_observed_tailwind","trick_room_field_observed":"set_observed_trick_room","same_turn_event_observed":"set_same_turn_event","first_end_of_turn_reached_observed":"mark_first_end_of_turn_reached","condition_removed_observed":"clear_condition","item_consumption_observed":"consume_item","item_removed_observed":"remove_item","weather_started_observed":"start_weather","weather_ended_observed":"end_weather","terrain_started_observed":"start_terrain","terrain_ended_observed":"end_terrain","side_condition_started_observed":"start_side_condition","side_condition_ended_observed":"end_side_condition","pokemon_switch_observed":"switch_active","pokemon_faint_observed":"mark_fainted"}

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
    steps=[{"observation_id":e["observation_id"],"observation_sequence":e["observation_sequence"],"event_kind":e.get("event_kind"),"turn_number":e.get("turn_number"),"source":e.get("source"),"trust":e.get("trust"),"scope":e.get("scope"),"eligibility":"candidate","planned_effect":_EFFECTS[e["event_kind"]], **({"side":e.get("side"),"slot_index":e.get("slot_index"),"pokemon_id":e.get("pokemon_id"),"canonical_move_id":canonical_moves.get(e["observation_id"])} if e.get("event_kind")=="used_move_observed" else {"side":e.get("side"),"slot_index":e.get("slot_index"),"pokemon_id":e.get("pokemon_id"),"hp_before":e.get("payload",{}).get("hp_before"),"hp_after":e.get("payload",{}).get("hp_after")} if e.get("event_kind") in {"exact_hp_transition_observed","exact_hp_recovery_observed"} else {"side":e.get("side"),"slot_index":e.get("slot_index"),"pokemon_id":e.get("pokemon_id"),"types":deepcopy(e.get("payload",{}).get("types"))} if e.get("event_kind")=="current_type_observed" else {"side":e.get("side"),"slot_index":e.get("slot_index"),"pokemon_id":e.get("pokemon_id"), **deepcopy(e.get("payload",{}))} if e.get("event_kind") in {"current_condition_observed","current_level_observed","current_final_combat_stat_observed","substitute_state_observed","same_turn_event_observed"} else {"side":e.get("side"),"slot_index":e.get("slot_index"),"pokemon_id":e.get("pokemon_id"),"condition":e.get("payload",{}).get("condition")} if e.get("event_kind")=="condition_applied_observed" else {"side":e.get("side"),"slot_index":e.get("slot_index"),"pokemon_id":e.get("pokemon_id"),"stat":e.get("payload",{}).get("stat"),"stage":e.get("payload",{}).get("stage")} if e.get("event_kind")=="stat_stage_observed" else {"side":e.get("side"), **deepcopy(e.get("payload",{}))} if e.get("event_kind")=="switch_hazards_observed" else {"side":e.get("side"),"tailwind_status":e.get("payload",{}).get("status")} if e.get("event_kind")=="tailwind_side_condition_observed" else {"trick_room_status":e.get("payload",{}).get("status")} if e.get("event_kind")=="trick_room_field_observed" else {})} for e in accepted]
    for step, event in zip(steps, accepted):
        if event.get("event_kind") == "current_weather_observed":
            step["weather"] = deepcopy(event.get("payload", {}).get("weather"))
        elif event.get("event_kind") == "current_ability_observed":
            step.update(side=event.get("side"), slot_index=event.get("slot_index"), pokemon_id=event.get("pokemon_id"), ability=deepcopy(event.get("payload", {}).get("ability")))
        elif event.get("event_kind") in {"current_item_observed", "current_terrain_observed", "current_side_conditions_observed", "current_battle_format_observed"}:
            step.update(**deepcopy(event.get("payload", {})))
    return {"status":"blocked_by_conflict" if conflicts else "planned","session_id":session,"accepted_events":accepted,"evidence_only_events":evidence,"unsupported_events":unsupported,"excluded_events":excluded,"conflicts":conflicts,"ordered_steps":steps,"limitations":["full_atomic_validation_before_mutation","no_state_mutation","no_q12_or_modifier_application"],"replay_policy_version":REPLAY_POLICY_VERSION}


def _resolve_canonical_move(move_id, resolver):
    if not isinstance(move_id, str) or not move_id or resolver is None:
        return None
    try:
        resolved = resolver(move_id)
    except Exception:
        return None
    canonical = resolved.get("move_id") if isinstance(resolved, dict) else getattr(resolved, "move_id", None)
    return canonical if canonical == move_id and move_id == move_id.lower() and " " not in move_id and "_" not in move_id else None
