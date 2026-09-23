from copy import deepcopy

from llm.advisor_population_bomb_attempt_observation_runtime_admission import admit_observed_population_bomb_result
from tests.test_observed_fixed_two_hit_ordered_graph_reconciliation import _runtime_state
from tests.test_observed_fixed_two_hit_ordered_graph_runtime import _FastManager
from tests.test_observed_population_bomb_attempt_graph_reconciliation import _artifact,_retain,_execution


def _state_for(r,hp=100):
    state=_runtime_state();state["session_id"]=r["session_id"]
    state["self_side"]["pokemon"][0]["pokemon_id"]=r["actor"]["pokemon_id"]
    state["opponent_side"]["pokemon"][0]["pokemon_id"]=r["target"]["pokemon_id"]
    state["opponent_side"]["pokemon"][0]["current_hp"]=hp
    state["opponent_side"]["pokemon"][0]["max_hp"]=max(100,hp)
    state["opponent_side"]["pokemon"][0]["fainted"]=False
    return state


def _attempt_rows(outcomes):
    hp=100;landed=0;rows=[]
    for i,outcome in enumerate(outcomes,1):
        if outcome=="miss":
            rows.append({"attempt_index":i,"attempt_outcome":"miss"});continue
        landed+=1;post=hp-5
        rows.append({"attempt_index":i,"attempt_outcome":"hit","hit_index":landed,"hp_before":hp,"hp_after":post,
                     "critical_state":None,"related_contact_observation_ids":()})
        hp=post
    return tuple(rows)


def test_population_bomb_production_admission_atomic_idempotent_and_conflict_rejecting():
    r=_retain(_artifact(stop=3));execution=_execution(r);manager=_FastManager(_state_for(r),[execution])
    attempts=_attempt_rows(("hit","hit","miss"))
    first=admit_observed_population_bomb_result(runtime_session_manager=manager,captured_session_id=r["session_id"],
        retained_prediction=r,turn_number=1,source_execution_observation=execution,action_outcome="landed",
        landed_hit_count=2,attempt_count=3,terminal_reason="first_miss_terminates_remaining_attempts",ordered_attempts=attempts)
    assert first["status"]=="resolved",first
    assert first["runtime_snapshot"]["state"]["opponent_side"]["pokemon"][0]["current_hp"]==90
    duplicate=admit_observed_population_bomb_result(runtime_session_manager=manager,captured_session_id=r["session_id"],
        retained_prediction=r,turn_number=1,source_execution_observation=execution,action_outcome="landed",
        landed_hit_count=2,attempt_count=3,terminal_reason="first_miss_terminates_remaining_attempts",ordered_attempts=attempts)
    assert duplicate["status"]=="resolved" and duplicate["idempotent"] is True
    changed=list(deepcopy(attempts));changed[-1]={"attempt_index":3,"attempt_outcome":"hit","hit_index":3,"hp_before":90,"hp_after":85,
                                                 "critical_state":None,"related_contact_observation_ids":()}
    assert admit_observed_population_bomb_result(runtime_session_manager=manager,captured_session_id=r["session_id"],
        retained_prediction=r,turn_number=1,source_execution_observation=execution,action_outcome="landed",
        landed_hit_count=3,attempt_count=3,terminal_reason="first_miss_terminates_remaining_attempts",ordered_attempts=changed)["status"]=="rejected"


def test_population_bomb_stale_session_turn_action_newer_execution_and_target_reject():
    r=_retain(_artifact(stop=1));execution=_execution(r);state=_state_for(r);manager=_FastManager(state,[execution])
    common=dict(runtime_session_manager=manager,retained_prediction=r,source_execution_observation=execution,
                action_outcome="miss",landed_hit_count=0,attempt_count=1,
                terminal_reason="first_miss_terminates_remaining_attempts",
                ordered_attempts=({"attempt_index":1,"attempt_outcome":"miss"},))
    assert admit_observed_population_bomb_result(captured_session_id="other",turn_number=1,**common)["status"]=="rejected"
    assert admit_observed_population_bomb_result(captured_session_id=r["session_id"],turn_number=2,**common)["status"]=="rejected"
    wrong=deepcopy(execution);wrong["payload"]["source_action_id"]="other"
    assert admit_observed_population_bomb_result(runtime_session_manager=manager,captured_session_id=r["session_id"],retained_prediction=r,
        turn_number=1,source_execution_observation=wrong,action_outcome="miss",landed_hit_count=0,attempt_count=1,
        terminal_reason="first_miss_terminates_remaining_attempts",ordered_attempts=({"attempt_index":1,"attempt_outcome":"miss"},))["status"]=="rejected"
    newer=deepcopy(execution);newer["observation_id"]="exec-newer";newer["observation_sequence"]=2
    manager=_FastManager(state,[execution,newer])
    result=admit_observed_population_bomb_result(runtime_session_manager=manager,captured_session_id=r["session_id"],retained_prediction=r,
        turn_number=1,source_execution_observation=execution,action_outcome="miss",landed_hit_count=0,attempt_count=1,
        terminal_reason="first_miss_terminates_remaining_attempts",ordered_attempts=({"attempt_index":1,"attempt_outcome":"miss"},))
    assert result["status"]=="rejected" and result["reason"]=="population_bomb_execution_observation_stale"
    state=_state_for(r);state["opponent_side"]["pokemon"][0]["pokemon_id"]="replacement";manager=_FastManager(state,[execution])
    result=admit_observed_population_bomb_result(runtime_session_manager=manager,captured_session_id=r["session_id"],retained_prediction=r,
        turn_number=1,source_execution_observation=execution,action_outcome="miss",landed_hit_count=0,attempt_count=1,
        terminal_reason="first_miss_terminates_remaining_attempts",ordered_attempts=({"attempt_index":1,"attempt_outcome":"miss"},))
    assert result["status"]=="rejected" and result["reason"]=="population_bomb_actor_or_target_stale"


def test_population_bomb_runtime_rejects_attempt_after_miss_and_changed_hp():
    r=_retain(_artifact(stop=2));execution=_execution(r);manager=_FastManager(_state_for(r),[execution])
    bad=(
        {"attempt_index":1,"attempt_outcome":"miss"},
        {"attempt_index":2,"attempt_outcome":"hit","hit_index":1,"hp_before":100,"hp_after":95,"critical_state":None,"related_contact_observation_ids":()},
    )
    assert admit_observed_population_bomb_result(runtime_session_manager=manager,captured_session_id=r["session_id"],retained_prediction=r,
        turn_number=1,source_execution_observation=execution,action_outcome="landed",landed_hit_count=1,attempt_count=2,
        terminal_reason="first_miss_terminates_remaining_attempts",ordered_attempts=bad)["status"]=="rejected"
