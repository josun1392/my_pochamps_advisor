from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from llm.advisor_current_action_paralysis_opportunity_authority import (
    materialize_current_action_paralysis_opportunity_authority,
    validate_current_action_paralysis_opportunity_authority,
)
from llm.advisor_detached_observed_rng_reconciliation import (
    link_direct_damage_observation_to_predictive_action,
    materialize_historical_predictive_action_binding,
    reconcile_observed_action_opportunity_rng,
)
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    EXECUTED_MOVE_SOURCE,
    PREVIOUS_ACTION_RESULT_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_observed_scalar_attack_rng_reconciliation import _ledger as _scalar_ledger


def _fixture(*, condition="paralysis", trusted=True, session="paralysis-c5", move="shadow-ball"):
    state = create_unknown_bootstrap_battle_state(session, "attacker", "target")["state"]
    actor_raw = state["self_side"]["pokemon"][0]
    target_raw = state["opponent_side"]["pokemon"][0]
    actor_raw["current_hp"] = actor_raw["max_hp"] = 100
    target_raw["current_hp"] = target_raw["max_hp"] = 100
    if condition == "unknown":
        actor_raw["condition"] = None
        actor_raw["condition_provenance"] = None
    else:
        actor_raw["condition"] = None if condition == "none" else condition
        actor_raw["condition_provenance"] = {
            "event_kind": "current_condition_observed",
            "trust": "user_confirmed_observation" if trusted else "legacy",
            "condition": condition,
            "turn_number": 1,
        }
    manager = BattleObservationRuntimeSessionManager.create(session, state)["manager"]
    snapshot = manager.capture_runtime_state_snapshot(session)
    actor = {"session_id": session, "side": "self", "slot_index": 0, "pokemon_id": "attacker"}
    target = {"session_id": session, "side": "opponent", "slot_index": 0, "pokemon_id": "target"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=actor)
    assert d0["status"] == "resolved"

    bindings = {
        "session_id": session,
        "source_runtime_fingerprint": snapshot["state_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(actor),
        "attacker": deepcopy(actor),
        "target": deepcopy(target),
        "move_id": move,
    }
    ledger = deepcopy(_scalar_ledger(move=move, critical=False))
    ledger["bindings"] = deepcopy(bindings)
    for leaf in ledger["terminal_leaves"]:
        leaf["provenance"] = deepcopy(bindings)
    assert ledger["status"] == "evaluable", ledger
    binding = materialize_historical_predictive_action_binding(
        predictive_ledger=ledger, turn_number=1,
    )
    assert binding["status"] == "resolved"
    authority = materialize_current_action_paralysis_opportunity_authority(
        predictive_binding=binding,
        predictive_ledger=ledger,
        runtime_snapshot=snapshot,
    )
    return manager, snapshot, d0, ledger, binding, authority


def _observations(binding, *result_classes):
    boundary = LifecycleConfirmationBoundary(
        binding["session_id"],
        {"self": deepcopy(binding["actor"]), "opponent": deepcopy(binding["target"])},
    )
    execution = boundary.confirm(
        event_kind="executed_move_observed",
        payload={"move_id": binding["move_id"], "source_action_id": binding["source_action_id"]},
        session_id=binding["session_id"],
        source=EXECUTED_MOVE_SOURCE,
        trust=USER_TRUST,
        confirmed=True,
        side=binding["actor"]["side"],
        slot_index=binding["actor"]["slot_index"],
        pokemon_id=binding["actor"]["pokemon_id"],
        observation_id="execution",
        turn_number=binding["turn_number"],
    )["observation"]
    execution["observation_sequence"] = 1
    results = []
    for index, result_class in enumerate(result_classes, start=2):
        row = boundary.confirm(
            event_kind="previous_action_result_observed",
            payload={
                "previous_action_id": binding["source_action_id"],
                "selected_move_id": binding["move_id"],
                "execution_move_id": binding["move_id"],
                "result_class": result_class,
            },
            session_id=binding["session_id"],
            source=PREVIOUS_ACTION_RESULT_SOURCE,
            trust=USER_TRUST,
            confirmed=True,
            side=binding["actor"]["side"],
            slot_index=binding["actor"]["slot_index"],
            pokemon_id=binding["actor"]["pokemon_id"],
            observation_id=f"result-{index}",
            turn_number=binding["turn_number"],
            related_observation_id=execution["observation_id"],
        )["observation"]
        row["observation_sequence"] = index
        results.append(row)
    return execution, results


def _linked_damage(ledger, binding, execution, *, amount=9, sequence=3):
    def owner(row):
        return {**deepcopy(row), "source": "ui_observed_damage_confirmation", "trust": "user_confirmed_observation"}
    raw = {
        "event_kind": "direct_move_damage_observed",
        "session_id": binding["session_id"],
        "turn_number": binding["turn_number"],
        "attacker": owner(binding["actor"]),
        "defender": owner(binding["target"]),
        "move_id": None,
        "move_slot": None,
        "source_action_id": None,
        "damage_amount": amount,
        "hp_unit": "exact",
        "source": "ui_observed_damage_confirmation",
        "trust": "user_confirmed_observation",
        "observed": True,
        "confirmed": True,
        "observation_id": "damage",
        "observation_sequence": sequence,
        "reconciliation_eligible": False,
    }
    linked = link_direct_damage_observation_to_predictive_action(
        observation=raw,
        predictive_binding=binding,
        predictive_ledger=ledger,
        executed_move_observation=execution,
    )
    assert linked.get("reconciliation_eligible") is True
    return linked


def test_predictive_authority_exact_branches_identity_and_mass():
    _manager, _snapshot, d0, _ledger, binding, authority = _fixture()
    assert authority["status"] == "resolved"
    assert authority["source_action_id"] == binding["source_action_id"]
    assert authority["source_runtime_fingerprint"] == d0["source_runtime_fingerprint"]
    assert authority["source_branch_fingerprint"] == d0["strategy_preview_fingerprint"]
    assert authority["decision_owner"] == d0["decision_owner"]
    assert authority["root_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert authority["branches"] == (
        {
            "branch_id": f"{binding['source_action_id']}:paralysis:fully_paralyzed",
            "state": "cancelled_due_to_paralysis",
            "kind": "fully_paralyzed",
            "executes": False,
            "probability": {"numerator": 1, "denominator": 8},
            "source_action_id": binding["source_action_id"],
            "move_id": binding["move_id"],
            "actor": binding["actor"],
            "prediction_kind": "action_opportunity_execution",
        },
        {
            "branch_id": f"{binding['source_action_id']}:paralysis:executes",
            "state": "executed",
            "kind": "executes",
            "executes": True,
            "probability": {"numerator": 7, "denominator": 8},
            "source_action_id": binding["source_action_id"],
            "move_id": binding["move_id"],
            "actor": binding["actor"],
            "prediction_kind": "action_opportunity_execution",
        },
    )
    assert validate_current_action_paralysis_opportunity_authority(
        authority=authority, predictive_binding=binding, predictive_ledger=_ledger,
    )["status"] == "resolved"


@pytest.mark.parametrize("condition", ["none", "burn", "poison", "toxic", "sleep", "freeze"])
def test_known_non_paralysis_is_not_applicable(condition):
    *_prefix, authority = _fixture(condition=condition)
    assert authority["status"] == "not_applicable"
    assert authority["reason"] == "actor_not_currently_paralyzed"


def test_unknown_condition_remains_incomplete():
    *_prefix, authority = _fixture(condition="unknown")
    assert authority["status"] == "incomplete"
    assert authority["reason"] == "current_condition_unknown"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda binding: binding.update(source_action_id="foreign"),
        lambda binding: binding.update(turn_number=9),
        lambda binding: binding["actor"].update(pokemon_id="foreign"),
        lambda binding: binding.update(move_id="tackle"),
        lambda binding: binding.update(source_runtime_fingerprint="stale"),
        lambda binding: binding.update(source_branch_fingerprint="foreign"),
        lambda binding: binding.update(decision_owner={**binding["decision_owner"], "pokemon_id": "foreign"}),
    ],
)
def test_predictive_authority_rejects_mismatched_historical_binding(mutation):
    _manager, snapshot, _d0, ledger, binding, _authority = _fixture()
    forged = deepcopy(binding)
    mutation(forged)
    result = materialize_current_action_paralysis_opportunity_authority(
        predictive_binding=forged, predictive_ledger=ledger, runtime_snapshot=snapshot,
    )
    assert result["status"] == "rejected"


def test_full_paralysis_reconciles_to_original_one_eighth_without_renormalization():
    _manager, _snapshot, _d0, ledger, binding, authority = _fixture()
    execution, results = _observations(binding, "full_paralysis")
    before = deepcopy((authority, binding, ledger, execution, results))
    result = reconcile_observed_action_opportunity_rng(
        predictive_authority=authority,
        predictive_binding=binding,
        predictive_ledger=ledger,
        executed_move_observation=execution,
        previous_action_result_observation=results[0],
    )
    assert result["status"] == "resolved"
    assert result["match_outcome"] == "uniquely_matched"
    assert result["compatible_branch_ids"] == (f"{binding['source_action_id']}:paralysis:fully_paralyzed",)
    assert result["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 8}
    assert result["probability_normalization"] == "none_preserve_original_mass"
    assert result["source_prediction_kind"] == "action_opportunity_execution"
    assert (authority, binding, ledger, execution, results) == before


def test_executed_move_alone_and_generic_success_are_not_execution_proof():
    _manager, _snapshot, _d0, ledger, binding, authority = _fixture()
    execution, _ = _observations(binding)
    result = reconcile_observed_action_opportunity_rng(
        predictive_authority=authority, predictive_binding=binding, predictive_ledger=ledger,
        executed_move_observation=execution,
    )
    assert result["status"] == "incomplete"
    assert result["reason"] == "insufficient_observation"
    assert result["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert len(result["compatible_branch_ids"]) == 2

    execution, rows = _observations(binding, "success")
    success = reconcile_observed_action_opportunity_rng(
        predictive_authority=authority, predictive_binding=binding, predictive_ledger=ledger,
        executed_move_observation=execution, previous_action_result_observation=rows[0],
    )
    assert success["status"] == "incomplete"
    assert success["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 1}


def test_accuracy_miss_and_linked_direct_damage_prove_execution_with_original_seven_eighths():
    _manager, _snapshot, _d0, ledger, binding, authority = _fixture()
    execution, rows = _observations(binding, "accuracy_miss")
    miss = reconcile_observed_action_opportunity_rng(
        predictive_authority=authority, predictive_binding=binding, predictive_ledger=ledger,
        executed_move_observation=execution, previous_action_result_observation=rows[0],
    )
    assert miss["status"] == "resolved"
    assert miss["match_outcome"] == "uniquely_matched"
    assert miss["compatible_branch_ids"] == (f"{binding['source_action_id']}:paralysis:executes",)
    assert miss["compatible_original_probability_mass"] == {"numerator": 7, "denominator": 8}

    execution, _ = _observations(binding)
    damage = _linked_damage(ledger, binding, execution)
    hit = reconcile_observed_action_opportunity_rng(
        predictive_authority=authority, predictive_binding=binding, predictive_ledger=ledger,
        executed_move_observation=execution, direct_damage_observation=damage,
    )
    assert hit["status"] == "resolved"
    assert hit["compatible_branch_ids"] == (f"{binding['source_action_id']}:paralysis:executes",)
    assert hit["compatible_original_probability_mass"] == {"numerator": 7, "denominator": 8}


def test_unlinked_damage_rejects_instead_of_becoming_execution_evidence():
    _manager, _snapshot, _d0, ledger, binding, authority = _fixture()
    execution, _ = _observations(binding)
    damage = _linked_damage(ledger, binding, execution)
    damage.pop("linked_execution_observation_id")
    result = reconcile_observed_action_opportunity_rng(
        predictive_authority=authority, predictive_binding=binding, predictive_ledger=ledger,
        executed_move_observation=execution, direct_damage_observation=damage,
    )
    assert result["status"] == "rejected"


def test_contradictory_full_paralysis_and_downstream_evidence_has_zero_mass():
    _manager, _snapshot, _d0, ledger, binding, authority = _fixture()
    execution, rows = _observations(binding, "full_paralysis")
    damage = _linked_damage(ledger, binding, execution)
    conflict = reconcile_observed_action_opportunity_rng(
        predictive_authority=authority, predictive_binding=binding, predictive_ledger=ledger,
        executed_move_observation=execution, previous_action_result_observation=rows[0],
        direct_damage_observation=damage,
    )
    assert conflict["status"] == "resolved"
    assert conflict["match_outcome"] == "incompatible_observation"
    assert conflict["compatible_branch_ids"] == ()
    assert conflict["compatible_original_probability_mass"] == {"numerator": 0, "denominator": 1}

    execution, rows = _observations(binding, "full_paralysis", "accuracy_miss")
    conflict = reconcile_observed_action_opportunity_rng(
        predictive_authority=authority, predictive_binding=binding, predictive_ledger=ledger,
        executed_move_observation=execution, previous_action_result_observation=rows,
    )
    assert conflict["status"] == "resolved"
    assert conflict["match_outcome"] == "incompatible_observation"
    assert conflict["compatible_original_probability_mass"] == {"numerator": 0, "denominator": 1}


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(prediction_fingerprint="0" * 64),
        lambda value: value["branches"][0]["probability"].update(numerator=2),
        lambda value: value["branches"][1]["probability"].update(numerator=6),
        lambda value: value.update(root_probability_mass={"numerator": 7, "denominator": 8}),
    ],
)
def test_authority_tamper_rejects(mutation):
    _manager, _snapshot, _d0, ledger, binding, authority = _fixture()
    forged = deepcopy(authority)
    mutation(forged)
    result = validate_current_action_paralysis_opportunity_authority(
        authority=forged, predictive_binding=binding, predictive_ledger=ledger,
    )
    assert result["status"] == "rejected"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda row: row["payload"].update(source_action_id="foreign"),
        lambda row: row.update(turn_number=99),
        lambda row: row.update(pokemon_id="foreign"),
        lambda row: row["payload"].update(move_id="tackle"),
    ],
)
def test_foreign_execution_observation_rejects(mutation):
    _manager, _snapshot, _d0, ledger, binding, authority = _fixture()
    execution, _ = _observations(binding)
    mutation(execution)
    result = reconcile_observed_action_opportunity_rng(
        predictive_authority=authority, predictive_binding=binding, predictive_ledger=ledger,
        executed_move_observation=execution,
    )
    assert result["status"] == "rejected"


def test_foreign_result_observation_rejects():
    _manager, _snapshot, _d0, ledger, binding, authority = _fixture()
    execution, rows = _observations(binding, "full_paralysis")
    rows[0]["payload"]["previous_action_id"] = "foreign"
    result = reconcile_observed_action_opportunity_rng(
        predictive_authority=authority, predictive_binding=binding, predictive_ledger=ledger,
        executed_move_observation=execution, previous_action_result_observation=rows[0],
    )
    assert result["status"] == "rejected"


def test_production_wiring_and_lifecycle_retirement_contract_are_present():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    install_start = source.index("def _install_historical_predictive_action_bindings")
    install_end = source.index("@staticmethod", install_start)
    install = source[install_start:install_end]
    assert "self._historical_predictive_action_bindings = {}" in install
    assert "materialize_current_action_paralysis_opportunity_authority" in install
    assert 'bundle["action_opportunity_authority"] = deepcopy(opportunity)' in install

    turn_start = source.index("def set_current_turn_number")
    turn_end = source.index("def advance_turn", turn_start)
    turn = source[turn_start:turn_end]
    assert "if prior != turn_number:" in turn
    assert "self._historical_predictive_action_bindings = {}" in turn

    session_start = source.index("def _begin_new_battle_session")
    session_end = source.index("def begin_new_battle", session_start)
    session = source[session_start:session_end]
    assert "manager.rollover(candidate_session_id" in session
    assert "self._historical_predictive_action_bindings = {}" in session

    reconcile_start = source.index("def _reconcile_linked_predictive_action")
    reconcile_end = source.index("def _confirm_action_restriction", reconcile_start)
    reconcile = source[reconcile_start:reconcile_end]
    assert 'bundle.get("action_opportunity_authority")' in reconcile
    assert "reconcile_observed_action_opportunity_rng" in reconcile


def test_runtime_change_cannot_reconstruct_old_opportunity_from_move_name():
    manager, _snapshot, _d0, ledger, binding, authority = _fixture()
    state = deepcopy(manager.read_state()["state"])
    state["self_side"]["pokemon"][0]["current_hp"] = 99
    new_manager = BattleObservationRuntimeSessionManager.create("paralysis-c5", state)["manager"]
    changed = new_manager.capture_runtime_state_snapshot("paralysis-c5")
    result = materialize_current_action_paralysis_opportunity_authority(
        predictive_binding=binding, predictive_ledger=ledger, runtime_snapshot=changed,
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "paralysis_opportunity_runtime_binding_mismatch"
    assert authority["move_id"] == binding["move_id"]
