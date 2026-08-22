from copy import deepcopy
from llm.advisor_candidate_outcome_materialization import materialize_candidates
from llm.advisor_deterministic_candidate_ranking import rank_candidates
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_forced_switch_execution import _state,_owner
def test_materialize_supplied_attack_siblings_and_rank():
 state,_=_state();owner=_owner(state,"self");fp=fingerprint_transition_preview_state(state)
 base={"schema_version":"deterministic-action-candidate-v1","decision_owner":owner,"source_branch_fingerprint":fp,"action_type":"attack"}
 a={**base,"candidate_id":"a","action_authority":{"user":owner,"target_owner":_owner(state,"opponent"),"damage_amount":20}}
 b={**base,"candidate_id":"b","action_authority":{"user":owner,"target_owner":_owner(state,"opponent"),"damage_amount":200}}
 result=materialize_candidates(decision_state=state,decision_owner=owner,candidates=[a,b]); assert state["active"]["opponent"]["current_hp"]==100
 outcomes=[x["outcome"] for x in result["outcomes"]]; assert rank_candidates(decision_owner=owner,candidates=outcomes)["preferred_frontier"]==["b"]
 assert materialize_candidates(decision_state=state,decision_owner=owner,candidates=[{**base,"candidate_id":"x","action_authority":None}])["outcomes"][0]["status"]=="incomplete"
