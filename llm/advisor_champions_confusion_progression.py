"""Observed, Pokémon-owned Champions confusion episode evidence."""
from copy import deepcopy
from typing import Mapping

SCHEMA = "champions-confusion-progression-v1"
OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def valid_confusion_progression(row, owner):
    try:
        return (isinstance(row, Mapping) and row.get("schema_version") == SCHEMA
                and row.get("owner") == owner and row.get("state") == "confused"
                and isinstance(row.get("origin_id"), str) and bool(row["origin_id"])
                and isinstance(row.get("established_turn"), int) and row["established_turn"] >= 1
                and isinstance(row.get("prior_opportunities"), int) and 0 <= row["prior_opportunities"] <= 4
                and (row.get("duration") is None or row.get("duration") in {2, 3, 4, 5})
                and isinstance(row.get("confusion_observation"), Mapping))
    except (KeyError, TypeError):
        return False


def observe_confusion_progression(*, state, pokemon, event):
    owner = {key: event.get(key) for key in OWNER_KEYS}
    observation = pokemon.get("confusion_provenance", {})
    if owner["session_id"] != state.get("session_id") or event.get("trust") != "user_confirmed_observation":
        return "untrusted_champions_confusion_progression"
    if (pokemon.get("current_confusion") != "confused" or event.get("state") != "confused"
            or observation.get("event_kind") != "current_confusion_observed"
            or observation.get("trust") != "user_confirmed_observation"
            or observation.get("state") != "confused"):
        return "champions_confusion_progression_state_unavailable"
    row = {"schema_version": SCHEMA, "owner": owner, "state": "confused", "origin_id": event.get("origin_id"),
           "established_turn": event.get("established_turn"), "prior_opportunities": event.get("prior_opportunities"),
           "duration": event.get("duration"), "confusion_observation": deepcopy(observation),
           "observed_turn": event.get("turn_number"), "provenance": "observed_champions_confusion_progression_v1"}
    if not valid_confusion_progression(row, owner) or not isinstance(row["observed_turn"], int) or row["observed_turn"] < max(row["established_turn"], observation.get("turn_number", 0)):
        return "invalid_champions_confusion_progression"
    prior = pokemon.get("champions_confusion_progression")
    if isinstance(prior, Mapping) and prior.get("confusion_observation") == observation:
        if not valid_confusion_progression(prior, owner) or prior["origin_id"] != row["origin_id"] or prior["established_turn"] != row["established_turn"] or row["prior_opportunities"] < prior["prior_opportunities"] or row["observed_turn"] < prior["observed_turn"]:
            return "stale_champions_confusion_progression"
        if prior.get("duration") is not None and prior["duration"] != row["duration"]:
            return "champions_confusion_duration_reroll_rejected"
    pokemon["champions_confusion_progression"] = row
    return None
