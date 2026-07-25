from copy import deepcopy

STATE_MODEL_VERSION="battle-state-v1"
_TARGETS={"set_condition":"pokemon.condition","clear_condition":"pokemon.condition","consume_item":"pokemon.known_item","remove_item":"pokemon.known_item","start_weather":"field.weather","end_weather":"field.weather","start_terrain":"field.terrain","end_terrain":"field.terrain","start_side_condition":"side.side_conditions","end_side_condition":"side.side_conditions","switch_active":"side.active_slot_index","mark_fainted":"pokemon.fainted"}

def validate_atomic_transition(base_state,replay_plan,expected_session_id):
    base=deepcopy(base_state) if isinstance(base_state,dict) else {}
    plan=deepcopy(replay_plan) if isinstance(replay_plan,dict) else {}
    if base.get("state_version")!=STATE_MODEL_VERSION:return _result("unsupported_state_version",base,plan)
    if base.get("session_id")!=expected_session_id or plan.get("session_id")!=expected_session_id:return _result("invalid_base_state",base,plan)
    if plan.get("status")!="planned":return _result("blocked_by_conflict" if plan.get("conflicts") else "invalid_replay_plan",base,plan)
    steps=plan.get("ordered_steps",[])
    if not steps:return _result("no_reducer_steps",base,plan)
    targets=[]
    for step in steps:
        effect=step.get("planned_effect"); target=_TARGETS.get(effect)
        if target is None:return _result("invalid_replay_plan",base,plan)
        targets.append({"observation_id":step.get("observation_id"),"target_state_field":target,"planned_effect":effect})
    return {"status":"ready_for_atomic_transition","base_state":base,"planned_next_state_schema":targets,"accepted_step_ids":[x.get("observation_id") for x in steps],"rejected_step_ids":[],"conflicts":[],"limitations":["dry_run_only","no_state_mutation","unknown_values_not_overwritten"]}
def _result(status,base,plan):return {"status":status,"base_state":base,"planned_next_state_schema":[],"accepted_step_ids":[],"rejected_step_ids":[x.get("observation_id") for x in plan.get("ordered_steps",[]) if isinstance(x,dict)],"conflicts":deepcopy(plan.get("conflicts",[])),"limitations":["dry_run_only","no_state_mutation"]}
