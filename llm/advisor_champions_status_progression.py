"""Pokémon-owned observed progression; no generic major-status lifecycle."""
from copy import deepcopy
from typing import Mapping

SCHEMA = "champions-sleep-freeze-progression-v1"
OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def valid_progression(row, owner):
    try:
        return _valid_progression(row, owner)
    except (KeyError, TypeError, ValueError):
        return False


def _valid_progression(row, owner):
    if not isinstance(row, Mapping) or row.get("schema_version") != SCHEMA or row.get("owner") != owner:
        return False
    n = row.get("prior_attempts")
    duration = row.get("sleep_duration")
    if "adjusted_duration" in row or "duration_adjustment" in row:
        adjustment = row.get("duration_adjustment")
        if type(duration) is not int or duration not in {2, 3} or not isinstance(adjustment, Mapping): return False
        active = adjustment.get("early_bird_active")
        abilities = adjustment.get("abilities", {})
        if (type(active) is not bool or adjustment.get("holder") != owner or adjustment.get("status") != "resolved"
                or adjustment.get("session_id") != owner.get("session_id")
                or not all(isinstance(adjustment.get(key), str) and adjustment[key] for key in ("source_runtime_fingerprint", "source_branch_fingerprint"))
                or not isinstance(adjustment.get("path"), (tuple, list))
                or not isinstance(abilities, Mapping) or set(abilities) != {"self", "opponent"}
                or not all(isinstance(value, str) and value for value in abilities.values())
                or adjustment.get("ability_id") != abilities.get(owner.get("side"))
                or adjustment.get("suppressed") != ("neutralizing-gas" in abilities.values())
                or active != (adjustment.get("ability_id") == "early-bird" and not adjustment.get("suppressed"))
                or type(row.get("adjusted_duration")) is not int
                or row.get("adjusted_duration") != (duration // 2 if active else duration)):
            return False
    return (row.get("condition") in {"sleep", "freeze"}
            and isinstance(n, int) and not isinstance(n, bool) and 0 <= n <= 2
            and isinstance(row.get("origin_id"), str) and bool(row["origin_id"])
            and isinstance(row.get("established_turn"), int) and not isinstance(row["established_turn"], bool) and row["established_turn"] >= 1
            and (duration is None or type(duration) is int and duration in {2, 3})
            and (row["condition"] == "sleep" or duration is None)
            and isinstance(row.get("condition_observation"), Mapping))


def observe_progression(*, state, pokemon, event):
    """Install an explicitly observed counter; never infer one from status."""
    owner = {k: event.get(k) for k in OWNER_KEYS}
    if owner["session_id"] != state.get("session_id") or event.get("trust") != "user_confirmed_observation":
        return "untrusted_champions_status_progression"
    observation = pokemon.get("condition_provenance", {})
    if (pokemon.get("condition") not in {"sleep", "freeze"}
            or event.get("condition") != pokemon.get("condition")
            or observation.get("event_kind") != "current_condition_observed"
            or observation.get("trust") != "user_confirmed_observation"
            or observation.get("condition") != pokemon.get("condition")):
        return "champions_status_progression_condition_unavailable"
    row = {"schema_version": SCHEMA, "owner": owner, "condition": pokemon["condition"],
           "origin_id": event.get("origin_id"), "established_turn": event.get("established_turn"),
           "prior_attempts": event.get("prior_attempts"), "sleep_duration": event.get("sleep_duration"),
           "condition_observation": deepcopy(observation), "observed_turn": event.get("turn_number"),
           "provenance": "observed_champions_status_progression_v1"}
    if not valid_progression(row, owner) or type(row["observed_turn"]) is not int or row["observed_turn"] < max(row["established_turn"], observation.get("turn_number", 0)):
        return "invalid_champions_status_progression"
    prior = pokemon.get("champions_status_progression")
    if isinstance(prior, Mapping) and prior.get("condition_observation") == observation:
        if not valid_progression(prior, owner): return "invalid_prior_champions_status_progression"
        if prior.get("origin_id") != row["origin_id"] or prior.get("established_turn") != row["established_turn"] or row["prior_attempts"] < prior["prior_attempts"] or row["observed_turn"] < prior["observed_turn"]:
            return "stale_champions_status_progression"
        if prior.get("sleep_duration") is not None and row["sleep_duration"] != prior["sleep_duration"]:
            return "champions_sleep_duration_reroll_rejected"
        for key in ("adjusted_duration", "duration_adjustment"):
            if key in prior: row[key] = deepcopy(prior[key])
    pokemon["champions_status_progression"] = row
    return None
