from copy import deepcopy
from fractions import Fraction

import pytest

from llm.advisor_detached_predictive_intermediate_state import (
    materialize_detached_predictive_intermediate_state,
)
from llm.advisor_runtime_d0_standard_charge_terminal_mechanics_authority import (
    freeze_runtime_d0_standard_charge_terminal_mechanics_authority,
)
from llm.advisor_runtime_d0_standard_charge_power_herb_skip_execution import (
    execute_runtime_d0_standard_charge_power_herb_skip,
    freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority,
    materialize_detached_standard_charge_power_herb_consumption_authority,
    materialize_runtime_d0_standard_charge_power_herb_terminal_execution_contract,
    validate_detached_standard_charge_power_herb_consumption_authority,
    validate_runtime_d0_standard_charge_power_herb_skip_execution_authority,
)
from llm.advisor_standard_charge_terminal_execution import (
    POWER_HERB_CURRENT_TURN_SKIP_MODE,
    execute_standard_charge_terminal_attack,
    validate_standard_charge_terminal_execution_contract,
)
from tests.test_detached_intermediate_predictive_authority import _owner
from tests.test_runtime_d0_standard_charge_terminal_mechanics_authority import (
    _ready,
    _refresh,
)
from tests.test_standard_charge_start_immediate_pair_integration import _own_action


SUPPORTED = ("sky-attack", "razor-wind", "freeze-shock", "ice-burn")


def _case(move_id="sky-attack"):
    state, _snapshot0, _d00 = _ready()
    state["self_side"]["pokemon"][0]["known_item"] = "power-herb"
    target_raw = state["opponent_side"]["pokemon"][0]
    target_raw["known_item"] = None
    target_raw["known_item_provenance"] = {
        "event_kind": "current_item_observed",
        "trust": "user_confirmed_observation",
        "turn_number": 1,
        "status": "known_absent",
    }
    snapshot, d0 = _refresh(state)
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = _own_action(d0, actor, move_id)
    terminal = freeze_runtime_d0_standard_charge_terminal_mechanics_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        move_metadata={"move_id": move_id},
    )
    assert terminal["status"] == "resolved", {
        "reason": terminal.get("reason"),
        "actor_missing": terminal.get("actor_participant_mechanics_authority", {}).get("missing_authority"),
        "target_missing": terminal.get("target_participant_mechanics_authority", {}).get("missing_authority"),
        "actor_item": terminal.get("actor_participant_mechanics_authority", {}).get("item"),
        "target_item": terminal.get("target_participant_mechanics_authority", {}).get("item"),
    }
    authority = freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        move_metadata={"move_id": move_id},
    )
    return state, snapshot, d0, actor, target, action, authority


@pytest.mark.parametrize("move_id", SUPPORTED)
def test_power_herb_same_turn_authority_contract_and_kernel_are_exact(move_id):
    _state0, snapshot, d0, actor, target, action, authority = _case(move_id)
    assert authority["status"] == "resolved", authority
    assert authority["execution_mode"] == POWER_HERB_CURRENT_TURN_SKIP_MODE
    assert authority["execution_grant"] == "authenticated_power_herb_current_turn_skip_only"
    assert authority["readiness_authority"]["outcome"] == "power_herb_charge_skip_ready"
    assert authority["terminal_mechanics_authority"]["mechanics_only"] is True
    assert authority["terminal_mechanics_authority"]["execution_grant"] is False
    assert validate_runtime_d0_standard_charge_power_herb_skip_execution_authority(
        authority=authority,
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        move_metadata={"move_id": move_id},
    ) is None

    consumption = materialize_detached_standard_charge_power_herb_consumption_authority(
        execution_authority=authority,
    )
    assert consumption["status"] == "resolved"
    assert consumption["item_before"] == "power-herb"
    assert consumption["item_after"] == {"status": "known_absent", "value": None}
    assert consumption["phase"] == "after_pre_action_gate_before_accuracy"
    assert validate_detached_standard_charge_power_herb_consumption_authority(
        authority=consumption,
        execution_authority=authority,
    ) is None

    contract = materialize_runtime_d0_standard_charge_power_herb_terminal_execution_contract(
        execution_authority=authority,
    )
    assert contract["status"] == "resolved", contract
    assert contract["execution_mode"] == POWER_HERB_CURRENT_TURN_SKIP_MODE
    assert contract["power_herb_consumption_authority"] == consumption
    assert validate_standard_charge_terminal_execution_contract(contract) is None

    kernel = execute_runtime_d0_standard_charge_power_herb_skip(
        execution_authority=authority,
    )
    assert kernel["status"] == "resolved", kernel
    assert kernel == execute_standard_charge_terminal_attack(execution_contract=contract)
    assert kernel["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert sum(
        (
            Fraction(leaf["probability"]["numerator"], leaf["probability"]["denominator"])
            for leaf in kernel["terminal_leaves"]
        ),
        Fraction(),
    ) == Fraction(1, 1)
    executing = [
        leaf for leaf in kernel["terminal_leaves"]
        if not leaf["consequences"].get("selected_move_does_not_execute")
        and not leaf["consequences"].get("execution_failure")
    ]
    assert executing
    assert all(
        leaf["consequences"]["power_herb_consumption"] == consumption
        and leaf["consequences"]["actor_item_after"] == {"status": "known_absent", "value": None}
        for leaf in executing
    )


def test_power_herb_is_not_consumed_when_pre_action_gate_cancels_move():
    state, _snapshot0, _d00 = _ready()
    state["self_side"]["pokemon"][0]["known_item"] = "power-herb"
    state["self_side"]["pokemon"][0]["current_hp"] = 0
    state["self_side"]["pokemon"][0]["fainted"] = True
    snapshot, d0 = _refresh(state)
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = _own_action(d0, actor, "sky-attack")
    authority = freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        move_metadata={"move_id": "sky-attack"},
    )
    assert authority["status"] == "resolved", authority
    kernel = execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    assert kernel["status"] == "resolved", kernel
    assert kernel["pre_action_gate"]["reason"] == "fainted_actor"
    leaf = kernel["terminal_leaves"][0]
    assert "power_herb_consumption" not in leaf["consequences"]
    assert "actor_item_after" not in leaf["consequences"]


def test_power_herb_paralysis_cancel_branch_keeps_item_and_execution_branch_consumes():
    state, _snapshot0, _d00 = _ready()
    pokemon = state["self_side"]["pokemon"][0]
    pokemon["known_item"] = "power-herb"
    pokemon["condition"] = "paralysis"
    pokemon["condition_provenance"] = {
        "event_kind": "current_condition_observed",
        "trust": "user_confirmed_observation",
        "condition": "paralysis",
        "turn_number": 1,
    }
    snapshot, d0 = _refresh(state)
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = _own_action(d0, actor, "sky-attack")
    authority = freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        move_metadata={"move_id": "sky-attack"},
    )
    assert authority["status"] == "resolved", authority
    kernel = execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    assert kernel["status"] == "resolved", kernel
    cancelled = [
        leaf for leaf in kernel["terminal_leaves"]
        if leaf["consequences"].get("execution_failure") == "cancelled_due_to_paralysis"
    ]
    executed = [
        leaf for leaf in kernel["terminal_leaves"]
        if leaf["consequences"].get("execution_failure") is None
    ]
    assert cancelled and executed
    assert all("power_herb_consumption" not in leaf["consequences"] for leaf in cancelled)
    assert all("power_herb_consumption" in leaf["consequences"] for leaf in executed)


def test_power_herb_execution_tampering_fails_closed():
    _state0, snapshot, d0, actor, target, action, authority = _case("sky-attack")
    assert authority["status"] == "resolved", authority
    for key in (
        "session_id",
        "source_runtime_fingerprint",
        "source_branch_fingerprint",
        "decision_owner",
        "actor",
        "target",
        "action_id",
        "move_id",
        "canonical_terminal_effect",
        "readiness_authority",
        "held_item_effect_applicability_authority",
        "terminal_mechanics_authority",
        "execution_mode",
    ):
        forged = deepcopy(authority)
        forged[key] = {"tampered": True}
        assert execute_runtime_d0_standard_charge_power_herb_skip(
            execution_authority=forged,
        )["status"] == "rejected", key

    assert validate_runtime_d0_standard_charge_power_herb_skip_execution_authority(
        authority={**deepcopy(authority), "move_id": "ice-burn"},
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
        move_metadata={"move_id": "sky-attack"},
    ) is not None


def test_power_herb_terminal_leaf_transports_itemless_state_to_intermediate_projection():
    _state0, _snapshot, d0, _actor, _target, _action, authority = _case("razor-wind")
    kernel = execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    leaf = next(
        leaf for leaf in kernel["terminal_leaves"]
        if "power_herb_consumption" in leaf["consequences"]
    )
    state = materialize_detached_predictive_intermediate_state(
        strategy_d0=d0,
        terminal_leaf=leaf,
    )
    assert state["status"] == "resolved", state
    actor_state = state["active"]["self"]
    assert actor_state["hypothetical_item"]["status"] == "known_absent"
    assert actor_state["hypothetical_item"]["value"] is None
    assert actor_state["hypothetical_item"]["source"] == "exact_terminal_leaf_power_herb_consumption"
