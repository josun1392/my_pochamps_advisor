from copy import deepcopy

import pytest

from llm.advisor_action_linked_condition_application_observation import (
    admit_action_linked_condition_application_observation,
)
from llm.advisor_detached_observed_rng_reconciliation import (
    link_condition_application_observation_to_predictive_action,
    materialize_historical_predictive_action_binding,
    reconcile_observed_scalar_attack_rng,
)
from llm.advisor_exact_predictive_outcome_ledger import normalize_exact_predictive_outcome_ledger
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    CONDITION_APPLICATION_SOURCE,
    CURRENT_CONDITION_SOURCE,
    EXECUTED_MOVE_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_previous_action_history_observation import admit_previous_action_history_observation
from llm.advisor_predictive_thunderbolt_paralysis_uncertainty import (
    compose_predictive_thunderbolt_paralysis_uncertainty,
)
from tests.test_predictive_thunderbolt_paralysis_uncertainty import (
    _authority as thunderbolt_authority,
    _candidate as thunderbolt_candidate,
    _interval as thunderbolt_interval,
)


def _owner(session, side, pokemon_id, slot=0):
    return {
        "session_id": session,
        "side": side,
        "slot_index": slot,
        "pokemon_id": pokemon_id,
    }


def _bindings(session="secondary-session", runtime="runtime", branch="preview"):
    actor = _owner(session, "self", "attacker")
    target = _owner(session, "opponent", "target")
    return {
        "session_id": session,
        "source_runtime_fingerprint": runtime,
        "source_branch_fingerprint": branch,
        "decision_owner": deepcopy(actor),
        "attacker": deepcopy(actor),
        "target": deepcopy(target),
        "move_id": "thunderbolt",
    }


def _secondary(bindings, rolls, *, probability=10, eligibility=None):
    leaves = []
    for index, damage in enumerate(rolls):
        mode = eligibility[index] if eligibility is not None else "eligible"
        row = {
            "roll_index": index,
            "random_factor_percent": 85 + index,
            "damage": damage,
            "secondary_eligibility": mode,
        }
        if mode == "eligible":
            row["secondary_branches"] = (
                {
                    "branch": "no_effect",
                    "conditional_secondary_probability": {
                        "numerator": 100 - probability,
                        "denominator": 100,
                    },
                },
                {
                    "branch": "effect",
                    "conditional_secondary_probability": {
                        "numerator": probability,
                        "denominator": 100,
                    },
                    "hypothetical_target_condition": {
                        "schema_version": "detached-hypothetical-current-condition-v1",
                        "owner": deepcopy(bindings["target"]),
                        "previous_condition": {"status": "known_none"},
                        "resulting_condition": "paralysis",
                        "provenance": "thunderbolt_successful_damage_roll_secondary_v1",
                    },
                },
            )
        elif mode == "target_fainted":
            row["secondary_branches"] = ()
        elif mode == "blocked_by_substitute":
            row["secondary_branches"] = (
                {
                    "branch": "no_effect",
                    "conditional_secondary_probability": {"numerator": 1, "denominator": 1},
                },
            )
        else:
            row["secondary_branches"] = (
                {
                    "branch": "no_effect",
                    "conditional_secondary_probability": {"numerator": 1, "denominator": 1},
                },
            )
        leaves.append(row)
    return {
        "status": "resolved",
        "schema_version": "deterministic-predictive-thunderbolt-paralysis-uncertainty-v1",
        **deepcopy(bindings),
        "damage_roll_leaves": tuple(leaves),
    }


def _roll_uncertainty(bindings, rolls, *, critical_scope=None):
    return {
        "status": "resolved",
        "schema_version": "deterministic-predictive-damage-roll-uncertainty-v1",
        "session_id": bindings["session_id"],
        "source_branch_fingerprint": bindings["source_branch_fingerprint"],
        "decision_owner": deepcopy(bindings["decision_owner"]),
        "move_id": "thunderbolt",
        "critical_scope": critical_scope,
        "outcomes": tuple(
            {
                "roll_index": index,
                "random_factor_percent": 85 + index,
                "damage": damage,
                "probability": {"numerator": 1, "denominator": 16},
            }
            for index, damage in enumerate(rolls)
        ),
    }


def _consequence(bindings, rolls, secondary, *, critical_scope=None, hp=100):
    return {
        "interval": {"target_hp_before": hp},
        "damage_roll_uncertainty": _roll_uncertainty(
            bindings, rolls, critical_scope=critical_scope,
        ),
        "thunderbolt_paralysis_uncertainty": deepcopy(secondary),
    }


def _ledger(
    *,
    session="secondary-session",
    runtime="runtime",
    branch="preview",
    rolls=(20,) * 16,
    critical=True,
    probability=10,
    eligibility=None,
    hp=100,
):
    bindings = _bindings(session, runtime, branch)
    secondary = _secondary(
        bindings, rolls, probability=probability, eligibility=eligibility,
    )
    if critical:
        critical_owner = {
            "status": "resolved",
            "schema_version": "deterministic-predictive-critical-hit-uncertainty-v1",
            **deepcopy(bindings),
            "critical_probability": {"numerator": 1, "denominator": 4},
            "branches": (
                {
                    "branch": "non_critical",
                    "conditional_critical_probability": {"numerator": 3, "denominator": 4},
                    "consequences": _consequence(
                        bindings, rolls, secondary, critical_scope="non_critical", hp=hp,
                    ),
                },
                {
                    "branch": "critical",
                    "conditional_critical_probability": {"numerator": 1, "denominator": 4},
                    "consequences": _consequence(
                        bindings, rolls, secondary, critical_scope="critical", hp=hp,
                    ),
                },
            ),
        }
        hit_consequence = {"critical_hit_uncertainty": critical_owner}
    else:
        hit_consequence = _consequence(bindings, rolls, secondary, hp=hp)

    root = {
        "status": "resolved",
        "schema_version": "deterministic-predictive-hit-miss-uncertainty-v1",
        **deepcopy(bindings),
        "probability_percent": 100,
        "branches": (
            {
                "branch": "hit",
                "probability_percent": 100,
                "consequences": hit_consequence,
            },
        ),
    }
    candidate = {
        "candidate_id": "attack:thunderbolt",
        "action_type": "attack",
        "session_id": session,
        "source_branch_fingerprint": branch,
        "decision_owner": deepcopy(bindings["decision_owner"]),
    }
    manifest = {
        "accuracy": {"status": "resolved"},
        "critical": {"status": "resolved" if critical else "not_applicable"},
        "damage_roll": {"status": "resolved"},
        "secondary": {"status": "resolved"},
    }
    result = normalize_exact_predictive_outcome_ledger(
        candidate=candidate,
        predictive_consequence=root,
        component_manifest=manifest,
        bindings=bindings,
    )
    assert result["status"] == "evaluable"
    return result


def _binding(ledger, turn=3):
    result = materialize_historical_predictive_action_binding(
        predictive_ledger=ledger, turn_number=turn,
    )
    assert result["status"] == "resolved"
    return result


def _execution(binding, *, observation_id="execution", sequence=1):
    boundary = LifecycleConfirmationBoundary(
        binding["session_id"], {"self": deepcopy(binding["actor"]), "opponent": deepcopy(binding["target"])},
    )
    confirmed = boundary.confirm(
        event_kind="executed_move_observed",
        payload={"move_id": binding["move_id"], "source_action_id": binding["source_action_id"]},
        session_id=binding["session_id"],
        source=EXECUTED_MOVE_SOURCE,
        trust=USER_TRUST,
        confirmed=True,
        side=binding["actor"]["side"],
        slot_index=binding["actor"]["slot_index"],
        pokemon_id=binding["actor"]["pokemon_id"],
        observation_id=observation_id,
        turn_number=binding["turn_number"],
    )
    observation = confirmed["observation"]
    observation["observation_sequence"] = sequence
    return observation


def _raw_condition(binding, *, condition="paralysis", sequence=2, event_kind="condition_applied_observed"):
    boundary = LifecycleConfirmationBoundary(
        binding["session_id"], {"self": deepcopy(binding["actor"]), "opponent": deepcopy(binding["target"])},
    )
    source = CONDITION_APPLICATION_SOURCE if event_kind == "condition_applied_observed" else CURRENT_CONDITION_SOURCE
    confirmed = boundary.confirm(
        event_kind=event_kind,
        payload={"condition": condition},
        session_id=binding["session_id"],
        source=source,
        trust=USER_TRUST,
        confirmed=True,
        side=binding["target"]["side"],
        slot_index=binding["target"]["slot_index"],
        pokemon_id=binding["target"]["pokemon_id"],
        observation_id=f"{event_kind}:{sequence}",
        turn_number=binding["turn_number"],
    )
    observation = confirmed["observation"]
    observation["observation_sequence"] = sequence
    return observation


def _linked_condition(ledger, binding, execution, *, condition="paralysis"):
    linked = link_condition_application_observation_to_predictive_action(
        observation=_raw_condition(binding, condition=condition),
        predictive_binding=binding,
        predictive_ledger=ledger,
        executed_move_observation=execution,
    )
    assert linked.get("reconciliation_eligible") is True
    return linked


def _raw_damage(binding, *, amount=20, sequence=2):
    def with_provenance(owner):
        return {
            **deepcopy(owner),
            "source": "ui_observed_damage_confirmation",
            "trust": "user_confirmed_observation",
        }
    return {
        "event_kind": "direct_move_damage_observed",
        "session_id": binding["session_id"],
        "turn_number": binding["turn_number"],
        "attacker": with_provenance(binding["actor"]),
        "defender": with_provenance(binding["target"]),
        "move_id": binding["move_id"],
        "move_slot": None,
        "source_action_id": binding["source_action_id"],
        "damage_amount": amount,
        "hp_unit": "exact",
        "source": "ui_observed_damage_confirmation",
        "trust": "user_confirmed_observation",
        "observed": True,
        "confirmed": True,
        "observation_id": "damage",
        "observation_sequence": sequence,
        "reconciliation_eligible": True,
        "linked_execution_observation_id": "execution",
        "predictive_ledger_fingerprint": binding["predictive_ledger_fingerprint"],
    }


def test_real_thunderbolt_predictive_owner_preserves_exact_effect_and_no_effect_branches():
    predictive = compose_predictive_thunderbolt_paralysis_uncertainty(
        candidate=thunderbolt_candidate(),
        interval=thunderbolt_interval(),
        runtime_authority=thunderbolt_authority(),
    )
    assert predictive["status"] == "resolved"
    assert [row["branch"] for row in predictive["damage_roll_leaves"][0]["secondary_branches"]] == [
        "no_effect", "effect"
    ]
    assert predictive["damage_roll_leaves"][0]["secondary_branches"][1][
        "hypothetical_target_condition"
    ]["resulting_condition"] == "paralysis"


def test_action_linked_condition_application_carries_exact_c5_identity():
    ledger = _ledger()
    binding = _binding(ledger)
    execution = _execution(binding)
    raw = _raw_condition(binding)
    linked = link_condition_application_observation_to_predictive_action(
        observation=raw,
        predictive_binding=binding,
        predictive_ledger=ledger,
        executed_move_observation=execution,
    )
    assert linked["move_id"] == "thunderbolt"
    assert linked["source_action_id"] == binding["source_action_id"]
    assert linked["linked_execution_observation_id"] == execution["observation_id"]
    assert linked["predictive_ledger_fingerprint"] == binding["predictive_ledger_fingerprint"]
    assert linked["reconciliation_eligible"] is True
    assert raw.get("reconciliation_eligible") is None


def test_current_condition_snapshot_is_not_secondary_application_evidence():
    ledger = _ledger()
    binding = _binding(ledger)
    execution = _execution(binding)
    current = _raw_condition(binding, event_kind="current_condition_observed")
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=execution,
        target_condition_application_observation=current,
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "condition_application_observation_invalid"


def test_legacy_unlinked_condition_application_remains_observation_but_not_c5_eligible():
    ledger = _ledger()
    binding = _binding(ledger)
    execution = _execution(binding)
    legacy = _raw_condition(binding)
    assert legacy["event_kind"] == "condition_applied_observed"
    assert legacy.get("reconciliation_eligible") is None
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=execution,
        target_condition_application_observation=legacy,
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "condition_application_action_link_mismatch"


def test_linked_paralysis_filters_no_effect_branches_and_preserves_hidden_crit_rolls():
    ledger = _ledger(critical=True, probability=10)
    binding = _binding(ledger)
    execution = _execution(binding)
    condition = _linked_condition(ledger, binding, execution)
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=execution,
        target_condition_application_observation=condition,
    )
    assert result["status"] == "resolved"
    assert result["match_outcome"] == "multiple_compatible_branches"
    assert len(result["compatible_leaf_ids"]) == 32
    assert result["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 10}
    assert result["probability_normalization"] == "none_preserve_original_mass"
    assert result["matched_observable_facts"]["target_condition_applied"] == "paralysis"
    assert set(result["unresolved_hidden_dimensions"]) >= {"critical_state", "damage_roll"}


def test_target_fainted_secondary_ineligible_rolls_are_removed_by_application_evidence():
    eligibility = tuple("target_fainted" if index < 8 else "eligible" for index in range(16))
    ledger = _ledger(critical=False, probability=10, eligibility=eligibility)
    binding = _binding(ledger)
    execution = _execution(binding)
    condition = _linked_condition(ledger, binding, execution)
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=execution,
        target_condition_application_observation=condition,
    )
    assert result["status"] == "resolved"
    assert len(result["compatible_leaf_ids"]) == 8
    assert all("secondary:effect" in leaf_id for leaf_id in result["compatible_leaf_ids"])


def test_substitute_blocked_secondary_is_incompatible_with_successful_application():
    eligibility = ("blocked_by_substitute",) * 16
    ledger = _ledger(critical=False, probability=10, eligibility=eligibility)
    binding = _binding(ledger)
    execution = _execution(binding)
    condition = _linked_condition(ledger, binding, execution)
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=execution,
        target_condition_application_observation=condition,
    )
    assert result["status"] == "resolved"
    assert result["match_outcome"] == "incompatible_observation"
    assert result["compatible_original_probability_mass"] == {"numerator": 0, "denominator": 1}


def test_direct_damage_and_paralysis_filters_compose_without_inferring_roll_or_crit():
    rolls = tuple(20 if index < 4 else 21 for index in range(16))
    ledger = _ledger(rolls=rolls, critical=True, probability=10)
    binding = _binding(ledger)
    execution = _execution(binding)
    condition = _linked_condition(ledger, binding, execution, condition="paralysis")
    damage = _raw_damage(binding, amount=20)
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=execution,
        direct_damage_observation=damage,
        target_condition_application_observation=condition,
    )
    assert result["status"] == "resolved"
    assert result["match_outcome"] == "multiple_compatible_branches"
    assert len(result["compatible_leaf_ids"]) == 8
    assert result["matched_observable_facts"] == {
        "direct_damage": 20,
        "target_condition_applied": "paralysis",
    }
    assert set(result["unresolved_hidden_dimensions"]) >= {"critical_state", "damage_roll"}


def test_unique_damage_plus_secondary_can_leave_one_compatible_leaf():
    rolls = tuple(20 + index for index in range(16))
    ledger = _ledger(rolls=rolls, critical=False, probability=10)
    binding = _binding(ledger)
    execution = _execution(binding)
    condition = _linked_condition(ledger, binding, execution)
    damage = _raw_damage(binding, amount=27)
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=execution,
        direct_damage_observation=damage,
        target_condition_application_observation=condition,
    )
    assert result["status"] == "resolved"
    assert result["match_outcome"] == "uniquely_matched"
    assert result["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 160}


def test_impossible_condition_application_returns_zero_compatible_mass():
    ledger = _ledger(critical=False, probability=10)
    binding = _binding(ledger)
    execution = _execution(binding)
    condition = _linked_condition(ledger, binding, execution, condition="burn")
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=execution,
        target_condition_application_observation=condition,
    )
    assert result["status"] == "resolved"
    assert result["match_outcome"] == "incompatible_observation"
    assert result["compatible_original_probability_mass"] == {"numerator": 0, "denominator": 1}


def test_absence_of_condition_application_does_not_imply_no_effect():
    ledger = _ledger(critical=False, probability=10)
    binding = _binding(ledger)
    execution = _execution(binding)
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=execution,
    )
    assert result["status"] == "incomplete"
    assert result["reason"] == "insufficient_observation"
    assert result["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert any("secondary:effect" in leaf_id for leaf_id in result["compatible_leaf_ids"])
    assert any("secondary:no_effect" in leaf_id for leaf_id in result["compatible_leaf_ids"])


@pytest.mark.parametrize(
    "mutation",
    [
        lambda obs: obs.update(session_id="foreign"),
        lambda obs: obs.update(turn_number=99),
        lambda obs: obs.update(pokemon_id="wrong"),
        lambda obs: obs.update(move_id="tackle"),
        lambda obs: obs.update(source_action_id="forged"),
        lambda obs: obs.update(linked_execution_observation_id="other-execution"),
        lambda obs: obs.update(predictive_ledger_fingerprint="0" * 64),
        lambda obs: obs.update(reconciliation_eligible=False),
    ],
)
def test_condition_application_binding_tamper_rejects(mutation):
    ledger = _ledger()
    binding = _binding(ledger)
    execution = _execution(binding)
    condition = _linked_condition(ledger, binding, execution)
    mutation(condition)
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=execution,
        target_condition_application_observation=condition,
    )
    assert result["status"] == "rejected"


def test_reconciliation_keeps_ledger_binding_execution_and_condition_immutable():
    ledger = _ledger()
    binding = _binding(ledger)
    execution = _execution(binding)
    condition = _linked_condition(ledger, binding, execution)
    originals = deepcopy((ledger, binding, execution, condition))
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=execution,
        target_condition_application_observation=condition,
    )
    assert result["status"] == "resolved"
    assert (ledger, binding, execution, condition) == originals


def test_production_admission_commits_linked_application_without_reconciliation_mutation():
    session = "production-secondary"
    state = create_unknown_bootstrap_battle_state(session, "attacker", "target")["state"]
    state["self_side"]["pokemon"][0]["condition"] = None
    state["self_side"]["pokemon"][0]["condition_provenance"] = None
    state["opponent_side"]["pokemon"][0]["condition"] = None
    state["opponent_side"]["pokemon"][0]["condition_provenance"] = None
    manager = BattleObservationRuntimeSessionManager.create(session, state)["manager"]
    pre = manager.capture_runtime_state_snapshot(session)
    ledger = _ledger(session=session, runtime=pre["state_fingerprint"], critical=False)
    binding = _binding(ledger, turn=1)

    execution_result = admit_previous_action_history_observation(
        runtime_session_manager=manager,
        captured_session_id=session,
        side="self",
        execution_move_id="thunderbolt",
        selected_move_id="thunderbolt",
        source_action_id=binding["source_action_id"],
        result_class=None,
        turn_number=1,
    )
    assert execution_result["status"] == "resolved"
    execution = execution_result["observations"][0]
    before_ledger = deepcopy(ledger)
    admitted = admit_action_linked_condition_application_observation(
        runtime_session_manager=manager,
        captured_session_id=session,
        predictive_binding=binding,
        predictive_ledger=ledger,
        executed_move_observation=execution,
        condition="paralysis",
    )
    assert admitted["status"] == "resolved"
    observation = admitted["observation"]
    assert observation["move_id"] == "thunderbolt"
    assert observation["source_action_id"] == binding["source_action_id"]
    assert observation["linked_execution_observation_id"] == execution["observation_id"]
    assert observation["predictive_ledger_fingerprint"] == binding["predictive_ledger_fingerprint"]
    assert observation["reconciliation_eligible"] is True
    runtime = manager.read_state()["state"]
    assert runtime["opponent_side"]["pokemon"][0]["condition"] == "paralysis"
    assert ledger == before_ledger


def test_production_admission_rejects_preexisting_status_instead_of_claiming_new_application():
    session = "preexisting-secondary"
    state = create_unknown_bootstrap_battle_state(session, "attacker", "target")["state"]
    state["opponent_side"]["pokemon"][0]["condition"] = "paralysis"
    state["opponent_side"]["pokemon"][0]["condition_provenance"] = None
    manager = BattleObservationRuntimeSessionManager.create(session, state)["manager"]
    pre = manager.capture_runtime_state_snapshot(session)
    ledger = _ledger(session=session, runtime=pre["state_fingerprint"], critical=False)
    binding = _binding(ledger, turn=1)
    execution_result = admit_previous_action_history_observation(
        runtime_session_manager=manager,
        captured_session_id=session,
        side="self",
        execution_move_id="thunderbolt",
        selected_move_id="thunderbolt",
        source_action_id=binding["source_action_id"],
        result_class=None,
        turn_number=1,
    )
    execution = execution_result["observations"][0]
    result = admit_action_linked_condition_application_observation(
        runtime_session_manager=manager,
        captured_session_id=session,
        predictive_binding=binding,
        predictive_ledger=ledger,
        executed_move_observation=execution,
        condition="paralysis",
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "target_condition_not_known_none_before_application"


def test_malformed_condition_and_forged_eligibility_without_linkage_reject():
    ledger = _ledger()
    binding = _binding(ledger)
    execution = _execution(binding)

    malformed = _linked_condition(ledger, binding, execution)
    malformed["payload"]["condition"] = "confusion"
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=execution,
        target_condition_application_observation=malformed,
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "condition_application_condition_invalid"

    forged = _raw_condition(binding)
    forged["reconciliation_eligible"] = True
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=execution,
        target_condition_application_observation=forged,
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "condition_application_action_link_mismatch"


def test_detached_reconciliation_does_not_mutate_runtime_or_reducer_state():
    session = "detached-runtime-proof"
    state = create_unknown_bootstrap_battle_state(session, "attacker", "target")["state"]
    state["opponent_side"]["pokemon"][0]["condition"] = None
    state["opponent_side"]["pokemon"][0]["condition_provenance"] = None
    manager = BattleObservationRuntimeSessionManager.create(session, state)["manager"]
    pre = manager.capture_runtime_state_snapshot(session)
    ledger = _ledger(session=session, runtime=pre["state_fingerprint"], critical=False)
    binding = _binding(ledger, turn=1)
    execution = _execution(binding)
    condition = _linked_condition(ledger, binding, execution)
    before = manager.capture_runtime_state_snapshot(session)
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=execution,
        target_condition_application_observation=condition,
    )
    after = manager.capture_runtime_state_snapshot(session)
    assert result["status"] == "resolved"
    assert after == before
