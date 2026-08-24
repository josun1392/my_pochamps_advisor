"""Detached hit/miss branches for already-authoritative regular accuracy."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA = "deterministic-predictive-hit-miss-uncertainty-v1"
HORIZON = "immediate_action_consequence"
_FACT_SCHEMA = "deterministic-guaranteed-candidate-facts-v1"


def compose_predictive_hit_miss_uncertainty(
    *, candidate: Mapping[str, Any], strict_hit_probability: Mapping[str, Any],
    hit_consequences: Mapping[str, Any], miss_baseline: Mapping[str, Any],
) -> dict[str, Any]:
    """Branch a supported hit-only consequence without recalculating it.

    The supplied hit consequence remains opaque and detached: this adapter only
    makes its reachability explicit.  A miss branch intentionally contains no
    damage, drain, recoil, or deterministic on-hit stage effect.
    """
    probability = _probability(strict_hit_probability)
    if probability.get("status") != "resolved":
        return probability
    if not _candidate(candidate) or candidate["candidate_id"] != f"attack:{probability['move_id']}":
        return _result("rejected", "hit_probability_candidate_mismatch")
    if any(candidate.get(key) != probability[key] for key in ("session_id", "source_branch_fingerprint", "decision_owner")):
        return _result("rejected", "hit_probability_binding_mismatch")
    hit_facts = hit_consequences.get("guaranteed_facts") if isinstance(hit_consequences, Mapping) else None
    baseline = _baseline(miss_baseline)
    if not _facts(hit_facts, candidate) or baseline is None:
        return _result("rejected", "invalid_hit_miss_consequence_input")

    p = probability["probability_percent"]
    hit_branch = _hit_branch(probability, hit_consequences, hit_facts)
    miss_branch = _miss_branch(probability, candidate, baseline)
    branches = (miss_branch,) if p <= 0 else (hit_branch,) if p >= 100 else (hit_branch, miss_branch)
    facts = _intersection(candidate=candidate, branches=branches)
    return {
        "status": "resolved", "schema_version": SCHEMA, "horizon": HORIZON,
        "session_id": candidate["session_id"], "source_branch_fingerprint": candidate["source_branch_fingerprint"],
        "decision_owner": deepcopy(dict(candidate["decision_owner"])),
        "attacker": deepcopy(dict(probability["attacker"])), "target": deepcopy(dict(probability["target"])),
        "move_id": probability["move_id"], "strict_hit_probability": deepcopy(dict(strict_hit_probability)),
        "raw_accuracy_threshold": probability["raw_accuracy_threshold"], "probability_percent": p,
        "branches": branches, "guaranteed_facts": facts,
        "provenance": "strict_hit_probability_to_detached_predictive_hit_miss_v1",
    }


def _probability(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return _result("rejected", "invalid_strict_hit_probability")
    status = value.get("status")
    if status in {"incomplete", "unsupported", "rejected"}:
        return _result(status, _reason(value, "strict_hit_probability_unavailable"))
    if value.get("schema_version") != "strict-deterministic-hit-probability-v1" or status != "resolved":
        return _result("rejected", "invalid_strict_hit_probability")
    if value.get("result") == "always_hit":
        return _bound_probability(value, probability_percent=100, raw_threshold=None)
    probability, threshold = value.get("probability_percent"), value.get("raw_accuracy_threshold")
    if not _percent(probability) or not _nonnegative_int(threshold) or value.get("result") != "exact_regular_accuracy":
        return _result("rejected", "invalid_resolved_strict_hit_probability")
    return _bound_probability(value, probability_percent=probability, raw_threshold=threshold)


def _bound_probability(value: Mapping[str, Any], *, probability_percent: int, raw_threshold: int | None) -> dict[str, Any]:
    required = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target", "move_id")
    if not all(key in value for key in required) or not isinstance(value.get("session_id"), str) or not value["session_id"]:
        return _result("rejected", "strict_hit_probability_binding_unavailable")
    if not all(isinstance(value.get(key), str) and value[key] for key in ("source_runtime_fingerprint", "source_branch_fingerprint", "move_id")):
        return _result("rejected", "strict_hit_probability_binding_unavailable")
    if not _owner(value.get("decision_owner")) or not _owner(value.get("attacker")) or not _owner(value.get("target")):
        return _result("rejected", "strict_hit_probability_identity_unavailable")
    return {
        "status": "resolved", "session_id": value["session_id"],
        "source_runtime_fingerprint": value["source_runtime_fingerprint"],
        "source_branch_fingerprint": value["source_branch_fingerprint"],
        "decision_owner": value["decision_owner"], "attacker": value["attacker"], "target": value["target"], "move_id": value["move_id"],
        "probability_percent": probability_percent, "raw_accuracy_threshold": raw_threshold,
    }


def _hit_branch(probability: Mapping[str, Any], consequences: Mapping[str, Any], facts: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "branch": "hit", "probability_percent": probability["probability_percent"],
        "raw_accuracy_threshold": probability["raw_accuracy_threshold"],
        "consequences": deepcopy(dict(consequences)), "branch_facts": deepcopy(dict(facts)),
    }


def _miss_branch(probability: Mapping[str, Any], candidate: Mapping[str, Any], baseline: Mapping[str, int]) -> dict[str, Any]:
    facts = _fact(
        candidate, own_fainted=False, opponent_fainted=False, exact_own_hp=baseline["attacker_current_hp"],
        possible_ko=False, evidence="accuracy_miss_branch",
    )
    return {
        "branch": "miss", "probability_percent": 100 - probability["probability_percent"],
        "raw_accuracy_threshold": probability["raw_accuracy_threshold"],
        "consequences": {
            "target_damage": 0, "hit_triggered_post_hit": None,
            "hit_triggered_stage_effects": None, "attacker_hp_after": baseline["attacker_current_hp"],
            "target_hp_after": baseline.get("target_current_hp"),
        },
        "branch_facts": facts,
    }


def _intersection(*, candidate: Mapping[str, Any], branches: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    facts = [branch["branch_facts"] for branch in branches]
    own = _common_bool(facts, "guaranteed_own_fainted")
    foe = _common_bool(facts, "guaranteed_opponent_fainted")
    hp_values = [fact.get("exact_own_hp") for fact in facts]
    exact_hp = hp_values[0] if hp_values and hp_values[0] is not None and all(value == hp_values[0] for value in hp_values) else None
    possible = any(bool(fact.get("possible_opponent_ko")) or fact.get("guaranteed_opponent_fainted") is True for fact in facts)
    return _fact(candidate, own_fainted=own, opponent_fainted=foe, exact_own_hp=exact_hp, possible_ko=possible, evidence="hit_miss_branch_intersection")


def _common_bool(facts: list[Mapping[str, Any]], key: str) -> bool | None:
    values = [fact.get(key) for fact in facts]
    return values[0] if values and values[0] in {True, False} and all(value == values[0] for value in values) else None


def _fact(candidate: Mapping[str, Any], *, own_fainted: bool | None, opponent_fainted: bool | None, exact_own_hp: int | None, possible_ko: bool, evidence: str) -> dict[str, Any]:
    return {
        "status": "resolved", "schema_version": _FACT_SCHEMA,
        "candidate_id": candidate["candidate_id"], "action_type": candidate["action_type"],
        "session_id": candidate["session_id"], "source_branch_fingerprint": candidate["source_branch_fingerprint"],
        "decision_owner": deepcopy(dict(candidate["decision_owner"])), "horizon": HORIZON,
        "evidence_class": evidence, "guaranteed_own_fainted": own_fainted,
        "guaranteed_opponent_fainted": opponent_fainted, "exact_own_hp": exact_own_hp,
        "possible_opponent_ko": possible_ko, "substitute_facts": {},
        "provenance": "detached_predictive_hit_miss_branch_intersection_v1",
    }


def _facts(value: Any, candidate: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and value.get("status") == "resolved" and value.get("schema_version") == _FACT_SCHEMA and all(
        value.get(key) == candidate.get(key) for key in ("candidate_id", "action_type", "session_id", "source_branch_fingerprint", "decision_owner")
    ) and value.get("horizon") == HORIZON


def _baseline(value: Any) -> dict[str, int] | None:
    if not isinstance(value, Mapping) or not _nonnegative_int(value.get("attacker_current_hp")):
        return None
    result = {"attacker_current_hp": value["attacker_current_hp"]}
    if "target_current_hp" in value:
        if not _nonnegative_int(value["target_current_hp"]):
            return None
        result["target_current_hp"] = value["target_current_hp"]
    return result


def _candidate(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("action_type") == "attack" and isinstance(value.get("candidate_id"), str) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and isinstance(value.get("source_branch_fingerprint"), str) and bool(value["source_branch_fingerprint"]) and _owner(value.get("decision_owner"))


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("side") in {"self", "opponent"} and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _percent(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 100


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _reason(value: Mapping[str, Any], fallback: str) -> str:
    return value.get("reason") if isinstance(value.get("reason"), str) and value["reason"] else fallback


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA, "reason": reason}
