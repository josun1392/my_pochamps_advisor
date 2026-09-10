from copy import deepcopy
from llm.advisor_candidate_outcome_materialization import materialize_candidates
from llm.advisor_deterministic_candidate_ranking import rank_candidates
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_forced_switch_execution import _state,_owner
from tests.test_executable_switch_transition import _branch,_incoming,_snapshot
def test_materialize_supplied_attack_siblings_and_rank():
 state,_=_state();owner=_owner(state,"self");fp=fingerprint_transition_preview_state(state)
 base={"schema_version":"deterministic-action-candidate-v1","decision_owner":owner,"source_branch_fingerprint":fp,"action_type":"attack"}
 a={**base,"candidate_id":"a","action_authority":{"user":owner,"target_owner":_owner(state,"opponent"),"damage_amount":20}}
 b={**base,"candidate_id":"b","action_authority":{"user":owner,"target_owner":_owner(state,"opponent"),"damage_amount":200}}
 result=materialize_candidates(decision_state=state,decision_owner=owner,candidates=[a,b]); assert state["active"]["opponent"]["current_hp"]==100
 outcomes=[x["outcome"] for x in result["outcomes"]]; assert rank_candidates(decision_owner=owner,candidates=outcomes)["preferred_frontier"]==["b"]
 assert materialize_candidates(decision_state=state,decision_owner=owner,candidates=[{**base,"candidate_id":"x","action_authority":None}])["outcomes"][0]["status"]=="incomplete"


def test_manual_switch_candidate_requires_and_consumes_bound_post_entry_authority():
 state=_branch(); owner=_owner(state,"self"); fp=fingerprint_transition_preview_state(state); incoming=_incoming(); post=_snapshot(rock="present",spikes=1)["current_state"]
 entry={"status":"resolved","schema_version":"runtime-d0-manual-switch-entry-authority-v1","session_id":"switch-exec","source_branch_fingerprint":fp,"incoming_owner":deepcopy(incoming["owner"]),"entry_authority":{"hazards":post["switch_hazard_context"],"target_roster_mechanics":post["self_roster_mechanics_context"]["entries"][0]}}
 candidate={"schema_version":"deterministic-action-candidate-v1","candidate_id":"manual_switch:incoming","action_type":"manual_switch","decision_owner":owner,"source_branch_fingerprint":fp,"action_authority":{**incoming,"manual_switch_entry_authority":entry}}
 complete=materialize_candidates(decision_state=state,decision_owner=owner,candidates=[candidate])["outcomes"][0]
 assert complete["status"]=="complete"
 assert complete["outcome"]["outcome_state"]["active"]["self"]["current_hp"]==43
 assert state["active"]["self"]["pokemon_id"]=="outgoing"
 assert materialize_candidates(decision_state=state,decision_owner=owner,candidates=[{**candidate,"action_authority":incoming}])["outcomes"][0]=={"status":"incomplete","candidate_id":"manual_switch:incoming","reason":"switch_entry_authority_required"}
 foreign=deepcopy(candidate); foreign["action_authority"]["manual_switch_entry_authority"]["source_branch_fingerprint"]="foreign"
 assert materialize_candidates(decision_state=state,decision_owner=owner,candidates=[foreign])["outcomes"][0]["status"]=="incomplete"
 ko=deepcopy(candidate); ko["action_authority"]["hp_authority"]["current_hp"]=1; ko["action_authority"]["current_state"]["current_hp_context"]["current_hp"][0]["current_hp"]=1
 ko["action_authority"]["manual_switch_entry_authority"]["entry_authority"]["target_roster_mechanics"]["hp_authority"]["current_hp"]=1
 terminal=materialize_candidates(decision_state=state,decision_owner=owner,candidates=[ko])["outcomes"][0]
 assert terminal["status"]=="incomplete" and terminal["reason"]=="replacement_required_after_entry_hazard_ko"
