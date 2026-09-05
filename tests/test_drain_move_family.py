from __future__ import annotations

from advisor.canonical_drain_move_family import resolve_canonical_drain_move
from llm.advisor_detached_drain_consequence import apply_detached_drain_consequence
from tests.test_detached_opponent_response_profile import _owner, _snapshot, _state


def _leaf(*, damage: int, pre: int, post: int, own: int = 20):
    return {"leaf_id":"hit", "hit_state":"hit", "consequences":{"own_final_hp":own,"target_final_hp":post,"damage":damage,"source_hit_context":{"target_routing":"target","target_pre_hp":pre,"target_post_hp":post,"actual_damage":damage}}, "provenance":{}}
def _inputs(*, item=None, ability=None):
    state=_state(); state["self_side"]["pokemon"][0].update(current_hp=20,max_hp=100,fainted=False,known_item=item,known_item_provenance={"event_kind":"current_item_observed","trust":"user_confirmed_observation","status":"known"} if item else {"event_kind":"current_item_observed","trust":"user_confirmed_observation","status":"known_absent"})
    state["opponent_side"]["pokemon"][0].update(known_item=None,known_item_provenance={"event_kind":"current_item_observed","trust":"user_confirmed_observation","status":"known_absent"})
    if ability is not None: state["opponent_side"]["pokemon"][0].update(current_ability=ability,current_ability_provenance={"event_kind":"current_ability_observed","trust":"user_confirmed_observation"})
    snap=_snapshot(state); return snap,_owner(state,"self"),_owner(state,"opponent")

def test_catalog_fractions_are_closed():
    assert resolve_canonical_drain_move(move={"move_id":"giga-drain","category":"special"})["effect"]["drain_denominator"] == 2
    assert resolve_canonical_drain_move(move={"move_id":"drain-punch","category":"physical"})["status"] == "resolved"
    assert resolve_canonical_drain_move(move={"move_id":"draining-kiss","category":"special"})["effect"]["drain_numerator"] == 3
    assert resolve_canonical_drain_move(move={"move_id":"tackle","category":"physical"})["status"] == "unsupported"

def test_half_up_overkill_cap_big_root_and_liquid_ooze():
    snap,a,t=_inputs(); move={"move_id":"giga-drain","category":"special"}
    row=apply_detached_drain_consequence(runtime_snapshot=snap,attacker=a,target=t,move_metadata=move,leaf=_leaf(damage=11,pre=11,post=0))
    assert row["leaf"]["consequences"]["drain"]["nominal_recovery"] == 6
    over=apply_detached_drain_consequence(runtime_snapshot=snap,attacker=a,target=t,move_metadata=move,leaf=_leaf(damage=20,pre=20,post=0))
    assert over["leaf"]["consequences"]["drain"]["actual_target_hp_loss"] == 20
    snap,a,t=_inputs(item="big-root",ability="liquid-ooze")
    ooze=apply_detached_drain_consequence(runtime_snapshot=snap,attacker=a,target=t,move_metadata=move,leaf=_leaf(damage=11,pre=11,post=0,own=100))
    drain=ooze["leaf"]["consequences"]["drain"]
    assert drain["big_root"]["would_be_recovery"] == 7 and drain["reversed_damage"] == 7 and drain["attacker_post_hp"] == 93

def test_three_quarters_and_zero_damage_do_not_fabricate_transfer():
    snap,a,t=_inputs(); move={"move_id":"draining-kiss","category":"special"}
    row=apply_detached_drain_consequence(runtime_snapshot=snap,attacker=a,target=t,move_metadata=move,leaf=_leaf(damage=10,pre=10,post=0))
    assert row["leaf"]["consequences"]["drain"]["nominal_recovery"] == 8
    zero=apply_detached_drain_consequence(runtime_snapshot=snap,attacker=a,target=t,move_metadata=move,leaf={**_leaf(damage=0,pre=10,post=10),"hit_state":"missed"})
    assert "drain" not in zero["leaf"]["consequences"]

def test_full_hp_caps_normal_heal_and_unknown_item_fails_closed():
    snap,a,t=_inputs(); move={"move_id":"giga-drain","category":"special"}
    full=apply_detached_drain_consequence(runtime_snapshot=snap,attacker=a,target=t,move_metadata=move,leaf=_leaf(damage=10,pre=10,post=0,own=100))
    assert full["leaf"]["consequences"]["drain"]["effective_heal"] == 0
    state=_state(); state["self_side"]["pokemon"][0].update(known_item=None, known_item_provenance={"event_kind":"current_item_observed","trust":"user_confirmed_observation","status":"unknown"})
    snap=_snapshot(state)
    assert apply_detached_drain_consequence(runtime_snapshot=snap,attacker=_owner(state,"self"),target=_owner(state,"opponent"),move_metadata=move,leaf=_leaf(damage=10,pre=10,post=0))["status"] == "incomplete"
