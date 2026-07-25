from copy import deepcopy
from llm.advisor_replay_policy import build_replay_plan

def base(): return {"session_id":"s","active":{"self":"pikachu","opponent":"eevee"}}
def event(oid,seq,kind="condition_applied_observed",eligibility="candidate",**x):
 d={"observation_id":oid,"observation_sequence":seq,"session_id":"s","event_kind":kind,"scope":"pokemon","reducer_eligibility":eligibility};d.update(x);return d
def test_idempotent_ordered_planning_and_no_mutation():
 state=base(); values=[event("b",2),event("a",1,"ability_activation_observed","evidence_only")]; before=deepcopy((state,values))
 first=build_replay_plan(state,values); assert first==build_replay_plan(state,list(reversed(values)))
 assert [(s["observation_id"],s["planned_effect"]) for s in first["ordered_steps"]]==[("b","set_condition")]
 assert (state,values)==before
def test_duplicate_repeated_conflict_and_eligibility_partition():
 duplicate=event("a",1); conflict=event("a",1,"condition_removed_observed"); repeated=event("b",2)
 plan=build_replay_plan(base(),[duplicate,duplicate,conflict,repeated,event("c",3,"item_activation_observed","evidence_only"),event("d",4,"field_effect_started_observed","unsupported")])
 assert [e["observation_id"] for e in plan["accepted_events"]]==["a","b"]
 assert plan["excluded_events"][0]["reason"]=="duplicate" and plan["conflicts"][0]["reason"]=="conflicting_duplicate"
 assert len(plan["evidence_only_events"])==len(plan["unsupported_events"])==1 and plan["status"]=="blocked_by_conflict"
def test_stale_invalid_and_session_boundary_are_excluded_without_state_change():
 plan=build_replay_plan(base(),[event("old",1,session_id="old"),event("bad",0)])
 assert len(plan["accepted_events"])==0 and len(plan["excluded_events"])==2
