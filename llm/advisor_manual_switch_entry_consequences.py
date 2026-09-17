"""Translate exact live manual-entry evaluation into bounded derived observations.

This is deliberately a producer only: the replay reducer remains the sole
runtime-state writer.  In particular, no detached ``next_state`` is accepted
here or copied back into a live battle.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_roster_mechanics import active_self_roster_mechanics_view, build_self_roster_mechanics_context_projection
from llm.advisor_reducer_state_model import is_trusted_current_weather
from llm.advisor_switch_entry_effects import evaluate_switch_entry_effects
from llm.advisor_switch_entry_mechanics_derived_observation import derive_switch_entry_consequence
from llm.advisor_switch_hazard_authority import project_switch_hazard_context
from llm.advisor_switch_entry_trace_authority import normalize_switch_entry_trace_authority
from llm.advisor_trace_runtime_copy_support import resolve_trace_runtime_copy_support


def derive_live_manual_switch_entry_consequences(*, state: Mapping[str, Any], switch_observation: Mapping[str, Any], turn_number: int, allocate_sequence) -> dict[str, Any]:
    """Return confirmed records for exact self-switch consequences, or fail closed."""
    if not isinstance(state, Mapping) or switch_observation.get("side") != "self":
        return {"status": "resolved", "confirmations": [], "entry_effects": None}
    payload = switch_observation.get("payload")
    if not isinstance(payload, Mapping):
        return _bad("switch_payload_invalid")
    try:
        roster = build_self_roster_mechanics_context_projection(state)
        target = active_self_roster_mechanics_view(
            roster, slot_index=payload.get("switch_in_slot_index"), pokemon_id=payload.get("switch_in_pokemon_id"),
        )
        hazards = project_switch_hazard_context(state, affected_side="self")
    except ValueError:
        return _bad("runtime_entry_authority_invalid")
    if not isinstance(target, Mapping):
        return _bad("incoming_entry_authority_unavailable")
    weather = _weather_context(state)
    if weather is None:
        return _bad("current_weather_unknown_or_unsupported")
    entry = evaluate_switch_entry_effects(
        hazards=hazards, target=target,
        intimidate_authority=state.get("switch_entry_intimidate_authority"),
        download_authority=state.get("switch_entry_download_authority"),
        trace_authority=state.get("switch_entry_trace_authority"),
        sturdy_authority=state.get("switch_entry_sturdy_authority"),
        field_state_context=weather,
    )
    if entry.get("entry_effects_supportability") != "complete" or entry.get("status") != "complete":
        return _bad("switch_entry_authority_incomplete")

    incoming = {key: target[key] for key in ("side", "slot_index", "pokemon_id")}
    trace_writeback = _trace_writeback_authority(state=state, incoming=incoming, trace_result=entry.get("trace_result"))
    if trace_writeback.get("status") != "resolved":
        return _bad(trace_writeback.get("reason", "trace_runtime_writeback_unsupported"))
    confirmations: list[dict[str, Any]] = []

    def add(kind: str, owner: Mapping[str, Any], data: Mapping[str, Any]) -> bool:
        allocated = allocate_sequence()
        if not isinstance(allocated, Mapping) or allocated.get("status") != "allocated":
            return False
        result = derive_switch_entry_consequence(
            event_kind=kind, session_id=state.get("session_id"), turn_number=turn_number,
            observation_id=f"{state.get('session_id')}:switch-entry-{allocated['observation_sequence']}",
            observation_sequence=allocated["observation_sequence"], source_switch_observation=dict(switch_observation),
            side=owner.get("side"), slot_index=owner.get("slot_index"), pokemon_id=owner.get("pokemon_id"), payload=dict(data),
        )
        if result.get("status") != "confirmed":
            return False
        confirmations.append(result)
        return True

    damage = entry
    hp = target.get("hp_authority", {})
    if damage.get("damage", 0) > 0 and not add("switch_entry_hp_transition_derived", incoming, {
        "mechanic": "entry_hazards", "hp_before": hp.get("current_hp"), "hp_after": damage.get("post_hazard_hp"),
    }): return _bad("entry_hp_observation_invalid")
    toxic = entry["toxic_spikes_result"]
    if toxic.get("outcome") == "status_applied" and not add("switch_entry_condition_applied_derived", incoming, {
        "mechanic": "toxic_spikes", "condition_before": target["persistent_condition_authority"].get("value"), "condition": toxic.get("post_condition"),
    }): return _bad("entry_condition_observation_invalid")
    sticky = entry["sticky_web_result"]
    if sticky.get("outcome") in {"speed_stage_lowered", "speed_stage_minimum"} and not add("switch_entry_stat_stage_transition_derived", incoming, {
        "mechanic": "sticky_web", "stat": "speed", "stage_before": sticky.get("speed_stage_before"), "stage_after": sticky.get("speed_stage_after"),
    }): return _bad("entry_sticky_web_observation_invalid")
    intimidate = entry["intimidate_result"]
    if intimidate.get("outcome") in {"attack_stage_lowered", "attack_stage_minimum", "attack_stage_reversed", "attack_stage_maximum"}:
        mechanic = "intimidate_reversed" if "reversed" in intimidate["outcome"] or "maximum" in intimidate["outcome"] and state.get("switch_entry_intimidate_authority", {}).get("interaction") == "reversed" else "intimidate"
        if not add("switch_entry_stat_stage_transition_derived", intimidate.get("opponent_identity", {}), {"mechanic": mechanic, "stat": "attack", "stage_before": intimidate.get("attack_stage_before"), "stage_after": intimidate.get("attack_stage_after")}): return _bad("entry_intimidate_observation_invalid")
    download = entry["download_result"]
    if download.get("outcome") in {"attack_stage_raised", "attack_stage_maximum", "special-attack_stage_raised", "special-attack_stage_maximum"} and not add("switch_entry_stat_stage_transition_derived", incoming, {
        "mechanic": "download", "stat": download.get("boosted_stat"), "stage_before": download.get("stage_before"), "stage_after": download.get("stage_after"),
    }): return _bad("entry_download_observation_invalid")
    weather_result = entry["weather_result"]
    if weather_result.get("outcome") == "weather_set" and not add("switch_entry_weather_transition_derived", incoming, {
        "source_ability": target["ability_authority"].get("value"), "weather_before": weather_result.get("weather_before"), "weather_after": weather_result.get("weather_after"),
    }): return _bad("entry_weather_observation_invalid")
    if trace_writeback.get("ability_after") is not None and not add("switch_entry_ability_transition_derived", incoming, {
        "mechanic": "trace", "ability_before": "trace", "ability_after": trace_writeback["ability_after"],
        "copied_from": trace_writeback["copied_from"],
    }): return _bad("entry_trace_ability_observation_invalid")
    if toxic.get("outcome") == "absorbed":
        before = {key: hazards[key] for key in ("stealth_rock", "spikes_layers", "toxic_spikes_layers", "sticky_web")}
        after = {**before, "toxic_spikes_layers": 0}
        if not add("switch_entry_hazard_transition_derived", {"side": "self", "slot_index": None, "pokemon_id": None}, {"hazards_before": before, "hazards_after": after}): return _bad("entry_hazard_observation_invalid")
    if damage.get("hazard_ko") is True and not add("switch_entry_faint_derived", incoming, {"mechanic": "entry_hazards"}):
        return _bad("entry_faint_observation_invalid")
    return {"status": "resolved", "confirmations": confirmations, "entry_effects": deepcopy(entry)}


def _trace_writeback_authority(*, state: Mapping[str, Any], incoming: Mapping[str, Any], trace_result: Any) -> dict[str, Any]:
    if not isinstance(trace_result, Mapping) or trace_result.get("status") != "complete":
        return {"status": "incomplete", "reason": "trace_result_incomplete"}
    if trace_result.get("outcome") != "ability_copied":
        return {"status": "resolved", "ability_after": None, "copied_from": None}
    copied = trace_result.get("copied_ability")
    copied_from = trace_result.get("opponent_identity")
    support = resolve_trace_runtime_copy_support(copied)
    if support.get("status") != "resolved":
        return {"status": "incomplete", "reason": support.get("reason", "trace_copied_ability_followup_unsupported")}
    if not isinstance(copied_from, Mapping) or copied_from.get("side") != "opponent":
        return {"status": "rejected", "reason": "trace_copied_source_identity_invalid"}
    opponent_side = state.get("opponent_side")
    roster = opponent_side.get("pokemon") if isinstance(opponent_side, Mapping) else None
    active_slot = opponent_side.get("active_slot_index") if isinstance(opponent_side, Mapping) else None
    opponent = roster.get(active_slot, roster.get(str(active_slot))) if isinstance(roster, Mapping) and isinstance(active_slot, int) else None
    provenance = opponent.get("current_ability_provenance") if isinstance(opponent, Mapping) else None
    if (active_slot != copied_from.get("slot_index") or not isinstance(opponent, Mapping)
            or opponent.get("pokemon_id") != copied_from.get("pokemon_id") or opponent.get("current_ability") != copied
            or not isinstance(provenance, Mapping) or provenance.get("trust") != "user_confirmed_observation"
            or provenance.get("event_kind") not in {"current_ability_observed", "current_opponent_switch_target_combat_observed"}):
        return {"status": "rejected", "reason": "trace_target_current_ability_mismatch"}
    authority = normalize_switch_entry_trace_authority(
        state.get("switch_entry_trace_authority"), session_id=state.get("session_id"), target=copied_from,
    )
    if (not isinstance(authority, Mapping) or authority.get("source") != dict(incoming)
            or authority.get("target_ability") != copied or authority.get("traceability") != "traceable"):
        return {"status": "rejected", "reason": "trace_authority_binding_mismatch"}
    return {"status": "resolved", "ability_after": copied, "copied_from": deepcopy(dict(copied_from))}


def _weather_context(state: Mapping[str, Any]) -> dict[str, Any] | None:
    field = state.get("field")
    value = field.get("weather") if isinstance(field, Mapping) else None
    provenance = field.get("weather_provenance") if isinstance(field, Mapping) else None
    return {"current_field": {"weather": value}} if is_trusted_current_weather(value, provenance) else None


def _bad(reason: str) -> dict[str, Any]:
    return {"status": "incomplete", "reason": reason, "confirmations": [], "entry_effects": None}
