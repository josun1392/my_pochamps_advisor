"""Advisor payload contract shared by UI payload builders and tests."""

from __future__ import annotations


ADVISOR_PAYLOAD_MODE = "ui-selected-pokemon-v0.8"

ADVISOR_KNOWN_LIMITATIONS = [
    "Only user-selected moves are included in the payload.",
    "Empty move slots are omitted.",
    "Move data is metadata only; damage calculation is not connected in v0.8.",
    "Do not infer damage, OHKO/2HKO, or KO chance unless damage data is explicitly provided.",
    "Opponent moves may be missing in v0.8.",
    "Base stats are species reference data, not EVs or final calculated battle stats.",
    "EV/IV/nature/items/boosts/weather/terrain/exact HP are not connected in v0.8.",
    "Terastallization is banned in PoChamps and must not be considered.",
    "Do not assume unprovided EVs, IVs, nature, held items, boosts, weather, terrain, exact HP, move sets, or Tera types.",
    "Speed tier, OHKO/2HKO, and survival claims are uncertain unless final stats, items, and damage data are explicitly provided.",
    "Recommendation is based on selected Pokemon identity and available UI state only.",
]

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
    "damage rolls",
    "OHKO/2HKO/KO chance",
    "turn order",
    "speed tie",
    "status duration",
    "Turn Engine state",
]
