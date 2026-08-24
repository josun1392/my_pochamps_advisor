"""Detached critical/non-critical branches inside one authoritative hit path."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "deterministic-predictive-critical-hit-uncertainty-v1"
HORIZON = "immediate_action_consequence"
FACT_SCHEMA = "deterministic-guaranteed-candidate-facts-v1"


def compose_predictive_critical_hit_uncertainty(
    *,
    candidate: Mapping[str, Any],
    strict_critical_hit_probability: Mapping[str, Any],
    paired_damage_contexts: Mapping[str, Any],
    non_critical_consequences: Mapping[str, Any],
    critical_consequences: Mapping[str, Any],
) -> dict[str, Any]:
    """Expose exact crit reachability without recalculating leaf mechanics."""
    probability = _probability(strict_critical_hit_probability)
    if probability.get("status") != "resolved":
        return probability
    if not _candidate(candidate) or candidate["candidate_id"] != f"attack:{probability['move_id']}" or not _same_candidate_binding(candidate, probability):
        return _result("rejected", "critical_probability_candidate_mismatch")
    contexts = _contexts(paired_damage_contexts, probability)
    if contexts is None:
        return _result("rejected", "critical_damage_context_binding_mismatch")
    non_facts = _facts(non_critical_consequences, candidate)
    critical_facts = _facts(critical_consequences, candidate)
    if non_facts is None or critical_facts is None:
        return _result("rejected", "invalid_critical_hit_consequence_input")

    numerator, denominator = probability["numerator"], probability["denominator"]
    non_branch = _branch("non_critical", denominator - numerator, denominator, contexts["non_critical"], non_critical_consequences, non_facts)
    critical_branch = _branch("critical", numerator, denominator, contexts["critical"], critical_consequences, critical_facts)
    branches = (non_branch,) if numerator == 0 else (critical_branch,) if numerator == denominator else (non_branch, critical_branch)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, "horizon": HORIZON,
        "session_id": probability["session_id"], "source_runtime_fingerprint": probability["source_runtime_fingerprint"],
        "source_branch_fingerprint": probability["source_branch_fingerprint"],
        "decision_owner": deepcopy(dict(probability["decision_owner"])), "attacker": deepcopy(dict(probability["attacker"])),
        "target": deepcopy(dict(probability["target"])), "move_id": probability["move_id"],
        "strict_critical_hit_probability": deepcopy(dict(strict_critical_hit_probability)),
        "critical_probability": {"numerator": numerator, "denominator": denominator},
        "branches": branches, "guaranteed_facts": _intersection(candidate, branches),
        "provenance": "strict_critical_probability_to_detached_predictive_critical_branches_v1",
    }


def _probability(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return _result("rejected", "invalid_strict_critical_hit_probability")
    status = value.get("status")
    if status in {"incomplete", "unsupported", "rejected"}:
        return _result(status, _reason(value, "strict_critical_hit_probability_unavailable"))
    probability = value.get("critical_probability")
    required = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target", "move_id")
    if value.get("schema_version") != "strict-critical-hit-probability-v1" or status != "resolved" or not all(key in value for key in required) or not _owner(value.get("decision_owner")) or not _owner(value.get("attacker")) or not _owner(value.get("target")) or not isinstance(probability, Mapping):
        return _result("rejected", "invalid_resolved_strict_critical_hit_probability")
    numerator, denominator = probability.get("numerator"), probability.get("denominator")
    if not _integer(numerator) or not _integer(denominator) or denominator <= 0 or numerator < 0 or numerator > denominator:
        return _result("rejected", "invalid_critical_probability_fraction")
    if not all(isinstance(value.get(key), str) and value[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "move_id")):
        return _result("rejected", "critical_probability_binding_unavailable")
    return {"status": "resolved", "session_id": value["session_id"], "source_runtime_fingerprint": value["source_runtime_fingerprint"], "source_branch_fingerprint": value["source_branch_fingerprint"], "decision_owner": value["decision_owner"], "attacker": value["attacker"], "target": value["target"], "move_id": value["move_id"], "numerator": numerator, "denominator": denominator}


def _contexts(value: Any, probability: Mapping[str, Any]) -> dict[str, Mapping[str, Any]] | None:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != "strict-predictive-critical-damage-context-v1":
        return None
    keys = ("session_id", "source_branch_fingerprint", "decision_owner", "attacker", "target", "move_id")
    if any(value.get(key) != probability.get(key) for key in keys):
        return None
    non_critical, critical = value.get("non_critical_context"), value.get("critical_context")
    if not all(isinstance(context, Mapping) and context.get("completeness") == "exact_complete" for context in (non_critical, critical)):
        return None
    if non_critical.get("scope", {}).get("critical") != "non_critical_assumed" or critical.get("scope", {}).get("critical") != "critical_assumed":
        return None
    return {"non_critical": non_critical, "critical": critical}


def _facts(consequences: Any, candidate: Mapping[str, Any]) -> Mapping[str, Any] | None:
    facts = consequences.get("guaranteed_facts") if isinstance(consequences, Mapping) else None
    return facts if isinstance(facts, Mapping) and facts.get("status") == "resolved" and facts.get("schema_version") == FACT_SCHEMA and facts.get("horizon") == HORIZON and all(facts.get(key) == candidate.get(key) for key in ("candidate_id", "action_type", "session_id", "source_branch_fingerprint", "decision_owner")) else None


def _branch(name: str, numerator: int, denominator: int, context: Mapping[str, Any], consequences: Mapping[str, Any], facts: Mapping[str, Any]) -> dict[str, Any]:
    return {"branch": name, "conditional_critical_probability": {"numerator": numerator, "denominator": denominator}, "damage_context": deepcopy(dict(context)), "consequences": deepcopy(dict(consequences)), "branch_facts": deepcopy(dict(facts))}


def _intersection(candidate: Mapping[str, Any], branches: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    facts = [branch["branch_facts"] for branch in branches]
    own = _common(facts, "guaranteed_own_fainted")
    target = _common(facts, "guaranteed_opponent_fainted")
    hp = _common(facts, "exact_own_hp")
    possible = any(bool(fact.get("possible_opponent_ko")) or fact.get("guaranteed_opponent_fainted") is True for fact in facts)
    return {"status": "resolved", "schema_version": FACT_SCHEMA, "candidate_id": candidate["candidate_id"], "action_type": candidate["action_type"], "session_id": candidate["session_id"], "source_branch_fingerprint": candidate["source_branch_fingerprint"], "decision_owner": deepcopy(dict(candidate["decision_owner"])), "horizon": HORIZON, "evidence_class": "critical_hit_branch_intersection", "guaranteed_own_fainted": own, "guaranteed_opponent_fainted": target, "exact_own_hp": hp, "possible_opponent_ko": possible, "substitute_facts": {}, "provenance": "detached_predictive_critical_hit_branch_intersection_v1"}


def _common(facts: list[Mapping[str, Any]], key: str) -> Any:
    values = [fact.get(key) for fact in facts]
    return values[0] if values and values[0] is not None and all(value == values[0] for value in values) else None


def _same_candidate_binding(candidate: Mapping[str, Any], probability: Mapping[str, Any]) -> bool:
    return all(candidate.get(key) == probability.get(key) for key in ("session_id", "source_branch_fingerprint", "decision_owner"))


def _candidate(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("action_type") == "attack" and isinstance(value.get("candidate_id"), str) and bool(value["candidate_id"]) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and isinstance(value.get("source_branch_fingerprint"), str) and bool(value["source_branch_fingerprint"]) and _owner(value.get("decision_owner"))


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("side") in {"self", "opponent"} and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and _integer(value.get("slot_index")) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _reason(value: Mapping[str, Any], fallback: str) -> str:
    return value.get("reason") if isinstance(value.get("reason"), str) and value["reason"] else fallback


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
