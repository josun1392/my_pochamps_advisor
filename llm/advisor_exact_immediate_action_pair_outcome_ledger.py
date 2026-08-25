"""Strict exact normalization for completed immediate action-pair branches."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping


SCHEMA_VERSION = "exact-immediate-action-pair-outcome-ledger-v1"
PAIR_SCHEMAS = {"immediate-move-vs-move-action-pair-v1", "immediate-attack-vs-opponent-switch-action-pair-v1"}
HORIZON = "immediate_action_pair"
_STATUSES = {"incomplete", "unsupported", "rejected"}


def normalize_exact_immediate_action_pair_outcome_ledger(*, pair: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and copy an evaluable pair without recomputing mechanics."""
    if not isinstance(pair, Mapping): return _result("rejected", "invalid_immediate_action_pair")
    if pair.get("status") != "evaluable":
        return _result(_status(pair), pair.get("reason", "immediate_action_pair_not_evaluable"), _base(pair))
    base = _base(pair)
    if base is None or pair.get("schema_version") not in PAIR_SCHEMAS or pair.get("horizon") != HORIZON:
        return _result("rejected", "immediate_action_pair_binding_or_schema_invalid")
    branches = pair.get("terminal_branches")
    if not isinstance(branches, (tuple, list)) or not branches: return _result("rejected", "pair_terminal_branches_missing", base)
    parsed: list[dict[str, Any]] = []
    identities: set[str] = set()
    for branch in branches:
        leaf = _switch_leaf(branch, base) if pair.get("schema_version") == "immediate-attack-vs-opponent-switch-action-pair-v1" else _leaf(branch, base)
        if isinstance(leaf, str): return _result("rejected", leaf, base)
        if leaf["pair_leaf_id"] in identities: return _result("rejected", "duplicate_pair_terminal_leaf_id", base)
        identities.add(leaf["pair_leaf_id"]); parsed.append(leaf)
    mass = sum((_fraction(leaf["probability"]) for leaf in parsed), Fraction())
    if mass != Fraction(1, 1): return _result("rejected", "pair_root_probability_mass_not_one", base, terminal_probability_mass=_fd(mass))
    declared = _fraction(pair.get("terminal_probability_mass"))
    if declared != mass: return _result("rejected", "pair_declared_terminal_mass_mismatch", base, terminal_probability_mass=_fd(mass))
    return {"status": "evaluable", "schema_version": SCHEMA_VERSION, "horizon": HORIZON, **base,
            "conditional_on": deepcopy(pair.get("conditional_on")),
            "terminal_leaves": tuple(parsed), "terminal_probability_mass": _fd(mass),
            "aggregation": "none_preserve_pair_branch_and_roll_identity",
            "provenance": "strict_detached_immediate_action_pair_outcome_normalization_v1"}


def _base(pair: Mapping[str, Any]) -> dict[str, Any] | None:
    if pair.get("schema_version") == "immediate-attack-vs-opponent-switch-action-pair-v1":
        required = ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_action_id", "opponent_switch_response_action_id", "own_actor", "replaced_opponent_actor")
        strings = ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "own_action_id", "opponent_switch_response_action_id")
        switch = pair.get("switch_in_authority")
        incoming = switch.get("target_owner") if isinstance(switch, Mapping) else None
        if not all(key in pair for key in required) or not all(isinstance(pair.get(key), str) and pair[key] for key in strings) or not all(isinstance(pair.get(key), Mapping) for key in ("decision_owner", "own_actor", "replaced_opponent_actor")) or not isinstance(incoming, Mapping): return None
        return {**{key: deepcopy(pair[key]) for key in required}, "opponent_action_id": pair["opponent_switch_response_action_id"], "opponent_actor": deepcopy(dict(incoming)), "response_action_type": "manual_switch"}
    required = ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_action_id", "opponent_action_id", "own_actor", "opponent_actor")
    strings = ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "own_action_id", "opponent_action_id")
    if not all(key in pair for key in required) or not all(isinstance(pair.get(key), str) and pair[key] for key in strings): return None
    if not isinstance(pair.get("decision_owner"), Mapping) or not isinstance(pair.get("own_actor"), Mapping) or not isinstance(pair.get("opponent_actor"), Mapping): return None
    return {key: deepcopy(pair[key]) for key in required}


def _switch_leaf(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or not isinstance(value.get("pair_leaf_id"), str) or value.get("action_order") != "opponent_switch_first": return "invalid_switch_pair_terminal_branch"
    source_base = {key: deepcopy(value) for key, value in base.items() if key not in {"opponent_action_id", "opponent_actor", "response_action_type"}}
    if value.get("provenance") != source_base: return "switch_pair_terminal_branch_provenance_mismatch"
    attack = value.get("attack_leaf")
    probability = _fraction(value.get("probability"))
    if not isinstance(attack, Mapping) or not isinstance(attack.get("leaf_id"), str) or _fraction(attack.get("probability")) <= 0 or probability != _fraction(attack["probability"]): return "switch_pair_attack_leaf_invalid"
    final = _final(attack, base)
    if isinstance(final, str): return final
    incoming = value.get("incoming_target")
    if incoming != base["opponent_actor"]: return "switch_pair_incoming_target_identity_mismatch"
    return {"pair_leaf_id": value["pair_leaf_id"], "action_order": value["action_order"], "probability": _fd(probability),
            "switch_response": {"action_id": base["opponent_action_id"], "incoming_target": deepcopy(dict(incoming)), "switch_in_state_id": value.get("switch_in_state_id"), "entry_consequence": deepcopy(value.get("entry_consequence"))},
            "attack_action": _action_leaf(attack), "final_consequences": final, "source_pair_branch": deepcopy(dict(value))}


def _leaf(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or not isinstance(value.get("pair_leaf_id"), str) or value.get("action_order") not in {"own_first", "opponent_first"}: return "invalid_pair_terminal_branch"
    if value.get("provenance") != dict(base): return "pair_terminal_branch_provenance_mismatch"
    first, second = value.get("first_action_leaf"), value.get("second_action")
    if not isinstance(first, Mapping) or not isinstance(first.get("leaf_id"), str) or _fraction(first.get("probability")) <= 0: return "first_action_leaf_invalid"
    if not isinstance(second, Mapping) or second.get("state") not in {"executed", "cancelled_due_to_faint"}: return "second_action_branch_invalid"
    conditional = _fraction(second.get("conditional_probability"))
    if conditional <= 0: return "second_action_probability_invalid"
    second_leaf = second.get("leaf")
    if second["state"] == "executed":
        if not isinstance(second_leaf, Mapping) or not isinstance(second_leaf.get("leaf_id"), str) or _fraction(second_leaf.get("probability")) != conditional: return "executed_second_action_leaf_invalid"
    elif second_leaf is not None or conditional != Fraction(1, 1) or second.get("reason") != "second_action_cancelled_due_to_faint": return "cancelled_second_action_branch_invalid"
    probability = _fraction(value.get("probability"))
    if probability != _fraction(first["probability"]) * conditional: return "pair_leaf_probability_composition_invalid"
    final_source = second_leaf if isinstance(second_leaf, Mapping) else first
    final = _final(final_source, base)
    if isinstance(final, str): return final
    return {"pair_leaf_id": value["pair_leaf_id"], "action_order": value["action_order"],
            "probability": _fd(probability), "first_action": _action_leaf(first),
            "second_action": {"state": second["state"], "actor": deepcopy(second.get("actor")), "conditional_probability": _fd(conditional), **({"leaf": _action_leaf(second_leaf)} if isinstance(second_leaf, Mapping) else {"reason": second["reason"]})},
            "intermediate_state_id": value.get("intermediate_state_id"), "final_consequences": final,
            "source_pair_branch": deepcopy(dict(value))}


def _action_leaf(leaf: Mapping[str, Any]) -> dict[str, Any]:
    return {"leaf_id": leaf["leaf_id"], "branch_path": deepcopy(leaf.get("branch_path")), "probability": deepcopy(leaf.get("probability")), "hit_state": leaf.get("hit_state"), "critical_state": leaf.get("critical_state"), "damage_roll": deepcopy(leaf.get("damage_roll")), "consequences": deepcopy(leaf.get("consequences")), "provenance": deepcopy(leaf.get("provenance"))}


def _final(source: Mapping[str, Any], base: Mapping[str, Any]) -> dict[str, Any] | str:
    provenance, consequences = source.get("provenance"), source.get("consequences")
    if not isinstance(provenance, Mapping) or not isinstance(consequences, Mapping): return "pair_final_consequence_missing"
    actor = provenance.get("attacker")
    if actor == base["own_actor"]:
        own_hp, opponent_hp = consequences.get("own_final_hp"), consequences.get("target_final_hp")
    elif actor == base["opponent_actor"]:
        own_hp, opponent_hp = consequences.get("target_final_hp"), consequences.get("own_final_hp")
    else: return "pair_final_actor_identity_mismatch"
    if not _hp(own_hp) or not _hp(opponent_hp): return "pair_final_hp_missing"
    return {"own_final_hp": own_hp, "opponent_final_hp": opponent_hp,
            "own_fainted": own_hp == 0, "opponent_fainted": opponent_hp == 0,
            "supported_stage_consequence": deepcopy(consequences.get("deterministic_stage_effect")),
            "supported_secondary_consequence": deepcopy(consequences.get("secondary"))}


def _hp(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool) and value >= 0
def _fraction(value: Any) -> Fraction:
    if not isinstance(value, Mapping) or not isinstance(value.get("numerator"), int) or not isinstance(value.get("denominator"), int) or value["denominator"] <= 0 or value["numerator"] <= 0: return Fraction(-1, 1)
    return Fraction(value["numerator"], value["denominator"])
def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _status(value: Mapping[str, Any]) -> str: return value.get("status") if value.get("status") in _STATUSES else "rejected"
def _result(status: str, reason: str, base: Mapping[str, Any] | None = None, **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **(deepcopy(dict(base)) if isinstance(base, Mapping) else {}), "reason": reason, **deepcopy(extra)}
