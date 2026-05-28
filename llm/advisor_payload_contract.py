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
    "v0.23 item UI uses Champions legal item repository options for normal selection.",
    "Damage-supported but non-legal/debug items are not normal item selector options.",
    "Legal items and modeled item effects are separate concepts.",
    "Legal-but-not-modeled items may be user-confirmed, but their effects are not applied unless item_effects marks them applied.",
    "Opponent item defaults to unknown unless T1 confirms no item or selects an item.",
    "system_default_none means damage was calculated with a no-item assumption.",
    "speed_context, when present, is raw/effective Speed comparison only and is not final turn order.",
    "Raw/effective Speed comparison is available only when both active Pokemon have user-confirmed final Speed in v0.30.",
    "Default Speed fallback is not used in v0.30.",
    "Do not say a Pokemon will move first when speed_context.is_final_turn_order is false.",
    "Use wording such as based on raw Speed only or appears faster by raw Speed for speed_context comparisons.",
    "effective_speed, when present, is a supported speed modifier estimate and is not final turn order.",
    "Choice Scarf speed may be applied in speed_context only when the item is user-confirmed.",
    "Choice lock remains not modeled when a user-confirmed Choice item is applied.",
    "If raw_speed and effective_speed disagree, explain the difference without guaranteeing action order.",
    "Only item effects marked as applied in damage_estimate.item_effects are included in damage numbers.",
    "When item_effects.attacker_item.status is applied, mention that the supported item damage modifier is applied.",
    "Type boosting item damage is included only when item_effects.attacker_item.status is applied.",
    "Do not say a type boosting item boosted damage when the move type does not match or the item is unsupported.",
    "Legal item selection does not imply the selected item has a modeled effect.",
    "Fairy Feather is legal but not damage-modeled until a catalog-backed modifier exists.",
    "If an item damage modifier is applied, describe the estimate as default assumptions plus the supported item modifier, not only default assumptions.",
    "If Life Orb is applied, say Life Orb recoil is not modeled.",
    "If Choice Scarf, Choice Band, or Choice Specs is applied, say choice lock is not modeled.",
    "Do not mention choice lock for non-Choice items such as Charcoal, Mystic Water, Black Belt, Metal Coat, Sharp Beak, Fairy Feather, Leftovers, or Focus Sash.",
    "Type matchup descriptions must use damage_estimate.type_effectiveness when present.",
    "Do not call a move super effective, resisted, or immune unless type_effectiveness explicitly supports it.",
    "Do not print raw type_effectiveness labels like super_effective or not_very_effective; convert them to natural wording.",
    "Life Orb recoil, Focus Sash survival, and Leftovers recovery are not connected.",
    "Do not infer damage, OHKO/2HKO, or KO chance unless damage data is explicitly provided.",
    "Known opponent moves are user-confirmed only.",
    "Opponent candidate moves are possible Champions moves, not confirmed moves.",
    "Do not assume the opponent has a candidate move unless it appears in known_moves.",
    "Candidate moves may be mentioned as possible threats only when labeled as unconfirmed.",
    "Opponent known move damage estimates, when present, are default-assumption reference values only.",
    "Opponent candidate move damage is not calculated in v0.18.",
    "opponent_assumptions, when present, contains possible opponent profiles, not confirmed sets.",
    "opponent_assumptions.calculation_usage context_only means samples are not used directly for damage or speed calculations.",
    "When opponent_assumptions.available is true and possible_samples exist, briefly mention that possible sample context exists when relevant.",
    "When possible sample context is mentioned, keep it to at most one short limitation sentence.",
    "Do not dump sample_id, full stats, source metadata, update_policy, coverage_probability, or full Top-K sample lists into the response.",
    "When opponent_assumptions.available is false, do not invent samples or force a sample limitation.",
    "Do not describe sample_assumed opponent samples as user-confirmed information.",
    "Do not interpret prior_probability null as zero probability.",
    "Do not claim Top-K omitted opponent sample archetypes are impossible.",
    "Do not infer final turn order, KO, survival, or exact stats from possible opponent samples.",
    "Priority, Tailwind, Trick Room, paralysis, Speed stages, selected ability speed effects, final action order, and Turn Engine state remain unknown.",
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
    "Recoil, speed, survival, recovery, and other non-damage item effects are not connected unless a specific supported field says otherwise.",
    "Use as rough reference only.",
    "OHKO/2HKO/KO chance is not provided in v0.16.",
]

ADVISOR_OPPONENT_DAMAGE_LIMITATIONS = [
    "This is not final battle damage.",
    "Opponent ability, EV/IV/nature, boosts, and final stats may be missing or defaulted.",
    "Only supported attacker-side damage item modifiers are applied when item_effects marks them as applied.",
    "Recoil, speed, survival, recovery, and other non-damage item effects are not connected unless a specific supported field says otherwise.",
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
