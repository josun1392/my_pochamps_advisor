"""Descriptive-only aggregation for validated nested Rock Slide pair ledgers."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_rock_slide_multi_recipient_immediate_pair_outcome_ledger import (
    SCHEMA_VERSION as LEDGER_SCHEMA,
    iter_rock_slide_multi_recipient_immediate_pair_terminal_rows,
)


SCHEMA_VERSION = "exact-rock-slide-multi-recipient-immediate-pair-descriptive-metrics-v1"


def project_rock_slide_multi_recipient_immediate_pair_descriptive_metrics(*, ledger: Mapping[str, Any]) -> dict[str, Any]:
    rows = iter_rock_slide_multi_recipient_immediate_pair_terminal_rows(ledger=ledger)
    if isinstance(rows, str): return _result("rejected", rows, _base(ledger))
    # Dynamic traversal is deliberately consumed once: source graph paths and
    # nested ordinary-action leaves are never persisted as a flattened table.
    recipient_hp: dict[tuple[int, tuple], dict[int, Fraction]] = defaultdict(lambda: defaultdict(Fraction))
    recipient_faint: dict[tuple[int, tuple], Fraction] = defaultdict(Fraction)
    order: dict[str, Fraction] = defaultdict(Fraction)
    pending_execution: dict[str, Fraction] = defaultdict(Fraction)
    pending_hp: dict[tuple, dict[int, Fraction]] = defaultdict(lambda: defaultdict(Fraction))
    pending_faint: dict[tuple, Fraction] = defaultdict(Fraction)
    joint: dict[tuple, dict[str, Any]] = {}
    root = Fraction()
    for row in rows:
        probability = row["probability"]
        if probability <= 0 or row["second_action_state"] not in {"outcome_ledger", "rock_slide_graph", "cancelled_due_to_faint"}:
            return _result("rejected", "rock_slide_nested_pair_metric_row_invalid", _base(ledger))
        root += probability; order[row["order"]] += probability
        state = "cancelled_due_to_faint" if row["second_action_state"] == "cancelled_due_to_faint" else "executed"
        pending_execution[state] += probability
        represented: list[Mapping[str, Any]] = []
        for index, recipient in enumerate(row["ordered_recipient_states"], 1):
            owner = recipient["owner"]; key = (index, _owner_key(owner))
            recipient_hp[key][recipient["hp"]] += probability
            if recipient["fainted"]: recipient_faint[key] += probability
            represented.append(recipient)
        actor = row["rock_slide_actor_state"]; represented.append(actor)
        pending = row["pending_actor_state"]
        if not isinstance(pending, Mapping): return _result("rejected", "rock_slide_nested_pair_pending_actor_final_state_missing", _base(ledger))
        pending_key = _owner_key(row["pending_actor"]); pending_hp[pending_key][pending["hp"]] += probability
        if pending["fainted"]: pending_faint[pending_key] += probability
        if all(existing["owner"] != pending["owner"] for existing in represented): represented.append(pending)
        joint_key = tuple((item["owner"]["side"], item["owner"]["slot_index"], item["owner"]["pokemon_id"], item["hp"], item["fainted"]) for item in represented)
        group = joint.setdefault(joint_key, {"probability": Fraction(), "pair_terminal_ids": [], "represented_states": tuple(_public_state(item) for item in represented)})
        group["probability"] += probability; group["pair_terminal_ids"].append(row["pair_terminal_id"])
    if root != Fraction(1, 1): return _result("rejected", "rock_slide_nested_pair_metric_root_mass_invalid", _base(ledger))
    base = _base(ledger)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "source_ledger_schema_version": LEDGER_SCHEMA,
            "terminal_probability_mass": _fd(root), "order_branches": tuple({"order": name, "probability": _fd(probability)} for name, probability in sorted(order.items())),
            "recipients": tuple(_recipient(index, owner, recipient_hp[(index, owner)], recipient_faint[(index, owner)]) for index, owner in sorted({key for key in recipient_hp})),
            "pending_second_action": {"execution_probability": _fd(pending_execution["executed"]), "cancelled_due_to_faint_probability": _fd(pending_execution["cancelled_due_to_faint"]), "final_states": tuple(_state_distribution(owner, values, pending_faint[owner]) for owner, values in pending_hp.items())},
            "pair": _pair_metrics(joint), "joint_final_states": {"status": "resolved", "outcomes": tuple({"represented_states": deepcopy(group["represented_states"]), "probability": _fd(group["probability"]), "pair_terminal_ids": tuple(group["pair_terminal_ids"])} for group in joint.values()), "probability_mass": _fd(root)},
            "ranking_influence": "none", "provenance": "exact_nested_rock_slide_pair_descriptive_dynamic_aggregation_v1"}


def _recipient(index: int, owner: tuple, hp: Mapping[int, Fraction], faint: Fraction) -> dict[str, Any]:
    return {"recipient_index": index, "owner_identity": _owner_public(owner), "faint_probability": _fd(faint), "survival_probability": _fd(Fraction(1, 1) - faint), "final_hp_distribution": {"outcomes": tuple({"final_hp": value, "probability": _fd(probability)} for value, probability in sorted(hp.items())), "probability_mass": _fd(sum(hp.values(), Fraction()))}}
def _state_distribution(owner: tuple, hp: Mapping[int, Fraction], faint: Fraction) -> dict[str, Any]:
    return {"owner_identity": _owner_public(owner), "faint_probability": _fd(faint), "final_hp_distribution": {"outcomes": tuple({"final_hp": value, "probability": _fd(probability)} for value, probability in sorted(hp.items())), "probability_mass": _fd(sum(hp.values(), Fraction()))}}
def _pair_metrics(joint: Mapping[tuple, Mapping[str, Any]]) -> dict[str, Any]:
    at_least = sum((group["probability"] for key, group in joint.items() if any(state[-1] for state in key)), Fraction())
    return {"no_represented_pokemon_faints_probability": _fd(Fraction(1, 1) - at_least), "at_least_one_represented_pokemon_faints_probability": _fd(at_least)}
def _owner_key(value: Mapping[str, Any]) -> tuple: return (value["session_id"], value["side"], value["slot_index"], value["pokemon_id"])
def _owner_public(value: tuple) -> dict[str, Any]: return {"session_id": value[0], "side": value[1], "slot_index": value[2], "pokemon_id": value[3]}
def _public_state(value: Mapping[str, Any]) -> dict[str, Any]: return {"owner": deepcopy(dict(value["owner"])), "final_hp": value["hp"], "fainted": value["fainted"]}
def _base(value: Any) -> dict[str, Any]:
    keys = ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_action_id", "opponent_action_id", "own_actor", "opponent_actor")
    return {key: deepcopy(value[key]) for key in keys} if isinstance(value, Mapping) and value.get("status") == "evaluable" and value.get("schema_version") == LEDGER_SCHEMA and all(key in value for key in keys) else {}
def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
