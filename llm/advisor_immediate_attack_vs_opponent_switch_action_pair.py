"""Detached switch-first immediate pair: one own attack versus one opponent switch."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_detached_opponent_switch_in_intermediate_authority import (
    materialize_detached_opponent_switch_in_intermediate_authority,
)
from llm.advisor_immediate_move_vs_move_action_pair import _normal_formula_ledger
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_strategy_d0,
    resolve_runtime_d0_selectable_move_metadata_authority,
    runtime_strategy_d0_freshness,
)


SCHEMA_VERSION = "immediate-attack-vs-opponent-switch-action-pair-v1"
HORIZON = "immediate_action_pair"


def materialize_immediate_attack_vs_opponent_switch_action_pair(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    own_action: Mapping[str, Any], switch_response_authority: Mapping[str, Any],
    selected_switch_response_action_id: str,
) -> dict[str, Any]:
    """Resolve a deterministic selected switch, then existing own attack leaves."""
    base = _base(strategy_d0, own_action, selected_switch_response_action_id)
    if base is None:
        return _result("rejected", "invalid_attack_vs_switch_pair_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    metadata = resolve_runtime_d0_selectable_move_metadata_authority(strategy_d0=strategy_d0, action=own_action)
    if metadata.get("status") != "resolved":
        return _result(_status(metadata), metadata.get("reason", "own_move_metadata_unavailable"), base)
    switch_in = materialize_detached_opponent_switch_in_intermediate_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        switch_response_authority=switch_response_authority,
        selected_response_action_id=selected_switch_response_action_id,
    )
    if switch_in.get("status") != "resolved":
        return _result(_status(switch_in), switch_in.get("reason", "switch_in_authority_unavailable"), base, switch_in_authority=deepcopy(switch_in))
    predictive = _switch_first_predictive_view(strategy_d0, runtime_snapshot, switch_in)
    if predictive.get("status") != "resolved":
        return _result(_status(predictive), predictive.get("reason", "switch_first_predictive_view_unavailable"), base)
    attack = _normal_formula_ledger(
        strategy_d0=predictive["strategy_d0"], runtime_snapshot=predictive["runtime_snapshot"],
        actor=predictive["own_actor"], target=predictive["incoming_target"],
        metadata_authority=metadata["metadata"],
    )
    if attack.get("status") != "evaluable":
        return _result(_status(attack), attack.get("reason", "own_attack_ledger_unavailable"), base, switch_in_authority=deepcopy(switch_in))
    branches = tuple(_branch(base, switch_in, leaf) for leaf in attack["terminal_leaves"])
    mass = sum((_fraction(row["probability"]) for row in branches), Fraction())
    if mass != Fraction(1, 1):
        return _result("rejected", "pair_terminal_probability_mass_not_one", base, terminal_probability_mass=_fd(mass))
    return {
        "status": "evaluable", "schema_version": SCHEMA_VERSION, "horizon": HORIZON,
        **base, "action_order": "opponent_switch_first",
        "conditional_on": "opponent_selected_exact_selectable_switch_response",
        "switch_in_authority": deepcopy(switch_in), "terminal_branches": branches,
        "terminal_probability_mass": _fd(mass),
        "aggregation": "none_preserve_switch_and_attack_leaf_identity",
        "provenance": "strict_detached_immediate_attack_vs_opponent_switch_pair_v1",
    }


def _switch_first_predictive_view(strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], switch_in: Mapping[str, Any]) -> dict:
    hypothetical = switch_in.get("hypothetical_switch_in_state") if isinstance(switch_in, Mapping) else None
    incoming = switch_in.get("target_owner") if isinstance(switch_in, Mapping) else None
    if not isinstance(hypothetical, Mapping) or not isinstance(incoming, Mapping) or hypothetical.get("active_owner") != incoming:
        return _result("rejected", "switch_in_hypothetical_target_mismatch", {})
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    synthetic = deepcopy(dict(state)) if isinstance(state, Mapping) else None
    side = synthetic.get("opponent_side") if isinstance(synthetic, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    target = roster.get(incoming.get("slot_index")) if isinstance(roster, Mapping) else None
    hp = hypothetical.get("hp_authority")
    if not isinstance(target, dict) or target.get("pokemon_id") != incoming.get("pokemon_id") or not isinstance(hp, Mapping) or hp.get("status") != "known" or not isinstance(hp.get("current_hp"), int) or not isinstance(hp.get("maximum_hp"), int):
        return _result("rejected", "switch_in_hypothetical_state_invalid", {})
    side["active_slot_index"] = incoming["slot_index"]
    target["current_hp"], target["max_hp"], target["fainted"] = hp["current_hp"], hp["maximum_hp"], False
    snapshot = {"status": "runtime_snapshot_ready", "session_id": strategy_d0["session_id"], "state": synthetic, "state_fingerprint": state_fingerprint(synthetic)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=strategy_d0["decision_owner"])
    if d0.get("status") != "resolved":
        return _result("incomplete", d0.get("reason", "switch_first_predictive_d0_unavailable"), {})
    return {"status": "resolved", "strategy_d0": d0, "runtime_snapshot": snapshot,
            "own_actor": deepcopy(d0["active_owners"]["self"]), "incoming_target": deepcopy(d0["active_owners"]["opponent"])}


def _base(d0: Any, own: Any, switch_id: Any) -> dict | None:
    own_actor = d0.get("active_owners", {}).get("self") if isinstance(d0, Mapping) else None
    opponent = d0.get("active_owners", {}).get("opponent") if isinstance(d0, Mapping) else None
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or d0.get("decision_owner") != own_actor or not isinstance(own, Mapping) or own.get("action_type") != "attack" or not isinstance(own.get("action_id"), str) or not isinstance(switch_id, str) or not isinstance(own_actor, Mapping) or not isinstance(opponent, Mapping):
        return None
    return {"pair_id": f"pair:{own['action_id']}:{switch_id}", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "own_action_id": own["action_id"], "opponent_switch_response_action_id": switch_id, "own_actor": deepcopy(dict(own_actor)), "replaced_opponent_actor": deepcopy(dict(opponent))}


def _branch(base: Mapping[str, Any], switch_in: Mapping[str, Any], attack_leaf: Mapping[str, Any]) -> dict:
    probability = _fraction(attack_leaf["probability"])
    consequence = attack_leaf.get("consequences") if isinstance(attack_leaf, Mapping) else {}
    return {"pair_leaf_id": f"switch:{base['opponent_switch_response_action_id']}/{attack_leaf['leaf_id']}", "action_order": "opponent_switch_first", "switch_response_action_id": base["opponent_switch_response_action_id"], "incoming_target": deepcopy(switch_in["target_owner"]), "switch_in_state_id": f"opponent-switch-in:{base['opponent_switch_response_action_id']}", "entry_consequence": deepcopy(switch_in["hypothetical_switch_in_state"]["entry_consequence"]), "attack_leaf": deepcopy(dict(attack_leaf)), "probability": _fd(probability), "final_own_hp": consequence.get("own_final_hp"), "final_opponent_hp": consequence.get("target_final_hp"), "own_fainted": consequence.get("self_fainted"), "opponent_fainted": consequence.get("target_ko"), "provenance": deepcopy(dict(base))}


def _fraction(value: Mapping[str, Any]) -> Fraction: return Fraction(value["numerator"], value["denominator"])
def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _status(value: Any) -> str: return value.get("status") if isinstance(value, Mapping) and value.get("status") in {"incomplete", "unsupported", "rejected"} else "rejected"
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
