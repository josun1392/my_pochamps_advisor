from copy import deepcopy

import pytest

from llm.advisor_runtime_d0_fling_berry_eat_item_interaction_authority import (
    assess_fling_berry_target_eat_item_consequence_readiness,
)
from llm.advisor_detached_berry_eaten_transition import (
    materialize_detached_fling_berry_eaten_transition,
)
from llm.advisor_runtime_d0_fling_major_status_cure_berry_target_effect_authority import (
    freeze_runtime_d0_fling_major_status_cure_berry_target_effect_authority,
    materialize_detached_fling_major_status_cure_berry_target_effect,
)
from tests.fling_status_cure_berry_test_support import berry_cure_case
from tests.test_runtime_d0_fling_item_execution_authority import _production_fling_pair


@pytest.mark.parametrize(
    ("item", "condition"),
    [
        ("cheri-berry", "paralysis"),
        ("chesto-berry", "sleep"),
        ("aspear-berry", "freeze"),
        ("rawst-berry", "burn"),
        ("pecha-berry", "poison"),
        ("pecha-berry", "toxic"),
    ],
)
def test_pressure_target_keeps_all_status_cure_berries_exact(item, condition):
    case = berry_cure_case(
        item=item,
        condition=condition,
        target_ability="pressure",
    )
    assert case["interaction"]["status"] == "resolved"
    assert case["interaction"]["target_ability_interaction"] == "not_applicable"
    assert case["interaction"]["ability_consequence_materialization"] == "not_applicable"
    readiness = assess_fling_berry_target_eat_item_consequence_readiness(
        case["interaction"],
    )
    assert readiness["status"] == "resolved"
    assert readiness["readiness"] == "ready"
    assert case["authority"]["status"] == "resolved"
    assert case["authority"]["outcome"] == "applied_major_status_cure"
    assert case["authority"]["target_eat_item_consequence_readiness"] == readiness


@pytest.mark.parametrize("ability", ["cheek-pouch", "ripen", "cud-chew"])
def test_direct_target_eat_item_hooks_remain_exact_but_consumer_fails_closed(ability):
    case = berry_cure_case(
        item="cheri-berry",
        condition="paralysis",
        target_ability=ability,
    )
    interaction = case["interaction"]
    assert interaction["status"] == "resolved"
    assert interaction["outcome"] == "post_hit_target_eat_item_dispatched"
    assert interaction["target_ability_interaction"] == "applies"
    assert interaction["ability_consequence_materialization"] == "deferred"

    readiness = assess_fling_berry_target_eat_item_consequence_readiness(interaction)
    assert readiness["status"] == "incomplete"
    assert readiness["readiness"] == "incomplete_due_to_deferred_direct_target_hook"
    assert readiness["reason"] == "fling_berry_direct_target_eat_item_consequence_deferred"

    authority = case["authority"]
    assert authority["status"] == "incomplete"
    assert authority["reason"] == "fling_berry_direct_target_eat_item_consequence_deferred"
    assert authority["target_eat_item_consequence_readiness"] == readiness


def test_direct_hook_gate_applies_to_non_cheri_representative_cure():
    case = berry_cure_case(
        item="rawst-berry",
        condition="burn",
        target_ability="cheek-pouch",
    )
    assert case["interaction"]["status"] == "resolved"
    assert case["authority"]["status"] == "incomplete"
    assert case["authority"]["reason"] == "fling_berry_direct_target_eat_item_consequence_deferred"


def test_neutralizing_gas_plus_direct_hook_remains_incomplete_at_interaction_layer():
    case = berry_cure_case(
        item="cheri-berry",
        condition="paralysis",
        source_ability="neutralizing-gas",
        target_ability="cheek-pouch",
    )
    interaction = case["interaction"]
    assert interaction["status"] == "incomplete"
    assert interaction["reason"] == "fling_berry_target_eat_item_neutralizing_gas_composition_unresolved"
    assert case["authority"]["status"] == "incomplete"
    assert case["authority"]["reason"] == interaction["reason"]


def test_tampered_materialization_cannot_hide_direct_hook():
    case = berry_cure_case(
        item="cheri-berry",
        condition="paralysis",
        target_ability="cheek-pouch",
    )
    forged = deepcopy(case["interaction"])
    forged["ability_consequence_materialization"] = "not_applicable"
    readiness = assess_fling_berry_target_eat_item_consequence_readiness(forged)
    assert readiness["status"] == "rejected"
    assert readiness["reason"] == "fling_berry_target_eat_item_readiness_state_inconsistent"

    authority = freeze_runtime_d0_fling_major_status_cure_berry_target_effect_authority(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        fling_execution_authority=case["execution"],
        source_leaf=case["leaf"],
        berry_eat_item_interaction_authority=forged,
        actor=case["actor"],
        target=case["target"],
    )
    assert authority["status"] == "rejected"


def test_tampered_target_classification_or_ability_binding_rejects():
    case = berry_cure_case(
        item="cheri-berry",
        condition="paralysis",
        target_ability="pressure",
    )
    forged_class = deepcopy(case["interaction"])
    forged_class["target_ability_classification"]["classification"]["direct_target_eat_item_hook"] = True
    assert assess_fling_berry_target_eat_item_consequence_readiness(
        forged_class
    )["status"] == "rejected"

    forged_ability = deepcopy(case["interaction"])
    forged_ability["target_ability_authority"]["ability_id"] = "cheek-pouch"
    assert assess_fling_berry_target_eat_item_consequence_readiness(
        forged_ability
    )["status"] == "rejected"


def test_materializer_rejects_forged_resolved_cure_with_deferred_direct_hook():
    pressure = berry_cure_case(
        item="cheri-berry",
        condition="paralysis",
        target_ability="pressure",
    )
    forged = deepcopy(pressure["authority"])
    direct = berry_cure_case(
        item="cheri-berry",
        condition="paralysis",
        target_ability="cheek-pouch",
    )["interaction"]
    forged["berry_eat_item_interaction_authority"] = direct
    forged["target_eat_item_consequence_readiness"] = {
        "status": "resolved",
        "schema_version": "fling-berry-target-eat-item-consequence-readiness-v1",
        "readiness": "ready",
    }
    assert materialize_detached_fling_major_status_cure_berry_target_effect(
        authority=forged
    )["status"] == "rejected"


def test_cheek_pouch_pair_fails_before_exact_continuation_without_fabricated_healing():
    pair, ledger = _production_fling_pair(
        item="cheri-berry",
        target_ability="cheek-pouch",
        target_condition="paralysis",
    )
    assert pair["status"] == "incomplete"
    assert ledger["status"] != "evaluable"
    serialized = repr(pair)
    assert "heal_amount" not in serialized
    assert "cheek_pouch_heal" not in serialized


def test_pressure_pair_remains_evaluable_and_ateberry_transition_is_unchanged():
    pair, ledger = _production_fling_pair(
        item="cheri-berry",
        target_ability="pressure",
        target_condition="paralysis",
    )
    assert pair["status"] == ledger["status"] == "evaluable"
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    for branch in pair["terminal_branches"]:
        transition = branch["first_action_leaf"]["consequences"][
            "fling_berry_eaten_transition"
        ]
        assert transition["status"] == "resolved"
        assert transition["resulting_state"] == "known_true"


def test_direct_hook_still_preserves_authenticated_ateberry_true_transition():
    case = berry_cure_case(
        item="cheri-berry",
        condition="paralysis",
        target_ability="cheek-pouch",
    )
    assert case["authority"]["status"] == "incomplete"
    transition = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=case["d0"],
        source_leaf=case["leaf"],
        interaction_authority=case["interaction"],
        target=case["target"],
    )
    assert transition["status"] == "resolved"
    assert transition["resulting_state"] == "known_true"


def test_gate_does_not_mutate_runtime_or_d0():
    case = berry_cure_case(
        item="cheri-berry",
        condition="paralysis",
        target_ability="cheek-pouch",
    )
    snapshot_before = deepcopy(case["snapshot"])
    d0_before = deepcopy(case["d0"])
    readiness = assess_fling_berry_target_eat_item_consequence_readiness(
        case["interaction"]
    )
    assert readiness["status"] == "incomplete"
    assert case["snapshot"] == snapshot_before
    assert case["d0"] == d0_before
