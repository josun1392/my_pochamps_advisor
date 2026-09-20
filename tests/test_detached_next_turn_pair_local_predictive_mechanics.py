from copy import deepcopy
from llm.advisor_detached_next_turn_ordinary_attack_execution import execute_detached_next_turn_ordinary_attack
from llm.advisor_detached_next_turn_pair_local_predictive_mechanics import materialize_detached_next_turn_pair_local_predictive_mechanics, validate_detached_next_turn_pair_local_predictive_mechanics
from tests.test_detached_next_turn_ordinary_attack_execution import _chain

def test_exact_ordinary_leaf_projects_authenticated_pair_local_hp():
    state, fp, _intents, execution = _chain("self")
    result=execute_detached_next_turn_ordinary_attack(execution_authority=execution)
    leaf=result["action_ledger"]["terminal_leaves"][0]
    overlay=materialize_detached_next_turn_pair_local_predictive_mechanics(next_decision_state=state,next_decision_fingerprint=fp,predictive_mechanics=execution["predictive_mechanics"],first_action_execution=execution,first_action_ledger=result,first_leaf_id=leaf["leaf_id"])
    assert overlay["status"]=="resolved"
    assert overlay["sides"]["self"]["current_hp"]["current_hp"]==leaf["consequences"]["own_final_hp"]
    assert overlay["sides"]["opponent"]["current_hp"]["current_hp"]==leaf["consequences"]["target_final_hp"]
    assert validate_detached_next_turn_pair_local_predictive_mechanics(authority=overlay,next_decision_state=state,next_decision_fingerprint=fp) is None

def test_forged_leaf_and_overlay_hp_reject():
    state,fp,_intents,execution=_chain("self"); result=execute_detached_next_turn_ordinary_attack(execution_authority=execution); leaf=result["action_ledger"]["terminal_leaves"][0]
    assert materialize_detached_next_turn_pair_local_predictive_mechanics(next_decision_state=state,next_decision_fingerprint=fp,predictive_mechanics=execution["predictive_mechanics"],first_action_execution=execution,first_action_ledger=result,first_leaf_id="forged")["status"]=="rejected"
    overlay=materialize_detached_next_turn_pair_local_predictive_mechanics(next_decision_state=state,next_decision_fingerprint=fp,predictive_mechanics=execution["predictive_mechanics"],first_action_execution=execution,first_action_ledger=result,first_leaf_id=leaf["leaf_id"]); forged=deepcopy(overlay);forged["sides"]["self"]["current_hp"]["current_hp"]+=1
    assert validate_detached_next_turn_pair_local_predictive_mechanics(authority=forged,next_decision_state=state,next_decision_fingerprint=fp) is not None
