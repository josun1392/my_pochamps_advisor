"""Conditional candidate intents when the legacy selection cycle is unavailable.

This contract cannot be supplied to legacy selection/execution consumers. Native
legality is evaluated separately inside each complete hypothetical state.
"""
from copy import deepcopy
from llm.advisor_runtime_d0_selection_projection import build_runtime_d0_selection_capture
from llm.advisor_showdown_shadow import evaluate_current_showdown_shadow
from llm.advisor_showdown_strategy_evaluation import fingerprint, native_strategy_binding, experimental_ranking

SCHEMA = "showdown-conditional-strategy-explanation-v1"


def build_conditional_native_preview(*, capture, strategy_d0, intents, context, bridge, deferred, experiment, legacy_reason):
    token = build_runtime_d0_selection_capture(strategy_d0=strategy_d0)
    if not isinstance(intents, dict) or intents.get("schema_version") != "showdown-ui-candidate-intents-v1" or intents.get("capture") != token:
        raise ValueError("native_candidate_capture_mismatch")
    moves, switches = intents["moves"], intents["switches"]
    if not isinstance(moves, list) or not isinstance(switches, list) or len(moves) > 4 or len(switches) > 5:
        raise ValueError("invalid_native_candidate_intents")
    if any(not isinstance(x, str) or not x for x in moves + switches) or len(set(moves)) != len(moves) or len(set(switches)) != len(switches):
        raise ValueError("invalid_native_candidate_intents")
    roster = capture["state"]["self_side"]["pokemon"]
    if any(sum(p["pokemon_id"] == sid for p in roster.values()) != 1 or sid == strategy_d0["decision_owner"]["pokemon_id"] for sid in switches):
        raise ValueError("native_switch_intent_identity_mismatch")
    actions = [{"action_id": f"{kind}:{identity}", "action_type": kind, "identity": identity, "selection": "conditional"}
        for kind, identities in (("attack", moves), ("manual_switch", switches)) for identity in identities]
    requested = context.get("conditional_candidate_ids")
    if requested is not None:
        if (not isinstance(requested, list) or not requested or any(not isinstance(x, str) for x in requested) or
            len(set(requested)) != len(requested) or not set(requested) <= {a["action_id"] for a in actions}):
            raise ValueError("invalid_conditional_candidate_filter")
        actions = [a for a in actions if a["action_id"] in requested]
    if not actions: raise ValueError("no_native_candidate_intents")
    selection = {"schema_version": "showdown-conditional-candidate-intents-v1",
        "interpretation": "hypothetical_candidates_not_observed_selectability",
        "session_id": capture["session_id"], "decision_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(strategy_d0["decision_owner"]), "actions": actions}
    explanation = {"schema_version": SCHEMA, "status": "resolved", "horizon": "conditional_native_rollout",
        "session_id": capture["session_id"], "source_runtime_fingerprint": capture["state_fingerprint"],
        "source_capture_fingerprint": fingerprint(capture), "decision_branch_fingerprint": selection["decision_branch_fingerprint"],
        "decision_owner": deepcopy(selection["decision_owner"]), "overall_status": "incomplete_comparison_set",
        "preferred_frontier": [], "comparison_matrix": [], "probability_aware_decisions": [],
        "legacy_selection_status": {"status": "rejected", "reason": legacy_reason},
        "candidate_scope": "hypothetical_native_legality_not_live_selection_authority",
        "candidate_filter": deepcopy(requested),
        "candidates": [{"candidate_id": a["action_id"], "action_type": a["action_type"], "evidence_class": "incomplete",
            "guaranteed_facts": None, "incomplete_reason": "native_conditional_only", "comparison_reasons": []} for a in actions]}
    job = {"runtime_snapshot": deepcopy(capture), "selection": selection, "context": deepcopy(context), "experimental_ranking": experiment is True}
    if deferred:
        evidence = {**native_strategy_binding(capture, selection), "status": "pending", "reason": "native_evaluation_running"}
    else:
        evidence = evaluate_current_showdown_shadow(runtime_snapshot=capture, selection=selection, context=context, bridge=bridge)
    explanation["sampled_simulation"] = evidence
    if not deferred:
        ranking = experimental_ranking(evidence=evidence, explanation=explanation, enabled=experiment)
        if ranking is not None: explanation["experimental_ranking"] = ranking
    return {"schema_version": "ui-detached-strategy-bridge-result-v1", "status": "resolved", "native_conditional_only": True,
        "source_runtime_fingerprint": capture["state_fingerprint"], "strategy_preview_fingerprint": selection["decision_branch_fingerprint"],
        "decision_owner": deepcopy(selection["decision_owner"]), "exact_outcome_ledgers": {}, "descriptive_metrics": {},
        "opponent_response_profiles": {}, "explanation": explanation,
        **({"native_evaluation_job": job} if deferred else {})}
