from copy import deepcopy
from llm.advisor_detached_next_turn_ordinary_attack_execution import execute_detached_next_turn_ordinary_attack
from llm.advisor_detached_next_turn_held_item_effect_applicability import materialize_detached_next_turn_held_item_effect_applicability
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

def test_pair_local_kernel_uses_authenticated_current_hp_and_keeps_root_execution_unchanged():
    state,fp,_intents,self_execution=_chain("self")
    first=execute_detached_next_turn_ordinary_attack(execution_authority=self_execution)
    leaf=first["action_ledger"]["terminal_leaves"][0]
    overlay=materialize_detached_next_turn_pair_local_predictive_mechanics(next_decision_state=state,next_decision_fingerprint=fp,predictive_mechanics=self_execution["predictive_mechanics"],first_action_execution=self_execution,first_action_ledger=first,first_leaf_id=leaf["leaf_id"])
    assert overlay["status"]=="resolved"
    _state,_fp,_intents,opponent_execution=_chain("opponent")
    pair_result=execute_detached_next_turn_ordinary_attack(execution_authority=opponent_execution,pair_local_predictive_mechanics=overlay)
    root_result=execute_detached_next_turn_ordinary_attack(execution_authority=opponent_execution)
    assert pair_result["action_ledger"]["terminal_probability_mass"]=={"numerator":1,"denominator":1}
    assert pair_result["pair_local_predictive_mechanics_authority"]==overlay
    assert root_result==execute_detached_next_turn_ordinary_attack(execution_authority=opponent_execution)

def test_pair_local_overlay_rejects_bare_item_absence_and_tampering():
    state,fp,_intents,execution=_chain("self"); result=execute_detached_next_turn_ordinary_attack(execution_authority=execution); leaf=result["action_ledger"]["terminal_leaves"][0]
    forged=deepcopy(result); forged["action_ledger"]["terminal_leaves"][0]["consequences"]["target_item_after"]={"status":"known_absent","value":None}
    assert materialize_detached_next_turn_pair_local_predictive_mechanics(next_decision_state=state,next_decision_fingerprint=fp,predictive_mechanics=execution["predictive_mechanics"],first_action_execution=execution,first_action_ledger=forged,first_leaf_id=leaf["leaf_id"])["status"]=="rejected"
