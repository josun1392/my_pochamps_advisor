from copy import deepcopy

import pytest

from advisor.canonical_fling_type_resist_empty_intrinsic_berry import (
    canonical_fling_type_resist_empty_intrinsic_berry_ids,
)
from llm.advisor_detached_berry_eaten_transition import (
    materialize_detached_fling_berry_eaten_transition,
)
from llm.advisor_runtime_d0_fling_berry_eat_item_interaction_authority import (
    freeze_runtime_d0_fling_berry_eat_item_interaction_authority,
)
from llm.advisor_runtime_d0_fling_type_resist_empty_intrinsic_berry_target_effect_authority import (
    freeze_runtime_d0_fling_type_resist_empty_intrinsic_berry_target_effect_authority,
    materialize_detached_fling_type_resist_empty_intrinsic_berry_target_effect,
)
from tests.test_runtime_d0_fling_berry_eat_item_interaction_authority import (
    _fixture,
    _leaf,
)


FAMILY = canonical_fling_type_resist_empty_intrinsic_berry_ids()


def _case(
    *,
    item="colbur-berry",
    source_ability="pressure",
    target_ability="pressure",
    hit_state="hit",
    damage=20,
    routing="target",
    hp=80,
    ko=False,
):
    state, snapshot, d0, actor, target, execution = _fixture(
        item=item,
        source_ability=source_ability,
        target_ability=target_ability,
    )
    leaf = _leaf(
        d0, actor, target, execution,
        hit_state=hit_state, damage=damage, routing=routing, hp=hp, ko=ko,
    )
    interaction = freeze_runtime_d0_fling_berry_eat_item_interaction_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        fling_execution_authority=execution,
        actor=actor,
        target=target,
        phase="post_hit_target_berry_interaction",
        source_leaf=leaf,
    )
    authority = freeze_runtime_d0_fling_type_resist_empty_intrinsic_berry_target_effect_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        fling_execution_authority=execution,
        source_leaf=leaf,
        berry_eat_item_interaction_authority=interaction,
        actor=actor,
        target=target,
    )
    return {
        "state": state, "snapshot": snapshot, "d0": d0,
        "actor": actor, "target": target, "execution": execution,
        "leaf": leaf, "interaction": interaction, "authority": authority,
    }


@pytest.mark.parametrize("item_id", FAMILY)
def test_all_18_pressure_targets_resolve_no_intrinsic_target_effect(item_id):
    case = _case(item=item_id)
    assert case["interaction"]["status"] == "resolved"
    assert case["interaction"]["target_ability_interaction"] == "not_applicable"
    assert case["interaction"]["ability_consequence_materialization"] == "not_applicable"
    authority = case["authority"]
    assert authority["status"] == "resolved"
    assert authority["outcome"] == "no_intrinsic_target_effect"
    assert authority["target_eat_item_consequence_readiness"]["readiness"] == "ready"

    detached = materialize_detached_fling_type_resist_empty_intrinsic_berry_target_effect(
        authority=authority,
    )
    assert detached["status"] == "resolved"
    assert detached["outcome"] == "no_intrinsic_target_effect"
    assert detached["intrinsic_hp_change"] == 0
    assert detached["intrinsic_major_condition_change"] == "none"
    assert detached["intrinsic_stage_change"] == "none"
    assert detached["intrinsic_item_change"] == "none"
    assert detached["intrinsic_type_change"] == "none"
    assert detached["intrinsic_field_change"] == "none"
    assert detached["intrinsic_action_order_change"] == "none"


@pytest.mark.parametrize("item_id", ["babiri-berry", "chilan-berry", "colbur-berry", "yache-berry"])
def test_representative_family_members_have_explicit_empty_intrinsic_materialization(item_id):
    case = _case(item=item_id)
    detached = materialize_detached_fling_type_resist_empty_intrinsic_berry_target_effect(
        authority=case["authority"],
    )
    assert detached["status"] == "resolved"
    assert detached["item_id"] == item_id
    assert detached["authority"]["berry_family_authority"]["intrinsic_on_eat"] == "empty"


@pytest.mark.parametrize("ability", ["cheek-pouch", "ripen", "cud-chew"])
def test_direct_target_eat_item_hooks_fail_closed_without_materializing_ability_effect(ability):
    case = _case(target_ability=ability)
    interaction = case["interaction"]
    assert interaction["status"] == "resolved"
    assert interaction["target_ability_interaction"] == "applies"
    assert interaction["ability_consequence_materialization"] == "deferred"
    authority = case["authority"]
    assert authority["status"] == "incomplete"
    assert authority["reason"] == "fling_berry_direct_target_eat_item_consequence_deferred"
    assert "heal_amount" not in repr(authority)


def test_neutralizing_gas_direct_hook_composition_remains_incomplete():
    case = _case(source_ability="neutralizing-gas", target_ability="cheek-pouch")
    assert case["interaction"]["status"] == "incomplete"
    assert case["interaction"]["reason"] == (
        "fling_berry_target_eat_item_neutralizing_gas_composition_unresolved"
    )
    assert case["authority"]["status"] == "incomplete"
    assert case["authority"]["reason"] == case["interaction"]["reason"]


def test_unnerve_try_eat_only_hook_remains_bypassed_for_direct_fling_eat():
    case = _case(source_ability="unnerve", target_ability="pressure")
    assert case["interaction"]["status"] == "resolved"
    assert case["interaction"]["opposing_try_eat_blocker_bypassed"] is True
    assert case["authority"]["status"] == "resolved"
    assert case["authority"]["outcome"] == "no_intrinsic_target_effect"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"hit_state": "miss"},
        {"damage": 0},
        {"routing": "substitute"},
        {"hp": 0, "ko": True},
    ],
)
def test_no_eat_boundaries_do_not_materialize_intrinsic_effect_or_ateberry_transition(kwargs):
    case = _case(**kwargs)
    assert case["interaction"]["status"] == "resolved"
    assert case["interaction"]["outcome"] == "post_hit_target_eat_not_reached"
    assert case["authority"]["status"] == "resolved"
    assert case["authority"]["outcome"] == "not_applicable"
    assert materialize_detached_fling_type_resist_empty_intrinsic_berry_target_effect(
        authority=case["authority"],
    )["status"] == "rejected"
    transition = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=case["d0"],
        source_leaf=case["leaf"],
        interaction_authority=case["interaction"],
        target=case["target"],
    )
    assert transition["status"] == "not_applicable"


def test_successful_eat_unknown_prior_becomes_known_true_without_runtime_mutation():
    case = _case(item="colbur-berry")
    snapshot_before = deepcopy(case["snapshot"])
    d0_before = deepcopy(case["d0"])
    transition = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=case["d0"],
        source_leaf=case["leaf"],
        interaction_authority=case["interaction"],
        target=case["target"],
    )
    assert transition["status"] == "resolved"
    assert transition["prior_state"] == "unknown"
    assert transition["resulting_state"] == "known_true"
    assert case["snapshot"] == snapshot_before
    assert case["d0"] == d0_before


def test_successful_eat_known_false_becomes_true_and_known_true_is_idempotent():
    false_case = _case(item="chilan-berry")
    false_case["d0"]["current_berry_eaten_authority"]["opponent"] = {
        "status": "resolved",
        "schema_version": "runtime-d0-current-berry-eaten-authority-v1",
        "session_id": false_case["d0"]["session_id"],
        "source_runtime_fingerprint": false_case["d0"]["source_runtime_fingerprint"],
        "source_branch_fingerprint": false_case["d0"]["strategy_preview_fingerprint"],
        "owner": deepcopy(false_case["target"]),
        "state": "known_false",
        "value": False,
        "state_provenance": {"basis": "fresh_battle_initialization"},
    }
    false_transition = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=false_case["d0"],
        source_leaf=false_case["leaf"],
        interaction_authority=false_case["interaction"],
        target=false_case["target"],
    )
    assert false_transition["status"] == "resolved"
    assert false_transition["prior_state"] == "known_false"
    assert false_transition["resulting_state"] == "known_true"
    assert false_transition["transition"] == "to_true"

    true_case = _case(item="yache-berry")
    true_case["d0"]["current_berry_eaten_authority"]["opponent"] = {
        "status": "resolved",
        "schema_version": "runtime-d0-current-berry-eaten-authority-v1",
        "session_id": true_case["d0"]["session_id"],
        "source_runtime_fingerprint": true_case["d0"]["source_runtime_fingerprint"],
        "source_branch_fingerprint": true_case["d0"]["strategy_preview_fingerprint"],
        "owner": deepcopy(true_case["target"]),
        "state": "known_true",
        "value": True,
        "state_provenance": {"basis": "observed_berry_consumption"},
    }
    true_transition = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=true_case["d0"],
        source_leaf=true_case["leaf"],
        interaction_authority=true_case["interaction"],
        target=true_case["target"],
    )
    assert true_transition["status"] == "resolved"
    assert true_transition["prior_state"] == "known_true"
    assert true_transition["resulting_state"] == "known_true"
    assert true_transition["transition"] == "true_to_true"


def test_target_effect_rejects_forged_family_and_interaction_bindings():
    case = _case(item="colbur-berry")
    forged_execution = deepcopy(case["execution"])
    forged_execution["fling_type_resist_empty_intrinsic_berry_authority"] = deepcopy(
        case["execution"]["fling_type_resist_empty_intrinsic_berry_authority"]
    )
    forged_execution["fling_type_resist_empty_intrinsic_berry_authority"]["item_id"] = "chilan-berry"
    rejected = freeze_runtime_d0_fling_type_resist_empty_intrinsic_berry_target_effect_authority(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        fling_execution_authority=forged_execution,
        source_leaf=case["leaf"],
        berry_eat_item_interaction_authority=case["interaction"],
        actor=case["actor"],
        target=case["target"],
    )
    assert rejected["status"] == "rejected"

    forged_interaction = deepcopy(case["interaction"])
    forged_interaction["target"] = deepcopy(case["actor"])
    rejected = freeze_runtime_d0_fling_type_resist_empty_intrinsic_berry_target_effect_authority(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        fling_execution_authority=case["execution"],
        source_leaf=case["leaf"],
        berry_eat_item_interaction_authority=forged_interaction,
        actor=case["actor"],
        target=case["target"],
    )
    assert rejected["status"] == "rejected"
