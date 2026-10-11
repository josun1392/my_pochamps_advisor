"""Versioned, source-bound native outcomes; no sampling-to-exact conversion."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID
from llm.advisor_battle_decision_phase import KEY as PHASE_KEY
from llm.advisor_showdown_simulation import (
    prove_deterministic_native_action, progress_native_showdown, _checkpoint_fingerprint,
)

SCHEMA_VERSION = "showdown-native-outcome-evidence-v1"
EXACT_SCOPE = "one_completed_native_move_attempt_constant_rng"
_UNIT = {"numerator": 1, "denominator": 1}
_STOCHASTIC = {"native_stochastic_rng_required", "native_raw_rng_not_proven",
               "untracked_randomness_not_proven", "forced_native_randomness_not_proven"}


def evidence_fingerprint(evidence: Mapping[str, Any]) -> str:
    value = {k: v for k, v in evidence.items() if k != "evidence_fingerprint"}
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def build_native_selected_action_outcome(*, strategy_d0, runtime_snapshot, action, actor, target,
                                        move_metadata, checkpoint, bridge, choices=None,
                                        require_deterministic=True) -> dict:
    """Prove one constant-RNG attempt or return a distinctly seeded execution.

    Unit mass covers observable mechanics through this attempt, conditional on
    the complete hypothetical root and choices. It excludes deferred actions,
    future PRNG state distributions, residuals and any opponent-set prior.
    """
    from llm.advisor_detached_selected_action_execution_result import _base
    base = _base(strategy_d0, runtime_snapshot, action, actor, target, move_metadata)
    if (base is None or type(require_deterministic) is not bool or action.get("action_type") != "attack" or
        _to_id(action.get("identity") or action.get("move_id") or "") != _to_id(base["move_id"])):
        return _error("rejected", "native_outcome_source_binding_invalid")
    operation = prove_deterministic_native_action if require_deterministic else progress_native_showdown
    result = operation(runtime_snapshot=runtime_snapshot, checkpoint=checkpoint, bridge=bridge, choices=choices)
    row = result.get("scenarios", [{}])[0] if result.get("scenarios") else result
    if row.get("status") != "simulated":
        reason = row.get("reason", "native_outcome_unavailable")
        status = "unsupported" if reason in _STOCHASTIC else row.get("status", "rejected")
        return _error(status, reason, base)
    attempts = row.get("native_progression", {}).get("move_attempts", [])
    expected = {"side": actor["side"], "slot_index": actor["slot_index"],
                "queued_move": _to_id(base["move_id"])}
    if attempts != [expected]:
        return _error("rejected", "native_outcome_selected_action_phase_mismatch", base)
    native = deepcopy(row)
    native.pop("elapsed_ms", None)
    evidence = {"status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "engine_commit": SHOWDOWN_COMMIT, "format_id": FORMAT_ID,
        "evidence_class": "native_conditional_exact" if require_deterministic else "native_seeded_execution",
        "source_native_phase": deepcopy(native["before"]["decision_phase"]),
        "observed_phase": deepcopy(runtime_snapshot["state"].get(PHASE_KEY)),
        "source_checkpoint_fingerprint": checkpoint.get("checkpoint_fingerprint"),
        "source_capture_fingerprint": evidence_fingerprint(runtime_snapshot),
        "source_action": deepcopy(action), "source_move_metadata": deepcopy(move_metadata),
        "choices": deepcopy(choices), "native_outcome": native,
        "hypothetical_provenance": {"scenario_id": checkpoint["scenario_id"],
            "assumptions": deepcopy(checkpoint["assumptions"]),
            "model_definition": deepcopy(checkpoint["model_definition"]),
            "interpretation": "conditional_hypothesis_never_observed_truth"},
        "probability_scope": {"scope": EXACT_SCOPE if require_deterministic else "specific_state_choices_seed",
            "complete": require_deterministic,
            "excluded": ["deferred_actions", "residuals", "future_rng_distribution", "opponent_set_prior"]}}
    if require_deterministic:
        evidence["probability_mass"] = deepcopy(_UNIT)
        evidence["branches"] = [{"probability": deepcopy(_UNIT),
            "post_checkpoint_fingerprint": native["checkpoint"]["checkpoint_fingerprint"]}]
    evidence["evidence_fingerprint"] = evidence_fingerprint(evidence)
    checked = validate_native_selected_action_outcome(evidence=evidence, base=base, runtime_snapshot=runtime_snapshot)
    return evidence if checked["status"] == "resolved" else checked


def validate_native_selected_action_outcome(*, evidence, base, runtime_snapshot) -> dict:
    """Validate the owned bridge contract before any compatible consumption."""
    try:
        if not isinstance(evidence, Mapping) or evidence.get("status") != "resolved":
            raise ValueError("native_outcome_not_resolved")
        if (evidence.get("schema_version") != SCHEMA_VERSION or
            evidence.get("engine_commit") != SHOWDOWN_COMMIT or evidence.get("format_id") != FORMAT_ID or
            evidence.get("evidence_fingerprint") != evidence_fingerprint(evidence)):
            raise ValueError("native_outcome_contract_or_digest_invalid")
        if any(evidence.get(k) != v for k, v in base.items()):
            raise ValueError("native_outcome_consumer_binding_mismatch")
        if (runtime_snapshot.get("session_id") != base["session_id"] or
            runtime_snapshot.get("state_fingerprint") != base["source_runtime_fingerprint"]):
            raise ValueError("native_outcome_runtime_mismatch")
        from llm.advisor_showdown_simulation import _state
        _state(runtime_snapshot)
        if (evidence.get("source_capture_fingerprint") != evidence_fingerprint(runtime_snapshot) or
            evidence["source_action"].get("action_id") != base["action_id"] or
            evidence["source_action"].get("action_type") != "attack" or
            _to_id(evidence["source_action"].get("identity") or evidence["source_action"].get("move_id") or "") != _to_id(base["move_id"]) or
            evidence["source_move_metadata"].get("move_id") != base["move_id"]):
            raise ValueError("native_outcome_capture_or_action_mismatch")
        row = evidence["native_outcome"]
        for key in ("root_checkpoint", "checkpoint"):
            cp = row[key]
            saved = {k: v for k, v in cp.items() if k != "checkpoint_fingerprint"}
            if (cp.get("checkpoint_fingerprint") != _checkpoint_fingerprint(saved) or
                cp.get("session_id") != base["session_id"] or cp.get("source_runtime_fingerprint") != base["source_runtime_fingerprint"] or
                cp.get("engine_commit") != SHOWDOWN_COMMIT or cp.get("format_id") != FORMAT_ID):
                raise ValueError("native_outcome_checkpoint_binding_invalid")
        root = row["root_checkpoint"]
        if (evidence["source_checkpoint_fingerprint"] != root["checkpoint_fingerprint"] or
            evidence["source_native_phase"] != row["before"]["decision_phase"] or
            evidence["hypothetical_provenance"] != {"scenario_id": root["scenario_id"],
                "assumptions": root["assumptions"], "model_definition": root["model_definition"],
                "interpretation": "conditional_hypothesis_never_observed_truth"} or
            evidence["observed_phase"] != runtime_snapshot["state"].get(PHASE_KEY) or
            row["native_progression"]["move_attempts"] != [{"side": base["actor"]["side"],
                "slot_index": base["actor"]["slot_index"], "queued_move": _to_id(base["move_id"])}]):
            raise ValueError("native_outcome_phase_or_hypothesis_mismatch")
        classification = evidence["evidence_class"]
        expected_scope = {"scope": EXACT_SCOPE if classification == "native_conditional_exact" else "specific_state_choices_seed",
            "complete": classification == "native_conditional_exact",
            "excluded": ["deferred_actions", "residuals", "future_rng_distribution", "opponent_set_prior"]}
        if evidence["probability_scope"] != expected_scope:
            raise ValueError("native_outcome_probability_scope_invalid")
        if classification == "native_conditional_exact":
            proof = row["determinism_proof"]
            if (evidence["probability_scope"].get("scope") != EXACT_SCOPE or
                evidence["probability_scope"].get("complete") is not True or
                proof.get("schema_version") != "showdown-constant-rng-proof-v1" or
                proof.get("method") != "native_rng_guard_no_nonconstant_draws" or
                proof.get("stochastic_draws") != 0 or proof.get("probability_mass") != _UNIT or
                proof.get("scope") != "one_completed_native_move_attempt_not_deferred_actions" or
                evidence.get("probability_mass") != _UNIT or
                evidence.get("branches") != [{"probability": _UNIT,
                    "post_checkpoint_fingerprint": row["checkpoint"]["checkpoint_fingerprint"]}]):
                raise ValueError("native_outcome_exact_mass_or_proof_invalid")
            draws = proof["constant_draws"]
            if (type(proof["stochastic_draws"]) is not int or type(proof["native_raw_calls"]) is not int or
                proof["native_raw_calls"] != len(draws) or not all(_constant_draw(draw) for draw in draws) or
                not all(type(p[k]) is int for p in (evidence["probability_mass"], evidence["branches"][0]["probability"]) for k in ("numerator", "denominator"))):
                raise ValueError("native_outcome_constant_rng_trace_invalid")
        elif classification == "native_seeded_execution":
            if (evidence["probability_scope"].get("complete") is not False or
                any(k in evidence for k in ("probability_mass", "branches")) or "determinism_proof" in row):
                raise ValueError("seeded_execution_cannot_own_probability")
        else:
            raise ValueError("native_outcome_evidence_class_unsupported")
        return {"status": "resolved"}
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        return _error("rejected", str(exc) if isinstance(exc, ValueError) else "native_outcome_shape_invalid", base)


def _to_id(value):
    return "".join(c for c in value.lower() if c.isascii() and c.isalnum())


def _constant_draw(draw):
    if draw.get("kind") == "singleton_integer":
        first, last = draw.get("from"), draw.get("to")
        return (type(first) is int and first == 1 and last is None or
                type(first) is int and type(last) is int and last > 0 and last - first == 1)
    if draw.get("kind") == "constant_bernoulli":
        n, d = draw.get("numerator"), draw.get("denominator")
        return type(n) in (int, float) and type(d) is int and d > 0 and (n <= 0 or n >= d)
    return False


def _error(status, reason, base=None):
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(base or {}), "reason": reason}
