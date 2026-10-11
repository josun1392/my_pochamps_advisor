"""Opt-in native evidence for the existing captured strategy/explanation seam.

Ranking, exact ledgers and guaranteed facts never consume this evidence.
"""
from copy import deepcopy
from math import isfinite
from llm.advisor_showdown_simulation import simulate_detached_showdown
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID

SCHEMA = "showdown-strategy-shadow-v1"
INTERPRETATION = "conditional_monte_carlo_estimate_not_exact_probability"
COUNTS = ("self_new_faint_samples", "opponent_new_faint_samples", "self_win_samples", "opponent_win_samples", "ended_samples", "switch_request_samples")


def evaluate_current_showdown_shadow(*, runtime_snapshot, selection, context, bridge):
    """Map selectable human actions, with an explicit opponent action per set."""
    if isinstance(context, dict) and context.get("schema_version") == "showdown-shadow-config-v2":
        from llm.advisor_showdown_strategy_evaluation import evaluate_current_native_strategy
        return evaluate_current_native_strategy(runtime_snapshot=runtime_snapshot, selection=selection, context=context, bridge=bridge)
    binding = {"schema_version": SCHEMA, "mode": "shadow", "interpretation": INTERPRETATION,
        "engine_commit": SHOWDOWN_COMMIT, "format_id": FORMAT_ID,
        "session_id": runtime_snapshot["session_id"], "source_runtime_fingerprint": runtime_snapshot["state_fingerprint"],
        "decision_branch_fingerprint": selection["decision_branch_fingerprint"], "decision_owner": deepcopy(selection["decision_owner"])}
    try:
        if selection["decision_owner"]["side"] != "self": raise ValueError("showdown_shadow_self_decision_required")
        if not isinstance(context, dict) or context.get("schema_version") != "showdown-shadow-config-v1": raise ValueError("invalid_showdown_shadow_context")
        scenarios, seeds = deepcopy(context["scenarios"]), deepcopy(context["seeds"])
        if not isinstance(scenarios, list) or not isinstance(seeds, list) or not 1 <= len(seeds) <= 64:
            raise ValueError("invalid_showdown_shadow_context")
        actions = [a for a in selection["actions"] if a["selection"] == "selectable"]
        if not actions or len(scenarios) * len(seeds) * len(actions) > 2048: raise ValueError("showdown_shadow_budget_exceeded")
        choices = selected_native_choices(runtime_snapshot, selection)
        for scenario in scenarios:
            opponent = scenario["choices"]["opponent"]
            if not isinstance(opponent, str) or not opponent.strip(): raise ValueError("explicit_opponent_choice_required")
            scenario["evaluation"] = {"seeds": seeds, "candidates": [
                {"candidate_id": cid, "choices": [{"self": own, "opponent": opponent}]} for cid, own in choices]}
        native = simulate_detached_showdown(runtime_snapshot=runtime_snapshot, scenarios=scenarios, bridge=bridge)
        if native["status"] != "simulated": return {**binding, "status": native["status"], "reason": native.get("reason", "showdown_scenarios_rejected"), "fields": native.get("fields", [])}
        rows = []
        for row in native["scenarios"]:
            if row["status"] != "simulated":
                rows.append({"scenario_id": row["scenario_id"], "status": "rejected", "reason": row["reason"]})
                continue
            candidates = [{key: deepcopy(value) for key, value in candidate.items() if key not in {"samples", "choices"}}
                for candidate in row["evaluation"]["candidates"]]
            rows.append({"scenario_id": row["scenario_id"], "status": "evaluated", "assumptions": row["assumptions"],
                "opponent_choice": next(s for s in scenarios if s["scenario_id"] == row["scenario_id"])["choices"]["opponent"], "candidates": candidates})
        if not any(c["status"] == "evaluated" for row in rows for c in row.get("candidates", [])):
            return {**binding, "status": "rejected", "reason": "no_supported_showdown_candidates"}
        return {**binding, "status": "evaluated", "scenarios": rows}
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        return {**binding, "status": "rejected", "reason": str(exc) if isinstance(exc, ValueError) else "invalid_showdown_shadow_context"}


def valid_shadow_evidence(value, explanation):
    """Presentation guard: sampled values are never exact probability authority."""
    if isinstance(value, dict) and value.get("schema_version") == "showdown-strategy-shadow-v2":
        from llm.advisor_showdown_strategy_evaluation import valid_native_strategy_evidence
        return valid_native_strategy_evidence(value, explanation)
    try:
        if (not isinstance(value, dict) or value.get("schema_version") != SCHEMA or value.get("mode") != "shadow" or
            value.get("interpretation") != INTERPRETATION or value.get("engine_commit") != SHOWDOWN_COMMIT or
            value.get("format_id") != FORMAT_ID or value.get("status") not in {"evaluated", "rejected", "unavailable"}): return False
        if any(value.get(key) != explanation.get(key) for key in ("session_id", "decision_branch_fingerprint", "decision_owner")): return False
        if value.get("source_runtime_fingerprint") != explanation.get("source_runtime_fingerprint"): return False
        if value["status"] != "evaluated": return isinstance(value.get("reason"), str)
        ids = {c["candidate_id"] for c in explanation["candidates"]}
        scenario_ids = set()
        if not isinstance(value["scenarios"], list) or not 1 <= len(value["scenarios"]) <= 16: return False
        for scenario in value["scenarios"]:
            if not isinstance(scenario["scenario_id"], str) or scenario["scenario_id"] in scenario_ids: return False
            scenario_ids.add(scenario["scenario_id"])
            if scenario["status"] == "rejected":
                if not isinstance(scenario.get("reason"), str): return False
                continue
            if scenario["status"] != "evaluated" or not scenario.get("assumptions") or not all(isinstance(a, str) and a for a in scenario["assumptions"]): return False
            seen = set()
            for row in scenario["candidates"]:
                if row["candidate_id"] not in ids or row["candidate_id"] in seen: return False
                seen.add(row["candidate_id"])
                if row["status"] == "rejected":
                    if not isinstance(row.get("reason"), str): return False
                    continue
                n = row["sample_count"]
                if row["status"] != "evaluated" or type(n) is not int or not 1 <= n <= 64 or row.get("horizon_decisions") != 1: return False
                if any(type(row[k]) is not int or not 0 <= row[k] <= n for k in COUNTS): return False
                if any(type(row[k]) not in (int, float) or not isfinite(row[k]) or row[k] < 0 for k in ("mean_self_team_hp", "mean_opponent_team_hp")): return False
            if seen != ids: return False
        return True
    except (KeyError, TypeError, AttributeError): return False


def selected_native_choices(runtime_snapshot, selection):
    choices = []
    roster = runtime_snapshot["state"]["self_side"]["pokemon"]
    conditional = selection.get("schema_version") == "showdown-conditional-candidate-intents-v1"
    if conditional and selection.get("interpretation") != "hypothetical_candidates_not_observed_selectability":
        raise ValueError("invalid_native_candidate_intents")
    for action in selection["actions"]:
        if action["selection"] != ("conditional" if conditional else "selectable"): continue
        if action["action_type"] == "attack": choice = "move " + action["identity"]
        elif action["action_type"] == "manual_switch":
            slots = [slot for slot, p in roster.items() if p["pokemon_id"] == action["identity"]]
            if len(slots) != 1: raise ValueError("showdown_shadow_switch_identity_ambiguous")
            choice = f"switch slot:{slots[0]}"
        else: raise ValueError("unsupported_showdown_shadow_action")
        choices.append((action["action_id"], choice))
    return choices
