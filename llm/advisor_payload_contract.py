"""Advisor payload contract shared by UI payload builders and tests."""

from __future__ import annotations


ADVISOR_PAYLOAD_MODE = "ui-selected-pokemon-v0.18"

ADVISOR_KNOWN_LIMITATIONS = [
    "Only user-selected moves and explicitly labeled opponent move data are included in the payload.",
    "Empty move slots are omitted.",
    "Move damage estimates, when present, use default assumptions and are not final battle damage.",
    "Every damage estimate includes an assumption_profile that identifies the stat model used.",
    "User-confirmed final stats may be used when stat_profiles provides all six stats.",
    "item_profiles distinguishes unknown, none, system_default_none, and user_confirmed item state.",
    "v0.18 item UI supports Unknown, No item, Choice Band, Choice Specs, Life Orb, Muscle Band, and Wise Glasses only.",
    "Opponent item defaults to unknown unless T1 confirms no item or selects an item.",
    "system_default_none means damage was calculated with a no-item assumption.",
    "Only item effects marked as applied in damage_estimate.item_effects are included in damage numbers.",
    "When item_effects.attacker_item.status is applied, mention that the supported item damage modifier is applied.",
    "If an item damage modifier is applied, describe the estimate as default assumptions plus the supported item modifier, not only default assumptions.",
    "If Life Orb is applied, say Life Orb recoil is not modeled.",
    "If Choice Band or Choice Specs is applied, say choice lock is not modeled.",
    "Type matchup descriptions must use damage_estimate.type_effectiveness when present.",
    "Do not call a move super effective, resisted, or immune unless type_effectiveness explicitly supports it.",
    "Do not print raw type_effectiveness labels like super_effective or not_very_effective; convert them to natural wording.",
    "Choice lock, Life Orb recoil, Choice Scarf speed, Focus Sash survival, and Leftovers recovery are not connected.",
    "Do not infer damage, OHKO/2HKO, or KO chance unless damage data is explicitly provided.",
    "Known opponent moves are user-confirmed only.",
    "Opponent candidate moves are possible Champions moves, not confirmed moves.",
    "Do not assume the opponent has a candidate move unless it appears in known_moves.",
    "Candidate moves may be mentioned as possible threats only when labeled as unconfirmed.",
    "Opponent known move damage estimates, when present, are default-assumption reference values only.",
    "Opponent candidate move damage is not calculated in v0.18.",
    "Selected ability, speed order, and Turn Engine state remain unknown; item state is limited to item_profiles.",
    "Use my_available_moves damage_estimates to compare the user's own move options.",
    "Base stats are species reference data, not EVs or final calculated battle stats.",
    "EV/IV/nature/boosts/weather/terrain/exact HP are not connected in v0.16.",
    "Do not infer EV/IV/nature/item from user-confirmed final stats.",
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

ADVISOR_DEFAULT_ASSUMPTION_PROFILE = {
    "id": "default_level50_ivs31_evs0_neutral_no_item",
    "label": "Default Level 50 / IV 31 / EV 0 / neutral nature / no item",
    "source": "system_default",
    "confidence": "rough_reference",
    "is_user_confirmed": False,
}

ADVISOR_USER_CONFIRMED_FINAL_STATS_PROFILE = {
    "id": "user_confirmed_final_stats_level50",
    "label": "User-confirmed final stats / Level 50",
    "source": "user_input",
    "confidence": "higher_confidence_reference",
    "is_user_confirmed": True,
}

ADVISOR_DEFAULT_WITH_DAMAGE_ITEM_PROFILE = {
    "id": "default_level50_ivs31_evs0_neutral_with_damage_item",
    "label": "Default Level 50 / IV 31 / EV 0 / neutral nature / supported damage item",
    "source": "system_default_and_user_input",
    "confidence": "rough_reference_with_user_confirmed_item",
    "is_user_confirmed": False,
}

ADVISOR_USER_CONFIRMED_FINAL_STATS_WITH_DAMAGE_ITEM_PROFILE = {
    "id": "user_confirmed_final_stats_level50_with_damage_item",
    "label": "User-confirmed final stats / Level 50 / supported damage item",
    "source": "user_input",
    "confidence": "higher_confidence_reference",
    "is_user_confirmed": True,
}

ADVISOR_DAMAGE_LIMITATIONS = [
    "This is not final battle damage.",
    "EV/IV/nature/final stats may be missing or defaulted.",
    "Only supported attacker-side damage item modifiers are applied when item_effects marks them as applied.",
    "Choice lock, recoil, speed, survival, recovery, and other non-damage item effects are not connected.",
    "Use as rough reference only.",
    "OHKO/2HKO/KO chance is not provided in v0.16.",
]

ADVISOR_OPPONENT_DAMAGE_LIMITATIONS = [
    "This is not final battle damage.",
    "Opponent ability, EV/IV/nature, boosts, and final stats may be missing or defaulted.",
    "Only supported attacker-side damage item modifiers are applied when item_effects marks them as applied.",
    "Choice lock, recoil, speed, survival, recovery, and other non-damage item effects are not connected.",
    "Use as rough threat reference only.",
    "OHKO/2HKO/KO chance is not provided in v0.16.",
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
    "full item effects",
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
