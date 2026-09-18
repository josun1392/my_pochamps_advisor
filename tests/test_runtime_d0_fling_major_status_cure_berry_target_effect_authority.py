from copy import deepcopy

import pytest

from llm.advisor_runtime_d0_fling_major_status_cure_berry_target_effect_authority import (
    freeze_runtime_d0_fling_major_status_cure_berry_target_effect_authority,
    materialize_detached_fling_major_status_cure_berry_target_effect,
)
from tests.fling_status_cure_berry_test_support import berry_cure_case


@pytest.mark.parametrize(
    ("item", "condition"),
    (
        ("cheri-berry", "paralysis"),
        ("chesto-berry", "sleep"),
        ("aspear-berry", "freeze"),
        ("rawst-berry", "burn"),
        ("pecha-berry", "poison"),
        ("pecha-berry", "toxic"),
    ),
)
def test_matching_condition_cures_exact_original_condition(item, condition):
    case = berry_cure_case(item=item, condition=condition)
    authority = case["authority"]
    assert case["execution"]["status"] == "resolved"
    assert case["interaction"]["outcome"] == "post_hit_target_eat_item_dispatched"
    assert authority["status"] == "resolved"
    assert authority["outcome"] == "applied_major_status_cure"
    assert authority["condition_before"] == condition
    assert authority["condition_after"] == "none"
    detached = materialize_detached_fling_major_status_cure_berry_target_effect(
        authority=authority,
    )
    marker = detached["hypothetical_target_condition_removal"]
    assert marker["condition_before"] == condition
    assert marker["condition_removed"] == condition
    assert marker["condition_after"] == "none"
    assert marker["source_berry_item_id"] == item
    assert marker["source_fling_action_id"] == case["execution"]["action_id"]
    assert marker["source_leaf_id"] == case["leaf"]["leaf_id"]


def test_nonmatching_and_healthy_are_exact_no_transition():
    nonmatching = berry_cure_case(item="cheri-berry", condition="burn")["authority"]
    assert nonmatching["outcome"] == "no_transition_nonmatching_condition"
    assert nonmatching["condition_before"] == nonmatching["condition_after"] == "burn"
    assert "hypothetical_target_condition_removal" not in (
        materialize_detached_fling_major_status_cure_berry_target_effect(
            authority=nonmatching,
        )
    )

    healthy = berry_cure_case(item="cheri-berry", condition="none")["authority"]
    assert healthy["outcome"] == "no_transition_healthy"
    assert healthy["condition_before"] == healthy["condition_after"] == "none"
    assert "hypothetical_target_condition_removal" not in (
        materialize_detached_fling_major_status_cure_berry_target_effect(
            authority=healthy,
        )
    )


def test_unknown_current_condition_fails_closed():
    authority = berry_cure_case(unknown_condition=True)["authority"]
    assert authority["status"] == "incomplete"
    assert authority["reason"] == "fling_status_cure_berry_target_condition_unknown"


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    (
        ({"hit_state": "miss"}, "fling_miss_or_pre_execution_cancellation"),
        ({"damage": 0}, "fling_protect_or_immunity_or_no_damage"),
        ({"routing": "substitute"}, "fling_target_effect_substitute_or_non_target_route"),
        ({"hp": 0, "ko": True}, "fling_target_fainted_before_effect"),
    ),
)
def test_no_target_eat_boundary_materializes_no_cure(kwargs, reason):
    case = berry_cure_case(**kwargs)
    assert case["interaction"]["outcome"] == "post_hit_target_eat_not_reached"
    assert case["interaction"]["reason"] == reason
    assert case["authority"]["status"] == "resolved"
    assert case["authority"]["outcome"] == "not_applicable"
    detached = materialize_detached_fling_major_status_cure_berry_target_effect(
        authority=case["authority"],
    )
    assert "hypothetical_target_condition_removal" not in detached


@pytest.mark.parametrize("field", ("target_eat_occurred", "target_eat_item_dispatched"))
def test_exact_eat_and_eat_item_dispatch_are_required(field):
    case = berry_cure_case()
    interaction = deepcopy(case["interaction"])
    interaction[field] = False
    authority = freeze_runtime_d0_fling_major_status_cure_berry_target_effect_authority(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        fling_execution_authority=case["execution"],
        source_leaf=case["leaf"],
        berry_eat_item_interaction_authority=interaction,
        actor=case["actor"],
        target=case["target"],
    )
    assert authority["status"] == "rejected"


def test_unresolved_eat_item_ability_composition_fails_closed():
    case = berry_cure_case(
        source_ability="neutralizing-gas",
        target_ability="cheek-pouch",
    )
    assert case["interaction"]["status"] == "incomplete"
    assert case["authority"]["status"] == "incomplete"
    assert case["authority"]["reason"] == "fling_berry_target_eat_item_neutralizing_gas_composition_unresolved"


def test_stale_foreign_leaf_action_owner_and_item_evidence_rejects():
    case = berry_cure_case()

    stale = deepcopy(case["snapshot"])
    stale["state_fingerprint"] = "stale"
    result = freeze_runtime_d0_fling_major_status_cure_berry_target_effect_authority(
        strategy_d0=case["d0"],
        runtime_snapshot=stale,
        fling_execution_authority=case["execution"],
        source_leaf=case["leaf"],
        berry_eat_item_interaction_authority=case["interaction"],
        actor=case["actor"],
        target=case["target"],
    )
    assert result["status"] == "rejected"

    forged_leaf = deepcopy(case["leaf"])
    forged_leaf["leaf_id"] = "foreign"
    result = freeze_runtime_d0_fling_major_status_cure_berry_target_effect_authority(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        fling_execution_authority=case["execution"],
        source_leaf=forged_leaf,
        berry_eat_item_interaction_authority=case["interaction"],
        actor=case["actor"],
        target=case["target"],
    )
    assert result["status"] == "rejected"

    forged_execution = deepcopy(case["execution"])
    forged_execution["action_id"] = "attack:foreign"
    result = freeze_runtime_d0_fling_major_status_cure_berry_target_effect_authority(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        fling_execution_authority=forged_execution,
        source_leaf=case["leaf"],
        berry_eat_item_interaction_authority=case["interaction"],
        actor=case["actor"],
        target=case["target"],
    )
    assert result["status"] == "rejected"

    result = freeze_runtime_d0_fling_major_status_cure_berry_target_effect_authority(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        fling_execution_authority=case["execution"],
        source_leaf=case["leaf"],
        berry_eat_item_interaction_authority=case["interaction"],
        actor=case["target"],
        target=case["actor"],
    )
    assert result["status"] == "rejected"

    forged_execution = deepcopy(case["execution"])
    forged_execution["user_item_before"]["value"] = "rawst-berry"
    result = freeze_runtime_d0_fling_major_status_cure_berry_target_effect_authority(
        strategy_d0=case["d0"],
        runtime_snapshot=case["snapshot"],
        fling_execution_authority=forged_execution,
        source_leaf=case["leaf"],
        berry_eat_item_interaction_authority=case["interaction"],
        actor=case["actor"],
        target=case["target"],
    )
    assert result["status"] == "rejected"


def test_runtime_and_source_d0_remain_immutable():
    case = berry_cure_case()
    before_snapshot = deepcopy(case["snapshot"])
    before_d0 = deepcopy(case["d0"])
    materialize_detached_fling_major_status_cure_berry_target_effect(
        authority=case["authority"],
    )
    assert case["snapshot"] == before_snapshot
    assert case["d0"] == before_d0
