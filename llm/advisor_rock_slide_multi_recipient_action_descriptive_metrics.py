"""Exact descriptive-only metrics for a validated Rock Slide recipient graph."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_rock_slide_multi_recipient_action_outcome_ledger import SCHEMA_VERSION as LEDGER_SCHEMA, graph_terminal_rows

SCHEMA_VERSION = "exact-rock-slide-multi-recipient-action-descriptive-metrics-v1"


def project_rock_slide_multi_recipient_action_descriptive_metrics(*, ledger: Mapping[str, Any]) -> dict[str, Any]:
    rows = graph_terminal_rows(ledger=ledger)
    base = _base(ledger)
    if isinstance(rows, str): return _result("rejected", rows, base)
    if base is None: return _result("rejected", "invalid_rock_slide_multi_recipient_ledger", None)
    mass = sum((row["probability"] for row in rows), Fraction())
    if mass != Fraction(1, 1): return _result("rejected", "rock_slide_multi_recipient_metric_root_mass_invalid", base)
    recipients = tuple(_recipient(rows, index, owner) for index, owner in enumerate(base["recipients"], 1))
    joint = _joint(rows, base["recipients"])
    action = _action(rows, base["recipients"])
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "source_ledger_schema_version": LEDGER_SCHEMA, "terminal_probability_mass": _fd(mass), "recipients": recipients, "joint_terminal_states": joint, "action": action, "ranking_influence": "none", "provenance": "exact_rock_slide_multi_recipient_graph_descriptive_aggregation_v1"}


def _recipient(rows: tuple[Mapping[str, Any], ...], index: int, owner: Mapping[str, Any]) -> dict[str, Any]:
    selected = [(row, row["ordered_recipient_outcomes"][index - 1]) for row in rows]
    def probability(predicate): return sum((row["probability"] for row, outcome in selected if predicate(outcome)), Fraction())
    groups: dict[int, dict[str, Any]] = {}
    for row, outcome in selected:
        hp = outcome["post_hp"]; group = groups.setdefault(hp, {"final_hp": hp, "probability": Fraction(), "terminal_edge_ids": []}); group["probability"] += row["probability"]; group["terminal_edge_ids"].append(row["terminal_edge_id"])
    hit = probability(lambda value: value["outcome"] == "hit")
    critical = probability(lambda value: value["outcome"] == "hit" and value["critical_state"] == "critical")
    prevention = probability(lambda value: value["outcome"] == "prevented_by_wide_guard")
    mat_block = probability(lambda value: value["outcome"] == "prevented_by_mat_block")
    return {"recipient_index": index, "recipient": deepcopy(owner), "hit_probability": _fd(hit), "miss_probability": _fd(probability(lambda value: value["outcome"] == "miss")), "immunity_or_prevention_probability": _fd(probability(lambda value: value["outcome"] in {"immune", "prevented_by_wide_guard", "prevented_by_mat_block"})), "wide_guard_prevention_probability": _fd(prevention), "mat_block_prevention_probability": _fd(mat_block), "critical_probability": _fd(critical), "critical_probability_given_hit": _fd(critical / hit) if hit else None, "faint_probability": _fd(probability(lambda value: value["fainted"])), "survival_probability": _fd(probability(lambda value: not value["fainted"])), "final_hp_distribution": {"outcomes": tuple({"final_hp": value["final_hp"], "probability": _fd(value["probability"]), "terminal_edge_ids": tuple(value["terminal_edge_ids"])} for _, value in sorted(groups.items())), "probability_mass": _fd(sum((value["probability"] for value in groups.values()), Fraction()))}}


def _joint(rows: tuple[Mapping[str, Any], ...], recipients: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    groups: dict[tuple[tuple[str, int, str, int, bool], ...], dict[str, Any]] = {}
    for row in rows:
        outcomes = row["ordered_recipient_outcomes"]
        key = tuple((value["recipient"]["side"], value["recipient"]["active_slot_index"], value["recipient"]["owner"]["pokemon_id"], value["post_hp"], value["fainted"]) for value in outcomes)
        group = groups.setdefault(key, {"probability": Fraction(), "terminal_edge_ids": [], "ordered_recipients": tuple({"recipient_index": value["recipient_index"], "recipient": deepcopy(value["recipient"]), "final_hp": value["post_hp"], "fainted": value["fainted"]} for value in outcomes)})
        group["probability"] += row["probability"]; group["terminal_edge_ids"].append(row["terminal_edge_id"])
    return {"status": "resolved", "outcomes": tuple({"ordered_recipients": deepcopy(group["ordered_recipients"]), "probability": _fd(group["probability"]), "terminal_edge_ids": tuple(group["terminal_edge_ids"])} for group in groups.values()), "probability_mass": _fd(sum((group["probability"] for group in groups.values()), Fraction()))}


def _action(rows: tuple[Mapping[str, Any], ...], recipients: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    at_least = sum((row["probability"] for row in rows if any(value["fainted"] for value in row["ordered_recipient_outcomes"])), Fraction())
    all_fainted = sum((row["probability"] for row in rows if all(value["fainted"] for value in row["ordered_recipient_outcomes"])), Fraction())
    return {"no_recipient_faints_probability": _fd(Fraction(1, 1) - at_least), "at_least_one_recipient_faints_probability": _fd(at_least), "all_represented_recipients_faint_probability": _fd(all_fainted), "represented_recipient_count": len(recipients)}


def _base(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("status") != "evaluable" or value.get("schema_version") != LEDGER_SCHEMA: return None
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "action_id", "move_id", "recipients")
    return {key: deepcopy(value[key]) for key in keys} if all(key in value for key in keys) else None
def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _result(status: str, reason: str, base: Mapping[str, Any] | None): return {"status": status, "schema_version": SCHEMA_VERSION, **(deepcopy(dict(base)) if isinstance(base, Mapping) else {}), "reason": reason}
