from copy import deepcopy

from llm.advisor_detached_berry_eaten_transition import (
    materialize_detached_fling_berry_eaten_transition,
    validate_detached_berry_eaten_transition,
)
from llm.advisor_exact_immediate_action_pair_outcome_ledger import (
    normalize_exact_immediate_action_pair_outcome_ledger,
)
from tests.fling_status_cure_berry_test_support import berry_cure_case
from tests.test_runtime_d0_fling_item_execution_authority import _production_fling_pair


def test_authenticated_fling_target_eat_materializes_exact_true_transition():
    case = berry_cure_case(item="cheri-berry", condition="paralysis")
    transition = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=case["d0"], source_leaf=case["leaf"],
        interaction_authority=case["interaction"], target=case["target"],
    )
    assert transition["status"] == "resolved"
    assert transition["owner"] == case["target"]
    assert transition["prior_state"] == "unknown"
    assert transition["resulting_state"] == "known_true"
    assert transition["source_berry_item_id"] == "cheri-berry"
    assert validate_detached_berry_eaten_transition(
        transition, leaf=case["leaf"], target=case["target"]
    )


def test_miss_no_damage_substitute_and_ko_do_not_materialize_transition():
    cases = [
        berry_cure_case(hit_state="miss"),
        berry_cure_case(damage=0),
        berry_cure_case(routing="substitute"),
        berry_cure_case(hp=0, ko=True),
    ]
    for case in cases:
        transition = materialize_detached_fling_berry_eaten_transition(
            strategy_d0=case["d0"], source_leaf=case["leaf"],
            interaction_authority=case["interaction"], target=case["target"],
        )
        assert transition["status"] == "not_applicable"


def test_true_to_true_is_idempotent():
    case = berry_cure_case(item="pecha-berry", condition="poison")
    case["d0"]["current_berry_eaten_authority"]["opponent"] = {
        "status": "resolved",
        "schema_version": "runtime-d0-current-berry-eaten-authority-v1",
        "session_id": case["d0"]["session_id"],
        "source_runtime_fingerprint": case["d0"]["source_runtime_fingerprint"],
        "source_branch_fingerprint": case["d0"]["strategy_preview_fingerprint"],
        "state": "known_true",
        "value": True,
        "owner": deepcopy(case["target"]),
    }
    transition = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=case["d0"], source_leaf=case["leaf"],
        interaction_authority=case["interaction"], target=case["target"],
    )
    assert transition["status"] == "resolved"
    assert transition["prior_state"] == "known_true"
    assert transition["resulting_state"] == "known_true"
    assert transition["transition"] == "true_to_true"


def test_supported_status_cure_fling_pair_and_ledger_retain_transition():
    pair, ledger = _production_fling_pair(item="cheri-berry", target_condition="paralysis")
    assert pair["status"] == ledger["status"] == "evaluable"
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    for branch in pair["terminal_branches"]:
        leaf = branch["first_action_leaf"]
        transition = leaf["consequences"]["fling_berry_eaten_transition"]
        assert transition["owner"] == leaf["provenance"]["target"]
        assert transition["resulting_state"] == "known_true"
        assert transition["source_action_id"] == "attack:fling"
        assert transition["source_leaf_id"] == leaf["leaf_id"]


def test_exact_pair_ledger_rejects_forged_berry_eaten_owner_item_action_and_leaf():
    pair, _ledger = _production_fling_pair(item="cheri-berry", target_condition="paralysis")
    for field, value in (
        ("owner", pair["own_actor"]),
        ("prior_state", "known_false"),
        ("source_berry_item_id", "pecha-berry"),
        ("source_action_id", "attack:foreign"),
        ("source_leaf_id", "foreign-leaf"),
    ):
        forged = deepcopy(pair)
        branch = deepcopy(forged["terminal_branches"][0])
        transition = branch["first_action_leaf"]["consequences"]["fling_berry_eaten_transition"]
        transition[field] = deepcopy(value)
        forged["terminal_branches"] = (branch, *forged["terminal_branches"][1:])
        assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"
