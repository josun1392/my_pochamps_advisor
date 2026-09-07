from llm.advisor_champions_paralysis_application import freeze_champions_paralysis_application as freeze,materialize_champions_paralysis_application as materialize
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_reducer_state_model import state_fingerprint
from tests.test_detached_opponent_response_profile import _state,_complete_state,_owner,_snapshot

def inputs(move="thunder-wave",outcome="hit",**changes):
 state=_complete_state(_state())
 for k,v in changes.items():
  raw=state["opponent_side"]["pokemon"][0] if k.startswith("target_") else state["self_side"]["pokemon"][0];raw[k.removeprefix("target_")]=v
  if k.endswith("_condition"):raw["condition_provenance"]["condition"]=v
 snapshot=_snapshot(state);d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=_owner(state,"self"));actor,target=_owner(state,"self"),_owner(state,"opponent");action={"action_id":f"attack:{move}","action_type":"attack","identity":move};hit={"status":"resolved","session_id":d0["session_id"],"source_runtime_fingerprint":d0["source_runtime_fingerprint"],"source_branch_fingerprint":d0["strategy_preview_fingerprint"],"actor":actor,"target":target,"action_id":action["action_id"],"move_id":move,"outcome":outcome,**({"damage_resolved":True} if move=="nuzzle" and outcome=="hit" else {})};return snapshot,d0,actor,target,action,hit

def test_thunder_wave_accuracy_and_boundaries():
 snapshot,d0,a,t,action,hit=inputs();authority=freeze(strategy_d0=d0,runtime_snapshot=snapshot,actor=a,target=t,action=action,move_success_authority=hit);assert authority["accuracy"]==90 and materialize(authority=authority,runtime_snapshot=snapshot)["paralysis_applied"]
 for outcome,expected in (("missed","move_missed"),("blocked_by_protection","blocked_by_protection")):
  s,d,a,t,x,h=inputs(outcome=outcome);assert freeze(strategy_d0=d,runtime_snapshot=s,actor=a,target=t,action=x,move_success_authority=h)["prevention"]==expected
 for change,expected in (({"target_current_type":["electric"]},"blocked_by_electric_type"),({"target_current_ability":"limber"},"blocked_by_limber"),({"target_condition":"burn"},"target_already_major_statused")):
  s,d,a,t,x,h=inputs(**change);assert freeze(strategy_d0=d,runtime_snapshot=s,actor=a,target=t,action=x,move_success_authority=h)["prevention"]==expected

def test_nuzzle_is_post_hit_contact_damage_secondary_only():
 s,d,a,t,x,h=inputs("nuzzle");authority=freeze(strategy_d0=d,runtime_snapshot=s,actor=a,target=t,action=x,move_success_authority=h);assert authority["accuracy"]==100 and authority["base_power"]==20 and authority["contact"] and materialize(authority=authority,runtime_snapshot=s)["paralysis_applied"]
 h.pop("damage_resolved");assert freeze(strategy_d0=d,runtime_snapshot=s,actor=a,target=t,action=x,move_success_authority=h)["status"]=="rejected"
 s,d,a,t,x,h=inputs("nuzzle",target_current_type=["electric"]);assert materialize(authority=freeze(strategy_d0=d,runtime_snapshot=s,actor=a,target=t,action=x,move_success_authority=h),runtime_snapshot=s)["outcome"]=="blocked_by_electric_type"
