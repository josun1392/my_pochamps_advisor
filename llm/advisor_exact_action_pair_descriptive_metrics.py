"""Objective exact summaries of one immediate action-pair outcome ledger."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping


SCHEMA_VERSION = "exact-immediate-action-pair-descriptive-metrics-v1"
LEDGER_SCHEMA = "exact-immediate-action-pair-outcome-ledger-v1"
HORIZON = "immediate_action_pair"
_STATUSES = {"incomplete", "unsupported", "rejected"}


def project_exact_immediate_action_pair_descriptive_metrics(*, ledger: Mapping[str, Any]) -> dict[str, Any]:
    """Aggregate exact pair leaves only; this owner has no policy semantics."""
    unavailable = _unavailable(ledger)
    if unavailable is not None: return unavailable
    base = _base(ledger)
    leaves = ledger["terminal_leaves"]
    parsed = [_leaf(leaf, base) for leaf in leaves]
    if any(isinstance(row, str) for row in parsed): return _result("rejected", next(row for row in parsed if isinstance(row, str)), base)
    rows = tuple(parsed)
    mass = sum((row["probability"] for row in rows), Fraction())
    if mass != Fraction(1, 1) or _fraction(ledger["terminal_probability_mass"]) != mass: return _result("rejected", "pair_ledger_probability_mass_mismatch", base)
    own = _side(rows, "own_final_hp")
    opponent = _side(rows, "opponent_final_hp")
    joint = _joint(rows)
    stages, conditions = _supported_outcomes(rows)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, "horizon": HORIZON, **base,
            "source_ledger_schema_version": LEDGER_SCHEMA, "source_ledger_status": "evaluable",
            "terminal_probability_mass": _fd(mass), "own": own, "opponent": opponent,
            "joint_terminal_states": joint, "supported_final_stage_outcomes": stages,
            "supported_final_condition_outcomes": conditions, "ranking_influence": "none",
            "provenance": "exact_immediate_action_pair_leaf_descriptive_aggregation_v1"}


def _unavailable(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping): return _result("rejected", "invalid_exact_immediate_action_pair_ledger")
    if value.get("status") != "evaluable": return _result(_status(value), value.get("reason", "exact_immediate_action_pair_ledger_unavailable"), _base(value))
    if value.get("schema_version") != LEDGER_SCHEMA or value.get("horizon") != HORIZON or _base(value) is None or not isinstance(value.get("terminal_leaves"), (tuple, list)) or not value["terminal_leaves"]: return _result("rejected", "invalid_evaluable_exact_immediate_action_pair_ledger", _base(value))
    return None


def _base(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping): return None
    keys = ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_action_id", "opponent_action_id", "own_actor", "opponent_actor")
    strings = ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "own_action_id", "opponent_action_id")
    if not all(key in value for key in keys) or not all(isinstance(value.get(key), str) and value[key] for key in strings) or not all(isinstance(value.get(key), Mapping) for key in ("decision_owner", "own_actor", "opponent_actor")): return None
    base = {key: deepcopy(value[key]) for key in keys}
    for key in ("opponent_switch_response_action_id", "replaced_opponent_actor", "response_action_type"):
        if key in value:
            base[key] = deepcopy(value[key])
    return base


def _leaf(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or not isinstance(value.get("pair_leaf_id"), str) or not isinstance(value.get("final_consequences"), Mapping): return "pair_metric_leaf_invalid"
    probability = _fraction(value.get("probability")); final = value["final_consequences"]
    if probability <= 0 or not _hp(final.get("own_final_hp")) or not _hp(final.get("opponent_final_hp")) or final.get("own_fainted") is not (final["own_final_hp"] == 0) or final.get("opponent_fainted") is not (final["opponent_final_hp"] == 0): return "pair_metric_leaf_consequence_invalid"
    return {"pair_leaf_id": value["pair_leaf_id"], "probability": probability, "final": final}


def _side(rows: tuple[Mapping[str, Any], ...], key: str) -> dict[str, Any]:
    groups: dict[int, dict[str, Any]] = {}
    for row in rows:
        hp = row["final"][key]; group = groups.setdefault(hp, {"final_hp": hp, "probability": Fraction(), "pair_leaf_ids": []})
        group["probability"] += row["probability"]; group["pair_leaf_ids"].append(row["pair_leaf_id"])
    distribution = tuple({"final_hp": group["final_hp"], "probability": _fd(group["probability"]), "pair_leaf_ids": tuple(group["pair_leaf_ids"])} for _, group in sorted(groups.items()))
    ko = sum((row["probability"] for row in rows if row["final"][key] == 0), Fraction())
    survive = sum((row["probability"] for row in rows if row["final"][key] > 0), Fraction())
    return {"status": "resolved", "final_hp_distribution": {"outcomes": distribution, "probability_mass": _fd(ko + survive)}, "ko_probability": _fd(ko), "survival_probability": _fd(survive)}


def _joint(rows: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    labels = (("both_survive", lambda own, opp: own > 0 and opp > 0), ("own_survives_opponent_faints", lambda own, opp: own > 0 and opp == 0), ("own_faints_opponent_survives", lambda own, opp: own == 0 and opp > 0), ("both_faint", lambda own, opp: own == 0 and opp == 0))
    outcomes = []
    for name, predicate in labels:
        selected = [row for row in rows if predicate(row["final"]["own_final_hp"], row["final"]["opponent_final_hp"])]
        probability = sum((row["probability"] for row in selected), Fraction())
        outcomes.append({"state": name, "probability": _fd(probability), "pair_leaf_ids": tuple(row["pair_leaf_id"] for row in selected)})
    return {"status": "resolved", "outcomes": tuple(outcomes), "probability_mass": _fd(sum((_fraction(row["probability"]) for row in outcomes), Fraction()))}


def _supported_outcomes(rows: tuple[Mapping[str, Any], ...]) -> tuple[dict[str, Any], dict[str, Any]]:
    stages: dict[str, dict[str, Any]] = {}; conditions: dict[str, dict[str, Any]] = {}
    for row in rows:
        final = row["final"]
        for key, groups in (("supported_stage_consequence", stages), ("supported_secondary_consequence", conditions)):
            value = final.get(key)
            if not isinstance(value, Mapping): continue
            identity = repr(value)
            group = groups.setdefault(identity, {"outcome": deepcopy(dict(value)), "probability": Fraction(), "pair_leaf_ids": []})
            group["probability"] += row["probability"]; group["pair_leaf_ids"].append(row["pair_leaf_id"])
    return _outcomes(stages), _outcomes(conditions)


def _outcomes(groups: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    if not groups: return {"status": "not_applicable", "outcomes": ()}
    return {"status": "resolved", "outcomes": tuple({"outcome": deepcopy(group["outcome"]), "probability": _fd(group["probability"]), "pair_leaf_ids": tuple(group["pair_leaf_ids"])} for group in groups.values())}


def _fraction(value: Any) -> Fraction:
    if not isinstance(value, Mapping) or not isinstance(value.get("numerator"), int) or not isinstance(value.get("denominator"), int) or value["numerator"] < 0 or value["denominator"] <= 0: return Fraction(-1, 1)
    return Fraction(value["numerator"], value["denominator"])
def _hp(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool) and value >= 0
def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _status(value: Mapping[str, Any]) -> str: return value.get("status") if value.get("status") in _STATUSES else "rejected"
def _result(status: str, reason: str, base: Mapping[str, Any] | None = None) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **(deepcopy(dict(base)) if isinstance(base, Mapping) else {}), "reason": reason}
