from copy import deepcopy

import pytest

from advisor.canonical_was_damaged_power_family import resolve_canonical_was_damaged_power_move
from llm.advisor_detached_was_damaged_by_target_power_authority import materialize_detached_was_damaged_by_target_power_authority
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from tests.test_detached_opponent_response_profile import _inputs
from tests.test_fixed_two_hit_immediate_move_pair_integration import _order


def _owners():
    return ({"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "a"}, {"session_id": "s", "side": "opponent", "slot_index": 0, "pokemon_id": "b"})


def _d0():
    user, target = _owners()
    return {"session_id": "s", "source_runtime_fingerprint": "runtime", "strategy_preview_fingerprint": "branch", "active_owners": {"self": user, "opponent": target}}, user, target


def _move(move_id="avalanche"):
    return {"move_id": move_id, "type": "ice" if move_id == "avalanche" else "fighting", "category": "physical", "power": 60, "accuracy": 100, "priority": -4, "contact": True}


def _leaf(target, user, *, state="hit", hits=()):
    return {"action_type": "attack", "leaf_id": "source-leaf", "hit_state": state, "ordered_hits": tuple(hits), "provenance": {"attacker": target, "target": user, "move_id": "source"}}


def _event(user, target, *, loss=0):
    return {"status": "resolved", "session_id": "s", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "pair_branch_source_leaf_id": "source-leaf", "recipient": user, "source_attacker": target, "qualifying_event": True, "damage_route": "target", "hp_lost": loss}


@pytest.mark.parametrize(("move_id", "type"), (("avalanche", "ice"), ("revenge", "fighting")))
def test_catalog_is_closed_and_canonical(move_id, type):
    resolved = resolve_canonical_was_damaged_power_move(move=_move(move_id))
    assert resolved["status"] == "resolved"
    assert resolved["effect"] == {"move_id": move_id, "type": type, "category": "physical", "power": 60, "accuracy": 100, "priority": -4, "contact": True, "family": "was_damaged_same_turn_power", "boosted_power": 120, "condition": "target_caused_positive_direct_hp_damage_earlier_this_turn"}
    assert resolve_canonical_was_damaged_power_move(move={"move_id": "tackle"})["status"] == "unsupported"


def test_first_execution_and_known_non_damage_select_60():
    d0, user, target = _d0()
    first = materialize_detached_was_damaged_by_target_power_authority(strategy_d0=d0, move=_move(), user=user, target=target, incoming_event=None)
    assert first["selected_base_power"] == 60
    for state in ("miss", "blocked", "immune"):
        authority = materialize_detached_was_damaged_by_target_power_authority(strategy_d0=d0, move=_move(), user=user, target=target, incoming_event={"status": "incomplete", "reason": state}, source_terminal_leaf=_leaf(target, user, state=state))
        assert authority["status"] == "resolved" and authority["selected_base_power"] == 60


@pytest.mark.parametrize("move_id", ("avalanche", "revenge"))
def test_positive_direct_damage_from_exact_target_selects_120(move_id):
    d0, user, target = _d0()
    leaf = _leaf(target, user, hits=({"hit_index": 1, "target_routing": "target", "pre_hp": 100, "post_hp": 85},))
    authority = materialize_detached_was_damaged_by_target_power_authority(strategy_d0=d0, move=_move(move_id), user=user, target=target, incoming_event=_event(user, target, loss=15), source_terminal_leaf=leaf, execution_order_provenance={"order": "opponent_first"})
    assert authority["selected_base_power"] == 120
    assert authority["qualifying_hit_provenance"] == {"leaf_id": "source-leaf", "hit_index": 1, "actual_hp_loss": 15, "target_routing": "target"}
    assert authority["execution_order_provenance"] == {"order": "opponent_first"}


def test_multihit_is_existential_but_substitute_only_and_all_zero_are_not():
    d0, user, target = _d0()
    positive_then_zero = _leaf(target, user, hits=({"hit_index": 1, "target_routing": "target", "pre_hp": 100, "post_hp": 90}, {"hit_index": 2, "target_routing": "target", "pre_hp": 90, "post_hp": 90}))
    assert materialize_detached_was_damaged_by_target_power_authority(strategy_d0=d0, move=_move(), user=user, target=target, incoming_event=_event(user, target), source_terminal_leaf=positive_then_zero)["selected_base_power"] == 120
    all_zero = _leaf(target, user, hits=({"target_routing": "target", "pre_hp": 100, "post_hp": 100},))
    assert materialize_detached_was_damaged_by_target_power_authority(strategy_d0=d0, move=_move(), user=user, target=target, incoming_event=_event(user, target), source_terminal_leaf=all_zero)["selected_base_power"] == 60
    substitute = _leaf(target, user, hits=({"target_routing": "substitute", "actual_damage": 30},))
    assert materialize_detached_was_damaged_by_target_power_authority(strategy_d0=d0, move=_move(), user=user, target=target, incoming_event=_event(user, target), source_terminal_leaf=substitute)["selected_base_power"] == 60


def test_forged_or_foreign_provenance_rejects_instead_of_boosting():
    d0, user, target = _d0()
    foreign = {**target, "pokemon_id": "foreign"}
    leaf = _leaf(foreign, user, hits=({"target_routing": "target", "actual_damage": 10},))
    assert materialize_detached_was_damaged_by_target_power_authority(strategy_d0=d0, move=_move(), user=user, target=target, incoming_event=_event(user, target, loss=10), source_terminal_leaf=leaf)["status"] == "rejected"
    leaf = _leaf(target, user, hits=({"target_routing": "target", "actual_damage": 10},))
    forged = _event(user, target, loss=10); forged["source_branch_fingerprint"] = "foreign"
    assert materialize_detached_was_damaged_by_target_power_authority(strategy_d0=d0, move=_move(), user=user, target=target, incoming_event=forged, source_terminal_leaf=leaf)["status"] == "rejected"


@pytest.mark.parametrize("move_id", ("avalanche", "revenge"))
def test_opponent_first_pair_binds_resolved_power_to_the_ordinary_formula(move_id):
    _state, snapshot, d0, own_action, responses, _orders = _inputs(own_move="tackle")
    own_action = {**own_action, "action_id": f"attack:{move_id}", "identity": move_id}
    own_authority = {**own_action["move_metadata_authority"], "candidate_id": f"attack:{move_id}", "move_id": move_id, "metadata": _move(move_id)}
    own_action["move_metadata_authority"] = own_authority
    opponent = next(row for row in responses["actions"] if row["action_id"] == "opponent_attack:tackle")
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, opponent_action=opponent, action_order_authority=_order(d0, own_action, opponent, "opponent_first"))
    assert pair["status"] == "evaluable", pair.get("reason")
    executed = [row["second_action"]["leaf"] for row in pair["terminal_branches"] if row["second_action"]["state"] == "executed"]
    assert executed
    assert all(row["provenance"]["was_damaged_power_authority"]["selected_base_power"] == 120 for row in executed)
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"
    forged = deepcopy(pair)
    forged_leaf = forged["terminal_branches"][0]["second_action"]["leaf"]
    forged_leaf["provenance"]["was_damaged_power_authority"]["selected_base_power"] = 60
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"


def test_own_first_uses_unboosted_power_and_later_damage_cannot_retroactively_change_it():
    _state, snapshot, d0, own_action, responses, _orders = _inputs(own_move="tackle")
    own_action = {**own_action, "action_id": "attack:avalanche", "identity": "avalanche"}
    own_action["move_metadata_authority"] = {**own_action["move_metadata_authority"], "candidate_id": "attack:avalanche", "move_id": "avalanche", "metadata": _move("avalanche")}
    opponent = next(row for row in responses["actions"] if row["action_id"] == "opponent_attack:tackle")
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, opponent_action=opponent, action_order_authority=_order(d0, own_action, opponent, "own_first"))
    assert pair["status"] == "evaluable", pair.get("reason")
    assert all(row["first_action_leaf"]["provenance"]["was_damaged_power_authority"]["selected_base_power"] == 60 for row in pair["terminal_branches"])
