from __future__ import annotations

from copy import deepcopy
from fractions import Fraction

import pytest

from llm.advisor_detached_observed_rng_reconciliation import (
    reconcile_observed_sleep_freeze_action_gate_rng,
    retain_historical_sleep_freeze_action_gate,
    validate_historical_sleep_freeze_action_gate,
)
from tests.test_champions_sleep_freeze_action_gate import gate


def _retain(*, condition="freeze", move="tackle", prior=0, duration=None, ability="pressure", opposing_ability="pressure"):
    _snapshot, _d0, source = gate(
        condition, move=move, prior=prior, duration=duration,
        ability=ability, opposing_ability=opposing_ability,
    )
    retained = retain_historical_sleep_freeze_action_gate(
        predictive_gate=source,
        turn_number=2,
        decision_point="decision:status:2:self",
    )
    assert retained["status"] == "resolved", retained
    return source, retained


def _observation(retained, outcome, *, sequence=7, **overrides):
    semantic = {
        "blocked_sleep": ("blocked", "sleep"),
        "wake_and_execute": ("executable", None),
        "sleep_exception_execute": ("executable", None),
        "blocked_freeze": ("blocked", "freeze"),
        "natural_thaw_and_execute": ("executable", None),
        "self_thaw_move_execute": ("executable", None),
    }[outcome]
    actor = retained["actor"]
    payload = {
        "decision_point": retained["decision_point"],
        "action_id": retained["action_id"],
        "move_id": retained["move_id"],
        "condition": retained["condition"],
        "execution_state": semantic[0],
        "blocker": semantic[1],
        "outcome_class": outcome,
    }
    payload.update(overrides.pop("payload_overrides", {}))
    row = {
        "event_kind": "pending_status_action_execution_observed",
        "session_id": retained["session_id"],
        "turn_number": retained["turn_number"],
        "side": actor["side"],
        "slot_index": actor["slot_index"],
        "pokemon_id": actor["pokemon_id"],
        "source": "ui_pending_status_action_execution_confirmation",
        "trust": "user_confirmed_observation",
        "observed": True,
        "confirmed": True,
        "observation_id": "status-action:7",
        "observation_sequence": sequence,
        "payload": payload,
    }
    row.update(overrides)
    return row


def _mass(result):
    value = result["compatible_original_probability_mass"]
    return Fraction(value["numerator"], value["denominator"])


def test_retention_is_stable_exact_and_does_not_mutate_source_gate():
    source, retained = _retain(condition="sleep")
    baseline = deepcopy(source)
    second = retain_historical_sleep_freeze_action_gate(
        predictive_gate=source, turn_number=2, decision_point=retained["decision_point"],
    )
    assert source == baseline
    assert second["prediction_fingerprint"] == retained["prediction_fingerprint"]
    assert retained["source_runtime_fingerprint"] == source["source_runtime_fingerprint"]
    assert retained["source_branch_fingerprint"] == source["source_branch_fingerprint"]
    assert validate_historical_sleep_freeze_action_gate(retained) == retained


@pytest.mark.parametrize("condition", ["sleep", "freeze"])
def test_retention_preserves_exact_action_identity_without_source_action_id(condition):
    source, retained = _retain(condition=condition)
    assert retained["session_id"] == source["session_id"]
    assert retained["actor"] == source["actor"]
    assert retained["action_id"] == source["action_id"]
    assert retained["move_id"] == source["move_id"]
    assert retained["condition"] == condition
    assert "source_action_id" not in retained
    assert retained["predictive_gate"]["root_probability_mass"] == {"numerator": 1, "denominator": 1}


def test_freeze_ordinary_blocked_and_natural_thaw_preserve_three_quarters_and_one_quarter():
    source, retained = _retain(condition="freeze", prior=0)
    assert [Fraction(b["probability"]["numerator"], b["probability"]["denominator"]) for b in source["branches"]] == [Fraction(1, 4), Fraction(3, 4)]

    blocked = reconcile_observed_sleep_freeze_action_gate_rng(
        retained_prediction=retained,
        pending_status_action_observation=_observation(retained, "blocked_freeze"),
    )
    thawed = reconcile_observed_sleep_freeze_action_gate_rng(
        retained_prediction=retained,
        pending_status_action_observation=_observation(retained, "natural_thaw_and_execute"),
    )

    assert blocked["compatible_branch_ids"] == (source["branches"][1]["branch_id"],)
    assert thawed["compatible_branch_ids"] == (source["branches"][0]["branch_id"],)
    assert _mass(blocked) == Fraction(3, 4)
    assert _mass(thawed) == Fraction(1, 4)
    assert blocked["probability_normalization"] == thawed["probability_normalization"] == "none_preserve_original_mass"


def test_freeze_deterministic_third_attempt_and_self_thaw_consume_source_gate_only():
    source, retained = _retain(condition="freeze", prior=2)
    natural = reconcile_observed_sleep_freeze_action_gate_rng(
        retained_prediction=retained,
        pending_status_action_observation=_observation(retained, "natural_thaw_and_execute"),
    )
    impossible = reconcile_observed_sleep_freeze_action_gate_rng(
        retained_prediction=retained,
        pending_status_action_observation=_observation(retained, "blocked_freeze"),
    )
    assert source["branches"][0]["kind"] == "thaws_and_executes"
    assert _mass(natural) == 1
    assert impossible["match_outcome"] == "incompatible_observation"
    assert _mass(impossible) == 0

    self_source, self_retained = _retain(condition="freeze", move="scald")
    self_thaw = reconcile_observed_sleep_freeze_action_gate_rng(
        retained_prediction=self_retained,
        pending_status_action_observation=_observation(self_retained, "self_thaw_move_execute"),
    )
    natural_against_self_thaw = reconcile_observed_sleep_freeze_action_gate_rng(
        retained_prediction=self_retained,
        pending_status_action_observation=_observation(self_retained, "natural_thaw_and_execute"),
    )
    assert self_source["branches"][0]["kind"] == "self_thaw_move_executes"
    assert _mass(self_thaw) == 1
    assert _mass(natural_against_self_thaw) == 0


def test_sleep_blocked_preserves_multiple_hidden_durations_and_original_mass():
    source, retained = _retain(condition="sleep", prior=0, duration=None)
    result = reconcile_observed_sleep_freeze_action_gate_rng(
        retained_prediction=retained,
        pending_status_action_observation=_observation(retained, "blocked_sleep"),
    )
    assert len(source["branches"]) == 2
    assert all(branch["kind"] == "cancelled_sleep" for branch in source["branches"])
    assert result["match_outcome"] == "multiple_compatible_branches"
    assert result["compatible_branch_ids"] == tuple(branch["branch_id"] for branch in source["branches"])
    assert _mass(result) == 1
    assert "sleep_duration" in result["unresolved_hidden_dimensions"]
    assert "duration_identity" in result["unresolved_hidden_dimensions"]
    assert "sleep_duration" not in result["matched_observable_facts"]
    assert result["probability_normalization"] == "none_preserve_original_mass"


def test_sleep_wake_and_blocked_condition_on_existing_hidden_duration_distribution():
    source, retained = _retain(condition="sleep", prior=1, duration=None)
    kinds = [branch["kind"] for branch in source["branches"]]
    assert kinds == ["wakes_and_executes", "cancelled_sleep"]
    wake = reconcile_observed_sleep_freeze_action_gate_rng(
        retained_prediction=retained,
        pending_status_action_observation=_observation(retained, "wake_and_execute"),
    )
    blocked = reconcile_observed_sleep_freeze_action_gate_rng(
        retained_prediction=retained,
        pending_status_action_observation=_observation(retained, "blocked_sleep"),
    )
    assert _mass(wake) == Fraction(1, 3)
    assert _mass(blocked) == Fraction(2, 3)


def test_sleep_exception_and_early_bird_are_consumed_from_validated_source_not_move_recomputed():
    source, retained = _retain(condition="sleep", move="sleep-talk")
    result = reconcile_observed_sleep_freeze_action_gate_rng(
        retained_prediction=retained,
        pending_status_action_observation=_observation(retained, "sleep_exception_execute"),
    )
    assert all(branch["kind"] == "move_specific_sleep_exception_executes" for branch in source["branches"])
    assert _mass(result) == 1
    assert result["match_outcome"] == "multiple_compatible_branches"

    early_source, early_retained = _retain(condition="sleep", ability="early-bird")
    early = reconcile_observed_sleep_freeze_action_gate_rng(
        retained_prediction=early_retained,
        pending_status_action_observation=_observation(early_retained, "wake_and_execute"),
    )
    assert all(branch["kind"] == "wakes_and_executes" for branch in early_source["branches"])
    assert {branch["adjusted_duration"] for branch in early_source["branches"]} == {1}
    assert _mass(early) == 1


def test_no_pending_observation_and_current_condition_only_preserve_full_source_mass():
    _source, retained = _retain(condition="freeze")
    absent = reconcile_observed_sleep_freeze_action_gate_rng(retained_prediction=retained)
    condition_only = reconcile_observed_sleep_freeze_action_gate_rng(
        retained_prediction=retained,
        pending_status_action_observation={
            "event_kind": "current_condition_observed",
            "session_id": retained["session_id"],
            "turn_number": retained["turn_number"],
        },
    )
    for result in (absent, condition_only):
        assert result["status"] == "incomplete"
        assert result["reason"] == "insufficient_observation"
        assert _mass(result) == 1
        assert result["source_observations"] == ()


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (lambda row: row.update(session_id="foreign"), "pending_status_action_observation_provenance_mismatch"),
        (lambda row: row.update(turn_number=99), "pending_status_action_observation_provenance_mismatch"),
        (lambda row: row.update(side="opponent"), "pending_status_action_actor_mismatch"),
        (lambda row: row["payload"].update(decision_point="foreign"), "pending_status_action_decision_point_mismatch"),
        (lambda row: row["payload"].update(action_id="foreign"), "pending_status_action_action_id_mismatch"),
        (lambda row: row["payload"].update(move_id="foreign"), "pending_status_action_move_mismatch"),
        (lambda row: row["payload"].update(condition="sleep"), "pending_status_action_condition_mismatch"),
    ],
)
def test_exact_observation_identity_fails_closed(mutation, reason):
    _source, retained = _retain(condition="freeze")
    row = _observation(retained, "blocked_freeze")
    mutation(row)
    result = reconcile_observed_sleep_freeze_action_gate_rng(
        retained_prediction=retained, pending_status_action_observation=row,
    )
    assert result["status"] == "rejected"
    assert result["reason"] == reason


def test_execution_state_and_blocker_must_agree_with_outcome_class():
    _source, retained = _retain(condition="freeze")
    bad_state = _observation(retained, "blocked_freeze", payload_overrides={"execution_state": "executable"})
    bad_blocker = _observation(retained, "blocked_freeze", payload_overrides={"blocker": None})
    for row in (bad_state, bad_blocker):
        result = reconcile_observed_sleep_freeze_action_gate_rng(
            retained_prediction=retained, pending_status_action_observation=row,
        )
        assert result["status"] == "rejected"
        assert result["reason"] == "pending_status_action_semantics_mismatch"


def test_forged_prediction_fingerprint_and_malformed_gate_reject():
    source, retained = _retain(condition="sleep")
    forged = deepcopy(retained)
    forged["prediction_fingerprint"] = "0" * 64
    assert validate_historical_sleep_freeze_action_gate(forged)["status"] == "rejected"

    malformed = deepcopy(source)
    malformed["branches"] = tuple(deepcopy(branch) for branch in malformed["branches"])
    malformed["branches"][0]["probability"] = {"numerator": 9, "denominator": 10}
    rejected = retain_historical_sleep_freeze_action_gate(
        predictive_gate=malformed, turn_number=2, decision_point="decision",
    )
    assert rejected["status"] == "rejected"


def test_ui_source_orders_gate_retention_before_production_observation_and_retires_lifecycle():
    source = open("ui/main_window.py", encoding="utf-8").read()
    start = source.index("def _submit_pending_status_action_result")
    end = source.index("def _present_pending_status_result", start)
    submit = source[start:end]
    retain_at = submit.index("retain_historical_sleep_freeze_action_gate(")
    admit_at = submit.index("admit_pending_status_action_execution(")
    reconcile_at = submit.index("reconcile_observed_sleep_freeze_action_gate_rng(")
    assert retain_at < admit_at < reconcile_at
    assert "runtime_snapshot=before" in submit
    assert "predictive_gate=predictive_gate" in submit
    assert 'result["observation"]' in submit
    assert "result.get(\"runtime_snapshot\")" in submit

    turn_start = source.index("def set_current_turn_number")
    turn_end = source.index("def advance_turn", turn_start)
    assert "self._historical_sleep_freeze_action_gates = {}" in source[turn_start:turn_end]
    battle_start = source.index("def _begin_new_battle_session")
    battle_end = source.index("def begin_new_battle", battle_start)
    assert "self._historical_sleep_freeze_action_gates = {}" in source[battle_start:battle_end]


def test_same_action_context_retention_is_deterministic_and_replacement_safe():
    source, first = _retain(condition="freeze")
    second = retain_historical_sleep_freeze_action_gate(
        predictive_gate=source,
        turn_number=first["turn_number"],
        decision_point=first["decision_point"],
    )
    key1 = (first["session_id"], first["turn_number"], first["decision_point"], first["action_id"])
    key2 = (second["session_id"], second["turn_number"], second["decision_point"], second["action_id"])
    storage = {key1: deepcopy(first)}
    storage[key2] = deepcopy(second)
    assert key1 == key2
    assert len(storage) == 1
    assert storage[key1] == second


def test_reconciliation_is_immutable_and_derived_lifecycle_is_not_second_rng_evidence():
    source, retained = _retain(condition="sleep")
    observation = _observation(retained, "blocked_sleep")
    baseline = deepcopy((source, retained, observation))
    result = reconcile_observed_sleep_freeze_action_gate_rng(
        retained_prediction=retained,
        pending_status_action_observation=observation,
    )
    assert (source, retained, observation) == baseline
    assert result["source_observations"] == ((
        {
            "observation_id": observation["observation_id"],
            "observation_sequence": observation["observation_sequence"],
            "event_kind": "pending_status_action_execution_observed",
        }
    ),)
    assert result["source_prediction_kind"] == "sleep_freeze_action_gate"
    assert "source_action_id" not in result
