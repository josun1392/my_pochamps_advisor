from copy import deepcopy
from llm.advisor_deterministic_candidate_ranking import rank_candidates
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_forced_switch_execution import _state,_owner
def _c(s,i,action="attack",source="f") : return {"schema_version":"deterministic-candidate-outcome-v1","candidate_id":i,"action_type":action,"source_branch_fingerprint":source,"outcome_state":s,"outcome_branch_fingerprint":fingerprint_transition_preview_state(s),"completeness":"complete"}
def _ko(s,side):s=deepcopy(s);s["active"][side]["current_hp"]=0;s["active"][side]["fainted"]=True;return s
def test_frontier_ties_incomplete_and_permutation():
 s,_=_state();o=_owner(s,"self"); foe=_ko(s,"opponent"); selfko=_ko(s,"self"); rows=[_c(foe,"a"),_c(s,"b"),_c(selfko,"c","manual_switch")]
 r=rank_candidates(decision_owner=o,candidates=rows);assert r["status"]=="uniquely_preferred" and r["preferred_frontier"]==["a"]
 tied=rank_candidates(decision_owner=o,candidates=[_c(s,"a"),_c(deepcopy(s),"b"),_c(selfko,"c")]);assert tied["preferred_frontier"]==["a","b"]
 assert rank_candidates(decision_owner=o,candidates=[rows[2],rows[0],rows[1]])["preferred_frontier"]==["a"]
 assert rank_candidates(decision_owner=o,candidates=[rows[0],rows[0]])["status"]=="rejected"
