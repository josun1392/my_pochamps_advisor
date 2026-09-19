from copy import deepcopy

import pytest

from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from tests.test_runtime_d0_fling_item_execution_authority import (
    _production_fling_pair,
)


def _pair(item="oran-berry", **kwargs):
    return _production_fling_pair(
        item=item,
        target_healing_prevented="inactive",
        opponent_move="protect",
        **kwargs,
    )


def _branch_with_effect(pair):
    for index, branch in enumerate(pair["terminal_branches"]):
        first = branch.get("first_action_leaf", {})
        payload = first.get("consequences", {}).get(
            "fling_hp_restore_berry_target_effect"
        )
        if isinstance(payload, dict):
            return index, branch
    raise AssertionError("no Fling HP-restore effect leaf found")


def _replace_branch(pair, index, branch):
    rows = list(pair["terminal_branches"])
    rows[index] = branch
    pair["terminal_branches"] = tuple(rows)


@pytest.mark.parametrize("item", ["oran-berry", "sitrus-berry"])
def test_exact_pair_root_mass_and_ateberry(item):
    pair, ledger = _pair(item)
    assert pair["status"] == "evaluable", pair.get("reason")
    assert ledger["status"] == "evaluable", ledger.get("reason")
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    hit_count = 0
    for branch in pair["terminal_branches"]:
        first = branch["first_action_leaf"]
        effect = first["consequences"].get("fling_hp_restore_berry_target_effect")
        if effect is None:
            continue
        hit_count += 1
        assert effect["outcome"] in {"healed", "no_effect_full_hp"}
        assert first["consequences"]["target_final_hp"] == effect["final_hp"]
        assert first["consequences"]["fling_berry_eaten_transition"]["resulting_state"] == "known_true"
        assert branch["action_order"] == "own_first"
    assert hit_count > 0


@pytest.mark.parametrize("item", ["oran-berry", "sitrus-berry"])
def test_pair_healing_prevented_keeps_eat_and_ateberry(item):
    pair, ledger = _production_fling_pair(
        item=item,
        target_healing_prevented="active",
        opponent_move="protect",
    )
    assert pair["status"] == ledger["status"] == "evaluable"
    _, branch = _branch_with_effect(pair)
    first = branch["first_action_leaf"]
    effect = first["consequences"]["fling_hp_restore_berry_target_effect"]
    assert effect["outcome"] == "healing_prevented"
    assert effect["actual_heal"] == 0
    assert effect["final_hp"] == effect["post_hit_hp"]
    assert first["consequences"]["fling_berry_eaten_transition"]["resulting_state"] == "known_true"


@pytest.mark.parametrize("item", ["oran-berry", "sitrus-berry"])
def test_pair_klutz_suppression_has_no_heal_but_ateberry(item):
    pair, ledger = _production_fling_pair(
        item=item,
        target_ability="klutz",
        target_item=None,
        target_healing_prevented="__unknown__",
        opponent_move="protect",
    )
    assert pair["status"] == ledger["status"] == "evaluable", (pair, ledger)
    _, branch = _branch_with_effect(pair)
    first = branch["first_action_leaf"]
    effect = first["consequences"]["fling_hp_restore_berry_target_effect"]
    assert effect["outcome"] == "intrinsic_suppressed_by_target_klutz"
    assert effect["actual_heal"] == 0
    assert effect["final_hp"] == effect["post_hit_hp"]
    assert first["consequences"]["fling_berry_eaten_transition"]["resulting_state"] == "known_true"


@pytest.mark.parametrize("item", ["oran-berry", "sitrus-berry"])
def test_pair_klutz_ability_shield_executes_heal_and_preserves_item(item):
    pair, ledger = _production_fling_pair(
        item=item,
        target_ability="klutz",
        target_item="ability-shield",
        target_healing_prevented="inactive",
        opponent_move="protect",
    )
    assert pair["status"] == ledger["status"] == "evaluable", (pair, ledger)
    _, branch = _branch_with_effect(pair)
    effect = branch["first_action_leaf"]["consequences"]["fling_hp_restore_berry_target_effect"]
    assert effect["outcome"] in {"healed", "no_effect_full_hp"}
    intrinsic = effect["authority"]["target_intrinsic_on_eat_readiness"]
    assert intrinsic["readiness"] == "executes"
    assert intrinsic["authority"]["target_item_authority"]["value"] == "ability-shield"
    assert "target_item_after" not in effect


def test_pair_unknown_healing_prevention_fails_closed():
    pair, ledger = _production_fling_pair(
        item="oran-berry",
        target_healing_prevented="__unknown__",
        opponent_move="protect",
    )
    assert pair["status"] == "incomplete"
    assert ledger["status"] == "incomplete"


@pytest.mark.parametrize(
    ("item", "field", "value"),
    [
        ("oran-berry", "nominal_heal", 11),
        ("sitrus-berry", "nominal_heal", 26),
        ("oran-berry", "maximum_hp", 101),
        ("oran-berry", "actual_heal", 999),
    ],
)
def test_ledger_rejects_forged_heal_arithmetic(item, field, value):
    pair, _ = _pair(item)
    forged = deepcopy(pair)
    index, branch = _branch_with_effect(forged)
    branch = deepcopy(branch)
    effect = branch["first_action_leaf"]["consequences"]["fling_hp_restore_berry_target_effect"]
    effect[field] = value
    effect["authority"][field] = value
    if field == "actual_heal":
        effect["final_hp"] = effect["post_hit_hp"] + value
        effect["authority"]["final_hp"] = effect["final_hp"]
        branch["first_action_leaf"]["consequences"]["target_final_hp"] = effect["final_hp"]
    _replace_branch(forged, index, branch)
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"


def test_ledger_rejects_healing_prevented_positive_heal():
    pair, _ = _production_fling_pair(
        item="oran-berry",
        target_healing_prevented="active",
        opponent_move="protect",
    )
    forged = deepcopy(pair)
    index, branch = _branch_with_effect(forged)
    branch = deepcopy(branch)
    effect = branch["first_action_leaf"]["consequences"]["fling_hp_restore_berry_target_effect"]
    effect["actual_heal"] = effect["authority"]["actual_heal"] = 1
    effect["final_hp"] = effect["authority"]["final_hp"] = effect["post_hit_hp"] + 1
    branch["first_action_leaf"]["consequences"]["target_final_hp"] = effect["final_hp"]
    _replace_branch(forged, index, branch)
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"


def test_ledger_rejects_klutz_suppressed_positive_heal():
    pair, _ = _production_fling_pair(
        item="sitrus-berry",
        target_ability="klutz",
        target_item=None,
        target_healing_prevented="__unknown__",
        opponent_move="protect",
    )
    forged = deepcopy(pair)
    index, branch = _branch_with_effect(forged)
    branch = deepcopy(branch)
    effect = branch["first_action_leaf"]["consequences"]["fling_hp_restore_berry_target_effect"]
    effect["nominal_heal"] = effect["authority"]["nominal_heal"] = 25
    effect["actual_heal"] = effect["authority"]["actual_heal"] = 25
    effect["final_hp"] = effect["authority"]["final_hp"] = min(
        effect["maximum_hp"], effect["post_hit_hp"] + 25
    )
    branch["first_action_leaf"]["consequences"]["target_final_hp"] = effect["final_hp"]
    _replace_branch(forged, index, branch)
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"


def test_ledger_rejects_forged_eat_ateberry_source_binding_and_target_item_consumption():
    pair, _ = _pair("oran-berry")
    mutators = []

    def forged_eat(effect, first):
        effect["authority"]["berry_eat_item_interaction_authority"]["target_eat_occurred"] = False

    def forged_ateberry(effect, first):
        first["consequences"]["fling_berry_eaten_transition"]["resulting_state"] = "known_false"

    def forged_source(effect, first):
        effect["authority"]["source_leaf_id"] = "forged-leaf"

    def forged_item(effect, first):
        effect["target_item_after"] = {"status": "known_absent", "value": None}

    mutators.extend((forged_eat, forged_ateberry, forged_source, forged_item))
    for mutate in mutators:
        forged = deepcopy(pair)
        index, branch = _branch_with_effect(forged)
        branch = deepcopy(branch)
        first = branch["first_action_leaf"]
        effect = first["consequences"]["fling_hp_restore_berry_target_effect"]
        mutate(effect, first)
        _replace_branch(forged, index, branch)
        assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"



@pytest.mark.parametrize("item", ["oran-berry", "sitrus-berry"])
def test_own_first_healed_leaf_continues_to_pending_target_attack_without_reordering(item):
    pair, ledger = _production_fling_pair(
        item=item,
        target_healing_prevented="inactive",
        opponent_move="water-gun",
    )
    assert pair["status"] == ledger["status"] == "evaluable", (pair.get("reason"), ledger.get("reason"))
    observed = 0
    for branch in pair["terminal_branches"]:
        first = branch["first_action_leaf"]
        effect = first.get("consequences", {}).get("fling_hp_restore_berry_target_effect")
        if not isinstance(effect, dict):
            continue
        observed += 1
        assert branch["action_order"] == "own_first"
        assert first["consequences"]["target_final_hp"] == effect["final_hp"]
        assert branch["second_action"]["state"] == "executed"
    assert observed > 0
