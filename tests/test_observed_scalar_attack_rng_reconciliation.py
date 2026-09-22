from copy import deepcopy

import pytest

from llm.advisor_detached_observed_rng_reconciliation import (
    BINDING_SCHEMA_VERSION,
    RECONCILIATION_SCHEMA_VERSION,
    link_direct_damage_observation_to_predictive_action,
    materialize_historical_predictive_action_binding,
    reconcile_observed_scalar_attack_rng,
    validate_historical_predictive_action_binding,
)
from llm.advisor_exact_predictive_outcome_ledger import normalize_exact_predictive_outcome_ledger
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    EXECUTED_MOVE_SOURCE,
    PREVIOUS_ACTION_RESULT_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_previous_action_history_observation import admit_previous_action_history_observation
from tests.test_exact_predictive_outcome_ledger import (
    OWNER,
    TARGET,
    _bindings,
    _candidate,
    _hit,
    _manifest,
)


def _ledger(*, move="shadow-ball", critical=True, probability=80, unique_damage=False):
    root = _hit(move, critical="resolved" if critical else "not_applicable", probability=probability)
    if unique_damage:
        consequences = root["branches"][0]["consequences"]
        rolls = consequences["damage_roll_uncertainty"]["outcomes"]
        consequences["damage_roll_uncertainty"]["outcomes"] = tuple(
            {**row, "damage": 20 + index} for index, row in enumerate(rolls)
        )
    result = normalize_exact_predictive_outcome_ledger(
        candidate=_candidate(move),
        predictive_consequence=root,
        component_manifest=_manifest(critical="resolved" if critical else "not_applicable"),
        bindings=_bindings(move),
    )
    assert result["status"] == "evaluable"
    return result


def _binding(ledger=None, *, turn=7):
    result = materialize_historical_predictive_action_binding(
        predictive_ledger=ledger or _ledger(), turn_number=turn,
    )
    assert result["status"] == "resolved"
    return result


def _observations(binding, *, result_class=None):
    boundary = LifecycleConfirmationBoundary(binding["session_id"], {"self": deepcopy(binding["actor"])})
    executed = boundary.confirm(
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
    result = None
    if result_class is not None:
        result = boundary.confirm(
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
            observation_id="result",
            turn_number=binding["turn_number"],
            related_observation_id=executed["observation_id"],
        )["observation"]
    return executed, result


def _raw_damage(binding, *, amount=9, sequence=3):
    def owner(value):
        return {
            **deepcopy(value),
            "source": "ui_observed_damage_confirmation",
            "trust": "user_confirmed_observation",
        }

    return {
        "event_kind": "direct_move_damage_observed",
        "session_id": binding["session_id"],
        "turn_number": binding["turn_number"],
        "attacker": owner(binding["actor"]),
        "defender": owner(binding["target"]),
        "move_id": None,
        "move_slot": None,
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


def _linked_damage(ledger, binding, executed, *, amount=9):
    linked = link_direct_damage_observation_to_predictive_action(
        observation=_raw_damage(binding, amount=amount),
        predictive_binding=binding,
        predictive_ledger=ledger,
        executed_move_observation=executed,
    )
    assert linked.get("reconciliation_eligible") is True
    return linked


def test_pre_action_binding_is_exact_immutable_and_repeated_turn_is_distinct():
    ledger = _ledger()
    before = deepcopy(ledger)
    first = _binding(ledger, turn=7)
    second = _binding(ledger, turn=8)
    assert first["schema_version"] == BINDING_SCHEMA_VERSION
    assert first["source_action_id"] == first["action_link_id"]
    assert first["source_action_id"] != second["source_action_id"]
    assert first["actor"] == OWNER and first["target"] == TARGET
    assert first["move_id"] == "shadow-ball"
    assert first["source_runtime_fingerprint"] == "runtime"
    assert first["source_branch_fingerprint"] == "preview"
    assert ledger == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("session_id", "foreign"),
        ("turn_number", 8),
        ("actor", {**OWNER, "pokemon_id": "wrong"}),
        ("target", {**TARGET, "pokemon_id": "wrong"}),
        ("move_id", "tackle"),
        ("source_runtime_fingerprint", "stale"),
        ("source_branch_fingerprint", "foreign-branch"),
        ("decision_owner", {**OWNER, "pokemon_id": "wrong"}),
        ("source_action_id", "forged-action"),
    ],
)
def test_forged_predictive_binding_rejects_every_exact_identity_dimension(field, value):
    ledger = _ledger()
    binding = _binding(ledger)
    binding[field] = value
    assert validate_historical_predictive_action_binding(
        binding=binding, predictive_ledger=ledger,
    )["status"] == "rejected"


def test_production_executed_action_can_reuse_precreated_action_link():
    ledger = _ledger()
    binding = _binding(ledger, turn=1)
    state = create_unknown_bootstrap_battle_state("ledger-session", "p1", "p2")["state"]
    manager = BattleObservationRuntimeSessionManager.create("ledger-session", state)["manager"]
    result = admit_previous_action_history_observation(
        runtime_session_manager=manager,
        captured_session_id="ledger-session",
        side="self",
        execution_move_id="shadow-ball",
        selected_move_id="shadow-ball",
        source_action_id=binding["source_action_id"],
        result_class="accuracy_miss",
        turn_number=1,
    )
    assert result["status"] == "resolved"
    execution = result["observations"][0]
    assert execution["payload"]["source_action_id"] == binding["source_action_id"]
    assert execution["payload"]["move_id"] == binding["move_id"]
    assert manager.read_state()["state"]["self_side"]["pokemon"][0]["last_executed_move"]["source_action_id"] == binding["source_action_id"]


def test_move_name_equality_without_precreated_link_cannot_reconcile():
    ledger = _ledger()
    binding = _binding(ledger)
    executed, _ = _observations(binding)
    forged = deepcopy(executed)
    forged["payload"]["source_action_id"] = "same-move-but-unlinked"
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=forged,
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "executed_move_action_link_mismatch"


def test_linked_direct_damage_carries_move_action_and_execution_reference_without_mutating_input():
    ledger = _ledger()
    binding = _binding(ledger)
    executed, _ = _observations(binding)
    raw = _raw_damage(binding)
    before = deepcopy(raw)
    linked = link_direct_damage_observation_to_predictive_action(
        observation=raw,
        predictive_binding=binding,
        predictive_ledger=ledger,
        executed_move_observation=executed,
    )
    assert raw == before
    assert linked["move_id"] == binding["move_id"]
    assert linked["source_action_id"] == binding["source_action_id"]
    assert linked["linked_execution_observation_id"] == executed["observation_id"]
    assert linked["reconciliation_eligible"] is True


def test_unlinked_damage_is_not_reconciliation_eligible_and_wrong_owner_link_rejects():
    ledger = _ledger()
    binding = _binding(ledger)
    executed, _ = _observations(binding)
    raw = _raw_damage(binding)
    assert raw["reconciliation_eligible"] is False and raw["move_id"] is None
    wrong = deepcopy(raw)
    wrong["attacker"]["pokemon_id"] = "wrong"
    result = link_direct_damage_observation_to_predictive_action(
        observation=wrong,
        predictive_binding=binding,
        predictive_ledger=ledger,
        executed_move_observation=executed,
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "direct_damage_owner_mismatch"


def test_equal_damage_crit_and_roll_collisions_remain_ambiguous_with_original_mass():
    ledger = _ledger(critical=True, probability=80)
    binding = _binding(ledger)
    executed, _ = _observations(binding)
    damage = _linked_damage(ledger, binding, executed, amount=9)
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=executed,
        direct_damage_observation=damage,
    )
    assert result["status"] == "resolved"
    assert result["schema_version"] == RECONCILIATION_SCHEMA_VERSION
    assert result["match_outcome"] == "multiple_compatible_branches"
    assert len(result["compatible_leaf_ids"]) == 4
    assert result["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 10}
    assert result["probability_normalization"] == "none_preserve_original_mass"
    assert set(result["unresolved_hidden_dimensions"]) >= {"critical_state", "damage_roll"}


def test_unique_exact_damage_produces_unique_match_without_creating_hidden_observation():
    ledger = _ledger(critical=False, probability=100, unique_damage=True)
    binding = _binding(ledger)
    executed, _ = _observations(binding)
    damage = _linked_damage(ledger, binding, executed, amount=27)
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=executed,
        direct_damage_observation=damage,
    )
    assert result["status"] == "resolved"
    assert result["match_outcome"] == "uniquely_matched"
    assert len(result["compatible_leaf_ids"]) == 1
    assert result["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 16}
    assert "critical_state" not in result["matched_observable_facts"]
    assert "damage_roll" not in result["matched_observable_facts"]


def test_impossible_damage_is_incompatible_with_exact_zero_mass():
    ledger = _ledger()
    binding = _binding(ledger)
    executed, _ = _observations(binding)
    damage = _linked_damage(ledger, binding, executed, amount=999)
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=executed,
        direct_damage_observation=damage,
    )
    assert result["status"] == "resolved"
    assert result["match_outcome"] == "incompatible_observation"
    assert result["compatible_leaf_ids"] == ()
    assert result["compatible_original_probability_mass"] == {"numerator": 0, "denominator": 1}


def test_explicit_accuracy_miss_filters_only_miss_and_preserves_original_miss_mass():
    ledger = _ledger(critical=True, probability=80)
    binding = _binding(ledger)
    executed, action_result = _observations(binding, result_class="accuracy_miss")
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=executed,
        previous_action_result_observation=action_result,
    )
    assert result["status"] == "resolved"
    assert result["match_outcome"] == "uniquely_matched"
    assert result["matched_observable_facts"] == {"accuracy_result": "miss"}
    assert result["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 5}


@pytest.mark.parametrize("result_class", [None, "success"])
def test_missing_or_generic_success_does_not_imply_hit_and_is_insufficient(result_class):
    ledger = _ledger()
    binding = _binding(ledger)
    executed, action_result = _observations(binding, result_class=result_class)
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=executed,
        previous_action_result_observation=action_result,
    )
    assert result["status"] == "incomplete"
    assert result["reason"] == "insufficient_observation"
    assert result["compatible_original_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert len(result["compatible_leaf_ids"]) == len(ledger["terminal_leaves"])


@pytest.mark.parametrize(
    "mutation",
    [
        lambda obs: obs.update(session_id="foreign"),
        lambda obs: obs.update(turn_number=99),
        lambda obs: obs.update(side="opponent"),
        lambda obs: obs["payload"].update(move_id="tackle"),
        lambda obs: obs["payload"].update(source_action_id="forged"),
    ],
)
def test_foreign_or_forged_execution_observation_rejects(mutation):
    ledger = _ledger()
    binding = _binding(ledger)
    executed, _ = _observations(binding)
    mutation(executed)
    assert reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=executed,
    )["status"] == "rejected"


def test_prediction_observations_and_runtime_inputs_remain_immutable():
    ledger = _ledger()
    binding = _binding(ledger)
    executed, action_result = _observations(binding, result_class="accuracy_miss")
    originals = tuple(deepcopy(value) for value in (ledger, binding, executed, action_result))
    result = reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=binding,
        executed_move_observation=executed,
        previous_action_result_observation=action_result,
    )
    assert result["status"] == "resolved"
    assert (ledger, binding, executed, action_result) == originals


def test_malformed_predictive_probability_and_stale_replaced_binding_fail_closed():
    ledger = _ledger()
    binding = _binding(ledger)
    malformed = deepcopy(ledger)
    malformed["terminal_leaves"] = list(malformed["terminal_leaves"])
    malformed["terminal_leaves"][0]["probability"] = {"numerator": 1, "denominator": 0}
    executed, _ = _observations(binding)
    assert reconcile_observed_scalar_attack_rng(
        predictive_ledger=malformed,
        predictive_binding=binding,
        executed_move_observation=executed,
    )["status"] == "rejected"

    replacement = _binding(ledger, turn=8)
    assert reconcile_observed_scalar_attack_rng(
        predictive_ledger=ledger,
        predictive_binding=replacement,
        executed_move_observation=executed,
    )["status"] == "rejected"


def test_turn_snapshot_preserves_only_explicit_c5_linkage_metadata():
    from llm.advisor_turn_snapshot import normalize_structured_observed_damage_confirmations

    pokemon = {
        "my_active": {"name_en": "pikachu", "slot_index": 0},
        "opponent_active": {"name_en": "eevee", "slot_index": 1},
    }
    def owner(side, pokemon_id, slot):
        return {
            "session_id": "s0", "side": side, "slot_index": slot, "pokemon_id": pokemon_id,
            "source": "ui_observed_damage_confirmation", "trust": "user_confirmed_observation",
        }
    raw = {
        "event_kind": "direct_move_damage_observed", "session_id": "s0",
        "attacker": owner("self", "pikachu", 0), "defender": owner("opponent", "eevee", 1),
        "move_id": "tackle", "move_slot": None, "source_action_id": "observed-rng:abc",
        "damage_amount": 17, "hp_unit": "exact", "source": "ui_observed_damage_confirmation",
        "trust": "user_confirmed_observation", "observed": True, "confirmed": True,
        "observation_id": "damage-1", "observation_sequence": 3, "turn_number": 2,
        "turn_source": "ui_turn_number_confirmation", "turn_trust": "user_confirmed_observation",
        "reconciliation_eligible": True, "linked_execution_observation_id": "execution-1",
        "predictive_ledger_fingerprint": "a" * 64,
    }
    normalized = normalize_structured_observed_damage_confirmations(
        [raw], pokemon=pokemon, session_id="s0",
    )
    assert len(normalized) == 1
    event = normalized[0]
    assert event["move_id"] == "tackle"
    assert event["source_action_id"] == "observed-rng:abc"
    assert event["reconciliation_eligible"] is True
    assert event["payload"]["mode"] == "action_linked"

    forged = deepcopy(raw)
    forged["reconciliation_eligible"] = False
    assert normalize_structured_observed_damage_confirmations(
        [forged], pokemon=pokemon, session_id="s0",
    ) == []
