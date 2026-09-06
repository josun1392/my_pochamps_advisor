from advisor.canonical_knock_off_item_power_and_removal import resolve_canonical_knock_off_move, resolve_knock_off_target_item
from llm.advisor_detached_knock_off_item_removal import materialize_detached_knock_off_item_removal
from llm.advisor_direct_mechanics import _knock_off_power_context
from tests.test_v15_direct_mechanics_slice_contract import _modifier_result


def test_catalog_and_exact_item_power_states():
    effect = resolve_canonical_knock_off_move(move={"move_id": "knock-off"})["effect"]
    assert (effect["type"], effect["category"], effect["base_power"], effect["accuracy"], effect["priority"], effect["contact"], effect["protection_blockable"]) == ("dark", "physical", 65, 100, 0, True, True)
    present = _modifier_result(move_id="knock-off", move_type="dark", power=65, defender_item="black-belt")
    neutral = _modifier_result(move_id="knock-off", move_type="dark", power=65, defender_item="bright-powder")
    unknown = _modifier_result(move_id="knock-off", move_type="dark", power=65, defender_item="unknown")
    absent = resolve_knock_off_target_item(item_authority={"status": "known_absent"}, target_species="eevee")
    assert absent["power_modifier_q12"] == 4096
    assert present["dynamic_power_evidence"]["power_modifier_q12"] == 6144
    assert present["dynamic_power_evidence"]["effective_power"] == 98
    assert neutral["status"] == "known" and neutral["dynamic_power_evidence"]["boost_eligible"] is True
    assert unknown["status"] == "insufficient_context"


def test_sticky_hold_is_power_eligible_but_surviving_removal_is_blocked():
    item = resolve_knock_off_target_item(item_authority={"status": "known", "value": "black-belt"}, target_species="eevee")
    authority = {"status": "resolved", "move_id": "knock-off", "target": {"side": "opponent"}, **item, "sticky_hold": True}
    leaf = {"leaf_id": "hit", "hit_state": "hit", "consequences": {"damage": 5, "target_final_hp": 10, "source_hit_context": {"target_routing": "target"}}, "provenance": {"move_id": "knock-off", "target": {"side": "opponent"}}}
    result = materialize_detached_knock_off_item_removal(authority=authority, source_leaf=leaf)
    assert item["boost_eligible"] is True
    assert (result["outcome"], result["item_after"]) == ("not_removed", "black-belt")


def test_neutralizing_gas_suppresses_sticky_hold_without_changing_power_eligibility():
    provenance = {"defender": {"pokemon_identity": "eevee", "known_item": {"status": "known", "value": "black-belt"}}}
    current = {"ability_context": {"current_abilities": [{"side": "self", "ability": "neutralizing-gas"}, {"side": "opponent", "ability": "sticky-hold"}]}}
    result = _knock_off_power_context(provenance, current)
    assert result["sticky_hold"] is False and result["boost_eligible"] is True


def test_mega_owner_exception_and_typed_hit_only_removal():
    exception = resolve_knock_off_target_item(item_authority={"status": "known", "value": "abomasite"}, target_species="abomasnow")
    assert exception["mega_stone_exception"] is True and exception["boost_eligible"] is False
    authority = {"status": "resolved", "move_id": "knock-off", "target": {"side": "opponent"}, **resolve_knock_off_target_item(item_authority={"status": "known", "value": "black-belt"}, target_species="eevee"), "sticky_hold": False}
    hit = {"leaf_id": "hit", "hit_state": "hit", "consequences": {"damage": 5, "target_final_hp": 10, "source_hit_context": {"target_routing": "target"}}, "provenance": {"move_id": "knock-off", "target": {"side": "opponent"}}}
    miss = {**hit, "leaf_id": "miss", "hit_state": "miss"}
    assert materialize_detached_knock_off_item_removal(authority=authority, source_leaf=hit)["outcome"] == "removed"
    assert materialize_detached_knock_off_item_removal(authority=authority, source_leaf=miss)["outcome"] == "not_removed"
    sticky = {**authority, "sticky_hold": True}
    assert materialize_detached_knock_off_item_removal(authority=sticky, source_leaf=hit)["reason"] == "sticky_hold_target_survived"
    faint = {**hit, "consequences": {"damage": 15, "target_final_hp": 0, "source_hit_context": {"target_routing": "target"}}}
    assert materialize_detached_knock_off_item_removal(authority=sticky, source_leaf=faint)["outcome"] == "removed"
    substitute = {**hit, "consequences": {"damage": 5, "target_final_hp": 10, "source_hit_context": {"target_routing": "substitute"}}}
    assert materialize_detached_knock_off_item_removal(authority=authority, source_leaf=substitute)["reason"] == "unsupported_or_substitute_target_routing"
