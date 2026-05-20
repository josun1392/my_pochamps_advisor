"""Advisor payload contract shared by UI payload builders and tests."""

from __future__ import annotations


ADVISOR_PAYLOAD_MODE = "ui-selected-pokemon-v0.10"

ADVISOR_KNOWN_LIMITATIONS = [
    "Only user-selected moves are included in the payload.",
    "Empty move slots are omitted.",
    "Move damage estimates, when present, use default assumptions and are not final battle damage.",
    "Do not infer damage, OHKO/2HKO, or KO chance unless damage data is explicitly provided.",
    "Opponent moves may be missing in v0.8.",
    "Base stats are species reference data, not EVs or final calculated battle stats.",
    "EV/IV/nature/items/boosts/weather/terrain/exact HP are not connected in v0.10.",
    "Terastallization is banned in PoChamps and must not be considered.",
    "Do not assume unprovided EVs, IVs, nature, held items, boosts, weather, terrain, exact HP, move sets, or Tera types.",
    "Speed tier, OHKO/2HKO, KO chance, and survival claims are uncertain unless explicit calculated fields are provided.",
    "Recommendation is based on selected Pokemon identity and available UI state only.",
]

ADVISOR_DAMAGE_ASSUMPTIONS = {
    "level": 50,
    "ivs": "31 all",
    "evs": "0 all",
    "nature": "neutral",
    "item": "none",
    "boosts": "none",
    "weather": "none",
    "terrain": "none",
    "screens": "none",
    "critical": False,
    "doubles": False,
    "ability_effects": "not_applied_unselected",
}

ADVISOR_DAMAGE_LIMITATIONS = [
    "This is not final battle damage.",
    "EV/IV/nature/item/final stats are not connected.",
    "Use as rough reference only.",
    "OHKO/2HKO/KO chance is not provided in v0.10.",
]

ADVISOR_DAMAGE_ESTIMATE_STATUSES = {
    "available_with_default_assumptions",
    "unavailable_missing_move",
    "unavailable_no_selected_move",
    "unavailable_status_move",
    "unavailable_missing_power",
    "unavailable_missing_pokemon",
    "unavailable_missing_base_stats",
    "unavailable_missing_type",
    "unavailable_unsupported_category",
    "unavailable_engine_error",
}

ADVISOR_MISSING_FIELDS = [
    "final calculated stats",
    "EV/IV/nature",
    "held item",
    "selected ability certainty",
    "weather",
    "terrain",
    "stat boosts",
    "exact current HP integer",
    "opponent moves",
    "OHKO/2HKO/KO chance",
    "turn order",
    "speed tie",
    "status duration",
    "Turn Engine state",
]
