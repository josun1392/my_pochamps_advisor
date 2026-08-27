"""Detached hypothetical switch-in authority for one selectable opponent target."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_reducer_state_model import is_unknown_battle_fact
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
from llm.advisor_runtime_strategy_d0 import freeze_runtime_current_stage_authority
from llm.advisor_runtime_d0_opponent_switch_target_combat_authority import freeze_runtime_d0_opponent_switch_target_combat_authority
from llm.advisor_switch_entry_hazards import evaluate_entry_hazards
from llm.advisor_switch_entry_effects import evaluate_download_entry, evaluate_entry_weather, evaluate_intimidate_entry, evaluate_sticky_web_entry, evaluate_toxic_spikes_entry, evaluate_sturdy_entry, evaluate_trace_entry
from llm.advisor_switch_entry_intimidate_authority import normalize_switch_entry_intimidate_authority
from llm.advisor_switch_entry_download_authority import normalize_switch_entry_download_authority
from llm.advisor_switch_entry_trace_authority import normalize_switch_entry_trace_authority
from llm.advisor_switch_entry_sturdy_authority import normalize_switch_entry_sturdy_authority
from llm.advisor_switch_hazard_authority import normalize_switch_hazard_context
from llm.advisor_prospective_entry_authority import normalize_prospective_entry_interactions


SCHEMA_VERSION = "detached-opponent-switch-in-intermediate-authority-v1"


def materialize_detached_opponent_switch_in_intermediate_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    switch_response_authority: Mapping[str, Any],
    selected_response_action_id: str,
) -> dict[str, Any]:
    """Materialize one hypothetical opponent switch-in without state writeback."""
    base = _base(strategy_d0)
    if not base or not isinstance(selected_response_action_id, str) or not selected_response_action_id:
        return _result("rejected", "invalid_switch_in_request", base)
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    action = _selected_action(switch_response_authority, base, selected_response_action_id)
    if action.get("status") != "resolved":
        return _result(action["status"], action["reason"], base)
    combat = freeze_runtime_d0_opponent_switch_target_combat_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, switch_response_authority=switch_response_authority, selected_response_action_id=selected_response_action_id)
    if combat.get("status") != "resolved":
        return _result(combat.get("status", "incomplete"), combat.get("reason", "switch_target_current_combat_unknown"), base, selected_response_action_id=selected_response_action_id, target_owner=action.get("target_owner"))
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    target = action["target_owner"]
    roster = state.get("opponent_side", {}).get("pokemon") if isinstance(state, Mapping) and isinstance(state.get("opponent_side"), Mapping) else None
    current = roster.get(target["slot_index"]) if isinstance(roster, Mapping) else None
    if not isinstance(current, Mapping) or current.get("pokemon_id") != target["pokemon_id"]:
        return _result("rejected", "switch_target_runtime_identity_mismatch", base, selected_response_action_id=selected_response_action_id)
    hp = _hp_authority(current)
    if hp is None:
        return _result("incomplete", "switch_target_hp_or_faint_unknown", base, selected_response_action_id=selected_response_action_id, target_owner=target)
    if hp["fainted"]:
        return _result("rejected", "selectable_switch_target_is_fainted", base, selected_response_action_id=selected_response_action_id, target_owner=target)
    hazards = _hazards(state, base["session_id"])
    entry = _entry_consequence(
        hazards, current, hp, target, strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot, own_actor=base["own_actor"],
        entry_intimidate_authority=state.get("switch_entry_intimidate_authority"),
        entry_download_authority=state.get("switch_entry_download_authority"),
        entry_trace_authority=state.get("switch_entry_trace_authority"),
        entry_sturdy_authority=state.get("switch_entry_sturdy_authority"),
        field_state_context=_field_weather_context(state),
    )
    if entry.get("status") != "resolved":
        return _result(entry["status"], entry["reason"], base, selected_response_action_id=selected_response_action_id, target_owner=target, entry_hazard_context=hazards)
    post_hp = entry["post_hp"]
    if post_hp == 0:
        return _result("unsupported", "replacement_required_after_switch_entry_ko", base, selected_response_action_id=selected_response_action_id, target_owner=target, entry_hazard_context=hazards, entry_consequence=entry)
    fields = _fields(current)
    trace = entry["trace_consequence"]
    if trace.get("outcome") == "ability_copied":
        copied = trace.get("copied_ability")
        if not isinstance(copied, str) or not copied:
            return _result("incomplete", "switch_in_trace_copied_ability_unknown", base, selected_response_action_id=selected_response_action_id, target_owner=target)
        fields["ability"] = {
            "status": "known", "value": copied,
            "provenance": "detached_opponent_switch_in_trace_entry_v1",
        }
    toxic = entry["toxic_spikes_consequence"]
    if toxic.get("outcome") == "status_applied":
        fields["condition"] = {
            "status": "known", "value": toxic["post_condition"],
            "provenance": "detached_toxic_spikes_entry_v1",
        }
    sticky = entry["sticky_web_consequence"]
    if sticky.get("outcome") == "speed_stage_lowered":
        stages = fields["stages"]
        if not isinstance(stages, Mapping) or stages.get("status") != "known" or not isinstance(stages.get("value"), Mapping):
            return _result("incomplete", "switch_in_sticky_web_stage_authority_unknown", base, selected_response_action_id=selected_response_action_id, target_owner=target)
        stages = deepcopy(dict(stages))
        stages["value"]["speed"] = sticky["speed_stage_after"]
        stages["provenance"] = "detached_sticky_web_entry_v1"
        fields["stages"] = stages
    download = entry["download_consequence"]
    if download.get("outcome") in {"attack_stage_raised", "attack_stage_maximum", "special-attack_stage_raised", "special-attack_stage_maximum"}:
        stages = fields["stages"]
        stat, after = download.get("boosted_stat"), download.get("stage_after")
        if not isinstance(stages, Mapping) or stages.get("status") != "known" or not isinstance(stages.get("value"), Mapping) or stat not in {"attack", "special-attack"} or not isinstance(after, int) or isinstance(after, bool) or not -6 <= after <= 6:
            return _result("incomplete", "switch_in_download_stage_authority_unknown", base, selected_response_action_id=selected_response_action_id, target_owner=target)
        stages = deepcopy(dict(stages))
        stages["value"][stat] = after
        stages["provenance"] = "detached_download_entry_v1"
        fields["stages"] = stages
    own_attack_overlay = entry["own_attack_stage_overlay"]
    hypothetical = {
        "schema_version": SCHEMA_VERSION,
        "hypothetical": True,
        "active_owner": deepcopy(target),
        "replaced_active_owner": deepcopy(base["opponent_actor"]),
        "hp_authority": {"status": "known", "current_hp": post_hp, "maximum_hp": hp["maximum_hp"], "provenance": "detached_switch_entry_v1"},
        "fainted_authority": {"status": "known", "value": False, "provenance": "detached_switch_entry_v1"},
        "condition_authority": fields["condition"],
        "item_authority": fields["item"],
        "ability_authority": fields["ability"],
        "type_authority": fields["type"],
        "final_stats_authority": fields["final_stats"],
        "stage_authority": fields["stages"],
        "incoming_offensive_stage_overlay": _incoming_offensive_stage_overlay(download, target),
        "trace_ability_overlay": _trace_ability_overlay(trace, target, base["own_actor"]),
        "own_attack_stage_overlay": deepcopy(own_attack_overlay),
        "sturdy_survival_authority": _sturdy_survival_authority(
            entry["sturdy_consequence"], target, base, post_hp, hp["maximum_hp"],
        ),
        "weather_authority": _weather_overlay(entry["weather_consequence"]),
        "substitute_authority": {"status": "unknown", "reason": "opponent_switch_in_substitute_untracked"},
        "entry_hazard_context": deepcopy(hazards),
        "post_entry_hazard_context": deepcopy(entry["post_entry_hazard_context"]),
        "entry_consequence": deepcopy(entry),
    }
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "selected_response_action_id": selected_response_action_id,
        "target_owner": deepcopy(target),
        "switch_response_authority_provenance": deepcopy(switch_response_authority.get("response_set_provenance")),
        "switch_target_combat_authority": deepcopy(combat),
        "hypothetical_switch_in_state": hypothetical,
        "current_authority_writeback": "forbidden",
        "reason": None,
    }


def _selected_action(authority: Any, base: Mapping[str, Any], action_id: str) -> dict:
    required = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "own_actor", "opponent_actor")
    if not isinstance(authority, Mapping) or authority.get("status") != "resolved" or any(authority.get(key) != base.get(key) for key in required):
        return {"status": "rejected", "reason": "switch_response_authority_binding_mismatch"}
    actions = authority.get("actions")
    if not isinstance(actions, (tuple, list)):
        return {"status": "rejected", "reason": "switch_response_actions_invalid"}
    matching = [row for row in actions if isinstance(row, Mapping) and row.get("action_id") == action_id]
    if len(matching) != 1:
        return {"status": "rejected", "reason": "selected_switch_response_unknown"}
    action = matching[0]
    target = action.get("target_owner")
    if action.get("action_type") != "manual_switch" or action.get("acting_side") != "opponent" or action.get("target_side") != "self" or action.get("selectability") != "selectable" or not _owner(target, "opponent", base["session_id"]) or target == base["opponent_actor"]:
        return {"status": "incomplete", "reason": "selected_switch_response_not_selectable"}
    if action_id not in authority.get("selectable_response_action_ids", ()):
        return {"status": "rejected", "reason": "selectable_switch_response_set_mismatch"}
    return {"status": "resolved", "target_owner": deepcopy(dict(target))}


def _hp_authority(current: Mapping[str, Any]) -> dict | None:
    hp, maximum, fainted = current.get("current_hp"), current.get("max_hp"), current.get("fainted")
    if not isinstance(hp, int) or isinstance(hp, bool) or not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0 or not isinstance(fainted, bool) or not 0 <= hp <= maximum or fainted is not (hp == 0):
        return None
    return {"current_hp": hp, "maximum_hp": maximum, "fainted": fainted}


def _hazards(state: Any, session_id: str) -> dict:
    raw = state.get("switch_hazard_context") if isinstance(state, Mapping) else None
    return normalize_switch_hazard_context(raw, session_id=session_id, affected_side="opponent")


def _entry_consequence(
    hazards: Mapping[str, Any], current: Mapping[str, Any], hp: Mapping[str, Any], target_owner: Mapping[str, Any],
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], own_actor: Mapping[str, Any],
    entry_intimidate_authority: Any, entry_download_authority: Any, entry_trace_authority: Any, entry_sturdy_authority: Any, field_state_context: Mapping[str, Any] | None,
) -> dict:
    if not isinstance(hazards, Mapping) or any(hazards.get(key) == "unknown" for key in ("stealth_rock", "spikes_layers", "toxic_spikes_layers", "sticky_web")):
        return {"status": "incomplete", "reason": "switch_entry_hazards_unknown"}
    target = {
        "session_id": target_owner["session_id"],
        "side": "opponent",
        "slot_index": target_owner["slot_index"],
        "pokemon_id": target_owner["pokemon_id"],
        "hp_authority": {"status": "known", "current_hp": hp["current_hp"], "maximum_hp": hp["maximum_hp"]},
        "item_authority": _entry_value_authority(current.get("known_item")),
        "ability_authority": _entry_value_authority(current.get("current_ability")),
        "current_type_authority": _entry_value_authority(current.get("current_type")),
        "persistent_condition_authority": _entry_condition_authority(current.get("condition")),
        "prospective_groundedness_authority": _groundedness_authority(current.get("prospective_groundedness_context"), target_owner),
        "prospective_speed_stage_authority": _entry_speed_stage_authority(current.get("stat_stages")),
        "prospective_offensive_stages_authority": _entry_offensive_stages_authority(current.get("stat_stages")),
        "prospective_entry_interactions_authority": _entry_interactions_authority(current.get("prospective_entry_interactions_context"), target_owner),
    }
    evaluated = evaluate_entry_hazards(hazards=hazards, target=target)
    if evaluated.get("status") != "complete":
        return {"status": "incomplete", "reason": str(evaluated.get("reason") or "switch_entry_hazard_authority_incomplete")}
    toxic = evaluate_toxic_spikes_entry(hazards=hazards, target=target)
    if toxic.get("status") != "complete":
        return {"status": "incomplete", "reason": str(toxic.get("reason") or "toxic_spikes_authority_incomplete")}
    sticky = evaluate_sticky_web_entry(hazards=hazards, target=target)
    if sticky.get("status") != "complete":
        return {"status": "incomplete", "reason": str(sticky.get("reason") or "sticky_web_authority_incomplete")}
    intimidate = _intimidate_consequence(
        authority_value=entry_intimidate_authority, target=target, damage=evaluated, strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot, incoming_owner=target_owner, own_actor=own_actor,
    )
    if intimidate.get("status") != "complete":
        status = "rejected" if intimidate.get("status") == "rejected" else "incomplete"
        return {"status": status, "reason": str(intimidate.get("reason") or "intimidate_authority_incomplete")}
    download = _download_consequence(
        authority_value=entry_download_authority, target=target, damage=evaluated,
        incoming_owner=target_owner, own_actor=own_actor,
    )
    if download.get("status") != "complete":
        status = "rejected" if download.get("status") == "rejected" else "incomplete"
        return {"status": status, "reason": str(download.get("reason") or "download_authority_incomplete")}
    trace = _trace_consequence(
        authority_value=entry_trace_authority, target=target, damage=evaluated,
        incoming_owner=target_owner, own_actor=own_actor,
    )
    if trace.get("status") != "complete":
        status = "rejected" if trace.get("status") == "rejected" else "incomplete"
        return {"status": status, "reason": str(trace.get("reason") or "trace_authority_incomplete")}
    sturdy = _sturdy_consequence(
        authority_value=entry_sturdy_authority, target=target, damage=evaluated,
        incoming_owner=target_owner, own_actor=own_actor,
    )
    if sturdy.get("status") != "complete":
        status = "rejected" if sturdy.get("status") == "rejected" else "incomplete"
        return {"status": status, "reason": str(sturdy.get("reason") or "sturdy_authority_incomplete")}
    weather = evaluate_entry_weather(target=target, damage=evaluated, field_state_context=field_state_context)
    if weather.get("status") != "complete":
        return {"status": "incomplete", "reason": str(weather.get("reason") or "switch_entry_weather_authority_incomplete")}
    after_hazards = deepcopy(dict(hazards))
    if toxic.get("removes_toxic_spikes") is True:
        after_hazards["toxic_spikes_layers"] = 0
    effect = "known_absent_entry_hazards" if hazards.get("stealth_rock") == "absent" and hazards.get("spikes_layers") == 0 and hazards.get("toxic_spikes_layers") == 0 and hazards.get("sticky_web") == "absent" else "supported_entry_hazards"
    return {
        "status": "resolved", "damage": evaluated["damage"], "post_hp": evaluated["post_hazard_hp"], "hazard_ko": evaluated["hazard_ko"], "effect": effect,
        "hazard_evidence": deepcopy(evaluated), "toxic_spikes_consequence": deepcopy(toxic),
        "sticky_web_consequence": deepcopy(sticky),
        "intimidate_consequence": deepcopy(intimidate),
        "download_consequence": deepcopy(download),
        "trace_consequence": deepcopy(trace),
        "sturdy_consequence": deepcopy(sturdy),
        "weather_consequence": deepcopy(weather),
        "own_attack_stage_overlay": _own_attack_stage_overlay(intimidate, own_actor),
        "post_entry_hazard_context": after_hazards,
    }


def _intimidate_consequence(
    *, authority_value: Any, target: Mapping[str, Any], damage: Mapping[str, Any],
    strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    incoming_owner: Mapping[str, Any], own_actor: Mapping[str, Any],
) -> dict:
    ability = target.get("ability_authority")
    if not isinstance(ability, Mapping) or ability.get("status") != "known":
        return {"status": "insufficient_context", "reason": "incoming_ability_unknown"}
    if ability.get("value") != "intimidate":
        return {"status": "complete", "outcome": "not_applicable"}
    raw = authority_value
    if raw is None:
        return {"status": "insufficient_context", "reason": "intimidate_interaction_unknown"}
    authority = normalize_switch_entry_intimidate_authority(
        raw, session_id=incoming_owner["session_id"], target=own_actor,
    )
    if authority is None:
        return {"status": "rejected", "reason": "intimidate_authority_binding_mismatch"}
    if not _same_identity(authority.get("source"), incoming_owner):
        return {"status": "rejected", "reason": "intimidate_source_identity_mismatch"}
    stages = freeze_runtime_current_stage_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=own_actor,
    )
    if stages.get("status") == "rejected":
        return {"status": "rejected", "reason": stages.get("reason", "own_attack_stage_authority_rejected")}
    attack = stages.get("stages", {}).get("attack") if isinstance(stages.get("stages"), Mapping) else None
    if not isinstance(attack, Mapping) or attack.get("status") != "known":
        return {"status": "insufficient_context", "reason": "own_attack_stage_unknown"}
    if authority.get("target_attack_stage") == "unknown":
        return {"status": "insufficient_context", "reason": "intimidate_interaction_unknown"}
    if authority.get("target_attack_stage") != attack.get("value"):
        return {"status": "rejected", "reason": "intimidate_pre_entry_attack_stage_mismatch"}
    return evaluate_intimidate_entry(target=target, damage=damage, authority=authority)


def _sturdy_consequence(*, authority_value: Any, target: Mapping[str, Any], damage: Mapping[str, Any], incoming_owner: Mapping[str, Any], own_actor: Mapping[str, Any]) -> dict:
    ability = target.get("ability_authority")
    if not isinstance(ability, Mapping) or ability.get("status") != "known":
        return {"status": "insufficient_context", "reason": "incoming_ability_unknown"}
    if ability.get("value") != "sturdy":
        return {"status": "complete", "outcome": "not_applicable"}
    if authority_value is None:
        return {"status": "insufficient_context", "reason": "sturdy_interaction_unknown"}
    authority = normalize_switch_entry_sturdy_authority(
        authority_value, session_id=incoming_owner["session_id"], target=own_actor,
    )
    if authority is None:
        return {"status": "rejected", "reason": "sturdy_authority_binding_mismatch"}
    if not _same_identity(authority.get("source"), incoming_owner):
        return {"status": "rejected", "reason": "sturdy_source_identity_mismatch"}
    return evaluate_sturdy_entry(target=target, damage=damage, authority=authority)


def _download_consequence(*, authority_value: Any, target: Mapping[str, Any], damage: Mapping[str, Any], incoming_owner: Mapping[str, Any], own_actor: Mapping[str, Any]) -> dict:
    ability = target.get("ability_authority")
    if not isinstance(ability, Mapping) or ability.get("status") != "known":
        return {"status": "insufficient_context", "reason": "incoming_ability_unknown"}
    if ability.get("value") != "download":
        return {"status": "complete", "outcome": "not_applicable"}
    if authority_value is None:
        return {"status": "insufficient_context", "reason": "download_authority_unknown"}
    authority = normalize_switch_entry_download_authority(
        authority_value, session_id=incoming_owner["session_id"], target=own_actor,
    )
    if authority is None:
        return {"status": "rejected", "reason": "download_authority_binding_mismatch"}
    if not _same_identity(authority.get("source"), incoming_owner):
        return {"status": "rejected", "reason": "download_source_identity_mismatch"}
    return evaluate_download_entry(target=target, damage=damage, authority=authority)


def _trace_consequence(*, authority_value: Any, target: Mapping[str, Any], damage: Mapping[str, Any], incoming_owner: Mapping[str, Any], own_actor: Mapping[str, Any]) -> dict:
    ability = target.get("ability_authority")
    if not isinstance(ability, Mapping) or ability.get("status") != "known":
        return {"status": "insufficient_context", "reason": "incoming_ability_unknown"}
    if ability.get("value") != "trace":
        return {"status": "complete", "outcome": "not_applicable"}
    if authority_value is None:
        return {"status": "insufficient_context", "reason": "trace_authority_unknown"}
    authority = normalize_switch_entry_trace_authority(
        authority_value, session_id=incoming_owner["session_id"], target=own_actor,
    )
    if authority is None:
        return {"status": "rejected", "reason": "trace_authority_binding_mismatch"}
    if not _same_identity(authority.get("source"), incoming_owner):
        return {"status": "rejected", "reason": "trace_source_identity_mismatch"}
    return evaluate_trace_entry(target=target, damage=damage, authority=authority)


def _sturdy_survival_authority(sturdy: Mapping[str, Any], incoming_owner: Mapping[str, Any], base: Mapping[str, Any], post_hp: int, maximum_hp: int) -> dict:
    bindings = {
        "schema_version": "detached-switch-in-sturdy-survival-authority-v1",
        "session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"],
        "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": deepcopy(base["decision_owner"]),
        "defender": deepcopy(dict(incoming_owner)), "attacker": deepcopy(base["own_actor"]),
    }
    if not isinstance(sturdy, Mapping) or sturdy.get("status") != "complete":
        return {**bindings, "status": "unknown"}
    if sturdy.get("outcome") != "survival_ready":
        return {**bindings, "status": "not_applicable", "outcome": sturdy.get("outcome")}
    if not isinstance(post_hp, int) or isinstance(post_hp, bool) or post_hp != maximum_hp or maximum_hp <= 1:
        return {**bindings, "status": "unknown"}
    if not _same_identity(sturdy.get("opponent_identity"), base["own_actor"]):
        return {**bindings, "status": "unknown"}
    return {
        **bindings, "status": "ready", "post_entry_hp": post_hp, "maximum_hp": maximum_hp,
        "provenance": "exact_detached_opponent_switch_in_sturdy_readiness_v1",
    }


def _own_attack_stage_overlay(intimidate: Mapping[str, Any], own_actor: Mapping[str, Any]) -> dict:
    outcome = intimidate.get("outcome") if isinstance(intimidate, Mapping) else None
    if outcome not in {"attack_stage_lowered", "attack_stage_minimum", "attack_drop_prevented", "attack_stage_reversed", "attack_stage_maximum"}:
        return {"status": "not_applicable"}
    before, after = intimidate.get("attack_stage_before"), intimidate.get("attack_stage_after")
    if not isinstance(before, int) or isinstance(before, bool) or not isinstance(after, int) or isinstance(after, bool) or not -6 <= before <= 6 or not -6 <= after <= 6:
        return {"status": "unknown"}
    return {
        "status": "known", "owner": deepcopy(dict(own_actor)), "stat": "attack",
        "before": before, "after": after, "outcome": outcome,
        "provenance": "detached_opponent_switch_in_intimidate_entry_v1",
    }


def _incoming_offensive_stage_overlay(download: Mapping[str, Any], incoming_owner: Mapping[str, Any]) -> dict:
    outcome = download.get("outcome") if isinstance(download, Mapping) else None
    if outcome not in {"attack_stage_raised", "attack_stage_maximum", "special-attack_stage_raised", "special-attack_stage_maximum"}:
        return {"status": "not_applicable"}
    stat, before, after = download.get("boosted_stat"), download.get("stage_before"), download.get("stage_after")
    if stat not in {"attack", "special-attack"} or not isinstance(before, int) or isinstance(before, bool) or not isinstance(after, int) or isinstance(after, bool) or not -6 <= before <= 6 or not -6 <= after <= 6:
        return {"status": "unknown"}
    return {"status": "known", "owner": deepcopy(dict(incoming_owner)), "stat": stat, "before": before, "after": after, "outcome": outcome, "provenance": "detached_opponent_switch_in_download_entry_v1"}


def _trace_ability_overlay(trace: Mapping[str, Any], incoming_owner: Mapping[str, Any], copied_source: Mapping[str, Any]) -> dict:
    if not isinstance(trace, Mapping) or trace.get("status") != "complete":
        return {"status": "unknown"}
    if trace.get("outcome") in {"not_applicable", "ability_untraceable", "not_activated_hazard_ko"}:
        return {"status": "not_applicable", "outcome": trace.get("outcome")}
    copied = trace.get("copied_ability")
    if trace.get("outcome") != "ability_copied" or not isinstance(copied, str) or not copied or not _same_identity(trace.get("opponent_identity"), copied_source):
        return {"status": "unknown"}
    return {
        "status": "known", "owner": deepcopy(dict(incoming_owner)), "copied_from": deepcopy(dict(copied_source)),
        "before": "trace", "after": copied, "outcome": "ability_copied",
        "provenance": "detached_opponent_switch_in_trace_entry_v1",
    }


def _field_weather_context(state: Any) -> dict | None:
    """Return only an exact frozen current weather view for entry resolution."""
    field = state.get("field") if isinstance(state, Mapping) else None
    weather = field.get("weather") if isinstance(field, Mapping) else None
    if not isinstance(weather, str) or weather not in {"none", "rain", "sun", "sandstorm", "snow"}:
        return None
    return {"current_field": {"weather": weather}}


def _weather_overlay(weather: Any) -> dict:
    if not isinstance(weather, Mapping) or weather.get("status") != "complete":
        return {"status": "unknown"}
    outcome = weather.get("outcome")
    if outcome == "not_applicable":
        return {"status": "not_applicable"}
    before, after = weather.get("weather_before"), weather.get("weather_after")
    if outcome not in {"weather_set", "weather_already_active"} or before not in {"none", "rain", "sun", "sandstorm", "snow"} or after not in {"rain", "sun", "sandstorm", "snow"}:
        return {"status": "unknown"}
    return {
        "status": "known", "before": before, "after": after, "outcome": outcome,
        "provenance": "detached_opponent_switch_in_weather_entry_v1",
    }


def _same_identity(left: Any, right: Any) -> bool:
    return isinstance(left, Mapping) and isinstance(right, Mapping) and all(
        left.get(key) == right.get(key) for key in ("side", "slot_index", "pokemon_id")
    )


def _fields(current: Mapping[str, Any]) -> dict:
    condition = {"status": "known", "value": "none", "provenance": "runtime_battle_state_v1"} if current.get("condition") is None else _simple_authority(current.get("condition"))
    return {
        "condition": condition,
        "item": {"status": "known", "value": None, "provenance": "runtime_battle_state_v1"} if current.get("known_item") is None else _simple_authority(current.get("known_item")),
        "ability": _simple_authority(current.get("current_ability")),
        "type": _simple_authority(current.get("current_type")),
        "final_stats": _simple_authority(current.get("current_final_stats")),
        "stages": _simple_authority(current.get("stat_stages")),
    }


def _simple_authority(value: Any) -> dict:
    if value is None or is_unknown_battle_fact(value):
        return {"status": "unknown"}
    return {"status": "known", "value": deepcopy(value), "provenance": "runtime_battle_state_v1"}


def _entry_value_authority(value: Any) -> dict:
    """Make a minimal exact-value view for the existing entry resolver."""
    if is_unknown_battle_fact(value) or value == "unknown":
        return {"status": "unknown"}
    return {"status": "known", "value": deepcopy(value)}


def _entry_condition_authority(value: Any) -> dict:
    if is_unknown_battle_fact(value) or value not in {None, "none", "burn", "poison", "toxic", "paralysis", "sleep", "freeze"}:
        return {"status": "unknown"}
    return {"status": "known", "value": deepcopy(value)}


def _entry_speed_stage_authority(value: Any) -> dict:
    speed = value.get("speed") if isinstance(value, Mapping) else None
    if not isinstance(speed, int) or isinstance(speed, bool) or not -6 <= speed <= 6:
        return {"status": "unknown"}
    return {"status": "known", "value": speed}


def _entry_offensive_stages_authority(value: Any) -> dict | None:
    if not isinstance(value, Mapping):
        return None
    result = {stat: value.get(stat) for stat in ("attack", "special-attack")}
    if any(not isinstance(stage, int) or isinstance(stage, bool) or not -6 <= stage <= 6 for stage in result.values()):
        return None
    return result


def _groundedness_authority(value: Any, target_owner: Mapping[str, Any]) -> dict:
    if not isinstance(value, Mapping) or value.get("schema_version") != "identity-groundedness-v1" or any(value.get(key) != target_owner.get(key) for key in ("side", "slot_index", "pokemon_id")):
        return {"status": "unknown"}
    status = value.get("status")
    return {"status": status} if status in {"grounded", "ungrounded"} else {"status": "unknown"}


def _entry_interactions_authority(value: Any, target_owner: Mapping[str, Any]) -> dict:
    normalized = normalize_prospective_entry_interactions(
        value, session_id=target_owner["session_id"], side=target_owner["side"],
        slot_index=target_owner["slot_index"], pokemon_id=target_owner["pokemon_id"],
    )
    return {"toxic_spikes": normalized["toxic_spikes"], "sticky_web": normalized["sticky_web"]}


def _base(d0: Any) -> dict:
    owners = d0.get("active_owners") if isinstance(d0, Mapping) else None
    own, opponent = owners.get("self") if isinstance(owners, Mapping) else None, owners.get("opponent") if isinstance(owners, Mapping) else None
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(own, "self", d0.get("session_id")) or not _owner(opponent, "opponent", d0.get("session_id")):
        return {}
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": deepcopy(d0.get("decision_owner")), "own_actor": deepcopy(dict(own)), "opponent_actor": deepcopy(dict(opponent))}


def _owner(value: Any, side: str, session_id: Any) -> bool:
    return isinstance(value, Mapping) and value.get("session_id") == session_id and value.get("side") == side and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
