from copy import deepcopy

import pytest

from llm.advisor_detached_predictive_intermediate_state import (
    materialize_detached_predictive_intermediate_state,
)
from llm.advisor_detached_target_condition_removal_validation import (
    validate_detached_target_condition_removal,
)
from llm.advisor_runtime_d0_fling_major_status_cure_berry_target_effect_authority import (
    materialize_detached_fling_major_status_cure_berry_target_effect,
)
from tests.fling_status_cure_berry_test_support import berry_cure_case


def _marker(case):
    return materialize_detached_fling_major_status_cure_berry_target_effect(
        authority=case["authority"],
    )["hypothetical_target_condition_removal"]


def test_valid_sparkling_aria_removal_is_still_admitted():
    leaf_id = "sparkling:leaf"
    marker = {
        "schema_version": "detached-hypothetical-target-condition-removal-v1",
        "condition_before": "burn",
        "condition_removed": "burn",
        "condition_after": "none",
        "removal_trigger": "successful_damaging_hit_target_survives",
        "provenance": "sparkling_aria_successful_damage_roll_burn_clearing_v1",
        "source_leaf_id": leaf_id,
    }
    assert validate_detached_target_condition_removal(marker, source_leaf_id=leaf_id)


def test_valid_berry_removal_is_admitted():
    case = berry_cure_case()
    assert validate_detached_target_condition_removal(
        _marker(case),
        source_leaf_id=case["leaf"]["leaf_id"],
        source_leaf=case["leaf"],
        expected_target=case["target"],
    )


def test_generic_known_none_or_cross_family_marker_is_not_admitted():
    case = berry_cure_case()
    generic = {
        "schema_version": "detached-hypothetical-target-condition-removal-v1",
        "condition_before": "paralysis",
        "condition_removed": "paralysis",
        "condition_after": "none",
        "source_leaf_id": case["leaf"]["leaf_id"],
    }
    assert not validate_detached_target_condition_removal(
        generic,
        source_leaf_id=case["leaf"]["leaf_id"],
        expected_target=case["target"],
    )
    sparkling = {
        "schema_version": "detached-hypothetical-target-condition-removal-v1",
        "condition_before": "burn",
        "condition_removed": "burn",
        "condition_after": "none",
        "removal_trigger": "successful_damaging_hit_target_survives",
        "provenance": "sparkling_aria_successful_damage_roll_burn_clearing_v1",
        "source_leaf_id": case["leaf"]["leaf_id"],
    }
    forged = deepcopy(sparkling)
    forged["provenance"] = "fling_major_status_cure_berry_intrinsic_on_eat_v1"
    assert not validate_detached_target_condition_removal(
        forged,
        source_leaf_id=case["leaf"]["leaf_id"],
        expected_target=case["target"],
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("source_berry_item_id", "rawst-berry"),
        ("condition_removed", "burn"),
        ("source_leaf_id", "foreign-leaf"),
        ("source_fling_action_id", "attack:foreign"),
    ),
)
def test_berry_removal_tampering_rejects(field, value):
    case = berry_cure_case()
    marker = _marker(case)
    marker[field] = value
    assert not validate_detached_target_condition_removal(
        marker,
        source_leaf_id=case["leaf"]["leaf_id"],
        source_leaf=case["leaf"],
        expected_target=case["target"],
    )


def test_foreign_target_rejects():
    case = berry_cure_case()
    foreign = deepcopy(case["target"])
    foreign["pokemon_id"] = "foreign"
    assert not validate_detached_target_condition_removal(
        _marker(case),
        source_leaf_id=case["leaf"]["leaf_id"],
        source_leaf=case["leaf"],
        expected_target=foreign,
    )


def test_intermediate_projects_known_none_to_exact_target_only_and_keeps_sources_immutable():
    case = berry_cure_case()
    before_snapshot = deepcopy(case["snapshot"])
    before_d0 = deepcopy(case["d0"])
    terminal = deepcopy(case["leaf"])
    terminal["consequences"]["fling_major_status_cure_berry_target_effect"] = (
        materialize_detached_fling_major_status_cure_berry_target_effect(
            authority=case["authority"],
        )
    )
    intermediate = materialize_detached_predictive_intermediate_state(
        strategy_d0=case["d0"],
        terminal_leaf=terminal,
    )
    assert intermediate["status"] == "resolved"
    cured = intermediate["active"][case["target"]["side"]]["hypothetical_condition"]
    assert cured["status"] == "known_none"
    assert cured["source"] == "exact_terminal_leaf_condition_removal"
    unchanged = intermediate["active"][case["actor"]["side"]]["hypothetical_condition"]
    assert unchanged == case["d0"]["current_condition_authority"][case["actor"]["side"]]["condition"]
    assert case["snapshot"] == before_snapshot
    assert case["d0"] == before_d0


def test_intermediate_rejects_forged_berry_removal_marker():
    case = berry_cure_case()
    terminal = deepcopy(case["leaf"])
    detached = materialize_detached_fling_major_status_cure_berry_target_effect(
        authority=case["authority"],
    )
    detached["hypothetical_target_condition_removal"]["source_leaf_id"] = "foreign"
    terminal["consequences"]["fling_major_status_cure_berry_target_effect"] = detached
    intermediate = materialize_detached_predictive_intermediate_state(
        strategy_d0=case["d0"],
        terminal_leaf=terminal,
    )
    assert intermediate["status"] == "rejected"
    assert intermediate["reason"] == "terminal_leaf_condition_removal_consequence_invalid"
