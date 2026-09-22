"""Detached scalar prediction/observation reconciliation for Roadmap C5.

Prediction remains prediction.  This module only authenticates one historical
scalar action binding and filters immutable exact predictive leaves by trusted
observations of that same real action.  It never mutates runtime, reducer, D0,
observations, or the predictive ledger and never renormalizes probability.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from typing import Any, Mapping, Sequence


BINDING_SCHEMA_VERSION = "historical-predictive-action-binding-v1"
RECONCILIATION_SCHEMA_VERSION = "detached-observed-rng-reconciliation-v1"
_LEDGER_SCHEMA_VERSION = "exact-predictive-outcome-ledger-v1"
_BINDING_PROVENANCE = "authenticated_pre_action_scalar_prediction_binding_v1"
_RECONCILIATION_PROVENANCE = "detached_historical_prediction_observation_compatibility_filter_v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def materialize_historical_predictive_action_binding(
    *, predictive_ledger: Mapping[str, Any], turn_number: int,
) -> dict[str, Any]:
    """Freeze one evaluable scalar attack ledger into a pre-action action link."""
    parsed = _validate_scalar_ledger(predictive_ledger)
    if isinstance(parsed, str):
        return _result("rejected", parsed)
    if not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _result("rejected", "invalid_trusted_turn_number")
    binding = parsed["bindings"]
    actor, target = binding["attacker"], binding["target"]
    prediction_fingerprint = _fingerprint(predictive_ledger)
    identity = {
        "session_id": binding["session_id"],
        "turn_number": turn_number,
        "actor": actor,
        "target": target,
        "move_id": binding["move_id"],
        "candidate_id": predictive_ledger["candidate_id"],
        "source_runtime_fingerprint": binding["source_runtime_fingerprint"],
        "source_branch_fingerprint": binding["source_branch_fingerprint"],
        "decision_owner": binding["decision_owner"],
        "predictive_ledger_fingerprint": prediction_fingerprint,
    }
    action_link_id = "observed-rng:" + hashlib.sha256(_canonical_bytes(identity)).hexdigest()[:24]
    return {
        "status": "resolved",
        "schema_version": BINDING_SCHEMA_VERSION,
        **deepcopy(identity),
        "source_action_id": action_link_id,
        "action_link_id": action_link_id,
        "prediction_identity": {
            "schema_version": _LEDGER_SCHEMA_VERSION,
            "candidate_id": predictive_ledger["candidate_id"],
            "predictive_ledger_fingerprint": prediction_fingerprint,
        },
        "provenance": _BINDING_PROVENANCE,
    }


def validate_historical_predictive_action_binding(
    *, binding: Mapping[str, Any], predictive_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the immutable binding against the exact historical ledger."""
    if not isinstance(binding, Mapping):
        return _result("rejected", "historical_predictive_binding_missing")
    turn = binding.get("turn_number")
    expected = materialize_historical_predictive_action_binding(
        predictive_ledger=predictive_ledger, turn_number=turn,
    )
    if expected.get("status") != "resolved":
        return expected
    if dict(binding) != expected:
        return _result("rejected", "historical_predictive_binding_mismatch")
    return deepcopy(expected)


def link_direct_damage_observation_to_predictive_action(
    *, observation: Mapping[str, Any], predictive_binding: Mapping[str, Any],
    predictive_ledger: Mapping[str, Any], executed_move_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a linked copy only when the real execution and prediction already agree."""
    checked = validate_historical_predictive_action_binding(
        binding=predictive_binding, predictive_ledger=predictive_ledger,
    )
    if checked.get("status") != "resolved":
        return checked
    execution_error = _validate_execution_observation(executed_move_observation, checked)
    if execution_error is not None:
        return _result("rejected", execution_error)
    if not isinstance(observation, Mapping) or observation.get("event_kind") != "direct_move_damage_observed":
        return _result("rejected", "direct_damage_observation_invalid")
    if (
        observation.get("session_id") != checked["session_id"]
        or observation.get("turn_number") != checked["turn_number"]
        or observation.get("source") != "ui_observed_damage_confirmation"
        or observation.get("trust") != "user_confirmed_observation"
        or observation.get("observed") is not True
        or observation.get("confirmed") is not True
    ):
        return _result("rejected", "direct_damage_observation_context_mismatch")
    amount = observation.get("damage_amount")
    if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0 or observation.get("hp_unit") != "exact":
        return _result("rejected", "direct_damage_amount_invalid")
    if observation.get("move_id") not in {None, checked["move_id"]} or observation.get("source_action_id") not in {None, checked["source_action_id"]}:
        return _result("rejected", "direct_damage_preexisting_link_conflict")
    if not _owner_identity_equal(observation.get("attacker"), checked["actor"]) or not _owner_identity_equal(observation.get("defender"), checked["target"]):
        return _result("rejected", "direct_damage_owner_mismatch")
    linked = deepcopy(dict(observation))
    linked.update(
        move_id=checked["move_id"],
        source_action_id=checked["source_action_id"],
        reconciliation_eligible=True,
        linked_execution_observation_id=executed_move_observation["observation_id"],
        predictive_ledger_fingerprint=checked["predictive_ledger_fingerprint"],
    )
    return linked


def link_condition_application_observation_to_predictive_action(
    *, observation: Mapping[str, Any], predictive_binding: Mapping[str, Any],
    predictive_ledger: Mapping[str, Any], executed_move_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a linked condition-application copy only after exact action authentication."""
    checked = validate_historical_predictive_action_binding(
        binding=predictive_binding, predictive_ledger=predictive_ledger,
    )
    if checked.get("status") != "resolved":
        return checked
    execution_error = _validate_execution_observation(executed_move_observation, checked)
    if execution_error is not None:
        return _result("rejected", execution_error)
    if not isinstance(observation, Mapping) or observation.get("event_kind") != "condition_applied_observed":
        return _result("rejected", "condition_application_observation_invalid")
    if (
        observation.get("session_id") != checked["session_id"]
        or observation.get("turn_number") != checked["turn_number"]
        or observation.get("source") != "ui_condition_application_confirmation"
        or observation.get("trust") != "user_confirmed_observation"
        or observation.get("observed") is not True
        or observation.get("confirmed") is not True
    ):
        return _result("rejected", "condition_application_context_mismatch")
    if not _owner_identity_equal(
        {
            "session_id": observation.get("session_id"),
            "side": observation.get("side"),
            "slot_index": observation.get("slot_index"),
            "pokemon_id": observation.get("pokemon_id"),
        },
        checked["target"],
    ):
        return _result("rejected", "condition_application_target_mismatch")
    condition = _payload(observation).get("condition")
    if condition not in {"burn", "poison", "toxic", "paralysis", "sleep", "freeze"}:
        return _result("rejected", "condition_application_condition_invalid")
    if observation.get("move_id") not in {None, checked["move_id"]} or observation.get("source_action_id") not in {None, checked["source_action_id"]}:
        return _result("rejected", "condition_application_preexisting_link_conflict")
    linked = deepcopy(dict(observation))
    linked.update(
        move_id=checked["move_id"],
        source_action_id=checked["source_action_id"],
        reconciliation_eligible=True,
        linked_execution_observation_id=executed_move_observation["observation_id"],
        predictive_ledger_fingerprint=checked["predictive_ledger_fingerprint"],
    )
    return linked


def reconcile_observed_scalar_attack_rng(
    *,
    predictive_ledger: Mapping[str, Any],
    predictive_binding: Mapping[str, Any],
    executed_move_observation: Mapping[str, Any],
    previous_action_result_observation: Mapping[str, Any] | None = None,
    direct_damage_observation: Mapping[str, Any] | None = None,
    target_condition_application_observation: Mapping[str, Any] | None = None,
    flinch_causality_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Filter original scalar terminal leaves by exact linked observations."""
    baseline_ledger = deepcopy(predictive_ledger)
    baseline_binding = deepcopy(predictive_binding)
    baseline_execution = deepcopy(executed_move_observation)
    baseline_result = deepcopy(previous_action_result_observation)
    baseline_damage = deepcopy(direct_damage_observation)
    baseline_condition = deepcopy(target_condition_application_observation)
    baseline_flinch = deepcopy(flinch_causality_observation)

    parsed = _validate_scalar_ledger(predictive_ledger)
    if isinstance(parsed, str):
        return _result("rejected", parsed)
    checked_binding = validate_historical_predictive_action_binding(
        binding=predictive_binding, predictive_ledger=predictive_ledger,
    )
    if checked_binding.get("status") != "resolved":
        return checked_binding
    execution_error = _validate_execution_observation(executed_move_observation, checked_binding)
    if execution_error is not None:
        return _result("rejected", execution_error)

    source_observations = [executed_move_observation]
    constraints: list[tuple[str, Any]] = []
    matched_facts: dict[str, Any] = {}

    if previous_action_result_observation is not None:
        result_error = _validate_result_observation(
            previous_action_result_observation, checked_binding, executed_move_observation,
        )
        if result_error is not None:
            return _result("rejected", result_error)
        source_observations.append(previous_action_result_observation)
        result_class = _payload(previous_action_result_observation).get("result_class")
        if result_class == "accuracy_miss":
            constraints.append(("hit_state", "miss"))
            matched_facts["accuracy_result"] = "miss"
        elif result_class == "success":
            # Existing history semantics do not prove a landed hit.
            matched_facts["action_result"] = "success_non_hit_proof"

    if direct_damage_observation is not None:
        damage_error = _validate_direct_damage_observation(
            direct_damage_observation, checked_binding, executed_move_observation,
        )
        if damage_error is not None:
            return _result("rejected", damage_error)
        source_observations.append(direct_damage_observation)
        damage_amount = direct_damage_observation.get("damage_amount")
        if damage_amount is None:
            damage_amount = _payload(direct_damage_observation).get("damage_amount")
        constraints.append(("actual_damage", damage_amount))
        matched_facts["direct_damage"] = damage_amount

    if target_condition_application_observation is not None:
        condition_error = _validate_condition_application_observation(
            target_condition_application_observation, checked_binding, executed_move_observation,
        )
        if condition_error is not None:
            return _result("rejected", condition_error)
        source_observations.append(target_condition_application_observation)
        condition = _payload(target_condition_application_observation).get("condition")
        constraints.append(("target_condition_applied", condition))
        matched_facts["target_condition_applied"] = condition

    if flinch_causality_observation is not None:
        flinch_error = _validate_flinch_causality_observation(
            flinch_causality_observation, checked_binding, executed_move_observation,
        )
        if flinch_error is not None:
            return _result("rejected", flinch_error)
        source_observations.append(flinch_causality_observation)
        constraints.append(("target_flinch_caused", checked_binding["target"]))
        matched_facts["target_flinch_caused"] = {
            "affected_owner": deepcopy(checked_binding["target"]),
            "cancelled_source_action_id": flinch_causality_observation["cancelled_source_action_id"],
        }

    if not constraints:
        return _reconciliation_result(
            status="incomplete", reason="insufficient_observation", binding=checked_binding,
            ledger=predictive_ledger, observations=source_observations,
            compatible_leaves=tuple(parsed["terminal_leaves"]),
            matched_observable_facts=matched_facts,
        )

    compatible = []
    for leaf in parsed["terminal_leaves"]:
        if all(_leaf_matches(leaf, name, expected) for name, expected in constraints):
            compatible.append(leaf)

    result = _reconciliation_result(
        status="resolved", reason=None, binding=checked_binding,
        ledger=predictive_ledger, observations=source_observations,
        compatible_leaves=tuple(compatible), matched_observable_facts=matched_facts,
    )
    if predictive_ledger != baseline_ledger or predictive_binding != baseline_binding:
        return _result("rejected", "reconciliation_input_mutated")
    if executed_move_observation != baseline_execution or previous_action_result_observation != baseline_result or direct_damage_observation != baseline_damage or target_condition_application_observation != baseline_condition or flinch_causality_observation != baseline_flinch:
        return _result("rejected", "reconciliation_observation_mutated")
    return result


def reconcile_observed_action_opportunity_rng(
    *,
    predictive_authority: Mapping[str, Any],
    predictive_binding: Mapping[str, Any],
    predictive_ledger: Mapping[str, Any],
    executed_move_observation: Mapping[str, Any],
    previous_action_result_observation: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    direct_damage_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Reconcile exact current-paralysis action-opportunity branches.

    Executed-move history authenticates the real action identity only.  It is
    deliberately not evidence that the paralysis gate was passed.
    """
    from llm.advisor_current_action_paralysis_opportunity_authority import (
        SCHEMA_VERSION as CURRENT_PARALYSIS_OPPORTUNITY_SCHEMA,
        validate_current_action_paralysis_opportunity_authority,
    )
    from llm.advisor_existing_paralysis_opportunity_reconciliation_adapters import (
        SCHEMA_VERSION as EXISTING_PARALYSIS_ADAPTER_SCHEMA,
        validate_existing_paralysis_opportunity_adapter,
    )

    baseline = deepcopy((
        predictive_authority, predictive_binding, predictive_ledger,
        executed_move_observation, previous_action_result_observation,
        direct_damage_observation,
    ))
    checked_binding = validate_historical_predictive_action_binding(
        binding=predictive_binding, predictive_ledger=predictive_ledger,
    )
    if checked_binding.get("status") != "resolved":
        return checked_binding
    if predictive_authority.get("schema_version") == CURRENT_PARALYSIS_OPPORTUNITY_SCHEMA:
        authority = validate_current_action_paralysis_opportunity_authority(
            authority=predictive_authority,
            predictive_binding=predictive_binding,
            predictive_ledger=predictive_ledger,
        )
    elif predictive_authority.get("schema_version") == EXISTING_PARALYSIS_ADAPTER_SCHEMA:
        authority = validate_existing_paralysis_opportunity_adapter(
            adapter=predictive_authority,
            predictive_binding=predictive_binding,
            predictive_ledger=predictive_ledger,
        )
    else:
        return _result("rejected", "action_opportunity_prediction_schema_invalid")
    if authority.get("status") != "resolved":
        return authority
    execution_error = _validate_execution_observation(
        executed_move_observation, checked_binding,
    )
    if execution_error is not None:
        return _result("rejected", execution_error)

    results: list[Mapping[str, Any]] = []
    if previous_action_result_observation is not None:
        if isinstance(previous_action_result_observation, Mapping):
            results = [previous_action_result_observation]
        elif isinstance(previous_action_result_observation, Sequence) and not isinstance(previous_action_result_observation, (str, bytes)):
            results = list(previous_action_result_observation)
        else:
            return _result("rejected", "previous_action_result_observation_invalid")

    observations: list[Mapping[str, Any]] = [executed_move_observation]
    matched: dict[str, Any] = {}
    require_cancelled = False
    require_executed = False
    for row in results:
        error = _validate_result_observation(row, checked_binding, executed_move_observation)
        if error is not None:
            return _result("rejected", error)
        observations.append(row)
        result_class = _payload(row).get("result_class")
        if result_class == "full_paralysis":
            require_cancelled = True
            matched.setdefault("action_result_classes", []).append("full_paralysis")
        elif result_class == "accuracy_miss":
            if authority.get("accuracy_miss_execution_evidence_allowed", True) is True:
                require_executed = True
                matched.setdefault("action_result_classes", []).append("accuracy_miss")
            else:
                matched.setdefault("action_result_classes", []).append("accuracy_miss_not_applicable_to_prediction")
        elif result_class == "success":
            matched.setdefault("action_result_classes", []).append("success_non_execution_proof")

    if direct_damage_observation is not None:
        error = _validate_direct_damage_observation(
            direct_damage_observation, checked_binding, executed_move_observation,
        )
        if error is not None:
            return _result("rejected", error)
        observations.append(direct_damage_observation)
        if authority.get("direct_damage_execution_evidence_allowed", True) is not True:
            return _result("rejected", "direct_damage_not_applicable_to_action_opportunity_prediction")
        require_executed = True
        amount = direct_damage_observation.get("damage_amount")
        if amount is None:
            amount = _payload(direct_damage_observation).get("damage_amount")
        matched["linked_direct_damage"] = amount

    branches = tuple(authority["branches"])
    if not require_cancelled and not require_executed:
        result = _action_opportunity_reconciliation_result(
            status="incomplete", reason="insufficient_observation",
            binding=checked_binding, authority=authority, observations=observations,
            compatible_branches=branches, matched_observable_facts=matched,
        )
    else:
        compatible = []
        for branch in branches:
            if require_cancelled and branch.get("state") != "cancelled_due_to_paralysis":
                continue
            if require_executed and branch.get("state") != "executed":
                continue
            compatible.append(branch)
        result = _action_opportunity_reconciliation_result(
            status="resolved", reason=None,
            binding=checked_binding, authority=authority, observations=observations,
            compatible_branches=tuple(compatible), matched_observable_facts=matched,
        )

    current = (
        predictive_authority, predictive_binding, predictive_ledger,
        executed_move_observation, previous_action_result_observation,
        direct_damage_observation,
    )
    if deepcopy(current) != baseline:
        return _result("rejected", "reconciliation_input_mutated")
    return result


def _action_opportunity_reconciliation_result(
    *,
    status: str,
    reason: str | None,
    binding: Mapping[str, Any],
    authority: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
    compatible_branches: Sequence[Mapping[str, Any]],
    matched_observable_facts: Mapping[str, Any],
) -> dict[str, Any]:
    mass = sum(
        (_fraction(branch.get("probability")) or Fraction() for branch in compatible_branches),
        Fraction(),
    )
    if status == "resolved":
        outcome = (
            "incompatible_observation" if not compatible_branches
            else "uniquely_matched" if len(compatible_branches) == 1
            else "multiple_compatible_branches"
        )
        uniqueness = (
            "none" if not compatible_branches
            else "unique" if len(compatible_branches) == 1
            else "ambiguous"
        )
    else:
        outcome = None
        uniqueness = "ambiguous"
    return {
        "status": status,
        "schema_version": RECONCILIATION_SCHEMA_VERSION,
        "reason": reason,
        **{
            key: deepcopy(binding[key])
            for key in (
                "session_id", "turn_number", "actor", "target", "move_id",
                "source_action_id", "source_runtime_fingerprint",
                "source_branch_fingerprint", "decision_owner",
            )
        },
        "source_prediction_kind": "action_opportunity_execution",
        "source_prediction_identity": deepcopy(authority["prediction_identity"]),
        "source_observations": tuple({
            "observation_id": row.get("observation_id"),
            "observation_sequence": _sequence(row),
            "event_kind": row.get("event_kind"),
        } for row in observations),
        "match_outcome": outcome,
        "compatible_branch_ids": tuple(
            branch["branch_id"] for branch in compatible_branches
        ),
        "compatible_original_probability_mass": _fd(mass),
        "probability_normalization": "none_preserve_original_mass",
        "matched_observable_facts": deepcopy(dict(matched_observable_facts)),
        "unresolved_hidden_dimensions": (
            ("paralysis_action_opportunity",) if len(compatible_branches) > 1 else ()
        ),
        "uniqueness": uniqueness,
        "provenance": _RECONCILIATION_PROVENANCE,
    }


def _validate_scalar_ledger(value: Any) -> dict[str, Any] | str:
    if not isinstance(value, Mapping):
        return "predictive_ledger_missing"
    if value.get("status") != "evaluable" or value.get("schema_version") != _LEDGER_SCHEMA_VERSION:
        return "predictive_ledger_not_evaluable"
    if value.get("action_type") != "attack" or not isinstance(value.get("candidate_id"), str):
        return "predictive_ledger_not_scalar_attack"
    if value.get("aggregation") != "none_preserve_roll_identity" or value.get("provenance") != "strict_detached_predictive_outcome_normalization_v1":
        return "predictive_ledger_provenance_invalid"
    manifest = value.get("component_manifest")
    if (
        not isinstance(manifest, Mapping)
        or set(manifest) != {"status", "accuracy", "critical", "damage_roll", "secondary"}
        or manifest.get("status") != "resolved"
        or any(manifest.get(name) not in {"resolved", "not_applicable"} for name in ("accuracy", "critical", "damage_roll", "secondary"))
    ):
        return "predictive_ledger_component_manifest_invalid"
    bindings = value.get("bindings")
    if not isinstance(bindings, Mapping):
        return "predictive_ledger_bindings_missing"
    required = (
        "session_id", "source_runtime_fingerprint", "source_branch_fingerprint",
        "decision_owner", "attacker", "target", "move_id",
    )
    if not all(key in bindings for key in required):
        return "predictive_ledger_binding_incomplete"
    if not all(isinstance(bindings.get(key), str) and bindings[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "move_id")):
        return "predictive_ledger_binding_invalid"
    if not all(_owner(bindings.get(key), bindings["session_id"]) for key in ("decision_owner", "attacker", "target")):
        return "predictive_ledger_owner_invalid"
    if bindings["decision_owner"] != bindings["attacker"]:
        return "predictive_ledger_decision_owner_mismatch"
    if value["candidate_id"] != f"attack:{bindings['move_id']}":
        return "predictive_ledger_candidate_move_mismatch"
    leaves = value.get("terminal_leaves")
    if not isinstance(leaves, (tuple, list)) or not leaves:
        return "predictive_terminal_leaves_missing"
    ids: set[str] = set()
    mass = Fraction()
    for leaf in leaves:
        if not isinstance(leaf, Mapping) or not isinstance(leaf.get("leaf_id"), str) or not leaf["leaf_id"] or leaf["leaf_id"] in ids:
            return "predictive_leaf_identity_invalid"
        if leaf.get("candidate_id") != value["candidate_id"] or leaf.get("action_type") != "attack" or leaf.get("provenance") != dict(bindings):
            return "predictive_leaf_binding_mismatch"
        probability = _fraction(leaf.get("probability"))
        if probability is None or probability <= 0:
            return "predictive_leaf_probability_invalid"
        hit_state = leaf.get("hit_state")
        if hit_state not in {"hit", "miss"}:
            return "predictive_leaf_hit_state_invalid"
        consequences = leaf.get("consequences")
        source_hit = consequences.get("source_hit_context") if isinstance(consequences, Mapping) else None
        if not isinstance(source_hit, Mapping) or source_hit.get("source_action_id") != value["candidate_id"] or source_hit.get("source_move_id") != bindings["move_id"]:
            return "predictive_leaf_source_hit_context_invalid"
        actual_damage = source_hit.get("actual_damage")
        if isinstance(actual_damage, bool) or not isinstance(actual_damage, int) or actual_damage < 0:
            return "predictive_leaf_actual_damage_invalid"
        if hit_state == "miss" and actual_damage != 0:
            return "predictive_miss_damage_invalid"
        ids.add(leaf["leaf_id"])
        mass += probability
    declared = _fraction(value.get("terminal_probability_mass"))
    if declared != Fraction(1, 1) or mass != Fraction(1, 1):
        return "predictive_root_probability_mass_invalid"
    return {"bindings": deepcopy(dict(bindings)), "terminal_leaves": tuple(leaves)}


def _validate_execution_observation(value: Any, binding: Mapping[str, Any]) -> str | None:
    if not isinstance(value, Mapping) or value.get("event_kind") != "executed_move_observed":
        return "executed_move_observation_missing"
    if not _common_observation(value, binding, actor=True):
        return "executed_move_observation_binding_mismatch"
    payload = _payload(value)
    if payload.get("move_id") != binding["move_id"] or payload.get("source_action_id") != binding["source_action_id"]:
        return "executed_move_action_link_mismatch"
    return None


def _validate_result_observation(value: Any, binding: Mapping[str, Any], execution: Mapping[str, Any]) -> str | None:
    if not isinstance(value, Mapping) or value.get("event_kind") != "previous_action_result_observed":
        return "previous_action_result_observation_invalid"
    if not _common_observation(value, binding, actor=True):
        return "previous_action_result_binding_mismatch"
    payload = _payload(value)
    if (
        payload.get("previous_action_id") != binding["source_action_id"]
        or payload.get("selected_move_id") != binding["move_id"]
        or payload.get("execution_move_id") != binding["move_id"]
        or payload.get("result_class") not in {
            "accuracy_miss", "type_or_ability_immunity", "move_specific_failure",
            "full_paralysis", "flinch", "sleep", "freeze", "success",
            "protection_block", "recharge", "sky_drop",
        }
    ):
        return "previous_action_result_action_link_mismatch"
    if value.get("related_observation_id") not in {None, execution.get("observation_id")}:
        return "previous_action_result_execution_reference_mismatch"
    if _sequence(value) <= _sequence(execution):
        return "previous_action_result_sequence_invalid"
    return None


def _validate_direct_damage_observation(value: Any, binding: Mapping[str, Any], execution: Mapping[str, Any]) -> str | None:
    if not isinstance(value, Mapping) or value.get("event_kind") != "direct_move_damage_observed":
        return "direct_damage_observation_invalid"
    if value.get("session_id") != binding["session_id"] or value.get("turn_number") != binding["turn_number"]:
        return "direct_damage_session_or_turn_mismatch"
    if value.get("source") != "ui_observed_damage_confirmation" or value.get("trust") != "user_confirmed_observation" or value.get("observed") is not True or value.get("confirmed") is not True:
        return "direct_damage_provenance_invalid"
    if value.get("move_id") != binding["move_id"] or value.get("source_action_id") != binding["source_action_id"]:
        return "direct_damage_action_link_mismatch"
    if not _owner_identity_equal(value.get("attacker"), binding["actor"]) or not _owner_identity_equal(value.get("defender"), binding["target"]):
        return "direct_damage_owner_mismatch"
    amount = value.get("damage_amount")
    if amount is None:
        amount = _payload(value).get("damage_amount")
    if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0 or value.get("hp_unit", _payload(value).get("hp_unit")) != "exact":
        return "direct_damage_amount_invalid"
    if value.get("reconciliation_eligible") is not True:
        return "direct_damage_not_reconciliation_eligible"
    if value.get("linked_execution_observation_id") != execution.get("observation_id"):
        return "direct_damage_execution_reference_mismatch"
    if _sequence(value) <= _sequence(execution):
        return "direct_damage_sequence_invalid"
    return None


def _validate_condition_application_observation(value: Any, binding: Mapping[str, Any], execution: Mapping[str, Any]) -> str | None:
    if not isinstance(value, Mapping) or value.get("event_kind") != "condition_applied_observed":
        return "condition_application_observation_invalid"
    if (
        value.get("session_id") != binding["session_id"]
        or value.get("turn_number") != binding["turn_number"]
        or value.get("source") != "ui_condition_application_confirmation"
        or value.get("trust") != "user_confirmed_observation"
        or value.get("observed") is not True
        or value.get("confirmed") is not True
    ):
        return "condition_application_provenance_invalid"
    target = {
        "session_id": value.get("session_id"),
        "side": value.get("side"),
        "slot_index": value.get("slot_index"),
        "pokemon_id": value.get("pokemon_id"),
    }
    if not _owner_identity_equal(target, binding["target"]):
        return "condition_application_target_mismatch"
    condition = _payload(value).get("condition")
    if condition not in {"burn", "poison", "toxic", "paralysis", "sleep", "freeze"}:
        return "condition_application_condition_invalid"
    if value.get("move_id") != binding["move_id"] or value.get("source_action_id") != binding["source_action_id"]:
        return "condition_application_action_link_mismatch"
    if value.get("linked_execution_observation_id") != execution.get("observation_id"):
        return "condition_application_execution_reference_mismatch"
    if value.get("predictive_ledger_fingerprint") != binding["predictive_ledger_fingerprint"]:
        return "condition_application_prediction_reference_mismatch"
    if value.get("reconciliation_eligible") is not True:
        return "condition_application_not_reconciliation_eligible"
    if _sequence(value) <= _sequence(execution):
        return "condition_application_sequence_invalid"
    return None


def _validate_flinch_causality_observation(value: Any, binding: Mapping[str, Any], execution: Mapping[str, Any]) -> str | None:
    if not isinstance(value, Mapping) or value.get("event_kind") != "flinch_causality_observed":
        return "flinch_causality_observation_invalid"
    if binding.get("move_id") != "iron-head":
        return "flinch_causality_producer_not_supported_in_v1"
    if (
        value.get("session_id") != binding["session_id"]
        or value.get("turn_number") != binding["turn_number"]
        or value.get("source") != "ui_flinch_causality_confirmation"
        or value.get("trust") != "user_confirmed_observation"
        or value.get("observed") is not True
        or value.get("confirmed") is not True
        or value.get("reducer_eligibility") != "evidence_only"
        or value.get("provenance") != "authenticated_c5_cross_action_flinch_causality_v1"
        or value.get("reconciliation_eligible") is not True
    ):
        return "flinch_causality_provenance_invalid"
    payload = _payload(value)
    if (
        value.get("producer_source_action_id") != binding["source_action_id"]
        or payload.get("producer_source_action_id") != binding["source_action_id"]
        or value.get("producer_move_id") != binding["move_id"]
        or payload.get("producer_move_id") != binding["move_id"]
        or value.get("producer_execution_observation_id") != execution.get("observation_id")
        or payload.get("producer_execution_observation_id") != execution.get("observation_id")
        or value.get("producer_predictive_ledger_fingerprint") != binding["predictive_ledger_fingerprint"]
        or payload.get("producer_predictive_ledger_fingerprint") != binding["predictive_ledger_fingerprint"]
    ):
        return "flinch_causality_producer_binding_mismatch"
    if not _owner_identity_equal(value.get("producer_owner"), binding["actor"]) or not _owner_identity_equal(payload.get("producer_owner"), binding["actor"]):
        return "flinch_causality_producer_owner_mismatch"
    if not _owner_identity_equal(value.get("affected_owner"), binding["target"]) or not _owner_identity_equal(payload.get("affected_owner"), binding["target"]):
        return "flinch_causality_affected_owner_mismatch"
    cancelled_action_id = value.get("cancelled_source_action_id")
    if (
        cancelled_action_id != payload.get("cancelled_source_action_id")
        or not isinstance(cancelled_action_id, str) or not cancelled_action_id
        or cancelled_action_id == binding["source_action_id"]
        or value.get("cancelled_move_id") != payload.get("cancelled_move_id")
        or value.get("cancelled_execution_observation_id") != payload.get("cancelled_execution_observation_id")
        or value.get("cancelled_result_observation_id") != payload.get("cancelled_result_observation_id")
    ):
        return "flinch_causality_cancelled_action_binding_mismatch"
    if not all(isinstance(value.get(key), str) and bool(value[key]) for key in (
        "cancelled_move_id", "cancelled_execution_observation_id", "cancelled_result_observation_id",
    )):
        return "flinch_causality_cancelled_reference_invalid"
    if _sequence(value) <= _sequence(execution):
        return "flinch_causality_sequence_invalid"
    return None


def _common_observation(value: Mapping[str, Any], binding: Mapping[str, Any], *, actor: bool) -> bool:
    if value.get("session_id") != binding["session_id"] or value.get("turn_number") != binding["turn_number"]:
        return False
    if value.get("trust") != "user_confirmed_observation" or value.get("observed") is not True or value.get("confirmed") is not True:
        return False
    if actor and (value.get("side"), value.get("slot_index"), value.get("pokemon_id")) != (
        binding["actor"]["side"], binding["actor"]["slot_index"], binding["actor"]["pokemon_id"],
    ):
        return False
    return isinstance(value.get("observation_id"), str) and bool(value["observation_id"]) and _sequence(value) > 0


def _leaf_matches(leaf: Mapping[str, Any], field: str, expected: Any) -> bool:
    if field == "hit_state":
        return leaf.get("hit_state") == expected
    if field == "actual_damage":
        consequences = leaf.get("consequences")
        source = consequences.get("source_hit_context") if isinstance(consequences, Mapping) else None
        return isinstance(source, Mapping) and source.get("actual_damage") == expected
    if field == "target_condition_applied":
        consequences = leaf.get("consequences")
        secondary = consequences.get("secondary") if isinstance(consequences, Mapping) else None
        if not isinstance(secondary, Mapping) or secondary.get("branch") != "effect":
            return False
        hypothetical = secondary.get("hypothetical_target_condition")
        if not isinstance(hypothetical, Mapping):
            return False
        owner = hypothetical.get("owner")
        return (
            hypothetical.get("schema_version") == "detached-hypothetical-current-condition-v1"
            and hypothetical.get("resulting_condition") == expected
            and isinstance(owner, Mapping)
            and _owner_identity_equal(owner, leaf.get("provenance", {}).get("target"))
        )
    if field == "target_flinch_caused":
        consequences = leaf.get("consequences")
        secondary = consequences.get("secondary") if isinstance(consequences, Mapping) else None
        hypothetical = secondary.get("hypothetical_target_flinch") if isinstance(secondary, Mapping) else None
        return (
            isinstance(secondary, Mapping)
            and secondary.get("branch") == "effect"
            and isinstance(hypothetical, Mapping)
            and hypothetical.get("schema_version") == "detached-hypothetical-immediate-flinch-v1"
            and hypothetical.get("state") == "flinched"
            and _owner_identity_equal(leaf.get("provenance", {}).get("target"), expected)
        )
    return False


def _reconciliation_result(
    *, status: str, reason: str | None, binding: Mapping[str, Any],
    ledger: Mapping[str, Any], observations: Sequence[Mapping[str, Any]],
    compatible_leaves: Sequence[Mapping[str, Any]], matched_observable_facts: Mapping[str, Any],
) -> dict[str, Any]:
    mass = sum((_fraction(leaf.get("probability")) or Fraction() for leaf in compatible_leaves), Fraction())
    if status == "resolved":
        outcome = "incompatible_observation" if not compatible_leaves else "uniquely_matched" if len(compatible_leaves) == 1 else "multiple_compatible_branches"
        uniqueness = "none" if not compatible_leaves else "unique" if len(compatible_leaves) == 1 else "ambiguous"
    else:
        outcome = None
        uniqueness = "ambiguous"
    hidden = _unresolved_hidden_dimensions(compatible_leaves)
    obs_refs = tuple({
        "observation_id": row.get("observation_id"),
        "observation_sequence": _sequence(row),
        "event_kind": row.get("event_kind"),
    } for row in observations)
    return {
        "status": status,
        "schema_version": RECONCILIATION_SCHEMA_VERSION,
        "reason": reason,
        **{key: deepcopy(binding[key]) for key in ("session_id", "turn_number", "actor", "target", "move_id", "source_action_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")},
        "source_prediction_identity": deepcopy(binding["prediction_identity"]),
        "source_observations": obs_refs,
        "match_outcome": outcome,
        "compatible_leaf_ids": tuple(leaf["leaf_id"] for leaf in compatible_leaves),
        "compatible_original_probability_mass": _fd(mass),
        "probability_normalization": "none_preserve_original_mass",
        "matched_observable_facts": deepcopy(dict(matched_observable_facts)),
        "unresolved_hidden_dimensions": hidden,
        "uniqueness": uniqueness,
        "provenance": _RECONCILIATION_PROVENANCE,
    }


def _unresolved_hidden_dimensions(leaves: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    if not leaves:
        return ()
    dimensions = []
    critical = {leaf.get("critical_state") for leaf in leaves}
    rolls = {
        (leaf.get("damage_roll") or {}).get("roll_index")
        for leaf in leaves
        if isinstance(leaf.get("damage_roll"), Mapping)
    }
    hit = {leaf.get("hit_state") for leaf in leaves}
    if len(hit) > 1:
        dimensions.append("hit_state")
    if len(critical) > 1:
        dimensions.append("critical_state")
    if len(rolls) > 1:
        dimensions.append("damage_roll")
    return tuple(dimensions)


def _owner_identity_equal(value: Any, expected: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(expected, Mapping)
        and all(value.get(key) == expected.get(key) for key in _OWNER_KEYS)
    )


def _owner(value: Any, session_id: str) -> bool:
    return (
        isinstance(value, Mapping)
        and set(_OWNER_KEYS) <= set(value)
        and value.get("session_id") == session_id
        and value.get("side") in {"self", "opponent"}
        and isinstance(value.get("slot_index"), int)
        and not isinstance(value.get("slot_index"), bool)
        and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str)
        and bool(value["pokemon_id"])
    )


def _payload(value: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = value.get("payload")
    return payload if isinstance(payload, Mapping) else value


def _sequence(value: Mapping[str, Any]) -> int:
    seq = value.get("observation_sequence")
    return seq if isinstance(seq, int) and not isinstance(seq, bool) else 0


def _fraction(value: Any) -> Fraction | None:
    if not isinstance(value, Mapping) or set(value) != {"numerator", "denominator"}:
        return None
    numerator, denominator = value.get("numerator"), value.get("denominator")
    if not isinstance(numerator, int) or isinstance(numerator, bool) or not isinstance(denominator, int) or isinstance(denominator, bool) or denominator <= 0:
        return None
    return Fraction(numerator, denominator)


def _fd(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fingerprint(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=list).encode("utf-8")


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": RECONCILIATION_SCHEMA_VERSION, "reason": reason}


_SLEEP_FREEZE_RETENTION_SCHEMA = "historical-sleep-freeze-action-gate-v1"
_SLEEP_FREEZE_RETENTION_PROVENANCE = "authenticated_pre_observation_sleep_freeze_action_gate_v1"
_SLEEP_FREEZE_OUTCOME_TO_BRANCH = {
    ("sleep", "blocked_sleep"): ("cancelled_sleep", "blocked", "sleep"),
    ("sleep", "wake_and_execute"): ("wakes_and_executes", "executable", None),
    ("sleep", "sleep_exception_execute"): ("move_specific_sleep_exception_executes", "executable", None),
    ("freeze", "blocked_freeze"): ("cancelled_freeze", "blocked", "freeze"),
    ("freeze", "natural_thaw_and_execute"): ("thaws_and_executes", "executable", None),
    ("freeze", "self_thaw_move_execute"): ("self_thaw_move_executes", "executable", None),
}


def retain_historical_sleep_freeze_action_gate(
    *, predictive_gate: Mapping[str, Any], turn_number: int, decision_point: str,
) -> dict[str, Any]:
    """Freeze one exact pre-observation sleep/freeze gate for later C5 comparison."""
    from llm.advisor_champions_sleep_freeze_action_gate import validate_status_gate

    if not validate_status_gate(predictive_gate):
        return _result("rejected", "invalid_sleep_freeze_action_gate")
    if predictive_gate.get("condition") not in {"sleep", "freeze"}:
        return _result("rejected", "unsupported_sleep_freeze_gate_condition")
    if not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _result("rejected", "invalid_trusted_turn_number")
    if not isinstance(decision_point, str) or not decision_point:
        return _result("rejected", "invalid_sleep_freeze_decision_point")
    gate = deepcopy(dict(predictive_gate))
    fingerprint = _fingerprint(gate)
    return {
        "status": "resolved",
        "schema_version": _SLEEP_FREEZE_RETENTION_SCHEMA,
        "session_id": gate["session_id"],
        "turn_number": turn_number,
        "decision_point": decision_point,
        "action_id": gate["action_id"],
        "move_id": gate["move_id"],
        "condition": gate["condition"],
        "actor": deepcopy(gate["actor"]),
        "source_runtime_fingerprint": gate["source_runtime_fingerprint"],
        "source_branch_fingerprint": gate["source_branch_fingerprint"],
        "prediction_fingerprint": fingerprint,
        "predictive_gate": gate,
        "provenance": _SLEEP_FREEZE_RETENTION_PROVENANCE,
    }


def validate_historical_sleep_freeze_action_gate(retained: Mapping[str, Any]) -> dict[str, Any]:
    from llm.advisor_champions_sleep_freeze_action_gate import validate_status_gate

    if not isinstance(retained, Mapping) or retained.get("schema_version") != _SLEEP_FREEZE_RETENTION_SCHEMA:
        return _result("rejected", "historical_sleep_freeze_gate_missing")
    gate = retained.get("predictive_gate")
    if not isinstance(gate, Mapping) or not validate_status_gate(gate):
        return _result("rejected", "historical_sleep_freeze_gate_invalid")
    if _fingerprint(gate) != retained.get("prediction_fingerprint"):
        return _result("rejected", "historical_sleep_freeze_prediction_fingerprint_mismatch")
    required = {
        "session_id": gate.get("session_id"),
        "action_id": gate.get("action_id"),
        "move_id": gate.get("move_id"),
        "condition": gate.get("condition"),
        "actor": gate.get("actor"),
        "source_runtime_fingerprint": gate.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": gate.get("source_branch_fingerprint"),
        "provenance": _SLEEP_FREEZE_RETENTION_PROVENANCE,
    }
    if any(retained.get(key) != value for key, value in required.items()):
        return _result("rejected", "historical_sleep_freeze_gate_identity_mismatch")
    if not isinstance(retained.get("turn_number"), int) or isinstance(retained.get("turn_number"), bool) or retained["turn_number"] < 1:
        return _result("rejected", "historical_sleep_freeze_turn_invalid")
    if not isinstance(retained.get("decision_point"), str) or not retained["decision_point"]:
        return _result("rejected", "historical_sleep_freeze_decision_point_invalid")
    return deepcopy(dict(retained))


def reconcile_observed_sleep_freeze_action_gate_rng(
    *, retained_prediction: Mapping[str, Any],
    pending_status_action_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Filter one immutable exact sleep/freeze gate by its exact production observation."""
    checked = validate_historical_sleep_freeze_action_gate(retained_prediction)
    if checked.get("status") != "resolved":
        return checked
    gate = checked["predictive_gate"]
    branches = gate["branches"]
    if pending_status_action_observation is None:
        return _sleep_freeze_reconciliation_result(
            status="incomplete", reason="insufficient_observation", retained=checked,
            observations=(), compatible_branches=branches, matched={},
        )
    if not isinstance(pending_status_action_observation, Mapping) or pending_status_action_observation.get("event_kind") != "pending_status_action_execution_observed":
        return _sleep_freeze_reconciliation_result(
            status="incomplete", reason="insufficient_observation", retained=checked,
            observations=(), compatible_branches=branches, matched={},
        )
    error = _validate_pending_status_action_observation(pending_status_action_observation, checked)
    if error:
        return _result("rejected", error)
    payload = pending_status_action_observation["payload"]
    mapping = _SLEEP_FREEZE_OUTCOME_TO_BRANCH.get((checked["condition"], payload["outcome_class"]))
    if mapping is None:
        return _result("rejected", "unsupported_pending_status_action_outcome")
    expected_kind, expected_state, expected_blocker = mapping
    if payload.get("execution_state") != expected_state or payload.get("blocker") != expected_blocker:
        return _result("rejected", "pending_status_action_semantics_mismatch")
    compatible = tuple(branch for branch in branches if branch.get("kind") == expected_kind)
    return _sleep_freeze_reconciliation_result(
        status="resolved", reason=None, retained=checked,
        observations=(pending_status_action_observation,), compatible_branches=compatible,
        matched={
            "outcome_class": payload["outcome_class"],
            "execution_state": payload["execution_state"],
            "blocker": payload["blocker"],
        },
    )


def _validate_pending_status_action_observation(value: Mapping[str, Any], retained: Mapping[str, Any]) -> str | None:
    if (
        value.get("session_id") != retained["session_id"]
        or value.get("turn_number") != retained["turn_number"]
        or value.get("source") != "ui_pending_status_action_execution_confirmation"
        or value.get("trust") != "user_confirmed_observation"
        or value.get("observed") is not True
        or value.get("confirmed") is not True
        or _sequence(value) <= 0
    ):
        return "pending_status_action_observation_provenance_mismatch"
    actor = retained["actor"]
    if (value.get("side"), value.get("slot_index"), value.get("pokemon_id")) != (
        actor.get("side"), actor.get("slot_index"), actor.get("pokemon_id"),
    ):
        return "pending_status_action_actor_mismatch"
    payload = value.get("payload")
    if not isinstance(payload, Mapping) or set(payload) != {
        "decision_point", "action_id", "move_id", "condition",
        "execution_state", "blocker", "outcome_class",
    }:
        return "pending_status_action_payload_invalid"
    if payload.get("decision_point") != retained["decision_point"]:
        return "pending_status_action_decision_point_mismatch"
    if payload.get("action_id") != retained["action_id"]:
        return "pending_status_action_action_id_mismatch"
    if payload.get("move_id") != retained["move_id"]:
        return "pending_status_action_move_mismatch"
    if payload.get("condition") != retained["condition"]:
        return "pending_status_action_condition_mismatch"
    if (retained["condition"], payload.get("outcome_class")) not in _SLEEP_FREEZE_OUTCOME_TO_BRANCH:
        return "unsupported_pending_status_action_outcome"
    return None


def _sleep_freeze_reconciliation_result(
    *, status: str, reason: str | None, retained: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]], compatible_branches: Sequence[Mapping[str, Any]],
    matched: Mapping[str, Any],
) -> dict[str, Any]:
    mass = sum((_fraction(branch.get("probability")) or Fraction() for branch in compatible_branches), Fraction())
    if status == "resolved":
        match_outcome = "incompatible_observation" if not compatible_branches else "uniquely_matched" if len(compatible_branches) == 1 else "multiple_compatible_branches"
    else:
        match_outcome = None
    refs = tuple({
        "observation_id": row.get("observation_id"),
        "observation_sequence": _sequence(row),
        "event_kind": row.get("event_kind"),
    } for row in observations)
    return {
        "status": status,
        "schema_version": RECONCILIATION_SCHEMA_VERSION,
        "reason": reason,
        "source_prediction_kind": "sleep_freeze_action_gate",
        "source_prediction_identity": {
            "schema_version": "champions-sleep-freeze-action-gate-v1",
            "prediction_fingerprint": retained["prediction_fingerprint"],
        },
        "session_id": retained["session_id"],
        "turn_number": retained["turn_number"],
        "actor": deepcopy(retained["actor"]),
        "decision_point": retained["decision_point"],
        "action_id": retained["action_id"],
        "move_id": retained["move_id"],
        "condition": retained["condition"],
        "source_runtime_fingerprint": retained["source_runtime_fingerprint"],
        "source_branch_fingerprint": retained["source_branch_fingerprint"],
        "source_observations": refs,
        "match_outcome": match_outcome,
        "compatible_branch_ids": tuple(branch["branch_id"] for branch in compatible_branches),
        "compatible_original_probability_mass": _fd(mass),
        "probability_normalization": "none_preserve_original_mass",
        "matched_observable_facts": deepcopy(dict(matched)),
        "unresolved_hidden_dimensions": _sleep_freeze_hidden_dimensions(compatible_branches),
        "provenance": _RECONCILIATION_PROVENANCE,
    }


def _sleep_freeze_hidden_dimensions(branches: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    if len(branches) < 2:
        return ()
    dimensions = []
    for key in ("sleep_duration", "adjusted_duration", "duration_adjustment", "duration_identity", "attempt"):
        values = {_canonical_bytes(branch.get(key)) for branch in branches if key in branch}
        if len(values) > 1:
            dimensions.append(key)
    return tuple(dimensions)


_CONFUSION_RETENTION_SCHEMA = "historical-confusion-action-gate-v1"
_CONFUSION_RETENTION_PROVENANCE = "authenticated_pre_observation_confusion_action_gate_v1"
_CONFUSION_OUTCOME_TO_BRANCH = {
    "confusion_self_hit": "confusion_self_hit",
    "confusion_selected_action_executes": "confusion_selected_action_executes",
    "confusion_snaps_out_and_executes": "confusion_snaps_out_and_executes",
}


def retain_historical_confusion_action_gate(
    *, predictive_gate: Mapping[str, Any], turn_number: int, decision_point: str,
) -> dict[str, Any]:
    from llm.advisor_champions_confusion_action_gate import validate_confusion_gate
    if not validate_confusion_gate(predictive_gate):
        return _result("rejected", "invalid_confusion_action_gate")
    if predictive_gate.get("confusion") != "confused":
        return _result("rejected", "confusion_action_gate_not_active")
    if not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1:
        return _result("rejected", "invalid_trusted_turn_number")
    if not isinstance(decision_point, str) or not decision_point:
        return _result("rejected", "invalid_confusion_decision_point")
    gate = deepcopy(dict(predictive_gate))
    progression = gate.get("progression")
    origin_id = progression.get("origin_id") if isinstance(progression, Mapping) else None
    if not isinstance(origin_id, str) or not origin_id:
        return _result("rejected", "confusion_progression_origin_missing")
    return {
        "status": "resolved", "schema_version": _CONFUSION_RETENTION_SCHEMA,
        "session_id": gate["session_id"], "turn_number": turn_number,
        "actor": deepcopy(gate["actor"]), "decision_point": decision_point,
        "action_id": gate["action_id"], "move_id": gate["move_id"],
        "confusion_origin_id": origin_id,
        "source_runtime_fingerprint": gate["source_runtime_fingerprint"],
        "source_branch_fingerprint": gate["source_branch_fingerprint"],
        "prediction_fingerprint": _fingerprint(gate),
        "predictive_gate": gate, "provenance": _CONFUSION_RETENTION_PROVENANCE,
    }


def validate_historical_confusion_action_gate(retained: Mapping[str, Any]) -> dict[str, Any]:
    from llm.advisor_champions_confusion_action_gate import validate_confusion_gate
    if not isinstance(retained, Mapping) or retained.get("schema_version") != _CONFUSION_RETENTION_SCHEMA:
        return _result("rejected", "historical_confusion_gate_missing")
    gate = retained.get("predictive_gate")
    if not isinstance(gate, Mapping) or not validate_confusion_gate(gate):
        return _result("rejected", "historical_confusion_gate_invalid")
    if _fingerprint(gate) != retained.get("prediction_fingerprint"):
        return _result("rejected", "historical_confusion_prediction_fingerprint_mismatch")
    progression = gate.get("progression")
    expected = {
        "session_id": gate.get("session_id"), "actor": gate.get("actor"),
        "action_id": gate.get("action_id"), "move_id": gate.get("move_id"),
        "confusion_origin_id": progression.get("origin_id") if isinstance(progression, Mapping) else None,
        "source_runtime_fingerprint": gate.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": gate.get("source_branch_fingerprint"),
        "provenance": _CONFUSION_RETENTION_PROVENANCE,
    }
    if any(retained.get(key) != value for key, value in expected.items()):
        return _result("rejected", "historical_confusion_gate_identity_mismatch")
    if not isinstance(retained.get("turn_number"), int) or isinstance(retained.get("turn_number"), bool) or retained["turn_number"] < 1:
        return _result("rejected", "historical_confusion_turn_invalid")
    if not isinstance(retained.get("decision_point"), str) or not retained["decision_point"]:
        return _result("rejected", "historical_confusion_decision_point_invalid")
    return deepcopy(dict(retained))


def reconcile_observed_confusion_action_gate_rng(
    *, retained_prediction: Mapping[str, Any],
    pending_confusion_action_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    checked = validate_historical_confusion_action_gate(retained_prediction)
    if checked.get("status") != "resolved":
        return checked
    branches = checked["predictive_gate"]["branches"]
    if pending_confusion_action_observation is None:
        return _confusion_reconciliation_result(
            status="incomplete", reason="insufficient_observation", retained=checked,
            observations=(), compatible_branches=branches, matched={})
    if (not isinstance(pending_confusion_action_observation, Mapping)
            or pending_confusion_action_observation.get("event_kind") != "pending_confusion_action_execution_observed"):
        return _confusion_reconciliation_result(
            status="incomplete", reason="insufficient_observation", retained=checked,
            observations=(), compatible_branches=branches, matched={})
    error = _validate_pending_confusion_action_observation(pending_confusion_action_observation, checked)
    if error:
        return _result("rejected", error)
    payload = pending_confusion_action_observation["payload"]
    kind = _CONFUSION_OUTCOME_TO_BRANCH[payload["outcome_class"]]
    compatible = tuple(branch for branch in branches if branch.get("kind") == kind)
    return _confusion_reconciliation_result(
        status="resolved", reason=None, retained=checked,
        observations=(pending_confusion_action_observation,), compatible_branches=compatible,
        matched={"outcome_class": payload["outcome_class"]})


def _validate_pending_confusion_action_observation(value: Mapping[str, Any], retained: Mapping[str, Any]) -> str | None:
    if (value.get("session_id") != retained["session_id"] or value.get("turn_number") != retained["turn_number"]
            or value.get("source") != "ui_pending_confusion_action_execution_confirmation"
            or value.get("trust") != "user_confirmed_observation"
            or value.get("observed") is not True or value.get("confirmed") is not True or _sequence(value) <= 0):
        return "pending_confusion_action_observation_provenance_mismatch"
    actor = retained["actor"]
    if (value.get("side"), value.get("slot_index"), value.get("pokemon_id")) != (
        actor.get("side"), actor.get("slot_index"), actor.get("pokemon_id")):
        return "pending_confusion_action_actor_mismatch"
    payload = value.get("payload")
    if not isinstance(payload, Mapping) or set(payload) != {"decision_point", "action_id", "move_id", "confusion_origin_id", "outcome_class"}:
        return "pending_confusion_action_payload_invalid"
    if payload.get("decision_point") != retained["decision_point"]:
        return "pending_confusion_action_decision_point_mismatch"
    if payload.get("action_id") != retained["action_id"]:
        return "pending_confusion_action_action_id_mismatch"
    if payload.get("move_id") != retained["move_id"]:
        return "pending_confusion_action_move_mismatch"
    if payload.get("confusion_origin_id") != retained["confusion_origin_id"]:
        return "pending_confusion_action_origin_mismatch"
    if payload.get("outcome_class") not in _CONFUSION_OUTCOME_TO_BRANCH:
        return "unsupported_pending_confusion_action_outcome"
    return None


def _confusion_reconciliation_result(*, status: str, reason: str | None, retained: Mapping[str, Any],
                                     observations: Sequence[Mapping[str, Any]],
                                     compatible_branches: Sequence[Mapping[str, Any]],
                                     matched: Mapping[str, Any]) -> dict[str, Any]:
    mass = sum((_fraction(branch.get("probability")) or Fraction() for branch in compatible_branches), Fraction())
    outcome = None if status != "resolved" else (
        "incompatible_observation" if not compatible_branches else
        "uniquely_matched" if len(compatible_branches) == 1 else "multiple_compatible_branches")
    refs = tuple({"observation_id": row.get("observation_id"), "observation_sequence": _sequence(row),
                  "event_kind": row.get("event_kind")} for row in observations)
    return {
        "status": status, "schema_version": RECONCILIATION_SCHEMA_VERSION, "reason": reason,
        "source_prediction_kind": "confusion_action_gate",
        "source_prediction_identity": {
            "schema_version": "champions-confusion-action-gate-v1",
            "prediction_fingerprint": retained["prediction_fingerprint"],
        },
        "session_id": retained["session_id"], "turn_number": retained["turn_number"],
        "actor": deepcopy(retained["actor"]), "decision_point": retained["decision_point"],
        "action_id": retained["action_id"], "move_id": retained["move_id"],
        "confusion_origin_id": retained["confusion_origin_id"],
        "source_runtime_fingerprint": retained["source_runtime_fingerprint"],
        "source_branch_fingerprint": retained["source_branch_fingerprint"],
        "source_observations": refs, "match_outcome": outcome,
        "compatible_branch_ids": tuple(branch["branch_id"] for branch in compatible_branches),
        "compatible_original_probability_mass": _fd(mass),
        "probability_normalization": "none_preserve_original_mass",
        "matched_observable_facts": deepcopy(dict(matched)),
        "unresolved_hidden_dimensions": _confusion_hidden_dimensions(compatible_branches),
        "provenance": _RECONCILIATION_PROVENANCE,
    }


def _confusion_hidden_dimensions(branches: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    if len(branches) < 2:
        return ()
    dimensions = []
    for key in ("duration", "duration_identity", "opportunity"):
        values = {_canonical_bytes(branch.get(key)) for branch in branches if key in branch}
        if len(values) > 1:
            dimensions.append(key)
    return tuple(dimensions)


_CONFUSION_SELF_HIT_RETENTION_SCHEMA = "historical-confusion-self-hit-v1"
_CONFUSION_SELF_HIT_RETENTION_PROVENANCE = "authenticated_pre_damage_confusion_self_hit_v1"


def retain_historical_confusion_self_hit(
    *, predictive_self_hits: Sequence[Mapping[str, Any]], retained_action_gate: Mapping[str, Any],
) -> dict[str, Any]:
    gate = validate_historical_confusion_action_gate(retained_action_gate)
    if gate.get("status") != "resolved":
        return gate
    hits = tuple(deepcopy(dict(row)) for row in predictive_self_hits if isinstance(row, Mapping))
    if not hits:
        return _result("rejected", "confusion_self_hit_prediction_missing")
    branch_ids = []
    canonical_rolls = None
    fingerprints = []
    for hit in hits:
        error = _validate_confusion_self_hit_prediction(hit, gate)
        if error:
            return _result("rejected", error)
        branch_ids.append(hit["branch"]["branch_id"])
        rolls = tuple(deepcopy(hit["damage_rolls"]))
        projection = tuple({
            "roll_index": row["roll_index"], "probability": deepcopy(row["probability"]),
            "damage": row["damage"], "raw_damage": row["raw_damage"],
            "hp_before": row["hp_before"], "hp_after": row["hp_after"],
            "self_fainted": row["self_fainted"], "disguise": deepcopy(row["disguise"]),
        } for row in rolls)
        if canonical_rolls is None:
            canonical_rolls = projection
        elif canonical_rolls != projection:
            return _result("rejected", "confusion_self_hit_branch_rolls_diverged")
        fingerprints.append(_fingerprint(hit))
    expected = tuple(
        branch["branch_id"] for branch in gate["predictive_gate"]["branches"]
        if branch.get("kind") == "confusion_self_hit"
    )
    if tuple(branch_ids) != expected:
        return _result("rejected", "confusion_self_hit_branch_set_mismatch")
    return {
        "status": "resolved", "schema_version": _CONFUSION_SELF_HIT_RETENTION_SCHEMA,
        "session_id": gate["session_id"], "turn_number": gate["turn_number"],
        "actor": deepcopy(gate["actor"]), "decision_point": gate["decision_point"],
        "action_id": gate["action_id"], "move_id": gate["move_id"],
        "confusion_origin_id": gate["confusion_origin_id"],
        "source_runtime_fingerprint": gate["source_runtime_fingerprint"],
        "source_branch_fingerprint": gate["source_branch_fingerprint"],
        "source_confusion_gate_prediction_fingerprint": gate["prediction_fingerprint"],
        "retained_action_gate": deepcopy(gate),
        "source_confusion_self_hit_branch_ids": tuple(branch_ids),
        "predictive_self_hits": hits,
        "predictive_self_hit_fingerprints": tuple(fingerprints),
        "canonical_damage_rolls": canonical_rolls,
        "artifact_fingerprint": _fingerprint({
            "gate": gate["prediction_fingerprint"], "hits": fingerprints,
            "branches": branch_ids, "rolls": canonical_rolls,
        }),
        "provenance": _CONFUSION_SELF_HIT_RETENTION_PROVENANCE,
    }


def validate_historical_confusion_self_hit(retained: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(retained, Mapping) or retained.get("schema_version") != _CONFUSION_SELF_HIT_RETENTION_SCHEMA:
        return _result("rejected", "historical_confusion_self_hit_missing")
    gate = validate_historical_confusion_action_gate(retained.get("retained_action_gate"))
    if gate.get("status") != "resolved":
        return _result("rejected", "historical_confusion_self_hit_gate_invalid")
    expected_identity = {
        "session_id": gate["session_id"], "turn_number": gate["turn_number"],
        "actor": gate["actor"], "decision_point": gate["decision_point"],
        "action_id": gate["action_id"], "move_id": gate["move_id"],
        "confusion_origin_id": gate["confusion_origin_id"],
        "source_runtime_fingerprint": gate["source_runtime_fingerprint"],
        "source_branch_fingerprint": gate["source_branch_fingerprint"],
        "source_confusion_gate_prediction_fingerprint": gate["prediction_fingerprint"],
    }
    if any(retained.get(key) != value for key, value in expected_identity.items()):
        return _result("rejected", "historical_confusion_self_hit_identity_mismatch")
    hits = retained.get("predictive_self_hits")
    fingerprints = retained.get("predictive_self_hit_fingerprints")
    if not isinstance(hits, (tuple, list)) or not isinstance(fingerprints, (tuple, list)) or len(hits) != len(fingerprints) or not hits:
        return _result("rejected", "historical_confusion_self_hit_invalid")
    branch_ids=[]
    for hit, fingerprint in zip(hits, fingerprints):
        if not isinstance(hit, Mapping) or _fingerprint(hit) != fingerprint:
            return _result("rejected", "historical_confusion_self_hit_fingerprint_mismatch")
        error=_validate_confusion_self_hit_prediction(hit,gate)
        if error:
            return _result("rejected",error)
        branch_ids.append(hit["branch"]["branch_id"])
    expected_branches=tuple(
        branch["branch_id"] for branch in gate["predictive_gate"]["branches"]
        if branch.get("kind")=="confusion_self_hit"
    )
    if tuple(branch_ids)!=expected_branches or tuple(retained.get("source_confusion_self_hit_branch_ids",()))!=expected_branches:
        return _result("rejected","historical_confusion_self_hit_branch_set_mismatch")
    expected_artifact = _fingerprint({
        "gate": retained.get("source_confusion_gate_prediction_fingerprint"),
        "hits": list(fingerprints),
        "branches": list(retained.get("source_confusion_self_hit_branch_ids", ())),
        "rolls": retained.get("canonical_damage_rolls"),
    })
    if retained.get("artifact_fingerprint") != expected_artifact:
        return _result("rejected", "historical_confusion_self_hit_artifact_fingerprint_mismatch")
    rolls = retained.get("canonical_damage_rolls")
    if not isinstance(rolls, (tuple, list)) or len(rolls) != 16:
        return _result("rejected", "historical_confusion_self_hit_rolls_invalid")
    mass = sum((_fraction(row.get("probability")) or Fraction() for row in rolls), Fraction())
    if mass != 1:
        return _result("rejected", "historical_confusion_self_hit_probability_mass_invalid")
    return deepcopy(dict(retained))


def _validate_confusion_self_hit_prediction(hit: Mapping[str, Any], gate: Mapping[str, Any]) -> str | None:
    if (hit.get("status") != "resolved" or hit.get("schema_version") != "champions-confusion-self-hit-v1"
            or hit.get("event") != "confusion_self_hit" or hit.get("selected_move_does_not_execute") is not True
            or hit.get("critical") is not False or hit.get("stab") is not False or hit.get("contact") is not False
            or hit.get("actor") != gate["actor"] or hit.get("target") != gate["actor"]):
        return "invalid_confusion_self_hit_prediction"
    branch = hit.get("branch")
    if not isinstance(branch, Mapping) or branch.get("kind") != "confusion_self_hit":
        return "confusion_self_hit_source_branch_invalid"
    if not any(branch == candidate for candidate in gate["predictive_gate"]["branches"]):
        return "confusion_self_hit_source_branch_foreign"
    rolls = hit.get("damage_rolls")
    if not isinstance(rolls, (tuple, list)) or len(rolls) != 16:
        return "confusion_self_hit_roll_count_invalid"
    if hit.get("root_probability_mass") != {"numerator": 1, "denominator": 1}:
        return "confusion_self_hit_root_mass_invalid"
    for index, row in enumerate(rolls):
        if (not isinstance(row, Mapping) or row.get("roll_index") != index
                or _fraction(row.get("probability")) != Fraction(1, 16)):
            return "confusion_self_hit_roll_probability_invalid"
    return None


def reconcile_observed_confusion_self_hit_damage_rng(
    *, retained_prediction: Mapping[str, Any],
    primary_confusion_observation: Mapping[str, Any] | None = None,
    damage_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    retained = validate_historical_confusion_self_hit(retained_prediction)
    if retained.get("status") != "resolved":
        return retained
    rolls = retained["canonical_damage_rolls"]
    if not isinstance(primary_confusion_observation, Mapping) or not isinstance(damage_observation, Mapping):
        return _confusion_self_hit_reconciliation_result(
            status="incomplete", reason="insufficient_observation", retained=retained,
            observations=(), compatible_rolls=rolls, matched={})
    error = _validate_confusion_self_hit_damage_observations(primary_confusion_observation, damage_observation, retained)
    if error:
        return _result("rejected", error)
    payload = damage_observation["payload"]
    compatible = tuple(row for row in rolls if _confusion_self_hit_roll_matches(row, payload))
    return _confusion_self_hit_reconciliation_result(
        status="resolved", reason=None, retained=retained,
        observations=(primary_confusion_observation, damage_observation),
        compatible_rolls=compatible,
        matched={
            "hp_before": payload["hp_before"], "hp_after": payload["hp_after"],
            "self_fainted": payload["self_fainted"], "disguise_outcome": payload["disguise_outcome"],
        })


def _validate_confusion_self_hit_damage_observations(primary: Mapping[str, Any], damage: Mapping[str, Any],
                                                     retained: Mapping[str, Any]) -> str | None:
    if (primary.get("event_kind") != "pending_confusion_action_execution_observed"
            or primary.get("source")!="ui_pending_confusion_action_execution_confirmation"
            or primary.get("trust")!="user_confirmed_observation"
            or primary.get("confirmed") is not True or primary.get("observed") is not True):
        return "confusion_self_hit_primary_observation_invalid"
    pp = primary.get("payload")
    if not isinstance(pp, Mapping) or pp.get("outcome_class") != "confusion_self_hit":
        return "confusion_self_hit_primary_outcome_mismatch"
    if damage.get("event_kind") != "confusion_self_hit_damage_observed":
        return "confusion_self_hit_damage_observation_invalid"
    dp = damage.get("payload")
    if not isinstance(dp, Mapping) or set(dp)!={"decision_point","action_id","move_id","confusion_origin_id","source_confusion_observation_id","hp_before","hp_after","self_fainted","disguise_outcome"}:
        return "confusion_self_hit_damage_payload_invalid"
    if (damage.get("source") != "ui_confusion_self_hit_damage_confirmation"
            or damage.get("trust") != "user_confirmed_observation"
            or damage.get("confirmed") is not True or damage.get("observed") is not True):
        return "confusion_self_hit_damage_provenance_mismatch"
    if damage.get("observation_sequence", 0) <= primary.get("observation_sequence", 0):
        return "confusion_self_hit_damage_observation_order_invalid"
    if dp.get("source_confusion_observation_id") != primary.get("observation_id"):
        return "confusion_self_hit_damage_source_observation_mismatch"
    for field, retained_key in (
        ("decision_point","decision_point"),("action_id","action_id"),("move_id","move_id"),
        ("confusion_origin_id","confusion_origin_id"),
    ):
        if dp.get(field) != retained.get(retained_key) or pp.get(field) != retained.get(retained_key):
            return f"confusion_self_hit_damage_{field}_mismatch"
    if (damage.get("session_id") != retained["session_id"] or primary.get("session_id") != retained["session_id"]
            or damage.get("turn_number") != retained["turn_number"] or primary.get("turn_number") != retained["turn_number"]):
        return "confusion_self_hit_damage_session_turn_mismatch"
    actor = retained["actor"]
    expected_actor = (actor.get("side"),actor.get("slot_index"),actor.get("pokemon_id"))
    if ((damage.get("side"),damage.get("slot_index"),damage.get("pokemon_id")) != expected_actor
            or (primary.get("side"),primary.get("slot_index"),primary.get("pokemon_id")) != expected_actor):
        return "confusion_self_hit_damage_actor_mismatch"
    return None


def _confusion_self_hit_roll_matches(row: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    status = row.get("disguise", {}).get("status")
    expected_disguise = "intact_to_broken" if status == "broken" else status
    return (
        row.get("hp_before") == payload.get("hp_before")
        and row.get("hp_after") == payload.get("hp_after")
        and row.get("self_fainted") is payload.get("self_fainted")
        and expected_disguise == payload.get("disguise_outcome")
    )


def _confusion_self_hit_reconciliation_result(*, status: str, reason: str | None, retained: Mapping[str, Any],
                                              observations: Sequence[Mapping[str, Any]],
                                              compatible_rolls: Sequence[Mapping[str, Any]],
                                              matched: Mapping[str, Any]) -> dict[str, Any]:
    mass = sum((_fraction(row.get("probability")) or Fraction() for row in compatible_rolls), Fraction())
    outcome = None if status != "resolved" else (
        "incompatible_observation" if not compatible_rolls else
        "uniquely_matched" if len(compatible_rolls) == 1 else "multiple_compatible_branches")
    dimensions = []
    if len(compatible_rolls) > 1:
        for key in ("roll_index","raw_damage"):
            if len({_canonical_bytes(row.get(key)) for row in compatible_rolls}) > 1:
                dimensions.append(key)
    return {
        "status": status, "schema_version": RECONCILIATION_SCHEMA_VERSION, "reason": reason,
        "source_prediction_kind": "confusion_self_hit_damage_rolls",
        "session_id": retained["session_id"], "turn_number": retained["turn_number"],
        "actor": deepcopy(retained["actor"]), "decision_point": retained["decision_point"],
        "action_id": retained["action_id"], "move_id": retained["move_id"],
        "confusion_origin_id": retained["confusion_origin_id"],
        "source_prediction_identity": {
            "schema_version": "champions-confusion-self-hit-v1",
            "artifact_fingerprint": retained["artifact_fingerprint"],
        },
        "source_observations": tuple({
            "observation_id": row.get("observation_id"), "observation_sequence": row.get("observation_sequence"),
            "event_kind": row.get("event_kind"),
        } for row in observations),
        "match_outcome": outcome,
        "compatible_roll_indices": tuple(row["roll_index"] for row in compatible_rolls),
        "compatible_original_probability_mass": _fd(mass),
        "probability_normalization": "none_preserve_original_mass",
        "probability_layer": "conditional_on_confusion_self_hit",
        "matched_observable_facts": deepcopy(dict(matched)),
        "unresolved_hidden_dimensions": tuple(dimensions),
        "provenance": _RECONCILIATION_PROVENANCE,
    }
