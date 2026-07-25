from copy import deepcopy

REPLAY_POLICY_VERSION = "v1"
_EFFECTS = {"exact_hp_transition_observed":"apply_exact_hp_transition","condition_applied_observed":"set_condition","condition_removed_observed":"clear_condition","item_consumption_observed":"consume_item","item_removed_observed":"remove_item","weather_started_observed":"start_weather","weather_ended_observed":"end_weather","terrain_started_observed":"start_terrain","terrain_ended_observed":"end_terrain","side_condition_started_observed":"start_side_condition","side_condition_ended_observed":"end_side_condition","pokemon_switch_observed":"switch_active","pokemon_faint_observed":"mark_fainted"}

def build_replay_plan(base_state, ordered_observations):
    """Pure, non-mutating future-reducer planning only."""
    state=deepcopy(base_state) if isinstance(base_state,dict) else {}
    session=state.get("session_id")
    accepted=[]; evidence=[]; unsupported=[]; excluded=[]; conflicts=[]; seen={}
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
        if eligibility=="candidate" and event.get("event_kind") in _EFFECTS: accepted.append(event)
        elif eligibility=="evidence_only": evidence.append(event)
        else: unsupported.append(event)
    accepted.sort(key=lambda e:(e["observation_sequence"],e["observation_id"]))
    steps=[{"observation_id":e["observation_id"],"observation_sequence":e["observation_sequence"],"event_kind":e.get("event_kind"),"scope":e.get("scope"),"eligibility":"candidate","planned_effect":_EFFECTS[e["event_kind"]]} for e in accepted]
    return {"status":"blocked_by_conflict" if conflicts else "planned","session_id":session,"accepted_events":accepted,"evidence_only_events":evidence,"unsupported_events":unsupported,"excluded_events":excluded,"conflicts":conflicts,"ordered_steps":steps,"limitations":["full_atomic_validation_before_mutation","no_state_mutation","no_q12_or_modifier_application"],"replay_policy_version":REPLAY_POLICY_VERSION}
