"""Versioned, conditional native rollout evidence. Never an exact ledger owner."""
from copy import deepcopy
from hashlib import sha256
import json
from math import isfinite

from advisor.showdown_bridge import FORMAT_ID, SHOWDOWN_COMMIT
from llm.advisor_showdown_simulation import simulate_detached_showdown

SCHEMA = "showdown-strategy-shadow-v2"
INTERPRETATION = "conditional_monte_carlo_estimate_not_exact_probability"
SCOPE = "terminal_win_within_bounded_native_rollout"
COUNTS = ("self_win_samples", "opponent_win_samples", "draw_samples", "truncated_samples")


def valid_rollout_policy(policy):
    try:
        if (not isinstance(policy, dict) or policy.get("schema_version") != "showdown-rollout-policy-v1" or
            policy.get("policy") != "showdown-random-player" or type(policy.get("max_decisions")) is not int or not 1 <= policy["max_decisions"] <= 128): return False
        for side in ("self", "opponent"):
            move, mega = policy[side]["move_probability"], policy[side]["mega_probability"]
            if type(move) not in (int, float) or not isfinite(move) or not 0 < move <= 1: return False
            if type(mega) not in (int, float) or not isfinite(mega) or not 0 <= mega <= 1: return False
        return True
    except (KeyError, TypeError): return False


def fingerprint(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def win_estimate(row):
    n, wins, unresolved = row["sample_count"], row["self_win_samples"], row["truncated_samples"]
    return {"scope": SCOPE, "estimate": wins / n, "unresolved_fraction": unresolved / n,
        "completion_bounds": [wins / n, (wins + unresolved) / n],
        "interpretation": "sample_frequencies_and_completion_bounds_not_exact_probability_or_confidence_interval"}


def native_strategy_binding(runtime_snapshot, selection):
    return {"schema_version": SCHEMA, "mode": "shadow", "interpretation": INTERPRETATION,
        "evidence_class": "monte_carlo_estimate", "probability_scope": SCOPE,
        "engine_commit": SHOWDOWN_COMMIT, "format_id": FORMAT_ID,
        "session_id": runtime_snapshot["session_id"], "source_runtime_fingerprint": runtime_snapshot["state_fingerprint"],
        "source_capture_fingerprint": fingerprint(runtime_snapshot),
        "candidate_scope": ("hypothetical_native_legality_not_live_selection_authority" if selection.get("schema_version") == "showdown-conditional-candidate-intents-v1" else "captured_current_selection_authority"),
        "decision_branch_fingerprint": selection["decision_branch_fingerprint"], "decision_owner": deepcopy(selection["decision_owner"])}


def evaluate_current_native_strategy(*, runtime_snapshot, selection, context, bridge):
    from llm.advisor_showdown_shadow import selected_native_choices
    binding = native_strategy_binding(runtime_snapshot, selection)
    try:
        if selection["decision_owner"]["side"] != "self": raise ValueError("showdown_shadow_self_decision_required")
        seeds, source_scenarios, policy = deepcopy(context["seeds"]), deepcopy(context["scenarios"]), deepcopy(context["rollout_policy"])
        choices = selected_native_choices(runtime_snapshot, selection)
        if not choices or not isinstance(seeds, list) or not 1 <= len(seeds) <= 64: raise ValueError("invalid_showdown_shadow_context")
        if not isinstance(source_scenarios, list) or not 1 <= len(source_scenarios) <= 16: raise ValueError("invalid_scenarios")
        hypothesis_ids = [s.get("scenario_id") for s in source_scenarios]
        if not all(isinstance(sid, str) and sid for sid in hypothesis_ids) or len(set(hypothesis_ids)) != len(hypothesis_ids): raise ValueError("invalid_scenario_identity")
        if not valid_rollout_policy(policy): raise ValueError("invalid_rollout_policy")
        modeled, identities = [], {}
        for source in source_scenarios:
            actions = source["opponent_actions"]
            if not isinstance(actions, list) or not 1 <= len(actions) <= 8: raise ValueError("explicit_opponent_actions_required")
            for action in actions:
                if not isinstance(action.get("action_id"), str) or not action["action_id"].strip() or not isinstance(action.get("choice"), str) or len(action["choice"]) > 100:
                    raise ValueError("explicit_opponent_actions_required")
                cid = json.dumps([source["scenario_id"], action["action_id"]], ensure_ascii=True, separators=(",", ":"))
                if cid in identities: raise ValueError("duplicate_scenario_action_identity")
                scenario = deepcopy(source)
                scenario.pop("opponent_actions")
                scenario["scenario_id"] = cid
                scenario["evaluation"] = {"seeds": seeds, "rollout_policy": policy, "candidates": [
                    {"candidate_id": identity, "choices": [{"self": choice, "opponent": action["choice"]}]} for identity, choice in choices]}
                modeled.append(scenario)
                identities[cid] = {"hypothesis_id": source["scenario_id"], "opponent_action_id": action["action_id"], "opponent_choice": action["choice"]}
        if not 1 <= len(modeled) <= 16 or len(modeled) * len(choices) * len(seeds) * policy["max_decisions"] > 32768:
            raise ValueError("showdown_rollout_budget_exceeded")
        binding.update(context_fingerprint=fingerprint(context), candidate_choices=dict(choices), seeds=seeds,
            rollout_policy=policy, requested_scenario_ids=list(identities), aggregation="per_hypothesis_and_opponent_action_no_implicit_prior")
        result = simulate_detached_showdown(runtime_snapshot=runtime_snapshot, scenarios=modeled, bridge=bridge)
        if result["status"] != "simulated": return {**binding, "status": result["status"], "reason": result.get("reason", "showdown_scenarios_rejected"), "fields": result.get("fields", [])}
        rows = []
        for native in result["scenarios"]:
            row = {"scenario_id": native["scenario_id"], **identities[native["scenario_id"]]}
            if native["status"] != "simulated": rows.append({**row, "status": "rejected", "reason": native["reason"]}); continue
            candidates = []
            for candidate in native["evaluation"]["candidates"]:
                candidate = {k: deepcopy(v) for k, v in candidate.items() if k not in {"samples", "choices", "rollout_policy"}}
                if candidate["status"] == "evaluated": candidate["win_rate"] = win_estimate(candidate)
                candidates.append(candidate)
            rows.append({**row, "status": "evaluated", "assumptions": native["assumptions"],
                "root_checkpoint_fingerprint": native["root_checkpoint"]["checkpoint_fingerprint"],
                "native_decision_phase": native["before"]["decision_phase"], "candidates": candidates})
        if not any(c["status"] == "evaluated" for row in rows for c in row.get("candidates", [])):
            return {**binding, "status": "rejected", "reason": "no_supported_showdown_candidates"}
        return {**binding, "status": "evaluated", "scenarios": rows}
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        return {**binding, "status": "rejected", "reason": str(exc) if isinstance(exc, ValueError) else "invalid_showdown_shadow_context"}


def valid_native_strategy_evidence(value, explanation):
    try:
        if (value.get("schema_version") != SCHEMA or value.get("mode") != "shadow" or value.get("interpretation") != INTERPRETATION or
            value.get("evidence_class") != "monte_carlo_estimate" or value.get("probability_scope") != SCOPE or
            value.get("engine_commit") != SHOWDOWN_COMMIT or value.get("format_id") != FORMAT_ID): return False
        for key in ("session_id", "source_runtime_fingerprint", "source_capture_fingerprint", "decision_branch_fingerprint", "decision_owner"):
            if value.get(key) != explanation.get(key): return False
        if value.get("candidate_scope") != explanation.get("candidate_scope", "captured_current_selection_authority"): return False
        if value.get("status") in {"rejected", "unavailable", "pending"}: return isinstance(value.get("reason"), str)
        if value.get("status") != "evaluated": return False
        ids = {c["candidate_id"] for c in explanation["candidates"]}
        if set(value["candidate_choices"]) != ids or not 1 <= len(value["scenarios"]) <= 16: return False
        for cid, choice in value["candidate_choices"].items():
            if cid.startswith("attack:"):
                if choice != "move " + cid.split(":", 1)[1]: return False
            elif cid.startswith("manual_switch:"):
                if not isinstance(choice, str) or not choice.startswith("switch slot:") or not choice.removeprefix("switch slot:").isdecimal(): return False
            else: return False
        if value["aggregation"] != "per_hypothesis_and_opponent_action_no_implicit_prior": return False
        for key in ("source_capture_fingerprint", "context_fingerprint"):
            if not isinstance(value[key], str) or len(value[key]) != 64: return False
        if value["requested_scenario_ids"] != [s["scenario_id"] for s in value["scenarios"]]: return False
        seeds = value["seeds"]
        if not 1 <= len(seeds) <= 64 or len({tuple(s) for s in seeds}) != len(seeds): return False
        if any(len(s) != 4 or any(type(x) is not int or not 0 <= x <= 65535 for x in s) for s in seeds): return False
        seen = set()
        horizon = value["rollout_policy"]["max_decisions"]
        if not valid_rollout_policy(value["rollout_policy"]) or len(value["scenarios"]) * len(ids) * len(seeds) * horizon > 32768: return False
        for scenario in value["scenarios"]:
            sid = scenario["scenario_id"]
            if sid in seen or sid != json.dumps([scenario["hypothesis_id"], scenario["opponent_action_id"]], ensure_ascii=True, separators=(",", ":")): return False
            seen.add(sid)
            if not isinstance(scenario["opponent_choice"], str): return False
            if scenario["status"] == "rejected":
                if not isinstance(scenario.get("reason"), str): return False
                continue
            if scenario["status"] != "evaluated" or not scenario.get("assumptions") or not all(isinstance(a, str) and a for a in scenario["assumptions"]): return False
            if not isinstance(scenario["root_checkpoint_fingerprint"], str) or len(scenario["root_checkpoint_fingerprint"]) != 64: return False
            if scenario["native_decision_phase"]["interpretation"] != "hypothetical_native_phase_not_observed": return False
            candidates = set()
            for row in scenario["candidates"]:
                if row["candidate_id"] not in ids or row["candidate_id"] in candidates: return False
                candidates.add(row["candidate_id"])
                if row["status"] == "rejected":
                    if not isinstance(row.get("reason"), str): return False
                    continue
                n = row["sample_count"]
                if row["status"] != "evaluated" or type(n) is not int or n != len(seeds) or row["horizon_decisions"] != horizon: return False
                for key in COUNTS + ("self_new_faint_samples", "opponent_new_faint_samples", "ended_samples", "switch_request_samples", "forced_replacement_samples"):
                    if type(row[key]) is not int or not 0 <= row[key] <= n: return False
                if sum(row[k] for k in COUNTS) != n or row["ended_samples"] != n - row["truncated_samples"]: return False
                if row["win_rate"] != win_estimate(row): return False
                first = row["immediate"]
                if first["schema_version"] != "showdown-sampled-first-request-v1" or first["scope"] != "first_native_request_after_initial_choices_not_always_a_complete_turn" or first["sample_count"] != n: return False
                counts = first["request_counts"]
                if set(counts) != {"move", "switch", "ended"} or any(type(v) is not int or not 0 <= v <= n for v in counts.values()) or sum(counts.values()) != n: return False
                for key in ("self_new_faint_samples", "opponent_new_faint_samples", "pending_action_samples"):
                    if type(first[key]) is not int or not 0 <= first[key] <= n: return False
                for key in ("mean_self_health_fraction", "mean_opponent_health_fraction"):
                    if type(first[key]) not in (int, float) or not isfinite(first[key]) or not 0 <= first[key] <= 1: return False
                for key, lo, hi in (("mean_self_health_fraction", 0, 1), ("mean_opponent_health_fraction", 0, 1), ("mean_outcome_value", -1, 1), ("mean_decisions", 1, horizon)):
                    number = row[key]
                    if type(number) not in (float, int) or not isfinite(number) or not lo <= number <= hi: return False
                for key in ("mean_self_team_hp", "mean_opponent_team_hp"):
                    number = row[key]
                    if type(number) not in (int, float) or not isfinite(number) or number < 0: return False
                wins, losses, truncated = (row[k] for k in ("self_win_samples", "opponent_win_samples", "truncated_samples"))
                if not (wins - losses - truncated) / n - 1e-12 <= row["mean_outcome_value"] <= (wins - losses + truncated) / n + 1e-12: return False
            if candidates != ids: return False
        return True
    except (KeyError, TypeError, ValueError, AttributeError): return False


def experimental_ranking(*, evidence, explanation, enabled=False):
    """Disabled by default. Robust comparison across the explicitly supplied grid.

    +1/-1/0 for terminal win/loss/draw; unfinished samples use normalized team HP
    difference. This score is not a win probability or an exact guarantee.
    """
    if enabled is not True: return None
    result = {"schema_version": "showdown-experimental-ranking-v1", "mode": "experimental_offline",
        "default_policy_changed": False, "evidence_class": "monte_carlo_estimate",
        "legacy_preferred_frontier": deepcopy(explanation["preferred_frontier"]),
        "evidence_fingerprint": fingerprint(evidence), "policy": "worst_configured_scenario_mean_terminal_or_hp_value_v1"}
    if not valid_native_strategy_evidence(evidence, explanation) or evidence["status"] != "evaluated":
        return {**result, "status": "unavailable", "reason": "native_evidence_unavailable"}
    if any(s["status"] != "evaluated" or any(c["status"] != "evaluated" for c in s.get("candidates", [])) for s in evidence["scenarios"]):
        return {**result, "status": "unavailable", "reason": "incomplete_scenario_candidate_coverage"}
    scores = []
    for cid in evidence["candidate_choices"]:
        values = [(next(c for c in s["candidates"] if c["candidate_id"] == cid)["mean_outcome_value"], s["scenario_id"]) for s in evidence["scenarios"]]
        score, scenario = min(values)
        scores.append({"candidate_id": cid, "estimated_score": score, "worst_configured_scenario": scenario})
    scores.sort(key=lambda row: (-row["estimated_score"], row["candidate_id"]))
    preferred = [row["candidate_id"] for row in scores if abs(row["estimated_score"] - scores[0]["estimated_score"]) <= 1e-12]
    return {**result, "status": "evaluated", "candidates": scores, "experimental_preferred_frontier": preferred,
        "agrees_with_legacy_frontier": set(preferred) == set(explanation["preferred_frontier"])}
