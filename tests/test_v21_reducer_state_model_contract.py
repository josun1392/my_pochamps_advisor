from copy import deepcopy
from llm.advisor_reducer_state_model import STATE_MODEL_VERSION, validate_atomic_transition

def state(session="s"):
 return {"session_id":session,"state_version":STATE_MODEL_VERSION,"self_side":{"active_slot_index":0,"pokemon":{}},"opponent_side":{"active_slot_index":1,"pokemon":{}},"field":{"weather":"unknown","terrain":"unknown","field_effects":[]},"last_applied_observation_sequence":None,"limitations":["unknown_values_not_overwritten"]}
def plan(session="s",status="planned",steps=None,conflicts=None):
 return {"session_id":session,"status":status,"ordered_steps":[{"observation_id":"a","planned_effect":"set_condition"}] if steps is None else steps,"conflicts":conflicts or []}
def test_ready_mapping_is_detached_immutable_and_idempotent():
 base=state(); replay=plan(); before=deepcopy((base,replay)); result=validate_atomic_transition(base,replay,"s")
 assert result["status"]=="ready_for_atomic_transition" and result["planned_next_state_schema"][0]["target_state_field"]=="pokemon.condition"
 assert validate_atomic_transition(base,replay,"s")==result and (base,replay)==before
def test_session_version_and_conflict_plans_are_blocked_without_mutation():
 assert validate_atomic_transition(state(),plan("old"),"s")["status"]=="invalid_base_state"
 assert validate_atomic_transition(state(),plan(status="blocked_by_conflict",conflicts=[{"reason":"x"}]),"s")["status"]=="blocked_by_conflict"
 assert validate_atomic_transition({"session_id":"s"},plan(),"s")["status"]=="unsupported_state_version"
def test_evidence_only_q12_or_unknown_values_never_become_transition_targets():
 assert validate_atomic_transition(state(),plan(steps=[]),"s")["status"]=="no_reducer_steps"
