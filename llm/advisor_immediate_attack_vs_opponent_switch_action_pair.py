"""Detached switch-first immediate pair: one own attack versus one opponent switch."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_detached_opponent_switch_in_intermediate_authority import (
    materialize_detached_opponent_switch_in_intermediate_authority,
)
from llm.advisor_detached_switch_first_hypothetical_condition_predictive_consumer import (
    materialize_detached_switch_first_hypothetical_condition_predictive_view,
)
from llm.advisor_immediate_move_vs_move_action_pair import _attack_ledger
from llm.advisor_runtime_strategy_d0 import (
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
    attack = _attack_ledger(
        strategy_d0=predictive["strategy_d0"], runtime_snapshot=predictive["runtime_snapshot"],
        actor=predictive["own_actor"], target=predictive["incoming_target"],
        metadata_authority=metadata["metadata"],
        sturdy_survival_authority=switch_in["hypothetical_switch_in_state"].get("sturdy_survival_authority"),
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
        "switch_first_condition_consumer": deepcopy(predictive["condition_consumer"]),
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
    stages = hypothetical.get("stage_authority")
    stage_values = stages.get("value") if isinstance(stages, Mapping) and stages.get("status") == "known" else None
    if not isinstance(stage_values, Mapping) or any(not isinstance(stage_values.get(stat), int) or isinstance(stage_values.get(stat), bool) or not -6 <= stage_values[stat] <= 6 for stat in ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")):
        return _result("incomplete", "switch_in_hypothetical_stage_authority_unknown", {})
    target["stat_stages"] = deepcopy(dict(stage_values))
    target["detached_switch_first_hypothetical_stage_authority"] = True
    trace = hypothetical.get("trace_ability_overlay")
    if isinstance(trace, Mapping) and trace.get("status") == "known":
        if trace.get("owner") != incoming or trace.get("before") != "trace" or not isinstance(trace.get("after"), str) or not trace["after"] or target.get("current_ability") != "trace":
            return _result("rejected", "switch_in_trace_overlay_binding_mismatch", {})
        target["current_ability"] = trace["after"]
        target["current_ability_provenance"] = {
            "event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1,
            "hypothetical_provenance": "exact_detached_switch_entry_trace",
        }
        target["detached_switch_first_hypothetical_trace_authority"] = True
    elif isinstance(trace, Mapping) and trace.get("status") not in {"not_applicable"}:
        return _result("incomplete", "switch_in_trace_overlay_unknown", {})
    overlay = hypothetical.get("own_attack_stage_overlay")
    if isinstance(overlay, Mapping) and overlay.get("status") == "known":
        own_side = synthetic.get("self_side") if isinstance(synthetic, Mapping) else None
        own_roster = own_side.get("pokemon") if isinstance(own_side, Mapping) else None
        own_owner = overlay.get("owner")
        own_target = own_roster.get(own_owner.get("slot_index")) if isinstance(own_owner, Mapping) and isinstance(own_roster, Mapping) else None
        after = overlay.get("after")
        if own_owner != strategy_d0.get("active_owners", {}).get("self") or not isinstance(own_target, dict) or own_target.get("pokemon_id") != own_owner.get("pokemon_id") or not isinstance(after, int) or isinstance(after, bool) or not -6 <= after <= 6:
            return _result("rejected", "switch_in_intimidate_overlay_binding_mismatch", {})
        own_stages = own_target.get("stat_stages")
        if not isinstance(own_stages, Mapping) or not isinstance(own_stages.get("attack"), int) or isinstance(own_stages.get("attack"), bool) or own_stages["attack"] != overlay.get("before"):
            return _result("rejected", "switch_in_intimidate_pre_entry_stage_mismatch", {})
        own_target["stat_stages"] = {**deepcopy(dict(own_stages)), "attack": after}
        own_target["detached_switch_first_hypothetical_intimidate_authority"] = True
    elif isinstance(overlay, Mapping) and overlay.get("status") not in {"not_applicable"}:
        return _result("incomplete", "switch_in_intimidate_overlay_unknown", {})
    weather = hypothetical.get("weather_authority")
    if isinstance(weather, Mapping) and weather.get("status") == "known":
        field = synthetic.get("field") if isinstance(synthetic, Mapping) else None
        before, after = weather.get("before"), weather.get("after")
        if not isinstance(field, dict) or field.get("weather") != before or after not in {"rain", "sun", "sandstorm", "snow"}:
            return _result("rejected", "switch_in_weather_overlay_binding_mismatch", {})
        field["weather"] = after
        field["weather_provenance"] = {
            "event_kind": "current_weather_observed", "trust": "user_confirmed_observation",
            "turn_number": 1,
            "hypothetical_provenance": "exact_detached_switch_entry_weather",
        }
        field["detached_switch_first_hypothetical_weather_authority"] = True
    elif isinstance(weather, Mapping) and weather.get("status") not in {"not_applicable"}:
        return _result("incomplete", "switch_in_weather_overlay_unknown", {})
    consumer = materialize_detached_switch_first_hypothetical_condition_predictive_view(
        strategy_d0=strategy_d0, synthetic_runtime_state=synthetic,
        switch_in_authority=switch_in,
    )
    if consumer.get("status") != "resolved":
        return _result(_status(consumer), consumer.get("reason", "switch_first_condition_consumer_unavailable"), {})
    d0, snapshot = consumer["strategy_d0"], consumer["runtime_snapshot"]
    return {"status": "resolved", "strategy_d0": d0, "runtime_snapshot": snapshot,
            "own_actor": deepcopy(d0["active_owners"]["self"]), "incoming_target": deepcopy(d0["active_owners"]["opponent"]),
            "condition_consumer": consumer}


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
