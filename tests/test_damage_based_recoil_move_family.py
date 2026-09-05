from __future__ import annotations
from advisor.canonical_damage_based_recoil_move_family import resolve_canonical_damage_based_recoil_move
from llm.advisor_detached_damage_based_recoil_consequence import apply_detached_damage_based_recoil
from tests.test_detached_opponent_response_profile import _owner, _snapshot, _state

def _leaf(damage, pre, post, own=20): return {"hit_state":"hit","consequences":{"own_final_hp":own,"source_hit_context":{"target_routing":"target","target_pre_hp":pre,"target_post_hp":post,"actual_damage":damage}},"provenance":{}}
def _inputs(ability="pressure"):
    state=_state(); state["self_side"]["pokemon"][0].update(current_ability=ability,current_ability_provenance={"event_kind":"current_ability_observed","trust":"user_confirmed_observation"})
    return _snapshot(state),_owner(state,"self")

def test_catalog_is_closed_and_has_exact_fractions():
    assert resolve_canonical_damage_based_recoil_move(move={"move_id":"wild-charge","category":"physical"})["effect"]["recoil_denominator"]==4
    assert resolve_canonical_damage_based_recoil_move(move={"move_id":"brave-bird","category":"physical"})["effect"]["recoil_denominator"]==3
    assert resolve_canonical_damage_based_recoil_move(move={"move_id":"head-smash","category":"physical"})["effect"]["recoil_denominator"]==2
    assert resolve_canonical_damage_based_recoil_move(move={"move_id":"tackle","category":"physical"})["status"]=="unsupported"

def test_actual_damage_rounding_minimum_and_ko():
    snap,actor=_inputs(); move={"move_id":"wild-charge","category":"physical"}
    result=apply_detached_damage_based_recoil(runtime_snapshot=snap,attacker=actor,move_metadata=move,leaf=_leaf(20,20,0,own=4))
    recoil=result["leaf"]["consequences"]["damage_based_recoil"]
    assert recoil["actual_target_hp_loss"]==20 and recoil["recoil_damage"]==5 and recoil["attacker_post_hp"]==0
    minimum=apply_detached_damage_based_recoil(runtime_snapshot=snap,attacker=actor,move_metadata=move,leaf=_leaf(1,1,0))
    assert minimum["leaf"]["consequences"]["damage_based_recoil"]["recoil_damage"]==1

def test_rock_head_and_magic_guard_prevent_only_family_recoil():
    for ability in ("rock-head","magic-guard"):
        snap,actor=_inputs(ability); result=apply_detached_damage_based_recoil(runtime_snapshot=snap,attacker=actor,move_metadata={"move_id":"head-smash","category":"physical"},leaf=_leaf(10,10,0))
        recoil=result["leaf"]["consequences"]["damage_based_recoil"]
        assert recoil["recoil_damage"]==0 and recoil["attacker_post_hp"]==20

def test_miss_and_substitute_routing_have_no_recoil():
    snap,actor=_inputs(); move={"move_id":"wild-charge","category":"physical"}
    miss=apply_detached_damage_based_recoil(runtime_snapshot=snap,attacker=actor,move_metadata=move,leaf={**_leaf(0,10,10),"hit_state":"missed"})
    sub=apply_detached_damage_based_recoil(runtime_snapshot=snap,attacker=actor,move_metadata=move,leaf={**_leaf(0,10,10),"hit_state":"hit","consequences":{"own_final_hp":20,"source_hit_context":{"target_routing":"substitute","target_pre_hp":10,"target_post_hp":10,"actual_damage":0}}})
    assert "damage_based_recoil" not in miss["leaf"]["consequences"] and "damage_based_recoil" not in sub["leaf"]["consequences"]
