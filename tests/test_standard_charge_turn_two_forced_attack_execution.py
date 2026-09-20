from __future__ import annotations

from copy import deepcopy

from llm.advisor_detached_standard_charge_forced_continuation import materialize_detached_standard_charge_forced_continuation
from llm.advisor_detached_standard_charge_turn_two_attack_execution import (
    execute_detached_standard_charge_turn_two_attacks,
    materialize_detached_standard_charge_turn_two_execution_authority,
)
from tests.test_next_turn_predictive_mechanics_state_transport import _rich_flow, _next_from_phase


def _execution():
    _, _, _, phase = _rich_flow()
    _, _, handoff = _next_from_phase(phase)
    state = handoff["next_state"]
    fingerprint = handoff["resulting_branch_fingerprint"]
    forced = materialize_detached_standard_charge_forced_continuation(next_decision_state=state, next_decision_fingerprint=fingerprint)
    authority = materialize_detached_standard_charge_turn_two_execution_authority(next_decision_state=state, next_decision_fingerprint=fingerprint, forced_continuation=forced, predictive_mechanics=handoff["next_turn_predictive_mechanics_authority"])
    assert authority["status"] == "resolved", authority
    return execute_detached_standard_charge_turn_two_attacks(execution_authority=authority)


def test_two_forced_charges_produce_independent_normalized_ledgers():
    result = _execution()
    assert result["status"] == "resolved", result
    assert result["unordered"] is True
    for row in result["actions"].values():
        assert row["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
        assert len(row["terminal_leaves"]) > 16


def test_naked_canonical_effect_cannot_execute():
    result = execute_detached_standard_charge_turn_two_attacks(execution_authority={"status": "resolved"})
    assert result["status"] == "rejected"


def test_mutated_bound_target_cannot_execute():
    _, _, _, phase = _rich_flow()
    _, _, handoff = _next_from_phase(phase)
    state, fingerprint = handoff["next_state"], handoff["resulting_branch_fingerprint"]
    forced = materialize_detached_standard_charge_forced_continuation(next_decision_state=state, next_decision_fingerprint=fingerprint)
    authority = materialize_detached_standard_charge_turn_two_execution_authority(next_decision_state=state, next_decision_fingerprint=fingerprint, forced_continuation=forced, predictive_mechanics=handoff["next_turn_predictive_mechanics_authority"])
    forged = deepcopy(authority)
    forged["actions"]["self"]["target"]["pokemon_id"] = "forged"
    assert execute_detached_standard_charge_turn_two_attacks(execution_authority=forged)["status"] == "rejected"
