from copy import deepcopy

from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from tests.test_runtime_d0_fling_item_execution_authority import _production_fling_pair
from tests.test_v15_direct_mechanics_slice_contract import _modifier_result


def _first_action_damage_rows(pair):
    rows = []
    for branch in pair["terminal_branches"]:
        leaf = branch["first_action_leaf"]
        rows.append((
            leaf.get("critical_state"),
            repr(leaf.get("damage_roll")),
            leaf.get("consequences", {}).get("damage"),
        ))
    return sorted(set(rows))


def test_pressure_colbur_and_chilan_pairs_are_evaluable_with_root_mass_one():
    for item in ("colbur-berry", "chilan-berry"):
        pair, ledger = _production_fling_pair(
            item=item, target_ability="pressure", target_condition="none",
        )
        assert pair["status"] == ledger["status"] == "evaluable", ledger.get("reason")
        assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
        assert {branch["action_order"] for branch in pair["terminal_branches"]} == {"own_first"}
        for branch in pair["terminal_branches"]:
            leaf = branch["first_action_leaf"]
            payload = leaf["consequences"][
                "fling_type_resist_empty_intrinsic_berry_target_effect"
            ]
            assert payload["status"] == "resolved"
            assert payload["outcome"] == "no_intrinsic_target_effect"
            transition = leaf["consequences"]["fling_berry_eaten_transition"]
            assert transition["status"] == "resolved"
            assert transition["resulting_state"] == "known_true"


def test_colbur_thrown_does_not_reduce_same_dark_fling_hit():
    colbur, colbur_ledger = _production_fling_pair(
        item="colbur-berry", target_ability="pressure",
    )
    chilan, chilan_ledger = _production_fling_pair(
        item="chilan-berry", target_ability="pressure",
    )
    assert colbur["status"] == colbur_ledger["status"] == "evaluable", colbur_ledger.get("reason")
    assert chilan["status"] == chilan_ledger["status"] == "evaluable"
    assert _first_action_damage_rows(colbur) == _first_action_damage_rows(chilan)
    assert "defender_item_type_resist_berry_reduction" not in repr(colbur)
    for branch in colbur["terminal_branches"]:
        evidence = branch["first_action_leaf"]["provenance"].get("direct_mechanics_evidence")
        if isinstance(evidence, dict):
            dynamic = evidence.get("dynamic_power_evidence")
            if isinstance(dynamic, dict):
                assert dynamic.get("effective_power") == 10
                assert dynamic.get("item_effects_active_during_damage") is False


def test_actual_held_colbur_still_reduces_qualifying_dark_hit():
    baseline = _modifier_result(
        move_id="tackle", category="physical", move_type="dark", power=100,
        defender_types=["psychic"], defender_current_hp=100,
    )
    held = _modifier_result(
        move_id="tackle", category="physical", move_type="dark", power=100,
        defender_item="colbur-berry", defender_types=["psychic"],
        defender_current_hp=100,
    )
    assert baseline["status"] == held["status"] == "known"
    assert held["damage_range"]["maximum"] < baseline["damage_range"]["maximum"]
    assert held["applied_damage_modifiers"] == [
        "defender_item_type_resist_berry_reduction"
    ]


def test_cheek_pouch_target_pair_is_not_evaluable_and_fabricates_no_heal():
    pair, ledger = _production_fling_pair(
        item="colbur-berry",
        target_ability="cheek-pouch",
        target_condition="none",
    )
    assert pair["status"] == "incomplete"
    assert ledger["status"] != "evaluable"
    assert "heal_amount" not in repr(pair)
    assert "cheek_pouch_heal" not in repr(pair)


def test_target_ko_before_eat_has_no_empty_intrinsic_or_ateberry_marker():
    pair, ledger = _production_fling_pair(
        item="colbur-berry",
        target_ability="pressure",
        opponent_hp=1,
        target_condition="none",
    )
    assert pair["status"] == ledger["status"] == "evaluable", ledger
    for branch in pair["terminal_branches"]:
        leaf = branch["first_action_leaf"]
        consequences = leaf["consequences"]
        assert consequences["target_ko"] is True
        assert "fling_type_resist_empty_intrinsic_berry_target_effect" not in consequences
        assert "fling_berry_eaten_transition" not in consequences


def test_exact_ledger_rejects_forged_family_item_action_leaf_and_intrinsic_change():
    pair, _ledger = _production_fling_pair(
        item="colbur-berry", target_ability="pressure",
    )
    mutations = (
        ("family_item", "chilan-berry"),
        ("action", "attack:foreign"),
        ("leaf", "foreign-leaf"),
        ("intrinsic_hp", 1),
    )
    for kind, value in mutations:
        forged = deepcopy(pair)
        branch = deepcopy(forged["terminal_branches"][0])
        payload = branch["first_action_leaf"]["consequences"][
            "fling_type_resist_empty_intrinsic_berry_target_effect"
        ]
        if kind == "family_item":
            payload["authority"]["berry_family_authority"]["item_id"] = value
        elif kind == "action":
            payload["authority"]["action_id"] = value
        elif kind == "leaf":
            payload["authority"]["source_leaf_id"] = value
        else:
            payload["intrinsic_hp_change"] = value
        forged["terminal_branches"] = (
            branch, *forged["terminal_branches"][1:]
        )
        assert normalize_exact_immediate_action_pair_outcome_ledger(
            pair=forged
        )["status"] == "rejected"
