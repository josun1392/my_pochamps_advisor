from advisor.canonical_final_gambit_self_hp_damage_family import resolve_canonical_final_gambit_self_hp_damage_move
from llm.advisor_detached_final_gambit_self_hp_damage import materialize_detached_final_gambit_self_hp_damage
from copy import deepcopy
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from tests.test_detached_opponent_response_profile import _fixed_damage_inputs

MOVE={"move_id":"final-gambit","type":"fighting","category":"special","accuracy":100,"contact":False}
def hp(value):return {"current_hp":value,"max_hp":100,"fainted":value==0}
def test_catalog_and_self_sacrifice_arithmetic():
 assert resolve_canonical_final_gambit_self_hp_damage_move(move=MOVE)["effect"]["family"]=="self_current_hp_damage"
 assert resolve_canonical_final_gambit_self_hp_damage_move(move={"move_id":"tackle"})["status"]=="unsupported"
 row=materialize_detached_final_gambit_self_hp_damage(move=MOVE,attacker_hp=hp(80),target_hp=hp(30),hit_state="hit",applicability="applicable")
 assert (row["raw_damage"],row["actual_target_hp_loss"],row["target_post_hp"],row["attacker_post_hp"],row["attacker_fainted"])==(80,30,0,0,True)
 assert materialize_detached_final_gambit_self_hp_damage(move=MOVE,attacker_hp=hp(37),target_hp=hp(100),hit_state="hit",applicability="immune")["attacker_fainted"] is False
def test_one_hp_and_no_roll_or_crit():
 row=materialize_detached_final_gambit_self_hp_damage(move=MOVE,attacker_hp=hp(1),target_hp=hp(100),hit_state="hit",applicability="applicable")
 assert row["raw_damage"]==1 and row["target_post_hp"]==99 and row["critical_state"]==row["damage_roll"]=="not_applicable"
def test_pair_self_faint_overkill_and_ledger_forgery_rejection():
 _,snapshot,d0,_,opponent,order=_fixed_damage_inputs(own_first=True,own_hp=80,opponent_hp=30); own={"action_id":"attack:final-gambit","action_type":"attack","identity":"final-gambit","move_metadata_authority":{"status":"resolved","candidate_id":"attack:final-gambit","active_attacker":d0["decision_owner"],"move_id":"final-gambit","metadata":MOVE,"session_id":d0["session_id"],"source_runtime_fingerprint":d0["source_runtime_fingerprint"],"source_branch_fingerprint":d0["strategy_preview_fingerprint"],"decision_owner":d0["decision_owner"]}}; pair=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=opponent,action_order_authority={**order,"own_action_id":"attack:final-gambit"})
 leaf=pair["terminal_branches"][0]["first_action_leaf"]; assert leaf["consequences"]["damage"]==80 and leaf["consequences"]["target_final_hp"]==leaf["consequences"]["own_final_hp"]==0 and normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"]=="evaluable"
 forged=deepcopy(pair); forged["terminal_branches"][0]["first_action_leaf"]["consequences"]["final_gambit_self_hp_damage"]["attacker_post_hp"]=1; assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"]=="rejected"
