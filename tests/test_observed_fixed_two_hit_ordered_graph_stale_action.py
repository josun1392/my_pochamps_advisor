from copy import deepcopy

from llm.advisor_fixed_two_hit_observation_runtime_admission import admit_observed_fixed_two_hit_result
from tests.test_observed_fixed_two_hit_ordered_graph_reconciliation import _artifact,_retain,_runtime_state,_execution
from tests.test_observed_fixed_two_hit_ordered_graph_runtime import _FastManager

def test_later_execution_observation_retires_same_turn_retained_opportunity():
    _predictive_state,artifact,_,_,_=_artifact(target_hp=1);ret=_retain(artifact)
    state=_runtime_state();state["session_id"]=ret["session_id"]
    state["self_side"]["pokemon"][0]["pokemon_id"]=ret["actor"]["pokemon_id"]
    state["opponent_side"]["pokemon"][0]["pokemon_id"]=ret["target"]["pokemon_id"]
    state["opponent_side"]["pokemon"][0]["current_hp"]=artifact["terminal_leaves"][0]["ordered_hits"][0]["pre_hp"]
    first=_execution(ret,observation_id="exec-1",seq=1)
    later=deepcopy(first);later["observation_id"]="exec-2";later["observation_sequence"]=2
    later["payload"]={"move_id":"tackle","source_action_id":"later-action"}
    manager=_FastManager(state,[first,later])
    leaf=artifact["terminal_leaves"][0]
    hits=tuple({"hit_index":h["hit_index"],"hp_before":h["pre_hp"],"hp_after":h["post_hp"],"critical_state":None,"related_contact_observation_ids":()} for h in leaf["ordered_hits"])
    result=admit_observed_fixed_two_hit_result(runtime_session_manager=manager,captured_session_id=state["session_id"],retained_prediction=ret,turn_number=1,source_execution_observation=first,action_outcome="landed",landed_hit_count=len(hits),terminal_reason=leaf["consequences"]["terminal_reason"],ordered_hits=hits)
    assert result["status"]=="rejected"
    assert result["reason"]=="fixed_two_hit_execution_observation_stale"
