"""C5 adapter/reconciliation for observed Sky Attack flinch terminal RNG."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from typing import Any, Mapping, Sequence

from llm.advisor_detached_observed_rng_reconciliation import (
    validate_historical_predictive_action_binding,
)

SCHEMA_VERSION = "standard-charge-flinch-reconciliation-adapter-v1"
PROVENANCE = "authenticated_standard_charge_flinch_terminal_reconciliation_v1"


def materialize_standard_charge_flinch_prediction(
    *, terminal_execution: Mapping[str, Any],
    predictive_binding: Mapping[str, Any],
    predictive_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    checked = validate_historical_predictive_action_binding(
        binding=predictive_binding, predictive_ledger=predictive_ledger,
    )
    if checked.get("status") != "resolved":
        return checked
    if checked.get("move_id") != "sky-attack":
        return _r("rejected", "unsupported_standard_charge_flinch_producer")
    if (
        not isinstance(terminal_execution, Mapping)
        or terminal_execution.get("status") != "resolved"
        or terminal_execution.get("schema_version") not in {"standard-charge-terminal-attack-kernel-v1", "detached-standard-charge-turn-two-attack-execution-v1"}
        or _fraction(terminal_execution.get("terminal_probability_mass")) != Fraction(1, 1)
    ):
        return _r("rejected", "standard_charge_terminal_artifact_invalid")
    leaves = terminal_execution.get("terminal_leaves")
    if not isinstance(leaves, (tuple, list)) or not leaves:
        return _r("rejected", "standard_charge_terminal_leaves_missing")
    if sum((_fraction(row.get("probability")) or Fraction() for row in leaves), Fraction()) != Fraction(1, 1):
        return _r("rejected", "standard_charge_terminal_root_mass_invalid")
    if any(not _leaf_binding(row, checked) for row in leaves):
        return _r("rejected", "standard_charge_terminal_leaf_binding_mismatch")

    authority = terminal_execution.get("execution_authority")
    if not isinstance(authority, Mapping):
        return _r("rejected", "standard_charge_terminal_execution_authority_missing")
    mode, lifecycle, caller_kind, original_action_id, runtime_fingerprint = _caller_context(authority)
    if (
        mode not in {"forced_turn_two_continuation", "power_herb_current_turn_skip"}
        or caller_kind != mode
        or original_action_id != checked["candidate_id"]
        or runtime_fingerprint != checked["source_runtime_fingerprint"]
    ):
        return _r("rejected", "standard_charge_terminal_caller_binding_mismatch")
    if not isinstance(lifecycle, Mapping):
        return _r("rejected", "standard_charge_terminal_lifecycle_missing")
    if mode == "forced_turn_two_continuation":
        if (
            lifecycle.get("status") != "resolved"
            or lifecycle.get("actor") != checked["actor"]
            or lifecycle.get("move_id") != "sky-attack"
            or lifecycle.get("action_id") != checked["candidate_id"]
            or lifecycle.get("turn_two_continuation_required") is not True
        ):
            return _r("rejected", "standard_charge_terminal_lifecycle_mismatch")
    elif (
        lifecycle.get("outcome") != "power_herb_charge_skip_ready"
        or lifecycle.get("actor") != checked["actor"]
        or lifecycle.get("move_id") != "sky-attack"
        or lifecycle.get("action_id") != checked["candidate_id"]
    ):
        return _r("rejected", "standard_charge_terminal_lifecycle_mismatch")

    identities = {row.get("candidate_id") for row in leaves}
    if len(identities) != 1 or not all(isinstance(value, str) and value for value in identities):
        return _r("rejected", "standard_charge_terminal_action_identity_ambiguous")
    fp = _fingerprint(terminal_execution)
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "prediction_kind": "standard_charge_terminal_execution",
        **{key: deepcopy(checked[key]) for key in (
            "session_id", "turn_number", "source_action_id", "action_link_id",
            "actor", "target", "move_id", "candidate_id",
            "source_runtime_fingerprint", "source_branch_fingerprint",
            "decision_owner", "predictive_ledger_fingerprint",
        )},
        "terminal_prediction_fingerprint": fp,
        "terminal_execution": deepcopy(dict(terminal_execution)),
        "terminal_leaf_ids": tuple(row["leaf_id"] for row in leaves),
        "terminal_action_identity": next(iter(identities)),
        "execution_mode": mode,
        "caller_kind": caller_kind,
        "original_charge_action_id": original_action_id,
        "charge_lifecycle": deepcopy(dict(lifecycle)),
        "root_probability_mass": {"numerator": 1, "denominator": 1},
        "provenance": PROVENANCE,
    }


def retain_standard_charge_flinch_prediction_from_strategy_result(
    *, strategy_result: Mapping[str, Any],
    predictive_binding: Mapping[str, Any],
    predictive_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    """Retain exactly one already-materialized terminal artifact from a prediction result.

    This function never reconstructs terminal mechanics.  Identical duplicated
    copies are deduplicated by the authenticated terminal fingerprint; multiple
    distinct compatible terminal artifacts fail closed.
    """
    artifacts: list[Mapping[str, Any]] = []
    seen_nodes: set[int] = set()
    accepted = {
        "standard-charge-terminal-attack-kernel-v1",
        "detached-standard-charge-turn-two-attack-execution-v1",
    }

    def visit(node: Any) -> None:
        if isinstance(node, Mapping):
            marker = id(node)
            if marker in seen_nodes:
                return
            seen_nodes.add(marker)
            if (
                node.get("status") == "resolved"
                and node.get("schema_version") in accepted
                and isinstance(node.get("terminal_leaves"), (tuple, list))
                and node.get("terminal_leaves")
            ):
                artifacts.append(node)
            for child in node.values():
                visit(child)
        elif isinstance(node, (tuple, list)):
            for child in node:
                visit(child)

    if not isinstance(strategy_result, Mapping):
        return _r("rejected", "strategy_result_invalid")
    visit(strategy_result)
    predictions: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        candidate = materialize_standard_charge_flinch_prediction(
            terminal_execution=artifact,
            predictive_binding=predictive_binding,
            predictive_ledger=predictive_ledger,
        )
        if candidate.get("status") == "resolved":
            predictions[candidate["terminal_prediction_fingerprint"]] = candidate
    if not predictions:
        return _r("incomplete", "standard_charge_terminal_prediction_not_retained")
    if len(predictions) != 1:
        return _r("rejected", "ambiguous_standard_charge_terminal_prediction")
    return {"status": "resolved", "prediction": deepcopy(next(iter(predictions.values())))}


def validate_standard_charge_flinch_prediction(
    *, prediction: Mapping[str, Any],
    predictive_binding: Mapping[str, Any],
    predictive_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(prediction, Mapping) or prediction.get("schema_version") != SCHEMA_VERSION:
        return _r("rejected", "standard_charge_flinch_prediction_invalid")
    expected = materialize_standard_charge_flinch_prediction(
        terminal_execution=prediction.get("terminal_execution"),
        predictive_binding=predictive_binding,
        predictive_ledger=predictive_ledger,
    )
    if expected.get("status") != "resolved":
        return expected
    return deepcopy(expected) if dict(prediction) == expected else _r("rejected", "standard_charge_flinch_prediction_tampered")


def reconcile_observed_standard_charge_flinch_rng(
    *, prediction: Mapping[str, Any],
    predictive_binding: Mapping[str, Any],
    predictive_ledger: Mapping[str, Any],
    executed_move_observation: Mapping[str, Any],
    flinch_causality_observation: Mapping[str, Any] | None = None,
    direct_damage_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    baseline = deepcopy((prediction, predictive_binding, predictive_ledger, executed_move_observation, flinch_causality_observation, direct_damage_observation))
    checked = validate_standard_charge_flinch_prediction(
        prediction=prediction, predictive_binding=predictive_binding, predictive_ledger=predictive_ledger,
    )
    if checked.get("status") != "resolved":
        return checked
    if _execution_error(executed_move_observation, checked):
        return _r("rejected", "producer_execution_observation_mismatch")

    observations=[executed_move_observation]
    constraints=[]
    matched={}
    if flinch_causality_observation is not None:
        error=_causal_error(flinch_causality_observation, checked, executed_move_observation)
        if error: return _r("rejected", error)
        observations.append(flinch_causality_observation)
        constraints.append("flinch")
        matched["target_flinch_caused"]={
            "affected_owner": deepcopy(checked["target"]),
            "cancelled_source_action_id": flinch_causality_observation["cancelled_source_action_id"],
        }
    if direct_damage_observation is not None:
        error=_damage_error(direct_damage_observation, checked, executed_move_observation)
        if error: return _r("rejected", error)
        observations.append(direct_damage_observation)
        amount=direct_damage_observation.get("damage_amount", _payload(direct_damage_observation).get("damage_amount"))
        constraints.append(("damage", amount)); matched["direct_damage"]=amount

    leaves=checked["terminal_execution"]["terminal_leaves"]
    if not constraints:
        result=_result("incomplete","insufficient_observation",checked,observations,leaves,matched)
    else:
        compatible=[]
        for leaf in leaves:
            ok=True
            for constraint in constraints:
                if constraint=="flinch": ok = ok and _flinch_leaf(leaf, checked["target"])
                else:
                    _,amount=constraint
                    source=leaf.get("consequences",{}).get("source_hit_context",{})
                    ok = ok and isinstance(source,Mapping) and source.get("actual_damage")==amount
            if ok: compatible.append(leaf)
        result=_result("resolved",None,checked,observations,compatible,matched)
    if (prediction, predictive_binding, predictive_ledger, executed_move_observation, flinch_causality_observation, direct_damage_observation) != baseline:
        return _r("rejected","reconciliation_input_mutated")
    return result


def _leaf_binding(leaf, checked):
    if not isinstance(leaf, Mapping) or not isinstance(leaf.get("leaf_id"), str) or not isinstance(leaf.get("candidate_id"), str):
        return False
    provenance=leaf.get("provenance")
    if not isinstance(provenance, Mapping):
        return False
    if provenance.get("attacker") != checked["actor"] or provenance.get("target") != checked["target"] or provenance.get("move_id") != checked["move_id"]:
        return False
    for key in ("session_id","source_runtime_fingerprint","source_branch_fingerprint","decision_owner"):
        if key in provenance and provenance.get(key) != checked[key]:
            return False
    return _fraction(leaf.get("probability")) is not None


def _caller_context(authority):
    if authority.get("execution_grant")=="authenticated_standard_charge_turn_two_only":
        return ("forced_turn_two_continuation",authority.get("original_charge_lifecycle"),"forced_turn_two_continuation",authority.get("original_charge_action_id"),authority.get("source_next_decision_fingerprint"))
    if authority.get("schema_version")=="runtime-d0-standard-charge-power-herb-skip-execution-authority-v1":
        lifecycle=authority.get("canonical_charge_lifecycle_authority")
        if not isinstance(lifecycle,Mapping):
            lifecycle=authority.get("readiness_authority")
        return ("power_herb_current_turn_skip",lifecycle,"power_herb_current_turn_skip",authority.get("action_id"),authority.get("source_runtime_fingerprint"))
    return (None,None,None,None,None)


def _flinch_leaf(leaf,target):
    if leaf.get("hit_state") != "hit":
        return False
    consequences=leaf.get("consequences")
    secondary=consequences.get("secondary") if isinstance(consequences,Mapping) else None
    hypothetical=secondary.get("hypothetical_target_flinch") if isinstance(secondary,Mapping) else None
    return (
        isinstance(secondary,Mapping) and secondary.get("branch")=="effect"
        and isinstance(hypothetical,Mapping)
        and hypothetical.get("schema_version")=="detached-hypothetical-immediate-flinch-v1"
        and hypothetical.get("state")=="flinched"
        and leaf.get("provenance",{}).get("target")==target
    )


def _execution_error(value, checked):
    payload=_payload(value) if isinstance(value,Mapping) else {}
    return (
        not isinstance(value,Mapping) or value.get("event_kind")!="executed_move_observed"
        or value.get("session_id")!=checked["session_id"] or value.get("turn_number")!=checked["turn_number"]
        or _owner_obs(value)!=checked["actor"]
        or payload.get("source_action_id")!=checked["source_action_id"] or payload.get("move_id")!=checked["move_id"]
    )


def _causal_error(value, checked, execution):
    if not isinstance(value,Mapping) or value.get("event_kind")!="flinch_causality_observed":
        return "flinch_causality_observation_invalid"
    if (
        value.get("session_id")!=checked["session_id"] or value.get("turn_number")!=checked["turn_number"]
        or value.get("source")!="ui_flinch_causality_confirmation"
        or value.get("trust")!="user_confirmed_observation"
        or value.get("observed") is not True or value.get("confirmed") is not True
        or value.get("reducer_eligibility")!="evidence_only"
        or value.get("reconciliation_eligible") is not True
        or value.get("provenance")!="authenticated_c5_cross_action_flinch_causality_v1"
    ): return "flinch_causality_charge_provenance_invalid"
    payload=_payload(value)
    required={
        "producer_source_action_id":checked["source_action_id"],
        "producer_move_id":checked["move_id"],
        "producer_owner":checked["actor"],
        "producer_execution_observation_id":execution.get("observation_id"),
        "affected_owner":checked["target"],
        "producer_predictive_ledger_fingerprint":checked["predictive_ledger_fingerprint"],
        "producer_prediction_kind":"standard_charge_terminal_execution",
        "producer_prediction_fingerprint":checked["terminal_prediction_fingerprint"],
        "original_charge_action_id":checked["original_charge_action_id"],
        "terminal_action_identity":checked["terminal_action_identity"],
        "execution_mode":checked["execution_mode"],
        "caller_kind":checked["caller_kind"],
        "charge_lifecycle":checked["charge_lifecycle"],
    }
    if any(value.get(key)!=expected or payload.get(key)!=expected for key,expected in required.items()):
        return "flinch_causality_charge_prediction_mismatch"
    for key in ("cancelled_source_action_id","cancelled_move_id","cancelled_execution_observation_id","cancelled_result_observation_id"):
        if not isinstance(value.get(key),str) or not value[key] or value.get(key)!=payload.get(key):
            return "flinch_causality_cancelled_reference_invalid"
    if value["cancelled_source_action_id"]==checked["source_action_id"]:
        return "flinch_causality_same_action_invalid"
    if _sequence(value)<=_sequence(execution):
        return "flinch_causality_sequence_invalid"
    return None


def _damage_error(value, checked, execution):
    if not isinstance(value,Mapping) or value.get("event_kind")!="direct_move_damage_observed": return "direct_damage_observation_invalid"
    if value.get("session_id")!=checked["session_id"] or value.get("turn_number")!=checked["turn_number"]: return "direct_damage_session_or_turn_mismatch"
    if value.get("source")!="ui_observed_damage_confirmation" or value.get("trust")!="user_confirmed_observation" or value.get("observed") is not True or value.get("confirmed") is not True: return "direct_damage_provenance_invalid"
    if value.get("source_action_id")!=checked["source_action_id"] or value.get("move_id")!=checked["move_id"]: return "direct_damage_action_link_mismatch"
    if value.get("predictive_ledger_fingerprint")!=checked["predictive_ledger_fingerprint"]: return "direct_damage_prediction_reference_mismatch"
    if value.get("linked_execution_observation_id")!=execution.get("observation_id") or value.get("reconciliation_eligible") is not True: return "direct_damage_execution_reference_mismatch"
    if not isinstance(value.get("attacker"),Mapping) or {k:value["attacker"].get(k) for k in ("session_id","side","slot_index","pokemon_id")} != checked["actor"]: return "direct_damage_owner_mismatch"
    if not isinstance(value.get("defender"),Mapping) or {k:value["defender"].get(k) for k in ("session_id","side","slot_index","pokemon_id")} != checked["target"]: return "direct_damage_owner_mismatch"
    amount=value.get("damage_amount",_payload(value).get("damage_amount"))
    if isinstance(amount,bool) or not isinstance(amount,int) or amount<0 or value.get("hp_unit",_payload(value).get("hp_unit"))!="exact": return "direct_damage_amount_invalid"
    if _sequence(value)<=_sequence(execution): return "direct_damage_sequence_invalid"
    return None


def _result(status,reason,checked,observations,leaves,matched):
    mass=sum((_fraction(row.get("probability")) or Fraction() for row in leaves),Fraction())
    outcome=None if status!="resolved" else "incompatible_observation" if not leaves else "uniquely_matched" if len(leaves)==1 else "multiple_compatible_branches"
    critical={row.get("critical_state") for row in leaves}; rolls={str(row.get("damage_roll")) for row in leaves}
    hidden=tuple(name for name,values in (("critical_state",critical),("damage_roll",rolls)) if len(values)>1)
    return {
        "status":status,"schema_version":"detached-observed-rng-reconciliation-v1","reason":reason,
        "source_prediction_kind":"standard_charge_terminal_execution",
        "source_prediction_identity":{"schema_version":SCHEMA_VERSION,"fingerprint":checked["terminal_prediction_fingerprint"],"source_action_id":checked["source_action_id"],"move_id":checked["move_id"]},
        "session_id":checked["session_id"],"turn_number":checked["turn_number"],"actor":deepcopy(checked["actor"]),"target":deepcopy(checked["target"]),"move_id":checked["move_id"],"source_action_id":checked["source_action_id"],
        "compatible_leaf_ids":tuple(row["leaf_id"] for row in leaves),"compatible_original_probability_mass":_fd(mass),
        "probability_normalization":"none_preserve_original_mass","matched_observable_facts":deepcopy(matched),
        "unresolved_hidden_dimensions":hidden,"match_outcome":outcome,
        "source_observations":tuple({"observation_id":row.get("observation_id"),"observation_sequence":row.get("observation_sequence"),"event_kind":row.get("event_kind")} for row in observations),
        "provenance":"detached_historical_prediction_observation_compatibility_filter_v1",
    }


def _payload(value):
    payload=value.get("payload") if isinstance(value,Mapping) else None
    return payload if isinstance(payload,Mapping) else value


def _owner_obs(value):
    return {key:value.get(key) for key in ("session_id","side","slot_index","pokemon_id")}


def _sequence(value):
    seq=value.get("observation_sequence") if isinstance(value,Mapping) else None
    return seq if isinstance(seq,int) and not isinstance(seq,bool) else 0


def _fraction(value):
    if not isinstance(value,Mapping): return None
    n,d=value.get("numerator"),value.get("denominator")
    if isinstance(n,bool) or isinstance(d,bool) or not isinstance(n,int) or not isinstance(d,int) or d<=0: return None
    return Fraction(n,d)


def _fd(value):
    return {"numerator":value.numerator,"denominator":value.denominator}


def _fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=list).encode("ascii")).hexdigest()


def _r(status,reason):
    return {"status":status,"schema_version":SCHEMA_VERSION,"reason":reason}
