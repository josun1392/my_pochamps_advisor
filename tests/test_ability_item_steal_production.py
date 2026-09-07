"""Exercise the real ordinary/fixed/graph production boundaries."""
from copy import deepcopy
import pytest
from tests.test_detached_opponent_response_profile import _state, _snapshot, _owner, _metadata
from tests.test_fixed_two_hit_immediate_move_pair_integration import _fixed_two_action
from tests.test_detached_variable_two_to_five_hit_graph_immediate_move_pair import _variable_action, _population_bomb_action, _escalating_action
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_immediate_move_vs_move_action_pair import _attack_ledger
from llm.advisor_detached_predictive_intermediate_state import materialize_detached_predictive_intermediate_state
from llm.advisor_detached_variable_two_to_five_hit_graph_immediate_move_pair import _variable_action_graph, _terminal_sources, _synthetic_terminal_leaf
from llm.advisor_detached_ability_item_steal_terminal import attach_ability_item_steal
from llm.advisor_runtime_d0_canonical_contact_classification_authority import canonical_move_contact_metadata


def inputs(ability="magician", donor_ability="pressure", receiver_item=None, donor_item="quick-claw", hp=100, own_hp=None):
    state = _state()
    receiver_side = "self" if ability == "magician" else "opponent"
    donor_side = "opponent" if receiver_side == "self" else "self"
    for side, value, item in ((receiver_side, ability, receiver_item), (donor_side, donor_ability, donor_item)):
        row = state[f"{side}_side"]["pokemon"][0]
        row.update(current_ability=value, known_item=item, current_hp=hp)
        row["known_item_provenance"]["status"] = "known" if item else "known_absent"
    if own_hp is not None:
        state["self_side"]["pokemon"][0]["current_hp"] = own_hp
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    return snapshot, d0


def ordinary(ability="magician", move="tackle", **kwargs):
    snapshot, d0 = inputs(ability, **kwargs)
    before = deepcopy((snapshot, d0))
    action = _fixed_two_action(d0, move_id=move)
    action["move_metadata_authority"]["metadata"].pop("min_hits")
    action["move_metadata_authority"]["metadata"].pop("max_hits")
    result = _attack_ledger(strategy_d0=d0, runtime_snapshot=snapshot, actor=d0["active_owners"]["self"], target=d0["active_owners"]["opponent"], metadata_authority=action["move_metadata_authority"], action=action)
    assert (snapshot, d0) == before
    assert result["status"] == "evaluable", result
    return snapshot, d0, result


@pytest.mark.parametrize("ability", ["magician", "pickpocket"])
def test_ordinary_transfer_and_detached_later_reader(ability):
    _, d0, result = ordinary(ability)
    transfers = [leaf for leaf in result["terminal_leaves"] if leaf["consequences"].get("ability_item_steal")]
    assert transfers
    for leaf in transfers:
        effect = leaf["consequences"]["ability_item_steal"]
        state = materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=leaf)
        assert state["status"] == "resolved"
        assert state["active"][effect["receiver"]["side"]]["hypothetical_item"]["value"] == "quick-claw"
        assert state["active"][effect["donor"]["side"]]["hypothetical_item"]["value"] is None


@pytest.mark.parametrize("ability", ["magician", "pickpocket"])
@pytest.mark.parametrize("kwargs", [{"receiver_item":"quick-claw"}, {"donor_item":None}, {"donor_ability":"sticky-hold"}, {"donor_ability":"neutralizing-gas"}])
def test_ordinary_no_effect_preconditions(ability, kwargs):
    _, _, result = ordinary(ability, **kwargs)
    assert all("ability_item_steal" not in leaf["consequences"] for leaf in result["terminal_leaves"])


def test_noncontact_and_sheer_force():
    assert any("ability_item_steal" in leaf["consequences"] for leaf in ordinary("magician", move="water-gun")[2]["terminal_leaves"])
    assert all("ability_item_steal" not in leaf["consequences"] for leaf in ordinary("pickpocket", move="water-gun")[2]["terminal_leaves"])
    assert any("ability_item_steal" in leaf["consequences"] for leaf in ordinary("pickpocket", donor_ability="sheer-force")[2]["terminal_leaves"])




@pytest.mark.parametrize("move", ["double-hit", "bullet-seed", "rock-blast", "population-bomb", "triple-axel", "triple-kick"])
@pytest.mark.parametrize("ability", ["magician", "pickpocket"])
def test_native_multihit_terminal_production(move, ability):
    snapshot, d0 = inputs(ability)
    actor, target = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
    if move == "double-hit":
        action = _fixed_two_action(d0, move_id=move, power=5)
        result = _attack_ledger(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, metadata_authority=action["move_metadata_authority"])
        assert result["status"] == "evaluable", result
        assert any("ability_item_steal" in row["consequences"] for row in result["terminal_leaves"])
        assert all("ability_item_steal" not in hit for row in result["terminal_leaves"] for hit in row["ordered_hits"])
        return
    action = _variable_action(d0, move, power=5) if move in {"bullet-seed", "rock-blast"} else _population_bomb_action(d0, power=5, accuracy=90) if move == "population-bomb" else _escalating_action(d0, move, accuracy=90)
    graph = _variable_action_graph(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, metadata_authority=action["move_metadata_authority"], sturdy_survival_authority=None)
    assert graph["status"] == "evaluable", graph
    before = deepcopy(graph)
    family = {"population-bomb":"population_bomb", "triple-axel":"triple_axel", "triple-kick":"triple_kick"}.get(move, "variable_two_to_five_hit")
    effects = []
    for source in _terminal_sources(graph):
        if "native_terminal" not in source: continue
        leaf = _synthetic_terminal_leaf(first_graph=graph, source=source)
        landed = source["consequences"].get("landed_hit_count", 1 if source.get("ordered_hit") else 0)
        leaf["hit_state"] = "hit" if landed else "miss"
        state = materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=leaf)
        status, row = attach_ability_item_steal(strategy_d0=d0, runtime_snapshot=snapshot, leaf=leaf, intermediate=state, family=family, graph=graph, terminal_edge=source["native_terminal"])
        assert status["status"] == "resolved", status
        effect = row["consequences"].get("ability_item_steal")
        if effect:
            effects.append(effect)
            assert effect["completion"]["terminal_id"] == source["native_terminal"]["edge_id"]
            assert effect["completion"]["terminal_reason"] == source["native_terminal"]["terminal_reason"]
        if not landed: assert effect is None
    assert bool(effects) == (ability == "magician" or move not in {"bullet-seed", "rock-blast"})
    assert graph == before
    assert all("ability_item_steal" not in edge for edge in graph["terminal_leaf_edges"])


@pytest.mark.parametrize("ability", ["magician", "pickpocket"])
def test_valid_ordinary_ledger_evidence(ability):
    from llm.advisor_ability_item_steal_ledger_validation import validate_ability_item_steal_leaf
    for leaf in ordinary(ability)[2]["terminal_leaves"]:
        assert validate_ability_item_steal_leaf(leaf) is None


@pytest.mark.parametrize("field,value", [("trigger_direction","magician_attacker_hit"), ("ability_holder",{}), ("item","orb"), ("source_leaf_id","foreign"), ("session_id","foreign"), ("source_branch_path",()), ("donor_item_after",{"status":"known","value":"quick-claw"}), ("receiver_item_after",{"status":"known_absent","value":None})])
def test_forged_ability_evidence_rejected(field, value):
    from llm.advisor_ability_item_steal_ledger_validation import validate_ability_item_steal_leaf
    leaf = deepcopy(ordinary("pickpocket")[2]["terminal_leaves"][0])
    leaf["consequences"]["ability_item_steal"][field] = value
    assert validate_ability_item_steal_leaf(leaf) is not None


@pytest.mark.parametrize("field,value", [("terminal",False), ("terminal_id","foreign"), ("terminal_reason","foreign")])
def test_forged_terminal_rejected(field, value):
    from llm.advisor_ability_item_steal_ledger_validation import validate_ability_item_steal_leaf
    leaf = deepcopy(ordinary("pickpocket")[2]["terminal_leaves"][0])
    leaf["provenance"]["ability_item_steal_terminal_effect"]["terminal_source"][field] = value
    assert validate_ability_item_steal_leaf(leaf) is not None


@pytest.mark.parametrize("kind", ["contact", "sheer", "sticky", "deletion", "duplicate"])
def test_forged_nested_evidence_rejected(kind):
    from llm.advisor_ability_item_steal_ledger_validation import validate_ability_item_steal_leaf
    leaf = deepcopy(ordinary("pickpocket")[2]["terminal_leaves"][0])
    effect = leaf["consequences"]["ability_item_steal"]
    if kind == "contact": effect["contact"]["is_contact"] = False
    if kind == "sheer": effect["sheer_force_trigger_applicability"]["prevents_trigger"] = True
    if kind == "sticky": effect["transfer_legality"]["sticky_hold_active"] = True
    if kind == "deletion": del leaf["consequences"]["ability_item_steal"]
    if kind == "duplicate": effect["donor_item_after"] = deepcopy(effect["receiver_item_after"])
    assert validate_ability_item_steal_leaf(leaf) is not None


@pytest.mark.parametrize("move", ["tackle", "double-hit", "bullet-seed", "population-bomb", "triple-axel", "triple-kick"])
def test_complete_pair_ledger_with_terminal_transfer(move):
    from tests.test_detached_opponent_response_profile import _complete_state, MOVES
    from tests.test_fixed_two_hit_immediate_move_pair_integration import _order
    from llm.advisor_runtime_d0_opponent_action_authority import freeze_runtime_d0_opponent_known_move_action_authority
    from llm.advisor_runtime_d0_complete_opponent_response_set_authority import freeze_runtime_d0_complete_opponent_response_set_authority
    from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
    from llm.advisor_detached_variable_two_to_five_hit_graph_immediate_move_pair import materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair
    from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
    snapshot, _ = inputs("magician", hp=30)
    state = _complete_state(snapshot["state"])
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state,"self"))
    known = freeze_runtime_d0_opponent_known_move_action_authority(strategy_d0=d0, runtime_snapshot=snapshot, canonical_move_metadata_authorities={m:_metadata(m) for m in MOVES})
    responses = freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_known_move_authority=known)
    opponent = next(a for a in responses["actions"] if a["action_id"] == "opponent_attack:tackle")
    action = _fixed_two_action(d0, move_id=move) if move in {"tackle","double-hit"} else _variable_action(d0, move) if move == "bullet-seed" else _population_bomb_action(d0, power=25, accuracy=90) if move == "population-bomb" else _escalating_action(d0, move, accuracy=90)
    if move == "tackle":
        action["move_metadata_authority"]["metadata"].pop("min_hits")
        action["move_metadata_authority"]["metadata"].pop("max_hits")
    builder = materialize_immediate_move_vs_move_action_pair if move in {"tackle","double-hit"} else materialize_detached_variable_two_to_five_hit_graph_immediate_move_pair
    pair = builder(strategy_d0=d0, runtime_snapshot=snapshot, own_action=action, opponent_action=opponent, action_order_authority=_order(d0,action,opponent,"own_first"))
    assert pair["status"] == "evaluable", pair.get("reason")
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable", ledger.get("reason")
    if "order_graphs" in pair:
        transitions = pair["order_graphs"][0]["terminal_transitions"]
        assert any(row["first_terminal_consequences"].get("ability_item_steal") for row in transitions)
        forged = deepcopy(pair)
        edge = forged["order_graphs"][0]["first_action_graph"]["terminal_leaf_edges"][0]
        edge["ability_item_steal"] = {"item":"forged"}
        assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"
        forged = deepcopy(pair)
        row = next(row for row in forged["order_graphs"][0]["terminal_transitions"] if row.get("ability_item_steal_terminal_effect"))
        row["ability_item_steal_terminal_effect"]["terminal_source"]["terminal_id"] = "foreign"
        assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"
    else:
        assert any(row["first_action_leaf"]["consequences"].get("ability_item_steal") for row in pair["terminal_branches"])


@pytest.mark.parametrize("ability", ["magician", "pickpocket"])
@pytest.mark.parametrize("failure", ["miss", "protect", "immunity", "cancelled", "attacker_fainted", "zero_damage_hit"])
def test_completed_unsuccessful_or_fainted_action_never_transfers(ability, failure):
    snapshot, d0, ledger = ordinary(ability)
    leaf = deepcopy(ledger["terminal_leaves"][0]["provenance"]["ability_item_steal_terminal_effect"]["source_leaf"])
    if failure == "attacker_fainted":
        leaf["consequences"]["own_final_hp"] = 0
    else:
        leaf["hit_state"] = "miss" if failure == "miss" else "hit" if failure == "zero_damage_hit" else "not_applicable"
        leaf["consequences"]["damage"] = 0
        leaf["consequences"]["contact"] = "not_applicable"
    state = materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=leaf)
    status, after = attach_ability_item_steal(strategy_d0=d0, runtime_snapshot=snapshot, leaf=leaf, intermediate=state, family="ordinary_single_hit")
    assert status["status"] == "resolved"
    assert "ability_item_steal" not in after["consequences"]


def test_sheer_force_blocking_uses_existing_canonical_result():
    _, _, ledger = ordinary("pickpocket", move="iron-head", donor_ability="sheer-force")
    assert all("ability_item_steal" not in leaf["consequences"] for leaf in ledger["terminal_leaves"])


@pytest.mark.parametrize("ability", ["magician", "pickpocket"])
def test_branch_overlay_wins_over_runtime_item_and_unknown_fails_closed(ability):
    snapshot, d0, ledger = ordinary(ability)
    effect = ledger["terminal_leaves"][0]["provenance"]["ability_item_steal_terminal_effect"]
    leaf, state = deepcopy(effect["source_leaf"]), deepcopy(effect["detached_state_before"])
    receiver, donor = effect["effect_authority"]["receiver"], effect["effect_authority"]["donor"]
    state["active"][donor["side"]]["hypothetical_item"] = {"status":"known","value":"black-belt","source":"earlier_detached_effect"}
    status, row = attach_ability_item_steal(strategy_d0=d0, runtime_snapshot=snapshot, leaf=leaf, intermediate=state, family="ordinary_single_hit")
    assert status["status"] == "resolved" and row["consequences"]["ability_item_steal"]["item"] == "black-belt"
    state["active"][receiver["side"]]["hypothetical_item"] = {"status":"known","value":"orb"}
    assert "ability_item_steal" not in attach_ability_item_steal(strategy_d0=d0, runtime_snapshot=snapshot, leaf=leaf, intermediate=state, family="ordinary_single_hit")[1]["consequences"]
    state["active"][receiver["side"]]["hypothetical_item"] = {"status":"unknown","reason":"branch_effect_unknown"}
    assert attach_ability_item_steal(strategy_d0=d0, runtime_snapshot=snapshot, leaf=leaf, intermediate=state, family="ordinary_single_hit")[0]["status"] == "incomplete"


def test_nonterminal_native_edge_rejected_without_item_projection():
    snapshot, d0, ledger = ordinary("pickpocket")
    effect = ledger["terminal_leaves"][0]["provenance"]["ability_item_steal_terminal_effect"]
    status, leaf = attach_ability_item_steal(strategy_d0=d0, runtime_snapshot=snapshot, leaf=effect["source_leaf"], intermediate=effect["detached_state_before"], family="fixed_two_hit", terminal_edge={"terminal":False,"edge_id":"hit:1"})
    assert status["status"] == "rejected" and "ability_item_steal" not in leaf["consequences"]


def test_terminal_overlay_has_priority_after_previous_item_effect():
    _, d0, ledger = ordinary("magician")
    leaf = deepcopy(ledger["terminal_leaves"][0])
    leaf["consequences"]["item_transfer_after_hit"] = {"outcome":"transferred","item":"old-item"}
    state = materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=leaf)
    assert state["active"]["self"]["hypothetical_item"]["value"] == "quick-claw"


@pytest.mark.parametrize("field", ["sheer_force_trigger_applicability", "transfer_legality", "receiver_item_after"])
def test_coordinated_forgery_cannot_bypass_canonical_or_atomic_validation(field):
    from llm.advisor_ability_item_steal_ledger_validation import validate_ability_item_steal_leaf
    leaf = deepcopy(ordinary("pickpocket")[2]["terminal_leaves"][0])
    effect = deepcopy(leaf["consequences"]["ability_item_steal"])
    if field == "sheer_force_trigger_applicability":
        effect[field]["canonical_applicability"]["boosted"] = True
    elif field == "transfer_legality":
        effect[field]["donor_ability"] = "sticky-hold"
    else:
        effect[field]["value"] = "different-item"
    leaf["consequences"]["ability_item_steal"] = deepcopy(effect)
    leaf["provenance"]["ability_item_steal_completion_authority"] = deepcopy(effect)
    envelope = leaf["provenance"]["ability_item_steal_terminal_effect"]
    envelope["effect_authority"] = deepcopy(effect)
    envelope["sheer_force"] = deepcopy(effect["sheer_force_trigger_applicability"])
    assert validate_ability_item_steal_leaf(leaf) is not None


def test_stale_runtime_snapshot_fails_closed():
    snapshot, d0, ledger = ordinary("magician")
    envelope = ledger["terminal_leaves"][0]["provenance"]["ability_item_steal_terminal_effect"]
    snapshot = deepcopy(snapshot)
    snapshot["state"]["self_side"]["pokemon"][0]["current_hp"] = 1
    snapshot = _snapshot(snapshot["state"])
    assert attach_ability_item_steal(strategy_d0=d0, runtime_snapshot=snapshot, leaf=envelope["source_leaf"], intermediate=envelope["detached_state_before"], family="ordinary_single_hit")[0]["status"] == "rejected"


@pytest.mark.parametrize("donor_ability,donor_item", [("rough-skin","quick-claw"), ("iron-barbs","quick-claw"), ("pressure","rocky-helmet")])
def test_contact_reaction_keeps_existing_order(donor_ability, donor_item):
    _, _, ledger = ordinary("magician", donor_ability=donor_ability, donor_item=donor_item)
    assert all(leaf["consequences"]["own_final_hp"] < 100 for leaf in ledger["terminal_leaves"])
    assert any("ability_item_steal" in leaf["consequences"] for leaf in ledger["terminal_leaves"])
    _, _, fainted = ordinary("magician", donor_ability=donor_ability, donor_item=donor_item, own_hp=1)
    assert all(leaf["consequences"]["own_final_hp"] == 0 and "ability_item_steal" not in leaf["consequences"] for leaf in fainted["terminal_leaves"])
