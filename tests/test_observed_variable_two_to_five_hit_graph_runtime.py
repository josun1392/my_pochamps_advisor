from copy import deepcopy

from llm.advisor_variable_two_to_five_hit_observation_runtime_admission import admit_observed_variable_two_to_five_hit_result
from tests.test_observed_fixed_two_hit_ordered_graph_reconciliation import _runtime_state
from tests.test_observed_fixed_two_hit_ordered_graph_runtime import _FastManager
from tests.test_observed_variable_two_to_five_hit_graph_reconciliation import _retained,_execution


def _state_for(retained, hp=100):
    state=_runtime_state();state["session_id"]=retained["session_id"]
    state["self_side"]["pokemon"][0]["pokemon_id"]=retained["actor"]["pokemon_id"]
    state["opponent_side"]["pokemon"][0]["pokemon_id"]=retained["target"]["pokemon_id"]
    state["opponent_side"]["pokemon"][0]["current_hp"]=hp
    state["opponent_side"]["pokemon"][0]["max_hp"]=max(100,hp)
    state["opponent_side"]["pokemon"][0]["fainted"]=False
    return state


def test_variable_production_admission_is_atomic_idempotent_and_conflict_rejecting():
    retained=_retained(root_counts=(2,))
    execution=_execution(retained);state=_state_for(retained)
    manager=_FastManager(state,[execution])
    hits=(
        {"hit_index":1,"hp_before":100,"hp_after":90,"critical_state":None,"related_contact_observation_ids":()},
        {"hit_index":2,"hp_before":90,"hp_after":80,"critical_state":None,"related_contact_observation_ids":()},
    )
    first=admit_observed_variable_two_to_five_hit_result(
        runtime_session_manager=manager,captured_session_id=retained["session_id"],retained_prediction=retained,
        turn_number=1,source_execution_observation=execution,action_outcome="landed",landed_hit_count=2,
        terminal_reason="selected_hit_count_reached",ordered_hits=hits)
    assert first["status"]=="resolved",first
    assert first["runtime_snapshot"]["state"]["opponent_side"]["pokemon"][0]["current_hp"]==80
    assert first["reconciliation"]["compatible_source_paths"][0]["selected_hit_count"]==2
    duplicate=admit_observed_variable_two_to_five_hit_result(
        runtime_session_manager=manager,captured_session_id=retained["session_id"],retained_prediction=retained,
        turn_number=1,source_execution_observation=execution,action_outcome="landed",landed_hit_count=2,
        terminal_reason="selected_hit_count_reached",ordered_hits=hits)
    assert duplicate["status"]=="resolved" and duplicate["idempotent"] is True
    changed=list(deepcopy(hits));changed[-1]["hp_after"]=85
    assert admit_observed_variable_two_to_five_hit_result(
        runtime_session_manager=manager,captured_session_id=retained["session_id"],retained_prediction=retained,
        turn_number=1,source_execution_observation=execution,action_outcome="landed",landed_hit_count=2,
        terminal_reason="selected_hit_count_reached",ordered_hits=changed)["status"]=="rejected"


def test_variable_production_stale_session_turn_action_and_newer_execution_fail_closed():
    retained=_retained(accuracy=50);execution=_execution(retained);state=_state_for(retained)
    manager=_FastManager(state,[execution])
    common=dict(runtime_session_manager=manager,retained_prediction=retained,source_execution_observation=execution,
                action_outcome="miss",landed_hit_count=0,terminal_reason="action_miss",ordered_hits=())
    assert admit_observed_variable_two_to_five_hit_result(captured_session_id="other",turn_number=1,**common)["status"]=="rejected"
    assert admit_observed_variable_two_to_five_hit_result(captured_session_id=retained["session_id"],turn_number=2,**common)["status"]=="rejected"
    wrong=deepcopy(execution);wrong["payload"]["source_action_id"]="attack:other"
    assert admit_observed_variable_two_to_five_hit_result(runtime_session_manager=manager,captured_session_id=retained["session_id"],
        retained_prediction=retained,turn_number=1,source_execution_observation=wrong,action_outcome="miss",
        landed_hit_count=0,terminal_reason="action_miss",ordered_hits=())["status"]=="rejected"
    newer=deepcopy(execution);newer["observation_id"]="exec-newer";newer["observation_sequence"]=2
    manager=_FastManager(state,[execution,newer])
    result=admit_observed_variable_two_to_five_hit_result(runtime_session_manager=manager,captured_session_id=retained["session_id"],
        retained_prediction=retained,turn_number=1,source_execution_observation=execution,action_outcome="miss",
        landed_hit_count=0,terminal_reason="action_miss",ordered_hits=())
    assert result["status"]=="rejected" and result["reason"]=="variable_two_to_five_execution_observation_stale"


def test_variable_production_stale_target_and_miss_contract_fail_closed():
    retained=_retained(accuracy=50);execution=_execution(retained);state=_state_for(retained)
    state["opponent_side"]["pokemon"][0]["pokemon_id"]="replacement"
    manager=_FastManager(state,[execution])
    result=admit_observed_variable_two_to_five_hit_result(
        runtime_session_manager=manager,captured_session_id=retained["session_id"],retained_prediction=retained,
        turn_number=1,source_execution_observation=execution,action_outcome="miss",landed_hit_count=0,
        terminal_reason="action_miss",ordered_hits=())
    assert result["status"]=="rejected" and result["reason"]=="variable_two_to_five_actor_or_target_stale"
