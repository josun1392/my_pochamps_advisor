from copy import deepcopy

from llm.advisor_detached_taunt_action_restriction import materialize_detached_taunt_application, materialize_taunt_execution_gate
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_runtime_d0_pure_status_action_execution_authority import freeze_runtime_d0_pure_status_action_execution_authority
from llm.advisor_runtime_d0_taunt_restriction_authority import freeze_runtime_d0_taunt_restriction_authority
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from tests.test_tail_whip_pure_status_action_execution import _inputs
from tests.test_detached_opponent_response_profile import _snapshot
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _taunt_inputs(order="own_first", category="status"):
    _, snapshot, d0, _, own, foe, _ = _inputs()
    bindings = {"session_id":d0["session_id"],"source_runtime_fingerprint":d0["source_runtime_fingerprint"],"source_branch_fingerprint":d0["strategy_preview_fingerprint"],"decision_owner":d0["decision_owner"]}
    taunt_meta = {"move_id":"taunt","category":"status","target":"selected-pokemon","accuracy":100,"power":None,"priority":0}
    own_action = {"action_id":"attack:taunt","action_type":"attack","identity":"taunt","move_metadata_authority":{"status":"resolved","candidate_id":"attack:taunt","move_id":"taunt","active_attacker":own,**bindings,"metadata":taunt_meta}}
    if category == "status":
        move_id, metadata = "tail-whip", {"move_id":"tail-whip","category":"status","target":"selected-pokemon","accuracy":100,"power":None,"priority":0}
    else:
        move_id, metadata = "tackle", {"move_id":"tackle","category":"physical","target":"selected-pokemon","accuracy":100,"power":40,"type":"normal","priority":0}
    opponent = {"status":"resolved","action_id":f"opponent_attack:{move_id}","action_type":"attack","move_id":move_id,"opponent_actor":foe,"target_owner":own,**bindings,"metadata_authority":{"status":"resolved","move_id":move_id,"metadata":metadata},"usability":{"status":"known_usable"},"selectability":"selectable"}
    order_auth = {"status":"resolved","schema_version":"runtime-d0-action-order-authority-v1","order":order,**bindings,"own_action_id":own_action["action_id"],"opponent_action_id":opponent["action_id"],"own_actor":own,"opponent_actor":foe}
    base = {**bindings,"actor":own,"target":foe,"action_id":own_action["action_id"],"move_id":"taunt"}
    known = lambda **extra: {"status":"resolved",**base,**extra}
    app = materialize_detached_taunt_application(strategy_d0=d0, action=own_action, actor=own, target=foe,
        accuracy_authority=known(outcome="hit"), target_ability_authority=known(ability="pressure"), target_side_ability_authority=known(ability="none"), reflection_authority=known(outcome="not_applicable"))
    pure = {}
    if category == "status":
        status_action={"action_id":opponent["action_id"],"action_type":"attack","identity":"tail-whip","metadata_authority":opponent["metadata_authority"]}
        accuracy={"status":"resolved",**bindings,"actor":foe,"target":own,"action_id":opponent["action_id"],"move_id":"tail-whip","outcome":"hit"}
        pure[opponent["action_id"]]=freeze_runtime_d0_pure_status_action_execution_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=status_action,actor=foe,target=own,status_accuracy_authority=accuracy)
    return snapshot,d0,own,foe,own_action,opponent,order_auth,app,pure


def test_faster_taunt_blocks_selected_status_with_no_hit_crit_roll_or_damage():
    snapshot,d0,_,_,own,opponent,order,app,pure=_taunt_inputs()
    pair=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=opponent,action_order_authority=order,taunt_application_authorities={own["action_id"]:app},pure_status_execution_authorities=pure)
    assert pair["status"] == "evaluable" and pair["terminal_probability_mass"] == {"numerator":1,"denominator":1}
    failed=pair["terminal_branches"][0]["second_action"]["leaf"]
    assert failed["consequences"]["execution_failure"] == "taunt_action_restriction"
    assert failed["hit_state"] == failed["critical_state"] == failed["damage_roll"] == "not_applicable"
    assert failed["consequences"]["damage"] == 0 and failed["consequences"]["contact"] == "not_applicable"
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"


def test_taunt_damaging_move_and_slower_timing_do_not_cancel_selected_action(monkeypatch):
    snapshot,d0,_,_,own,opponent,order,app,pure=_taunt_inputs(category="physical")
    leaf={"leaf_id":"tackle:hit","candidate_id":opponent["action_id"],"probability":{"numerator":1,"denominator":1},"hit_state":"hit","critical_state":"non_critical","damage_roll":{"damage":10},"consequences":{"damage":10,"own_final_hp":100,"target_final_hp":90,"target_ko":False,"self_fainted":False,"secondary":None,"contact":"not_applicable"},"provenance":{"attacker":d0["active_owners"]["opponent"],"target":d0["active_owners"]["self"],"move_id":"tackle"}}
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair._attack_ledger", lambda **_: {"status":"evaluable","terminal_leaves":(leaf,)})
    pair=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=opponent,action_order_authority=order,taunt_application_authorities={own["action_id"]:app},pure_status_execution_authorities=pure)
    assert pair["terminal_branches"][0]["second_action"]["leaf"]["consequences"]["damage"] == 10
    snapshot,d0,_,_,own,opponent,order,app,pure=_taunt_inputs(order="opponent_first")
    pair=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=opponent,action_order_authority=order,taunt_application_authorities={own["action_id"]:app},pure_status_execution_authorities=pure)
    assert pair["terminal_branches"][0]["first_action_leaf"]["consequences"]["pure_status_outcome"] == "status_action_applied"


def test_equal_speed_preserves_half_order_mass_and_only_taunt_first_blocks():
    snapshot,d0,_,_,own,opponent,order,app,pure=_taunt_inputs()
    order["order"]="unresolved_tie"; order["order_engine"]={"status":"speed_tie"}
    pair=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=opponent,action_order_authority=order,taunt_application_authorities={own["action_id"]:app},pure_status_execution_authorities=pure)
    assert pair["status"] == "evaluable" and pair["terminal_probability_mass"] == {"numerator":1,"denominator":1}
    by_order={branch["action_order"]:branch for branch in pair["terminal_branches"]}
    assert by_order["own_first"]["probability"] == by_order["opponent_first"]["probability"] == {"numerator":1,"denominator":2}
    assert by_order["own_first"]["second_action"]["leaf"]["consequences"]["execution_failure"] == "taunt_action_restriction"
    assert by_order["opponent_first"]["first_action_leaf"]["consequences"]["pure_status_outcome"] == "status_action_applied"


def test_oblivious_unknown_and_stale_current_restriction_fail_closed():
    snapshot,d0,own,foe,action,_,_,_,_=_taunt_inputs()
    bindings={"session_id":d0["session_id"],"source_runtime_fingerprint":d0["source_runtime_fingerprint"],"source_branch_fingerprint":d0["strategy_preview_fingerprint"],"decision_owner":d0["decision_owner"],"actor":own,"target":foe,"action_id":action["action_id"],"move_id":"taunt"}
    known=lambda **extra:{"status":"resolved",**bindings,**extra}
    immune=materialize_detached_taunt_application(strategy_d0=d0,action=action,actor=own,target=foe,accuracy_authority=known(outcome="hit"),target_ability_authority=known(ability="oblivious"),target_side_ability_authority=known(ability="none"),reflection_authority=known(outcome="not_applicable"))
    assert immune["outcome"] == "no_effect"
    unknown=materialize_detached_taunt_application(strategy_d0=d0,action=action,actor=own,target=foe,accuracy_authority=known(outcome="hit"),target_ability_authority={"status":"incomplete",**bindings},target_side_ability_authority=known(ability="none"),reflection_authority=known(outcome="not_applicable"))
    assert unknown["status"] == "incomplete"
    state=deepcopy(snapshot["state"]); state["current_taunt_restrictions"]={"opponent":{"owner":foe,"state":"active","remaining_target_turns":3,"provenance":{}}}
    refreshed=_snapshot(state); current_d0=freeze_runtime_strategy_d0(runtime_snapshot=refreshed,decision_owner=own)
    current=freeze_runtime_d0_taunt_restriction_authority(strategy_d0=current_d0,runtime_snapshot=refreshed,owner=current_d0["active_owners"]["opponent"])
    assert current["status"] == "resolved"
    gate=materialize_taunt_execution_gate(selected_action={"action_id":"x","metadata_authority":{"metadata":{"move_id":"tail-whip","category":"status"}}},actor=own,current_restriction=current)
    assert gate["status"] == "rejected" and gate["reason"] == "taunt_restriction_actor_binding_mismatch"
