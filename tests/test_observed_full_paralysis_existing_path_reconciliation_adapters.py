from __future__ import annotations

from copy import deepcopy

import pytest

from llm.advisor_detached_intermediate_predictive_authority import (
    freeze_detached_intermediate_predictive_authority,
)
from llm.advisor_detached_intermediate_paralysis_second_action_authority import (
    consume_detached_intermediate_paralysis_for_second_action,
)
from llm.advisor_detached_observed_rng_reconciliation import (
    materialize_historical_predictive_action_binding,
    reconcile_observed_action_opportunity_rng,
)
from llm.advisor_existing_paralysis_opportunity_reconciliation_adapters import (
    adapt_intermediate_paralysis_second_action_opportunity,
    adapt_standard_charge_terminal_paralysis_opportunity,
    validate_existing_paralysis_opportunity_adapter,
)
from llm.advisor_standard_charge_terminal_execution import (
    execute_standard_charge_terminal_attack,
)
from llm.advisor_runtime_d0_standard_charge_power_herb_skip_execution import (
    execute_runtime_d0_standard_charge_power_herb_skip,
    freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority,
)
from llm.advisor_runtime_d0_solar_weather_skip_execution import (
    execute_runtime_d0_solar_weather_skip,
    freeze_runtime_d0_solar_weather_skip_execution_authority,
)
from llm.advisor_runtime_d0_standard_charge_start_readiness_authority import (
    freeze_runtime_d0_standard_charge_start_readiness_authority,
)
from llm.advisor_geomancy_charge_status_terminal_execution import (
    execute_geomancy_status_terminal,
    execute_runtime_d0_geomancy_power_herb_skip,
)
from tests.test_detached_intermediate_predictive_authority import (
    _intermediate,
    _metadata_authority,
    _owner,
    _snapshot,
    _state,
)
from llm.advisor_lifecycle_confirmation import (
    EXECUTED_MOVE_SOURCE,
    PREVIOUS_ACTION_RESULT_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from tests.test_observed_full_paralysis_action_cancellation_reconciliation import (
    _linked_damage,
)
from tests.test_observed_scalar_attack_rng_reconciliation import _ledger as _scalar_ledger
from tests.test_standard_charge_shared_terminal_execution_contract import (
    _forced_case,
    _recontract,
)
from tests.test_runtime_d0_standard_charge_terminal_mechanics_authority import (
    _ready,
    _refresh,
)
from tests.test_standard_charge_start_immediate_pair_integration import _own_action
from tests.test_solar_weather_sensitive_charge_execution import _state_case
from tests.test_geomancy_charge_status_terminal_execution import (
    _forced_geomancy_contract,
    _power_herb_geomancy_authority,
    _recontract_geomancy,
)


def _binding_for(
    *,
    session: str,
    runtime: str,
    branch: str,
    actor: dict,
    target: dict,
    move: str,
    turn: int = 1,
):
    ledger = deepcopy(_scalar_ledger(move=move, critical=False))
    bindings = {
        "session_id": session,
        "source_runtime_fingerprint": runtime,
        "source_branch_fingerprint": branch,
        "decision_owner": deepcopy(actor),
        "attacker": deepcopy(actor),
        "target": deepcopy(target),
        "move_id": move,
    }
    ledger["bindings"] = deepcopy(bindings)
    for leaf in ledger["terminal_leaves"]:
        leaf["provenance"] = deepcopy(bindings)
    binding = materialize_historical_predictive_action_binding(
        predictive_ledger=ledger, turn_number=turn,
    )
    assert binding["status"] == "resolved"
    return ledger, binding


def _observations(binding, *result_classes):
    owners = {
        binding["actor"]["side"]: deepcopy(binding["actor"]),
        binding["target"]["side"]: deepcopy(binding["target"]),
    }
    boundary = LifecycleConfirmationBoundary(binding["session_id"], owners)
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
    assert execution is not None
    execution["observation_sequence"] = 1
    rows = []
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
        assert row is not None
        row["observation_sequence"] = index
        rows.append(row)
    return execution, rows


def _second_action_source():
    state = _state()
    snapshot = _snapshot(state)
    from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0

    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=snapshot, decision_owner=_owner(state, "self"),
    )
    intermediate = _intermediate(d0)
    intermediate["active"]["opponent"]["hypothetical_condition"] = {
        "status": "known_present",
        "condition": "paralysis",
        "source": "exact_terminal_leaf_condition_effect",
    }
    authority = freeze_detached_intermediate_predictive_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        intermediate_state=intermediate,
        actor=_owner(state, "opponent"),
        target=_owner(state, "self"),
        move_metadata_authority=_metadata_authority(d0),
    )
    source = consume_detached_intermediate_paralysis_for_second_action(
        intermediate_predictive_authority=authority,
    )
    assert source["status"] == "resolved"
    ledger, binding = _binding_for(
        session=source["session_id"],
        runtime=source["source_runtime_fingerprint"],
        branch=source["source_branch_fingerprint"],
        actor=source["predictive_actor"],
        target=source["predictive_target"],
        move=source["move_id"],
    )
    adapter = adapt_intermediate_paralysis_second_action_opportunity(
        source_authority=source,
        predictive_binding=binding,
        predictive_ledger=ledger,
    )
    assert adapter["status"] == "resolved", adapter
    return source, ledger, binding, adapter


def _charge_source():
    _state_value, _fingerprint, _authority, base = _forced_case(
        own_move="sky-attack", opponent_move="razor-wind",
    )
    actor_mechanics = deepcopy(base["actor_mechanics"])
    actor_mechanics["condition"] = {"status": "known_present", "condition": "paralysis"}
    actor_mechanics["direct_mechanics"]["combatant"]["status"] = "paralysis"
    contract = _recontract(base, actor_mechanics=actor_mechanics)
    assert contract["status"] == "resolved", contract
    terminal = execute_standard_charge_terminal_attack(execution_contract=contract)
    assert terminal["status"] == "resolved", terminal
    caller = terminal["execution_authority"]
    runtime = caller["source_next_decision_fingerprint"]
    branch = terminal["terminal_leaves"][0].get("provenance", {}).get(
        "source_branch_fingerprint", "charge-terminal-adapter-test-branch",
    )
    ledger, binding = _binding_for(
        session=contract["actor"]["session_id"],
        runtime=runtime,
        branch=branch,
        actor=contract["actor"],
        target=contract["target"],
        move=contract["move_id"],
        turn=2,
    )
    adapter = adapt_standard_charge_terminal_paralysis_opportunity(
        terminal_execution=terminal,
        predictive_binding=binding,
        predictive_ledger=ledger,
    )
    assert adapter["status"] == "resolved", adapter
    return terminal, ledger, binding, adapter


def test_second_action_adapter_reuses_exact_existing_branches_and_causal_identity():
    source, ledger, binding, adapter = _second_action_source()
    assert [row["branch_id"] for row in adapter["branches"]] == [
        "second_action:fully_paralyzed",
        "second_action:can_act_after_paralysis",
    ]
    assert [row["probability"] for row in adapter["branches"]] == [
        {"numerator": 1, "denominator": 8},
        {"numerator": 7, "denominator": 8},
    ]
    assert [row["source_branch"] for row in adapter["branches"]] == list(
        source["second_action_execution_branches"]
    )
    assert adapter["causal_provenance"]["source_first_action_leaf_id"] == source["source_first_action_leaf_id"]
    assert adapter["causal_provenance"]["intermediate_state_id"] == source["intermediate_state_id"]
    assert adapter["source_action_id"] == binding["source_action_id"]
    assert validate_existing_paralysis_opportunity_adapter(
        adapter=adapter, predictive_binding=binding, predictive_ledger=ledger,
    )["status"] == "resolved"


def test_second_action_full_paralysis_and_execution_evidence_preserve_original_mass():
    _source, ledger, binding, adapter = _second_action_source()
    execution, results = _observations(binding, "full_paralysis")
    cancelled = reconcile_observed_action_opportunity_rng(
        predictive_authority=adapter,
        predictive_binding=binding,
        predictive_ledger=ledger,
        executed_move_observation=execution,
        previous_action_result_observation=results[0],
    )
    assert cancelled["status"] == "resolved"
    assert cancelled["match_outcome"] == "uniquely_matched"
    assert cancelled["compatible_branch_ids"] == ("second_action:fully_paralyzed",)
    assert cancelled["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 8}
    assert cancelled["probability_normalization"] == "none_preserve_original_mass"

    execution, results = _observations(binding, "accuracy_miss")
    executed = reconcile_observed_action_opportunity_rng(
        predictive_authority=adapter,
        predictive_binding=binding,
        predictive_ledger=ledger,
        executed_move_observation=execution,
        previous_action_result_observation=results[0],
    )
    assert executed["compatible_branch_ids"] == ("second_action:can_act_after_paralysis",)
    assert executed["compatible_original_probability_mass"] == {"numerator": 7, "denominator": 8}


@pytest.mark.parametrize("field", ["source_first_action_leaf_id", "intermediate_state_id"])
def test_second_action_wrong_causal_source_rejects(field):
    source, ledger, binding, _adapter = _second_action_source()
    forged = deepcopy(source)
    forged[field] = "forged"
    result = adapt_intermediate_paralysis_second_action_opportunity(
        source_authority=forged,
        predictive_binding=binding,
        predictive_ledger=ledger,
    )
    assert result["status"] == "rejected"


def test_first_action_paralysis_effect_is_not_second_action_full_paralysis_observation():
    source, ledger, binding, adapter = _second_action_source()
    assert source["changed_condition_roles"] == ("actor",)
    execution, _ = _observations(binding)
    result = reconcile_observed_action_opportunity_rng(
        predictive_authority=adapter,
        predictive_binding=binding,
        predictive_ledger=ledger,
        executed_move_observation=execution,
    )
    assert result["status"] == "incomplete"
    assert result["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert len(result["compatible_branch_ids"]) == 2


def test_charge_terminal_adapter_reuses_shared_gate_and_preserves_lifecycle():
    terminal, ledger, binding, adapter = _charge_source()
    assert [row["branch_id"] for row in adapter["branches"]] == [
        "cancelled_due_to_paralysis",
        "executes_after_paralysis",
    ]
    assert [row["source_branch"] for row in adapter["branches"]] == list(
        terminal["pre_action_gate"]["branches"]
    )
    assert adapter["causal_provenance"]["execution_mode"] == "forced_turn_two_continuation"
    assert adapter["causal_provenance"]["caller_kind"] == "forced_turn_two_continuation"
    assert adapter["causal_provenance"]["charge_lifecycle"] == terminal["execution_authority"]["original_charge_lifecycle"]
    assert adapter["source_action_id"] == binding["source_action_id"]
    assert validate_existing_paralysis_opportunity_adapter(
        adapter=adapter, predictive_binding=binding, predictive_ledger=ledger,
    )["status"] == "resolved"


def test_charge_terminal_full_paralysis_execution_and_contradiction_mass():
    _terminal, ledger, binding, adapter = _charge_source()

    execution, results = _observations(binding, "full_paralysis")
    cancelled = reconcile_observed_action_opportunity_rng(
        predictive_authority=adapter,
        predictive_binding=binding,
        predictive_ledger=ledger,
        executed_move_observation=execution,
        previous_action_result_observation=results[0],
    )
    assert cancelled["compatible_branch_ids"] == ("cancelled_due_to_paralysis",)
    assert cancelled["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 8}

    execution, results = _observations(binding, "accuracy_miss")
    executed = reconcile_observed_action_opportunity_rng(
        predictive_authority=adapter,
        predictive_binding=binding,
        predictive_ledger=ledger,
        executed_move_observation=execution,
        previous_action_result_observation=results[0],
    )
    assert executed["compatible_branch_ids"] == ("executes_after_paralysis",)
    assert executed["compatible_original_probability_mass"] == {"numerator": 7, "denominator": 8}

    execution, results = _observations(binding, "full_paralysis")
    damage = _linked_damage(ledger, binding, execution)
    contradiction = reconcile_observed_action_opportunity_rng(
        predictive_authority=adapter,
        predictive_binding=binding,
        predictive_ledger=ledger,
        executed_move_observation=execution,
        previous_action_result_observation=results[0],
        direct_damage_observation=damage,
    )
    assert contradiction["status"] == "resolved"
    assert contradiction["match_outcome"] == "incompatible_observation"
    assert contradiction["compatible_original_probability_mass"] == {"numerator": 0, "denominator": 1}


def test_charge_terminal_wrong_caller_and_lifecycle_reject():
    terminal, ledger, binding, _adapter = _charge_source()

    wrong_caller = deepcopy(terminal)
    wrong_caller["execution_authority"]["original_charge_action_id"] = "attack:forged"
    assert adapt_standard_charge_terminal_paralysis_opportunity(
        terminal_execution=wrong_caller,
        predictive_binding=binding,
        predictive_ledger=ledger,
    )["status"] == "rejected"

    wrong_lifecycle = deepcopy(terminal)
    wrong_lifecycle["execution_authority"]["original_charge_lifecycle"] = {}
    assert adapt_standard_charge_terminal_paralysis_opportunity(
        terminal_execution=wrong_lifecycle,
        predictive_binding=binding,
        predictive_ledger=ledger,
    )["status"] == "rejected"


def _paralysis_runtime_binding(*, snapshot, d0, actor, target, move, turn=1):
    return _binding_for(
        session=actor["session_id"],
        runtime=snapshot["state_fingerprint"],
        branch=d0["strategy_preview_fingerprint"],
        actor=actor,
        target=target,
        move=move,
        turn=turn,
    )


def test_standard_power_herb_same_turn_terminal_uses_same_adapter_without_new_probability_owner():
    state, _s0, _d0 = _ready()
    own = state["self_side"]["pokemon"][0]
    own["known_item"] = "power-herb"
    own["condition"] = "paralysis"
    own["condition_provenance"] = {
        "event_kind": "current_condition_observed",
        "trust": "user_confirmed_observation",
        "condition": "paralysis",
        "turn_number": 1,
    }
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
    terminal = execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    assert terminal["status"] == "resolved", terminal
    ledger, binding = _paralysis_runtime_binding(
        snapshot=snapshot, d0=d0, actor=actor, target=target, move="sky-attack",
    )
    adapter = adapt_standard_charge_terminal_paralysis_opportunity(
        terminal_execution=terminal, predictive_binding=binding, predictive_ledger=ledger,
    )
    assert adapter["status"] == "resolved", adapter
    assert adapter["causal_provenance"]["execution_mode"] == "power_herb_current_turn_skip"
    assert [row["probability"] for row in adapter["branches"]] == [
        {"numerator": 1, "denominator": 8},
        {"numerator": 7, "denominator": 8},
    ]


def test_sunny_solar_same_turn_skip_uses_same_adapter_without_move_special_case():
    state, _snapshot, _d0, _actor, _target, _action = _state_case(
        "solar-beam", weather="sun",
    )
    raw = state["self_side"]["pokemon"][0]
    raw["condition"] = "paralysis"
    raw["condition_provenance"] = {
        "event_kind": "current_condition_observed",
        "trust": "user_confirmed_observation",
        "condition": "paralysis",
        "turn_number": 1,
    }
    snapshot, d0 = _refresh(state)
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = _own_action(d0, actor, "solar-beam")
    readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0, runtime_snapshot=snapshot,
        action=action, actor=actor, target=target,
    )
    assert readiness["outcome"] == "weather_charge_skip_ready"
    execution = freeze_runtime_d0_solar_weather_skip_execution_authority(
        strategy_d0=d0, runtime_snapshot=snapshot,
        action=action, actor=actor, target=target,
        move_metadata={"move_id": "solar-beam"},
        readiness_authority=readiness,
    )
    assert execution["status"] == "resolved", execution
    terminal = execute_runtime_d0_solar_weather_skip(execution_authority=execution)
    assert terminal["status"] == "resolved", terminal
    ledger, binding = _paralysis_runtime_binding(
        snapshot=snapshot, d0=d0, actor=actor, target=target, move="solar-beam",
    )
    adapter = adapt_standard_charge_terminal_paralysis_opportunity(
        terminal_execution=terminal, predictive_binding=binding, predictive_ledger=ledger,
    )
    assert adapter["status"] == "resolved", adapter
    assert adapter["causal_provenance"]["execution_mode"] == "weather_current_turn_skip"
    assert adapter["branches"][0]["branch_id"] == "cancelled_due_to_paralysis"
    assert adapter["branches"][1]["branch_id"] == "executes_after_paralysis"


def test_geomancy_forced_terminal_reuses_gate_but_status_only_rejects_damage_evidence():
    _handoff, _execution_authority, _row, base = _forced_geomancy_contract()
    actor_mechanics = deepcopy(base["actor_mechanics"])
    actor_mechanics["condition"] = {"status": "known_present", "condition": "paralysis"}
    actor_mechanics["direct_mechanics"]["combatant"]["status"] = "paralysis"
    contract = _recontract_geomancy(base, actor_mechanics)
    terminal = execute_geomancy_status_terminal(contract)
    assert terminal["status"] == "resolved", terminal
    caller = contract["caller_action_authority"]
    ledger, binding = _binding_for(
        session=contract["actor"]["session_id"],
        runtime=caller["source_next_decision_fingerprint"],
        branch=caller.get("source_branch_fingerprint", caller["source_next_decision_fingerprint"]),
        actor=contract["actor"], target=contract["target"], move="geomancy", turn=2,
    )
    adapter = adapt_standard_charge_terminal_paralysis_opportunity(
        terminal_execution=terminal, predictive_binding=binding, predictive_ledger=ledger,
    )
    assert adapter["status"] == "resolved", adapter
    assert adapter["direct_damage_execution_evidence_allowed"] is False
    assert adapter["accuracy_miss_execution_evidence_allowed"] is False

    execution, results = _observations(binding, "full_paralysis")
    cancelled = reconcile_observed_action_opportunity_rng(
        predictive_authority=adapter, predictive_binding=binding, predictive_ledger=ledger,
        executed_move_observation=execution, previous_action_result_observation=results[0],
    )
    assert cancelled["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 8}

    execution, results = _observations(binding, "accuracy_miss")
    not_proof = reconcile_observed_action_opportunity_rng(
        predictive_authority=adapter, predictive_binding=binding, predictive_ledger=ledger,
        executed_move_observation=execution, previous_action_result_observation=results[0],
    )
    assert not_proof["status"] == "incomplete"
    assert not_proof["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 1}

    execution, _ = _observations(binding)
    impossible_damage = _linked_damage(ledger, binding, execution)
    rejected = reconcile_observed_action_opportunity_rng(
        predictive_authority=adapter, predictive_binding=binding, predictive_ledger=ledger,
        executed_move_observation=execution, direct_damage_observation=impossible_damage,
    )
    assert rejected["status"] == "rejected"
    assert rejected["reason"] == "direct_damage_not_applicable_to_action_opportunity_prediction"


def test_geomancy_power_herb_same_turn_terminal_uses_same_status_only_adapter():
    snapshot, d0, _own, authority = _power_herb_geomancy_authority(condition="paralysis")
    terminal = execute_runtime_d0_geomancy_power_herb_skip(authority)
    assert terminal["status"] == "resolved", terminal
    actor, target = authority["actor"], authority["target"]
    ledger, binding = _paralysis_runtime_binding(
        snapshot=snapshot, d0=d0, actor=actor, target=target, move="geomancy",
    )
    adapter = adapt_standard_charge_terminal_paralysis_opportunity(
        terminal_execution=terminal, predictive_binding=binding, predictive_ledger=ledger,
    )
    assert adapter["status"] == "resolved", adapter
    assert adapter["causal_provenance"]["execution_mode"] == "power_herb_current_turn_skip"
    assert adapter["direct_damage_execution_evidence_allowed"] is False
    assert [row["probability"] for row in adapter["branches"]] == [
        {"numerator": 1, "denominator": 8},
        {"numerator": 7, "denominator": 8},
    ]


def test_shared_insufficient_observation_and_adapter_tamper_fail_closed():
    for source_builder in (_second_action_source, _charge_source):
        _source, ledger, binding, adapter = source_builder()
        execution, _ = _observations(binding)
        before = deepcopy((adapter, ledger, binding, execution))
        result = reconcile_observed_action_opportunity_rng(
            predictive_authority=adapter,
            predictive_binding=binding,
            predictive_ledger=ledger,
            executed_move_observation=execution,
        )
        assert result["status"] == "incomplete"
        assert result["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 1}
        assert result["probability_normalization"] == "none_preserve_original_mass"
        assert (adapter, ledger, binding, execution) == before

        forged = deepcopy(adapter)
        forged["prediction_fingerprint"] = "0" * 64
        assert reconcile_observed_action_opportunity_rng(
            predictive_authority=forged,
            predictive_binding=binding,
            predictive_ledger=ledger,
            executed_move_observation=execution,
        )["status"] == "rejected"

        foreign = deepcopy(binding)
        foreign["source_action_id"] = "foreign"
        assert reconcile_observed_action_opportunity_rng(
            predictive_authority=adapter,
            predictive_binding=foreign,
            predictive_ledger=ledger,
            executed_move_observation=execution,
        )["status"] == "rejected"
