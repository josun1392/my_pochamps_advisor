from copy import deepcopy

from advisor.canonical_target_was_damaged_power_family import resolve_canonical_target_was_damaged_power_move
from llm.advisor_detached_target_was_damaged_power_authority import materialize_detached_target_was_damaged_power_authority
from llm.advisor_immediate_move_vs_move_action_pair import _attack_ledger, materialize_immediate_move_vs_move_action_pair
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from tests.test_detached_opponent_response_profile import _inputs
from tests.test_fixed_two_hit_immediate_move_pair_integration import _order


def _move(): return {"move_id": "assurance", "type": "dark", "category": "physical", "power": 60, "accuracy": 100, "priority": 0, "contact": True}


def _d0():
    _state, snapshot, d0, _own, _responses, _orders = _inputs(own_move="tackle")
    return snapshot, d0


def _leaf(d0, *, kind=None, loss=0, foreign=False):
    attacker = deepcopy(d0["active_owners"]["opponent"]); target = deepcopy(d0["active_owners"]["self"])
    if foreign: attacker["pokemon_id"] = "foreign"
    consequences = {"own_final_hp": 100, "target_final_hp": 80}
    if kind == "recoil": consequences["damage_based_recoil"] = {"attacker_pre_hp": 100, "attacker_post_hp": 100-loss, "recoil_damage": loss}
    if kind == "life_orb": consequences["life_orb"] = {"authority": {"recoil": {"pre_hp": 100, "post_hp": 100-loss, "recoil_damage": loss}}}
    if kind == "contact": consequences["contact_reactive_damage"] = {"outcome": "applies", "ordered_sources": ({"source_kind": "rocky-helmet", "pre_hp": 100, "post_hp": 100-loss, "reactive_damage": loss},)}
    if kind == "substitute": consequences["source_hit_context"] = {"target_routing": "substitute", "target_pre_hp": 100, "target_post_hp": 70}
    return {"action_type": "attack", "leaf_id": "prior", "hit_state": "hit", "consequences": consequences, "provenance": {"attacker": attacker, "target": target, "move_id": "source"}}


def _authority(d0, leaf=None):
    return materialize_detached_target_was_damaged_power_authority(strategy_d0=d0, move=_move(), user=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"], source_terminal_leaf=leaf, execution_order_provenance={"order": "opponent_first"})


def test_catalog_is_closed_and_first_execution_is_unboosted():
    assert resolve_canonical_target_was_damaged_power_move(move=_move())["effect"]["boosted_power"] == 120
    assert resolve_canonical_target_was_damaged_power_move(move={"move_id": "tackle"})["status"] == "unsupported"
    _snapshot, d0 = _d0()
    authority = _authority(d0)
    assert authority["target_was_damaged_before_execution"] is False and authority["selected_base_power"] == 60


def test_only_explicit_positive_qualifying_self_damage_kinds_boost():
    _snapshot, d0 = _d0()
    for kind in ("recoil", "life_orb", "contact"):
        authority = _authority(d0, _leaf(d0, kind=kind, loss=10))
        assert authority["selected_base_power"] == 120
        assert authority["qualifying_damage_event"]["source_kind"] in {"damage_based_recoil", "life_orb_recoil", "contact_reactive_damage"}
    assert _authority(d0, _leaf(d0, kind="recoil", loss=0))["selected_base_power"] == 60
    assert _authority(d0, _leaf(d0, kind="substitute"))["selected_base_power"] == 60


def test_foreign_target_and_unknown_source_kind_cannot_boost():
    _snapshot, d0 = _d0()
    assert _authority(d0, _leaf(d0, kind="recoil", loss=10, foreign=True))["selected_base_power"] == 60
    leaf = _leaf(d0); leaf["consequences"]["own_final_hp"] = 80
    assert _authority(d0, leaf)["selected_base_power"] == 60


def test_direct_damage_to_the_exact_target_qualifies_without_requiring_assurance_user_as_source():
    _snapshot, d0 = _d0()
    target = d0["active_owners"]["opponent"]; foreign_source = {**d0["active_owners"]["self"], "pokemon_id": "third-source"}
    leaf = {"action_type": "attack", "leaf_id": "prior-direct", "hit_state": "hit", "consequences": {"source_hit_context": {"target_routing": "target", "target_pre_hp": 100, "target_post_hp": 90}}, "provenance": {"attacker": foreign_source, "target": target, "move_id": "source"}}
    authority = _authority(d0, leaf)
    assert authority["selected_base_power"] == 120
    assert authority["qualifying_damage_event"]["source_kind"] == "direct_attack_damage"


def test_assurance_uses_60_or_120_through_the_ordinary_formula_seam():
    snapshot, d0 = _d0()
    metadata = {"status": "resolved", "move_id": "assurance", "metadata": _move()}
    unboosted = _attack_ledger(strategy_d0=d0, runtime_snapshot=snapshot, actor=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"], metadata_authority=metadata, source_terminal_leaf=None)
    boosted = _attack_ledger(strategy_d0=d0, runtime_snapshot=snapshot, actor=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"], metadata_authority=metadata, source_terminal_leaf=_leaf(d0, kind="recoil", loss=10), source_execution_order_provenance={"order": "opponent_first"})
    assert unboosted["status"] == boosted["status"] == "evaluable"
    assert all(row["provenance"]["target_was_damaged_power_authority"]["selected_base_power"] == 60 for row in unboosted["terminal_leaves"])
    assert all(row["provenance"]["target_was_damaged_power_authority"]["selected_base_power"] == 120 for row in boosted["terminal_leaves"])


def test_assurance_first_pair_is_unboosted_and_later_damage_is_not_retroactive():
    _state, snapshot, d0, own, responses, _orders = _inputs(own_move="tackle")
    own = {**own, "action_id": "attack:assurance", "identity": "assurance"}
    own["move_metadata_authority"] = {**own["move_metadata_authority"], "candidate_id": "attack:assurance", "move_id": "assurance", "metadata": _move()}
    opponent = next(row for row in responses["actions"] if row["action_id"] == "opponent_attack:tackle")
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=_order(d0, own, opponent, "own_first"))
    assert pair["status"] == "evaluable", pair.get("reason")
    assert all(row["first_action_leaf"]["provenance"]["target_was_damaged_power_authority"]["selected_base_power"] == 60 for row in pair["terminal_branches"])
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"
    forged = deepcopy(pair); authority = forged["terminal_branches"][0]["first_action_leaf"]["provenance"]["target_was_damaged_power_authority"]
    authority["target_was_damaged_before_execution"] = True; authority["selected_base_power"] = 120
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"
