"""Narrow mechanics-derived observations for one already-confirmed switch."""
from copy import deepcopy

MECHANICS_DERIVED_TRUST = "mechanics_derived_runtime"
SWITCH_ENTRY_MECHANICS_SOURCE = "runtime_switch_entry_mechanics_v1"
DERIVED_KINDS = frozenset({
    "switch_entry_hp_transition_derived",
    "switch_entry_condition_applied_derived",
    "switch_entry_stat_stage_transition_derived",
    "switch_entry_weather_transition_derived",
    "switch_entry_hazard_transition_derived",
    "switch_entry_faint_derived",
})
_WEATHER_BY_ABILITY = {
    "drizzle": "rain", "drought": "sun", "sand-stream": "sandstorm", "snow-warning": "snow",
}
_HAZARD_KEYS = frozenset({"stealth_rock", "spikes_layers", "toxic_spikes_layers", "sticky_web"})


def derive_switch_entry_consequence(*, event_kind, session_id, turn_number, observation_id,
                                    observation_sequence, source_switch_observation, side=None,
                                    slot_index=None, pokemon_id=None, payload=None):
    """Create a strict collection-facing record; replay and reducer recheck it."""
    if event_kind not in DERIVED_KINDS or not isinstance(source_switch_observation, dict):
        return _bad("unsupported_switch_entry_derived_event")
    switch = source_switch_observation
    if (switch.get("event_kind") != "pokemon_switch_observed"
            or switch.get("session_id") != session_id
            or not isinstance(switch.get("observation_id"), str)
            or not switch["observation_id"]):
        return _bad("source_switch_invalid")
    if not _turn(turn_number) or switch.get("turn_number") != turn_number:
        return _bad("invalid_turn")
    if not _sequence(observation_sequence) or observation_sequence <= switch.get("observation_sequence", 0):
        return _bad("source_switch_ordering_invalid")
    switch_payload = switch.get("payload")
    if not isinstance(switch_payload, dict):
        return _bad("source_switch_invalid")
    incoming = {
        "side": switch.get("side"),
        "slot_index": switch_payload.get("switch_in_slot_index"),
        "pokemon_id": switch_payload.get("switch_in_pokemon_id"),
    }
    data = deepcopy(payload) if isinstance(payload, dict) else {}
    data["source_switch_observation_id"] = switch["observation_id"]
    if not _valid(event_kind, incoming, side, slot_index, pokemon_id, data):
        return _bad("invalid_switch_entry_derived_payload")
    return {"status": "confirmed", "observation": {
        "event_kind": event_kind, "session_id": session_id, "turn_number": turn_number,
        "observation_id": observation_id, "observation_sequence": observation_sequence,
        "side": side, "slot_index": slot_index, "pokemon_id": pokemon_id,
        "payload": data, "source": SWITCH_ENTRY_MECHANICS_SOURCE,
        "trust": MECHANICS_DERIVED_TRUST, "scope": "switch_entry",
        "reducer_eligibility": "candidate",
    }}


def _valid(kind, incoming, side, slot, pokemon_id, payload):
    owner = (side, slot, pokemon_id)
    incoming_owner = (incoming["side"], incoming["slot_index"], incoming["pokemon_id"])
    if not _owner(*incoming_owner) or not isinstance(payload.get("source_switch_observation_id"), str):
        return False
    if kind in {"switch_entry_hp_transition_derived", "switch_entry_condition_applied_derived", "switch_entry_faint_derived", "switch_entry_weather_transition_derived"} and owner != incoming_owner:
        return False
    if kind == "switch_entry_hp_transition_derived":
        return (payload.get("mechanic") == "entry_hazards" and _hp(payload.get("hp_before"))
                and _hp(payload.get("hp_after")) and payload["hp_after"] <= payload["hp_before"])
    if kind == "switch_entry_condition_applied_derived":
        return (payload.get("mechanic") == "toxic_spikes" and payload.get("condition") in {"poison", "toxic"}
                and payload.get("condition_before") in {None, "unknown"})
    if kind == "switch_entry_faint_derived":
        return payload.get("mechanic") == "entry_hazards"
    if kind == "switch_entry_weather_transition_derived":
        return (payload.get("source_ability") in _WEATHER_BY_ABILITY
                and _WEATHER_BY_ABILITY[payload["source_ability"]] == payload.get("weather_after")
                and payload.get("weather_before") in {None, "none", "sun", "rain", "sandstorm", "snow", "unknown"})
    if kind == "switch_entry_hazard_transition_derived":
        before, after = payload.get("hazards_before"), payload.get("hazards_after")
        return (owner == (incoming["side"], None, None) and _hazards(before) and _hazards(after)
                and before["toxic_spikes_layers"] in {1, 2} and after["toxic_spikes_layers"] == 0
                and all(before[key] == after[key] for key in _HAZARD_KEYS - {"toxic_spikes_layers"}))
    if kind == "switch_entry_stat_stage_transition_derived":
        before, after, stat, mechanic = (payload.get("stage_before"), payload.get("stage_after"),
                                         payload.get("stat"), payload.get("mechanic"))
        if not _stage(before) or not _stage(after):
            return False
        if mechanic == "sticky_web":
            return owner == incoming_owner and stat == "speed" and after == max(-6, before - 1)
        if mechanic == "download":
            return owner == incoming_owner and stat in {"attack", "special-attack"} and after == min(6, before + 1)
        return (mechanic in {"intimidate", "intimidate_reversed"} and owner != incoming_owner
                and owner[0] in {"self", "opponent"} and owner[0] != incoming_owner[0]
                and stat == "attack" and after == (max(-6, before - 1) if mechanic == "intimidate" else min(6, before + 1)))
    return False


def _owner(side, slot, pokemon_id):
    return side in {"self", "opponent"} and isinstance(slot, int) and not isinstance(slot, bool) and slot >= 0 and isinstance(pokemon_id, str) and bool(pokemon_id)


def _hp(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _stage(value):
    return isinstance(value, int) and not isinstance(value, bool) and -6 <= value <= 6


def _sequence(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _turn(value):
    return _sequence(value)


def _hazards(value):
    return (isinstance(value, dict) and set(value) == _HAZARD_KEYS
            and value.get("stealth_rock") in {"present", "absent"}
            and value.get("spikes_layers") in {0, 1, 2, 3}
            and value.get("toxic_spikes_layers") in {0, 1, 2}
            and value.get("sticky_web") in {"present", "absent"})


def _bad(reason):
    return {"status": "rejected", "reason": reason, "observation": None}
