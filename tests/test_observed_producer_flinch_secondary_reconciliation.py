from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from llm.advisor_detached_observed_rng_reconciliation import (
    link_direct_damage_observation_to_predictive_action,
    materialize_historical_predictive_action_binding,
    reconcile_observed_scalar_attack_rng,
)
from llm.advisor_exact_predictive_outcome_ledger import normalize_exact_predictive_outcome_ledger
from llm.advisor_flinch_causality_observation import admit_flinch_causality_observation
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_previous_action_history_observation import admit_previous_action_history_observation
from llm.advisor_replay_policy import build_replay_plan
from tests.test_exact_predictive_outcome_ledger import (
    OWNER,
    TARGET,
    _bindings,
    _candidate,
    _hit,
    _manifest,
    _secondary,
)


def _ledger(*, critical=True, hit_probability=100, eligibility="eligible"):
    flinch = _secondary(
        "deterministic-predictive-iron-head-flinch-uncertainty-v1",
        move="iron-head",
        per_roll=True,
    )
    rows = []
    for row in flinch["damage_roll_leaves"]:
        updated = deepcopy(row)
        updated["secondary_eligibility"] = eligibility
        if eligibility == "eligible":
            updated["secondary_branches"] = (
                {
                    "branch": "no_effect",
                    "conditional_secondary_probability": {"numerator": 70, "denominator": 100},
                },
                {
                    "branch": "effect",
                    "conditional_secondary_probability": {"numerator": 30, "denominator": 100},
                    "hypothetical_target_flinch": {
                        "schema_version": "detached-hypothetical-immediate-flinch-v1",
                        "state": "flinched",
                    },
                },
            )
        elif eligibility == "target_fainted":
            updated["secondary_branches"] = ()
        elif eligibility == "blocked_by_substitute":
            updated["secondary_branches"] = (
                {
                    "branch": "no_effect",
                    "conditional_secondary_probability": {"numerator": 1, "denominator": 1},
                },
            )
        else:
            raise AssertionError(eligibility)
        rows.append(updated)
    flinch["damage_roll_leaves"] = tuple(rows)
    ledger = normalize_exact_predictive_outcome_ledger(
        candidate=_candidate("iron-head"),
        predictive_consequence=_hit(
            "iron-head",
            critical="resolved" if critical else "not_applicable",
            secondary=("iron_head_flinch_uncertainty", flinch),
            probability=hit_probability,
        ),
        component_manifest=_manifest(
            critical="resolved" if critical else "not_applicable",
            secondary="resolved",
        ),
        bindings=_bindings("iron-head"),
    )
    assert ledger["status"] == "evaluable", ledger
    return ledger


def _manager():
    state = create_unknown_bootstrap_battle_state("ledger-session", "p1", "p2")["state"]
    return BattleObservationRuntimeSessionManager.create("ledger-session", state)["manager"]


def _binding(ledger):
    binding = materialize_historical_predictive_action_binding(
        predictive_ledger=ledger, turn_number=1,
    )
    assert binding["status"] == "resolved"
    return binding


def _history(manager, binding, *, cancelled_result="flinch"):
    # Deliberately confirm cancelled action first. Observation admission order is
    # not battle action order; the later causal observation supplies that edge.
    cancelled = admit_previous_action_history_observation(
        runtime_session_manager=manager,
        captured_session_id="ledger-session",
        side="opponent",
        execution_move_id="tackle",
        selected_move_id="tackle",
        source_action_id="ledger-session:cancelled-action",
        result_class=cancelled_result,
        turn_number=1,
    )
    assert cancelled["status"] == "resolved", cancelled
    producer = admit_previous_action_history_observation(
        runtime_session_manager=manager,
        captured_session_id="ledger-session",
        side="self",
        execution_move_id="iron-head",
        selected_move_id="iron-head",
        source_action_id=binding["source_action_id"],
        result_class=None,
        turn_number=1,
    )
    assert producer["status"] == "resolved", producer
    return producer["observations"][0], cancelled["observations"][0], cancelled["observations"][1]


def _causal(manager, ledger, binding, producer, cancelled_execution, cancelled_result):
    result = admit_flinch_causality_observation(
        runtime_session_manager=manager,
        captured_session_id="ledger-session",
        predictive_binding=binding,
        predictive_ledger=ledger,
        producer_execution_observation=producer,
        cancelled_execution_observation=cancelled_execution,
        cancelled_result_observation=cancelled_result,
    )
    assert result["status"] == "resolved", result
    return result["observation"]


def _linked_damage(ledger, binding, producer, amount=9):
    observation = {
        "event_kind": "direct_move_damage_observed",
        "session_id": binding["session_id"],
        "turn_number": binding["turn_number"],
        "attacker": {**deepcopy(binding["actor"]), "source": "ui_observed_damage_confirmation", "trust": "user_confirmed_observation"},
        "defender": {**deepcopy(binding["target"]), "source": "ui_observed_damage_confirmation", "trust": "user_confirmed_observation"},
        "move_id": None,
        "move_slot": None,
        "source_action_id": None,
        "damage_amount": amount,
        "hp_unit": "exact",
        "source": "ui_observed_damage_confirmation",
        "trust": "user_confirmed_observation",
        "observed": True,
        "confirmed": True,
        "observation_id": "producer-damage",
        "observation_sequence": producer["observation_sequence"] + 10,
        "reconciliation_eligible": False,
    }
    linked = link_direct_damage_observation_to_predictive_action(
        observation=observation,
        predictive_binding=binding,
        predictive_ledger=ledger,
        executed_move_observation=producer,
    )
    assert linked["reconciliation_eligible"] is True
    return linked


def test_causal_observation_preserves_distinct_actions_exact_refs_and_sequence_rule():
    ledger = _ledger()
    binding = _binding(ledger)
    manager = _manager()
    producer, cancelled_execution, cancelled_result = _history(manager, binding)
    before = deepcopy(manager.read_state()["state"])
    causal = _causal(manager, ledger, binding, producer, cancelled_execution, cancelled_result)

    assert causal["producer_source_action_id"] == binding["source_action_id"]
    assert causal["cancelled_source_action_id"] == "ledger-session:cancelled-action"
    assert causal["producer_source_action_id"] != causal["cancelled_source_action_id"]
    assert causal["producer_execution_observation_id"] == producer["observation_id"]
    assert causal["cancelled_execution_observation_id"] == cancelled_execution["observation_id"]
    assert causal["cancelled_result_observation_id"] == cancelled_result["observation_id"]
    assert causal["affected_owner"] == TARGET
    assert causal["producer_owner"] == OWNER
    assert causal["producer_predictive_ledger_fingerprint"] == binding["predictive_ledger_fingerprint"]
    assert causal["reconciliation_eligible"] is True
    assert causal["observation_sequence"] > max(
        producer["observation_sequence"],
        cancelled_execution["observation_sequence"],
        cancelled_result["observation_sequence"],
    )
    # Producer was entered after cancelled history, proving source entry order is
    # not interpreted as battle order.
    assert producer["observation_sequence"] > cancelled_result["observation_sequence"]
    assert manager.read_state()["state"] == before

    collection = manager.read_collection_snapshot()["ordered_observations"]
    plan = build_replay_plan(before, collection)
    evidence = [row for row in plan["evidence_only_events"] if row["event_kind"] == "flinch_causality_observed"]
    assert evidence == [causal]


def test_iron_head_causal_flinch_selects_effect_only_with_exact_three_tenths_mass():
    ledger = _ledger(critical=True, hit_probability=100)
    binding = _binding(ledger)
    manager = _manager()
    producer, cancelled_execution, cancelled_result = _history(manager, binding)
    causal = _causal(manager, ledger, binding, producer, cancelled_execution, cancelled_result)
    originals = deepcopy((ledger, binding, producer, cancelled_execution, cancelled_result, causal))

    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=producer,
        flinch_causality_observation=causal,
    )
    assert result["status"] == "resolved"
    assert result["match_outcome"] == "multiple_compatible_branches"
    assert result["compatible_original_probability_mass"] == {"numerator": 3, "denominator": 10}
    assert result["probability_normalization"] == "none_preserve_original_mass"
    assert all("secondary:effect" in leaf_id for leaf_id in result["compatible_leaf_ids"])
    assert not any("secondary:no_effect" in leaf_id for leaf_id in result["compatible_leaf_ids"])
    assert set(result["unresolved_hidden_dimensions"]) >= {"critical_state", "damage_roll"}
    assert result["matched_observable_facts"]["target_flinch_caused"]["cancelled_source_action_id"] == "ledger-session:cancelled-action"
    assert (ledger, binding, producer, cancelled_execution, cancelled_result, causal) == originals


@pytest.mark.parametrize("eligibility", ["target_fainted", "blocked_by_substitute"])
def test_ineligible_secondary_cannot_match_observed_causal_flinch(eligibility):
    ledger = _ledger(critical=False, hit_probability=100, eligibility=eligibility)
    binding = _binding(ledger)
    manager = _manager()
    producer, cancelled_execution, cancelled_result = _history(manager, binding)
    causal = _causal(manager, ledger, binding, producer, cancelled_execution, cancelled_result)
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=producer,
        flinch_causality_observation=causal,
    )
    assert result["status"] == "resolved"
    assert result["match_outcome"] == "incompatible_observation"
    assert result["compatible_original_probability_mass"] == {"numerator": 0, "denominator": 1}


def test_miss_and_no_effect_leaves_are_removed_by_causal_flinch():
    ledger = _ledger(critical=False, hit_probability=80)
    binding = _binding(ledger)
    manager = _manager()
    producer, cancelled_execution, cancelled_result = _history(manager, binding)
    causal = _causal(manager, ledger, binding, producer, cancelled_execution, cancelled_result)
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=producer,
        flinch_causality_observation=causal,
    )
    assert result["status"] == "resolved"
    assert all("secondary:effect" in leaf_id for leaf_id in result["compatible_leaf_ids"])
    assert all("hit:miss" not in leaf_id for leaf_id in result["compatible_leaf_ids"])
    assert result["compatible_original_probability_mass"] == {"numerator": 6, "denominator": 25}


def test_direct_damage_and_flinch_compose_without_resolving_crit_or_roll():
    ledger = _ledger(critical=True, hit_probability=100)
    binding = _binding(ledger)
    manager = _manager()
    producer, cancelled_execution, cancelled_result = _history(manager, binding)
    causal = _causal(manager, ledger, binding, producer, cancelled_execution, cancelled_result)
    damage = _linked_damage(ledger, binding, producer, amount=9)
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=producer,
        direct_damage_observation=damage,
        flinch_causality_observation=causal,
    )
    assert result["status"] == "resolved"
    assert result["match_outcome"] == "multiple_compatible_branches"
    assert result["matched_observable_facts"]["direct_damage"] == 9
    assert "target_flinch_caused" in result["matched_observable_facts"]
    assert set(result["unresolved_hidden_dimensions"]) >= {"critical_state", "damage_roll"}


def test_absence_of_causal_observation_does_not_imply_no_effect():
    ledger = _ledger(critical=False, hit_probability=100)
    binding = _binding(ledger)
    manager = _manager()
    producer, _cancelled_execution, _cancelled_result = _history(manager, binding)
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=producer,
    )
    assert result["status"] == "incomplete"
    assert result["reason"] == "insufficient_observation"
    assert result["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert any("secondary:effect" in leaf_id for leaf_id in result["compatible_leaf_ids"])
    assert any("secondary:no_effect" in leaf_id for leaf_id in result["compatible_leaf_ids"])


@pytest.mark.parametrize(
    "which,mutation",
    [
        ("producer", lambda row: row["payload"].update(source_action_id="foreign")),
        ("cancelled_execution", lambda row: row["payload"].update(source_action_id="foreign")),
        ("cancelled_result", lambda row: row["payload"].update(previous_action_id="foreign")),
        ("cancelled_result", lambda row: row["payload"].update(result_class="success")),
        ("cancelled_result", lambda row: row.update(related_observation_id="foreign")),
        ("producer", lambda row: row.update(turn_number=99)),
        ("cancelled_execution", lambda row: row.update(pokemon_id="wrong")),
    ],
)
def test_causal_admission_tamper_rejects(which, mutation):
    ledger = _ledger()
    binding = _binding(ledger)
    manager = _manager()
    producer, cancelled_execution, cancelled_result = _history(manager, binding)
    rows = {
        "producer": deepcopy(producer),
        "cancelled_execution": deepcopy(cancelled_execution),
        "cancelled_result": deepcopy(cancelled_result),
    }
    mutation(rows[which])
    result = admit_flinch_causality_observation(
        runtime_session_manager=manager,
        captured_session_id="ledger-session",
        predictive_binding=binding,
        predictive_ledger=ledger,
        producer_execution_observation=rows["producer"],
        cancelled_execution_observation=rows["cancelled_execution"],
        cancelled_result_observation=rows["cancelled_result"],
    )
    assert result["status"] == "rejected"


def test_same_producer_and_cancelled_id_rejects():
    ledger = _ledger()
    binding = _binding(ledger)
    manager = _manager()
    producer = admit_previous_action_history_observation(
        runtime_session_manager=manager,
        captured_session_id="ledger-session",
        side="self",
        execution_move_id="iron-head",
        selected_move_id="iron-head",
        source_action_id=binding["source_action_id"],
        result_class=None,
        turn_number=1,
    )["observations"][0]
    cancelled = admit_previous_action_history_observation(
        runtime_session_manager=manager,
        captured_session_id="ledger-session",
        side="opponent",
        execution_move_id="tackle",
        selected_move_id="tackle",
        source_action_id=binding["source_action_id"],
        result_class="flinch",
        turn_number=1,
    )
    result = admit_flinch_causality_observation(
        runtime_session_manager=manager,
        captured_session_id="ledger-session",
        predictive_binding=binding,
        predictive_ledger=ledger,
        producer_execution_observation=producer,
        cancelled_execution_observation=cancelled["observations"][0],
        cancelled_result_observation=cancelled["observations"][1],
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "producer_and_cancelled_action_must_differ"


def test_incompatible_producer_result_rejects_even_though_execution_identity_exists():
    ledger = _ledger()
    binding = _binding(ledger)
    manager = _manager()
    cancelled = admit_previous_action_history_observation(
        runtime_session_manager=manager,
        captured_session_id="ledger-session",
        side="opponent",
        execution_move_id="tackle",
        selected_move_id="tackle",
        source_action_id="ledger-session:cancelled-action",
        result_class="flinch",
        turn_number=1,
    )
    producer = admit_previous_action_history_observation(
        runtime_session_manager=manager,
        captured_session_id="ledger-session",
        side="self",
        execution_move_id="iron-head",
        selected_move_id="iron-head",
        source_action_id=binding["source_action_id"],
        result_class="accuracy_miss",
        turn_number=1,
    )
    result = admit_flinch_causality_observation(
        runtime_session_manager=manager,
        captured_session_id="ledger-session",
        predictive_binding=binding,
        predictive_ledger=ledger,
        producer_execution_observation=producer["observations"][0],
        cancelled_execution_observation=cancelled["observations"][0],
        cancelled_result_observation=cancelled["observations"][1],
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "producer_result_incompatible_with_flinch_causality"


def test_v1_explicitly_excludes_deterministic_fake_out_and_fling_producers():
    source = Path("llm/advisor_flinch_causality_observation.py").read_text(encoding="utf-8")
    assert 'checked.get("move_id") != "iron-head"' in source
    assert "fake-out" not in source
    assert "fling" not in source


def test_ambiguous_duplicate_producer_execution_rejects():
    ledger = _ledger()
    binding = _binding(ledger)
    manager = _manager()
    producer, cancelled_execution, cancelled_result = _history(manager, binding)
    duplicate = admit_previous_action_history_observation(
        runtime_session_manager=manager,
        captured_session_id="ledger-session",
        side="self",
        execution_move_id="iron-head",
        selected_move_id="iron-head",
        source_action_id=binding["source_action_id"],
        result_class=None,
        turn_number=1,
    )
    assert duplicate["status"] == "resolved"
    result = admit_flinch_causality_observation(
        runtime_session_manager=manager,
        captured_session_id="ledger-session",
        predictive_binding=binding,
        predictive_ledger=ledger,
        producer_execution_observation=producer,
        cancelled_execution_observation=cancelled_execution,
        cancelled_result_observation=cancelled_result,
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "ambiguous_producer_execution_evidence"


def test_forged_causality_eligibility_or_prediction_reference_rejects():
    ledger = _ledger()
    binding = _binding(ledger)
    manager = _manager()
    producer, cancelled_execution, cancelled_result = _history(manager, binding)
    causal = _causal(manager, ledger, binding, producer, cancelled_execution, cancelled_result)

    forged = deepcopy(causal)
    forged["producer_predictive_ledger_fingerprint"] = "0" * 64
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=producer,
        flinch_causality_observation=forged,
    )
    assert result["status"] == "rejected"

    raw = deepcopy(causal)
    raw.pop("provenance")
    raw["reconciliation_eligible"] = True
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=producer,
        flinch_causality_observation=raw,
    )
    assert result["status"] == "rejected"


def test_ui_requires_explicit_causal_choice_and_reuses_internal_action_ids():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    start = source.index("def _confirm_flinch_causality_for_cancelled_history")
    end = source.index("def _confirm_action_restriction", start)
    contract = source[start:end]
    assert '"Confirm Flinch Cause"' in contract
    assert '"Not confirmed"' in contract
    assert 'checked.get("move_id") != "iron-head"' in contract
    assert "admit_flinch_causality_observation(" in contract
    assert 'selected["binding"]["source_action_id"]' in contract
    # The UI selects a human-readable producer option; it never asks for an
    # internal action id string.
    assert "producer_source_action_id" not in contract


def test_pair_flinch_cancellation_contract_is_conditional_one_without_rng_duplication():
    source = Path("llm/advisor_immediate_move_vs_move_action_pair.py").read_text(encoding="utf-8")
    assert '"execution_branch_id": "second_action:flinched"' in source
    assert '"state": "cancelled_due_to_flinch"' in source
    assert '"conditional_probability": _fd(Fraction(1, 1))' in source
    # Producer probability is owned by the first-action leaf; the cancellation
    # branch itself contains no 3/10 probability.
    fragment = source[source.index('"execution_branch_id": "second_action:flinched"'):]
    fragment = fragment[:500]
    assert "Fraction(3, 10)" not in fragment
