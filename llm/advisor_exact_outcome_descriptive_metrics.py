"""Pure, exact descriptive summaries of one evaluable outcome ledger.

The projection owns aggregation only.  It has no utility, comparison, or
ranking semantics and leaves the supplied terminal ledger untouched.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping


SCHEMA_VERSION = "exact-outcome-descriptive-metrics-v1"
LEDGER_SCHEMA_VERSION = "exact-predictive-outcome-ledger-v1"
HORIZON = "immediate_action_consequence"


def project_exact_outcome_descriptive_metrics(*, ledger: Mapping[str, Any]) -> dict[str, Any]:
    """Project objective distributions from a complete ledger, or fail closed."""
    unavailable = _unavailable(ledger)
    if unavailable is not None:
        return unavailable
    leaves = ledger["terminal_leaves"]
    bindings = ledger["bindings"]
    if not _leaves_match(leaves, ledger, bindings):
        return _result("rejected", "terminal_leaf_binding_or_probability_invalid", bindings)
    mass = sum((_fraction(leaf["probability"]) for leaf in leaves), Fraction(0, 1))
    if mass != Fraction(1, 1) or _fraction(ledger["terminal_probability_mass"]) != mass:
        return _result("rejected", "ledger_probability_mass_mismatch", bindings)

    target = _target_metrics(leaves)
    own = _own_metrics(leaves)
    stages, conditions = _secondary_metrics(leaves)
    guaranteed, possible = _facts(leaves, target, own, stages, conditions)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, "horizon": HORIZON,
        "candidate_id": ledger["candidate_id"], "action_type": ledger["action_type"],
        "source_ledger_schema_version": LEDGER_SCHEMA_VERSION,
        "source_ledger_status": "evaluable", "bindings": deepcopy(dict(bindings)),
        "terminal_probability_mass": _fraction_dict(mass),
        "target": target, "own": own,
        "hypothetical_stage_outcomes": stages,
        "hypothetical_target_conditions": conditions,
        "guaranteed_facts": guaranteed, "possible_facts": possible,
        "ranking_influence": "none", "provenance": "exact_terminal_outcome_leaf_aggregation_v1",
    }


def _unavailable(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return _result("rejected", "invalid_exact_outcome_ledger")
    status = value.get("status")
    bindings = value.get("bindings") if isinstance(value.get("bindings"), Mapping) else None
    if status in {"incomplete", "unsupported", "rejected"}:
        return _result(status, value.get("reason", "exact_outcome_ledger_unavailable"), bindings)
    if status != "evaluable" or value.get("schema_version") != LEDGER_SCHEMA_VERSION or value.get("horizon") != HORIZON:
        return _result("rejected", "invalid_evaluable_exact_outcome_ledger", bindings)
    if not isinstance(value.get("candidate_id"), str) or value.get("action_type") not in {"attack", "manual_switch"} or not isinstance(value.get("terminal_leaves"), (tuple, list)) or not value["terminal_leaves"] or not isinstance(value.get("terminal_probability_mass"), Mapping) or not isinstance(bindings, Mapping):
        return _result("rejected", "evaluable_ledger_shape_invalid", bindings)
    return None


def _leaves_match(leaves: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]], ledger: Mapping[str, Any], bindings: Mapping[str, Any]) -> bool:
    identities: set[str] = set()
    for leaf in leaves:
        if not isinstance(leaf, Mapping) or not isinstance(leaf.get("leaf_id"), str) or leaf["leaf_id"] in identities:
            return False
        identities.add(leaf["leaf_id"])
        if leaf.get("candidate_id") != ledger["candidate_id"] or leaf.get("action_type") != ledger["action_type"] or leaf.get("provenance") != bindings or _fraction(leaf.get("probability")) is None or not isinstance(leaf.get("consequences"), Mapping):
            return False
    return True


def _target_metrics(leaves: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]]) -> dict[str, Any]:
    values = [_consequence(leaf).get("target_final_hp") for leaf in leaves]
    if all(value is None for value in values):
        return {"status": "not_applicable"}
    if any(not _nonnegative(value) for value in values):
        return {"status": "incomplete", "reason": "target_final_hp_not_complete"}
    distribution = _distribution(leaves, "target_final_hp")
    ko = _probability_where(leaves, lambda row: row["target_final_hp"] == 0)
    survival = _probability_where(leaves, lambda row: row["target_final_hp"] > 0)
    if ko + survival != 1:
        return {"status": "rejected", "reason": "target_ko_survival_mass_invalid"}
    return {"status": "resolved", "final_hp_distribution": distribution, "ko_probability": _fraction_dict(ko), "survival_probability": _fraction_dict(survival)}


def _own_metrics(leaves: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]]) -> dict[str, Any]:
    values = [_consequence(leaf).get("own_final_hp") for leaf in leaves]
    if all(value is None for value in values):
        return {"status": "not_applicable"}
    if any(not _nonnegative(value) for value in values):
        return {"status": "incomplete", "reason": "own_final_hp_not_complete"}
    distribution = _distribution(leaves, "own_final_hp")
    faint = _probability_where(leaves, lambda row: row["own_final_hp"] == 0)
    return {"status": "resolved", "final_hp_distribution": distribution, "self_faint_probability": _fraction_dict(faint)}


def _secondary_metrics(leaves: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    stages: dict[tuple, dict[str, Any]] = {}
    conditions: dict[str, dict[str, Any]] = {}
    for leaf in leaves:
        secondary = _consequence(leaf).get("secondary")
        if not isinstance(secondary, Mapping) or secondary.get("branch") != "effect":
            continue
        probability = _fraction(leaf["probability"])
        stage = secondary.get("hypothetical_stage_effect")
        if isinstance(stage, Mapping) and isinstance(stage.get("owner"), str) and isinstance(stage.get("stat"), str) and isinstance(stage.get("resulting_stage"), int) and not isinstance(stage.get("resulting_stage"), bool):
            key = (stage["owner"], stage["stat"], stage["resulting_stage"])
            row = stages.setdefault(key, {"owner": stage["owner"], "stat": stage["stat"], "resulting_stage": stage["resulting_stage"], "probability": Fraction(0, 1), "leaf_ids": []})
            row["probability"] += probability; row["leaf_ids"].append(leaf["leaf_id"])
        condition = secondary.get("hypothetical_target_condition")
        resulting = condition.get("resulting_condition") if isinstance(condition, Mapping) else None
        if isinstance(resulting, str) and resulting:
            row = conditions.setdefault(resulting, {"condition": resulting, "probability": Fraction(0, 1), "leaf_ids": []})
            row["probability"] += probability; row["leaf_ids"].append(leaf["leaf_id"])
    return _outcomes(stages.values()), _outcomes(conditions.values())


def _outcomes(values: Any) -> dict[str, Any]:
    rows = []
    for value in values:
        row = {key: deepcopy(item) for key, item in value.items() if key != "probability"}
        row["probability"] = _fraction_dict(value["probability"])
        row["leaf_ids"] = tuple(row["leaf_ids"])
        rows.append(row)
    return {"status": "resolved" if rows else "not_applicable", "outcomes": tuple(rows)}


def _facts(leaves: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]], target: Mapping[str, Any], own: Mapping[str, Any], stages: Mapping[str, Any], conditions: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    target_rows = [_consequence(leaf).get("target_final_hp") for leaf in leaves]
    own_rows = [_consequence(leaf).get("own_final_hp") for leaf in leaves]
    guaranteed = {
        "target_ko": target.get("status") == "resolved" and all(value == 0 for value in target_rows),
        "target_survival": target.get("status") == "resolved" and all(value > 0 for value in target_rows),
        "self_faint": own.get("status") == "resolved" and all(value == 0 for value in own_rows),
        "self_survival": own.get("status") == "resolved" and all(value > 0 for value in own_rows),
        "exact_own_final_hp": own_rows[0] if own.get("status") == "resolved" and all(value == own_rows[0] for value in own_rows) else None,
        "hypothetical_stage_outcomes": () if stages.get("status") != "resolved" else tuple(row for row in stages["outcomes"] if row["probability"] == {"numerator": 1, "denominator": 1}),
        "hypothetical_target_conditions": () if conditions.get("status") != "resolved" else tuple(row for row in conditions["outcomes"] if row["probability"] == {"numerator": 1, "denominator": 1}),
    }
    possible = {
        "target_ko_leaf_ids": tuple(leaf["leaf_id"] for leaf in leaves if _consequence(leaf).get("target_final_hp") == 0),
        "self_faint_leaf_ids": tuple(leaf["leaf_id"] for leaf in leaves if _consequence(leaf).get("own_final_hp") == 0),
        "hypothetical_stage_outcomes": () if stages.get("status") != "resolved" else deepcopy(stages["outcomes"]),
        "hypothetical_target_conditions": () if conditions.get("status") != "resolved" else deepcopy(conditions["outcomes"]),
    }
    return guaranteed, possible


def _distribution(leaves: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[int, dict[str, Any]] = {}
    for leaf in leaves:
        hp = _consequence(leaf)[key]; probability = _fraction(leaf["probability"])
        row = groups.setdefault(hp, {"final_hp": hp, "probability": Fraction(0, 1), "leaf_ids": []})
        row["probability"] += probability; row["leaf_ids"].append(leaf["leaf_id"])
    rows = []
    for hp in sorted(groups):
        row = groups[hp]
        rows.append({"final_hp": hp, "probability": _fraction_dict(row["probability"]), "leaf_ids": tuple(row["leaf_ids"])})
    return {"outcomes": tuple(rows), "probability_mass": _fraction_dict(sum((group["probability"] for group in groups.values()), Fraction(0, 1)))}


def _probability_where(leaves: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]], predicate: Any) -> Fraction:
    return sum((_fraction(leaf["probability"]) for leaf in leaves if predicate(_consequence(leaf))), Fraction(0, 1))


def _consequence(leaf: Mapping[str, Any]) -> Mapping[str, Any]:
    return leaf["consequences"]


def _fraction(value: Any) -> Fraction | None:
    if not isinstance(value, Mapping) or not isinstance(value.get("numerator"), int) or isinstance(value.get("numerator"), bool) or not isinstance(value.get("denominator"), int) or isinstance(value.get("denominator"), bool) or value["numerator"] < 0 or value["denominator"] <= 0:
        return None
    return Fraction(value["numerator"], value["denominator"])


def _fraction_dict(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _nonnegative(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _result(status: str, reason: str, bindings: Mapping[str, Any] | None = None) -> dict[str, Any]:
    result = {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
    if isinstance(bindings, Mapping):
        result["bindings"] = deepcopy(dict(bindings))
    return result
