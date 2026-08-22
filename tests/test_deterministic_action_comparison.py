from copy import deepcopy
from llm.advisor_deterministic_action_comparison import compare_candidates
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_forced_switch_execution import _state,_owner

def _candidate(state, ident, source="f0", action="attack"):
 return {"schema_version":"deterministic-candidate-outcome-v1","candidate_id":ident,"action_type":action,"source_branch_fingerprint":source,"outcome_state":state,"outcome_branch_fingerprint":fingerprint_transition_preview_state(state),"completeness":"complete"}
def test_terminal_hp_unknown_and_purity():
 state,_=_state(); owner=_owner(state,"self"); alive=deepcopy(state); ko=deepcopy(state);ko["active"]["self"]["current_hp"]=0;ko["active"]["self"]["fainted"]=True
 a,b=_candidate(alive,"a"),_candidate(ko,"b"); before=deepcopy(a); result=compare_candidates(decision_owner=owner,candidate_a=a,candidate_b=b);assert result["preferred_candidate"]=="a" and result["reason"]=="avoids_self_ko" and a==before
 foe=deepcopy(state);foe["active"]["opponent"]["current_hp"]=0;foe["active"]["opponent"]["fainted"]=True;assert compare_candidates(decision_owner=owner,candidate_a=_candidate(foe,"a"),candidate_b=_candidate(alive,"b"))["reason"]=="causes_opponent_ko"
 hp=deepcopy(state);hp["active"]["self"]["current_hp"]=70;assert compare_candidates(decision_owner=owner,candidate_a=_candidate(alive,"a"),candidate_b=_candidate(hp,"b"))["reason"]=="safer_exact_self_hp"
 assert compare_candidates(decision_owner=owner,candidate_a=a,candidate_b=_candidate(alive,"x",source="other"))["status"]=="rejected"
