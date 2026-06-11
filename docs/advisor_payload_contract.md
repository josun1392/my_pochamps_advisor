# Advisor Payload Contract

**Milestone:** v0.38 - Opponent Possible Sample Payload
**Payload mode:** `ui-selected-pokemon-v0.18`
**Status:** Current contract for the PySide6 UI to Gemini LLM advisor path.

## Purpose

The advisor payload is the boundary between deterministic UI / engine state and the Gemini natural-language recommendation layer. This contract prevents the LLM from treating incomplete UI metadata as confirmed battle math.

The current app can send selected Pokemon identity, HP percent, user-confirmed move metadata, optional user-confirmed final stats for the active Pokemon, top-level item profiles, context-only opponent sample assumptions, raw/effective Speed comparison context, limited Quick Claw speed-order item context, limited Light Ball species-stat item context, damage estimates for the user's confirmed moves, additive limited KO context, explicitly labeled opponent move information, and damage estimates for user-confirmed opponent known moves. Every damage estimate includes an `assumption_profile` describing the stat/item model used. Supported attacker-side damage items may be applied only when `damage_estimate.item_effects` marks them as applied. v0.23 connects the normal item selector to the Champions legal item repository: normal UI options include Unknown, No item, and legal fixture items. Damage-supported but non-legal/debug items such as Choice Band, Choice Specs, and Life Orb are not normal selector options. v0.28 adds `speed_context` for raw Speed comparison only when both active Pokemon have user-confirmed final Speed. v0.30 extends `speed_context` with Choice Scarf effective Speed when Choice Scarf is user-confirmed. v0.98 adds move-level `speed_order_context` for user-confirmed legal Quick Claw as limited advice context only. v1.3 adds move-level `species_stat_item_context` for user-confirmed legal Light Ball on Pikachu as limited explanatory context only. v0.38 adds `opponent_assumptions` as context-only possible opponent sample profiles. The app does not yet send EV/IV/nature breakdowns, final battle KO truth, final turn order, candidate move damage estimates, sample-based damage or Speed calculations, or Turn Engine state.

## Current Payload Shape

Top-level sections:

- `scenario`
- `pokemon`
- `stat_profiles`
- `item_profiles`
- `opponent_assumptions`
- `speed_context`
- `moves`
- `opponent_moves`

`scenario` contains:

- `mode`: currently `ui-selected-pokemon-v0.18`
- `format_note`: explains that this is selected Pokemon identity plus default-assumption user-confirmed move estimates and opponent move context, not full battle state
- `known_limitations`: guardrails the prompt and UI must preserve

`pokemon.my_active` and `pokemon.opponent_active` contain:

- `slot_index`
- `name_en`
- `name_ko`
- `types`
- `types_ko`
- `base_stats`
- `abilities`
- `abilities_ko`
- `hp_percent`
- `selected_move_index`

`stat_profiles` contains:

- `my_active`
- `opponent_active`

Each active stat profile contains:

- `status`: `default_assumption` or `user_confirmed_final_stats`
- `source`: `system_default` or `user_input`
- `level`
- `final_stats`
- `evs`
- `ivs`
- `nature`
- `item`
- `notes`

`item_profiles` contains:

- `my_active`
- `opponent_active`

Each active item profile contains:

- `status`: `unknown`, `none`, `system_default_none`, or `user_confirmed`
- `source`
- `item_id`
- `name_en`
- `name_ko`
- `effects_scope`
- `damage_modifier_status`
- `notes`

In v0.23 the UI can emit `system_default_none`, `unknown`, `none`, or `user_confirmed` item profiles for active Pokemon. My active defaults to `system_default_none` for compatibility with the previous no-item calculation assumption. Opponent active defaults to `unknown` unless T1 confirms no item or selects a legal item from the repository-backed selector.

`opponent_assumptions` contains possible opponent sample profiles for the active opponent species. It is context-only in v0.38 and is not confirmed battle information.

When samples are available, `opponent_assumptions` contains:

- `mode`: `multi_sample_assumption_v0.38`
- `schema_version`: current payload shape, currently `opponent_assumptions_v0.47`
- `metadata_version`: current `possible_samples` metadata shape, currently `minimal_metadata_v1`
- `available`: `true`
- `scope`: `opponent_active`
- `is_confirmed_information`: always `false`
- `calculation_usage`: `context_only`
- `payload_features`: developer/debug feature flags
- `opponent_active.species_id`
- `opponent_active.known_status`: currently `not_confirmed`
- `opponent_active.is_user_confirmed`: `false`
- `opponent_active.user_confirmed_fields`: currently `{}`
- `opponent_active.possible_samples`
- `opponent_active.samples_meta`
- `opponent_active.observation_history`: currently `[]`
- `opponent_active.update_policy.mode`: `static`
- `limitations`

`mode` is a historical behavior label. It remains `multi_sample_assumption_v0.38` for compatibility. `schema_version` describes the current payload shape, and `metadata_version` describes the minimal metadata shape inside `possible_samples`. These version fields are additive developer/contract metadata. The LLM should not mention version fields in user-facing battle advice.

`payload_features` currently contains:

- `possible_samples`: `true`
- `minimal_metadata`: `true`
- `debug_summary_supported`: `true`
- `full_stats_excluded`: `true`
- `damage_speed_integration`: `false`

Each `possible_samples` entry contains:

- `sample_id`
- `species_id`
- `label_en`
- `label_ko`
- `source`: `sample_assumed`
- `source_type`
- `confidence`
- `prior_probability`: currently `null`
- `prior_probability_type`: `not_available`
- `evidence_basis`
- `is_user_confirmed`: `false`
- `possible_item`
- `role`: estimated sample role when available
- `archetype_id`: estimated sample archetype label when available
- `possible_items`: possible item assumptions, not confirmed held items
- `calculation_usage`: `context_only`
- `limitations`

`possible_samples` deliberately excludes full stats, SP distribution, source URL, source note, long reviewer notes, and full source metadata. Role, archetype, and possible item metadata are context-only labels. They must not be treated as confirmed opponent role, confirmed opponent item, damage calculation input, or Speed calculation input.

`samples_meta` contains:

- `total_known_archetypes`
- `included_top_k`
- `default_top_k`: `3`
- `coverage_probability`: currently `null`
- `coverage_probability_type`: `not_available`
- `omitted_archetypes_note`

When samples are unavailable, `opponent_assumptions.available` is `false` and `reason` is one of:

- `no_samples_for_species`
- `opponent_active_missing`
- `repository_unavailable`

The LLM must not invent possible samples when `available` is `false`.

`opponent_assumptions.calculation_usage` is `context_only` in v0.38:

- possible samples are not used by `damage_estimate`
- possible samples are not used by `speed_context`
- possible samples do not provide KO, OHKO, 2HKO, survival, or final turn order
- `prior_probability: null` means the prior is unavailable, not zero probability
- Top-K omission does not mean omitted archetypes are impossible

`speed_context` contains raw and supported effective Speed comparison metadata. It is not final turn order.

When both active Pokemon have user-confirmed final stats with `spe`, `speed_context` contains:

- `mode`: `choice_scarf_effective_speed_v0.30`
- `available`: `true`
- `my_active.raw_speed`
- `my_active.effective_speed`
- `my_active.source`: `user_confirmed_final_stats`
- `my_active.is_user_confirmed`
- `my_active.speed_modifiers`
- `opponent_active.raw_speed`
- `opponent_active.effective_speed`
- `opponent_active.source`: `user_confirmed_final_stats`
- `opponent_active.is_user_confirmed`
- `opponent_active.speed_modifiers`
- `comparison.raw_speed_relation`: `my_active_faster`, `opponent_active_faster`, or `speed_tie`
- `comparison.raw_speed_margin`
- `comparison.raw_speed_tie`
- `comparison.effective_speed_relation`
- `comparison.effective_speed_margin`
- `comparison.effective_speed_tie`
- `comparison.speed_margin`: raw Speed margin compatibility alias
- `comparison.speed_tie`: raw Speed tie compatibility alias
- `limitations`
- `is_final_turn_order`: always `false`

When either active Pokemon is missing user-confirmed final Speed, `speed_context` contains:

- `mode`: `choice_scarf_effective_speed_v0.30`
- `available`: `false`
- `reason`: `insufficient_confirmed_final_stats`
- `limitations`
- `is_final_turn_order`: always `false`

Default Speed fallback is not used in v0.30.

`moves` contains:

- `my_selected_move_index`
- `my_available_moves`
- `my_selected_move`
- `opponent_available_moves`
- `opponent_selected_move`
- `opponent_selected_move_index`
- `move_data_status`
- `notes`

`moves.opponent_available_moves` remains a legacy compatibility field and is empty in v0.18. New opponent move semantics live in `opponent_moves`.

`opponent_moves` contains:

- `status`
- `known_moves`
- `candidate_moves`
- `candidate_moves_limit`
- `candidate_source_status`
- `unknown_moves`
- `limitations`

User-confirmed move entries contain:

- `slot`
- `move_id`
- `name_en`
- `name_ko`
- `type`
- `category`
- `power`
- `accuracy`
- `pp`
- `damage_estimate` on each user-confirmed entry in `moves.my_available_moves`
- `damage_estimate` on `moves.my_selected_move`
- `damage_estimate` on each user-confirmed entry in `opponent_moves.known_moves`

Each move `damage_estimate` contains:

- `status`
- `scope`
- `is_final_battle_damage`
- `assumption_profile`
- `item_effects`
- `target` when the estimate is for opponent known move damage against `my_active`
- `selected_move_id` when available
- `damage_range` when available
- `percent_range` when available
- `type_effectiveness` when available
- `rolls` when available
- `assumptions`
- `derived_stats` when available
- `limitations`

## Opponent Move Semantics

Opponent move data is split into separate categories:

- `known_moves`: moves the user directly confirmed in the opponent Q/W/E/R slots. These are the only confirmed opponent moves.
- `candidate_moves`: possible moves from the Serebii-derived Champions movepool cache. These include `confidence: "possible_not_confirmed"` and are not the opponent's known moveset.
- `unknown_moves`: explicit state for missing or partial opponent move information.

Opponent candidate moves are capped by `candidate_moves_limit`. Known opponent moves may include `damage_estimate` in v0.18 when they are user-confirmed moves. Candidate moves do not include `damage_estimate` in v0.18.
Candidate moves may be mentioned as possible threats only when clearly labeled as unconfirmed. The advisor should use `my_available_moves[*].damage_estimate` to compare the user's own move options.
Opponent known move damage estimates use `target: "my_active"` and are rough threat references only.

## Item Semantics

Item state is separate from stat state:

- `unknown`: the item is not known.
- `none`: the user confirmed no held item.
- `system_default_none`: the calculation assumes no held item by default.
- `user_confirmed`: the user or a test/helper payload supplied an item.

`unknown` and `none` must not be treated as the same thing.

The normal v0.23 selector is legal-item based. Legal item and modeled item are separate concepts:

- `legal_but_not_modeled`: selectable as user-confirmed item information, but the item effect does not change damage.
- `legal_and_damage_supported`: recognized by the legal fixture as having local damage support, but damage still counts the item only when `damage_estimate.item_effects` marks the effect as `applied`.
- `damage_supported_but_not_champions_legal`: debug/test only and not exposed in the normal selector.

The legacy damage-test subset remains available to tests/helpers, not the normal legal selector:

- `choice-band`: physical move damage modifier only
- `choice-specs`: special move damage modifier only
- `life-orb`: damage modifier only
- `muscle-band`: physical move damage modifier only
- `wise-glasses`: special move damage modifier only

Legal catalog-backed type boosting items may apply as attacker-side damage modifiers:

- when `item_profiles.<attacker>.status` is `user_confirmed`
- when the item is a Champions legal `type_boosting_item`
- when a local catalog-backed damage modifier exists
- when the move type matches the item's boosted type

When applied, these items use a `1.2x` damage modifier and `damage_estimate.item_effects.attacker_item.status` is `applied`.
When the move type does not match the boosted type, `status` is `not_applicable` and damage is unchanged.
When a legal item such as Fairy Feather has no catalog-backed damage modifier, `status` is `unsupported_item` and damage is unchanged.

Excluded from v0.30 item application:

- Expert Belt
- Assault Vest
- Choice lock
- Life Orb recoil
- candidate move damage

Legal item modeling examples:

- Choice Scarf: selectable; its supported speed modifier may be applied in `speed_context` when user-confirmed, but speed order and Choice Scarf choice lock are not modeled.
- Focus Sash: selectable; its limited survival context may be included only when user-confirmed and full HP. It is not damage reduction and does not change raw damage estimates.
- Focus Band: selectable; its limited survival context may be included only when user-confirmed and the raw incoming hit is potentially lethal. Survival is not guaranteed, and activation probability is not calculated.
- Leftovers / Sitrus Berry: selectable; limited recovery context may be included only when user-confirmed and max HP is available. Exact turn sequencing and item consumption are not modeled.
- Quick Claw: selectable; limited `speed_order_context` may be included only when user-confirmed and Champions legal. Activation probability and final move order are not calculated.
- Light Ball: selectable; limited `species_stat_item_context` may be included only when user-confirmed, Champions legal, local species-stat metadata exists, and the holder species is Pikachu. It is explanatory and does not create a new damage formula or KO path.

### Legal Item Gate

User-facing modeled item contexts require Champions legal item coverage from `data/static/champions_legal_items.json`.

The following are not legal coverage sources by themselves:

- `data/static/items.json`
- `data/static/items_damage.json`
- context helper existence
- engine/debug metadata
- `data/static/charge_moves.json`

If an item is user-confirmed but absent from the Champions legal item fixture, the payload must not emit a modeled item context for that item. The stable unavailable reason is `blocked_by_legal_item_coverage`.

Loaded Dice is currently implemented as future-only multi-hit context support but is blocked from user-facing modeled context until Loaded Dice legal coverage is confirmed. Power Herb remains blocked; `charge_moves.json` is move metadata and does not establish Power Herb legality.

Blocked or future-only item reasons are developer/debug/contract metadata, not normal user-facing advice content. When an item is blocked by legal coverage, the LLM should not include the blocked item effect in the default recommendation text, mention the blocked item name, say "user-confirmed Loaded Dice," say "Power Herb," say "Loaded Dice is not modeled," say "Power Herb is not modeled," or say the blocked item effect is not included. It should also avoid generic substitutes such as "the user-confirmed item effect," "held item effect," "selected item effect," or "item-based limitation." The default response should not mention that a blocked item exists by saying its effect is absent, ignored, unavailable, excluded, unsupported, or outside the estimate. The response must not imply blocked or future-only items are available in Champions.

If the user explicitly asks about a blocked item, the LLM may give only a short explanation that Champions legal coverage is not confirmed, so the item effect is not reflected in advice. It must not calculate, strategize around, or imply availability for the blocked item.

`damage_estimate.item_effects` is the source of truth for whether an item effect was applied to a specific calculation.

When `damage_estimate.item_effects.attacker_item.status` is `applied`, the LLM should explicitly mention that the supported item damage modifier is included in that estimate. It should describe the number as being calculated under the stated assumptions plus the supported item modifier, not as only default assumptions. Non-damage item effects remain unmodeled.

If Life Orb is applied, the LLM should say the damage modifier is applied and Life Orb recoil is not modeled. If Choice Scarf, Choice Band, or Choice Specs is applied, the LLM should say the relevant supported effect is applied and choice lock is not modeled.

For type boosting items, the LLM should say the damage modifier is included only when `damage_estimate.item_effects.attacker_item.status` is `applied`. It must not say the item boosted damage when the move type does not match, when the item is unsupported, or merely because the item is legal. Fairy Feather should be described as legal but not damage-modeled until a catalog-backed modifier exists.

## Type Boost Context Semantics

`type_boost_context` is an additive limited context for user-confirmed Champions legal type-boosting items whose catalog metadata supports a matching move type. It is never nested inside `damage_estimate` or `ko_context`.

The context is explanatory: it surfaces the same supported item relationship that `damage_estimate.item_effects` already uses when applicable. It does not create a new damage formula path, does not recalculate raw damage rolls, and does not add type-boost-adjusted KO/OHKO/2HKO context.

Available type boost context requires:

- attacker item profile must be `status: user_confirmed`
- item must pass Champions legal item coverage
- item category must be `type_boosting_item`
- item effect support status must be `legal_and_damage_supported`
- item must exist in `items_damage.json` `type_boost_items`
- move type must be known
- move type must match the item boosted type

The first supported scope is the legal damage-supported type-boosting item set:

- `black-belt`
- `black-glasses`
- `charcoal`
- `dragon-fang`
- `hard-stone`
- `magnet`
- `metal-coat`
- `miracle-seed`
- `mystic-water`
- `never-melt-ice`
- `poison-barb`
- `sharp-beak`
- `silk-scarf`
- `silver-powder`
- `soft-sand`
- `spell-tag`
- `twisted-spoon`

Excluded items:

- `fairy-feather`: Champions legal, but no catalog-backed damage metadata/helper support yet.
- `odd-incense`, `rose-incense`, `sea-incense`, `wave-incense`: present in `items_damage.json`, but not confirmed as Champions legal items in `champions_legal_items.json`.

Available context may include:

- `mode`: `limited_type_boost_context`
- `available`: `true`
- `attacker_side`: `my_active` or `opponent_active`
- `item.item_id`: the item id
- `item.status`: `user_confirmed`
- `item.legal_status`: `legal_modeled`
- `type_boost_effect.boosted_type`: boosted type from `items_damage.json`
- `type_boost_effect.move_type`: move type
- `type_boost_effect.effect_label`: `may_boost_matching_type_move`
- `type_boost_effect.formula_label`: `type_boost_limited_damage_modifier_context`
- `type_boost_effect.damage_estimate_item_effect_status`: the related `damage_estimate.item_effects.attacker_item.status`
- `type_boost_effect.raw_damage_rolls_changed`: `false`
- `type_boost_effect.ko_context_changed`: `false`
- `type_boost_effect.type_boost_adjusted_ko_integrated`: `false`
- `type_boost_effect.type_boost_adjusted_ohko_2hko_integrated`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_type_boost_item`
- `item_not_user_confirmed`
- `blocked_by_legal_item_coverage`
- `not_type_boosting_item`
- `type_boost_metadata_missing`
- `boosted_type_missing`
- `move_type_missing`
- `move_type_does_not_match_boosted_type`
- `damage_estimate_missing`

When `type_boost_context.available` is true, the note should stay concise. The LLM may say the user-confirmed item may boost matching-type moves and that the damage estimate may already include the supported item modifier when applicable. It should not say the context is final battle truth.

The LLM must not say:

- "This guarantees KO."
- "This secures the KO."
- "Boosted damage proves the KO."
- "This is final damage."
- "The type-boost-adjusted KO chance is 70%."

If `type_boost_context.available` is false in the enriched/debug payload, the default advice payload should omit `type_boost_context`. The unavailable reason is developer/debug/contract metadata only. The LLM should not mention the unavailable type-boost item name, effect, or reason in default advice unless the user explicitly asks about that item.

For non-Choice items such as Charcoal, Mystic Water, Black Belt, Metal Coat, Sharp Beak, Fairy Feather, Light Ball, Leftovers, Focus Sash, or Focus Band, the LLM must not say choice lock is not modeled. Choice lock is relevant only to Choice Scarf, Choice Band, and Choice Specs.

## Species Stat Item Context Semantics

`species_stat_item_context` is an additive limited context for species-specific stat items that already have local metadata and damage-helper support. It is never nested inside `damage_estimate` or `ko_context`.

In v1.3, modeled species-stat item context is limited to Light Ball:

- attacker item profile must be `status: user_confirmed`
- attacker item id must be `light-ball`
- attacker item must pass Champions legal item coverage
- `items_damage.json` must provide `species_stat_items.light-ball` metadata
- holder species must normalize to `pikachu`
- move must be a damaging move with physical or special category metadata

The context is explanatory: `damage_estimate.item_effects` remains the source of truth for whether a supported item modifier was applied to a specific estimate. `species_stat_item_context` does not create a new damage formula path, does not recalculate raw damage rolls, does not change Q12 multipliers, and does not add Light-Ball-adjusted KO/OHKO/2HKO context.

Available context may include:

- `mode`: `limited_species_stat_item_context`
- `available`: `true`
- `attacker_side`: `my_active` or `opponent_active`
- `item.item_id`: `light-ball`
- `item.status`: `user_confirmed`
- `item.legal_status`: `legal_modeled`
- `species_stat_effect.holder_species_id`: `pikachu`
- `species_stat_effect.supported_species`: `["pikachu"]`
- `species_stat_effect.boosted_stats`: stat ids from local metadata
- `species_stat_effect.effect_label`: `may_boost_pikachu_offensive_stats`
- `species_stat_effect.formula_label`: `species_stat_item_limited_modifier_context`
- `species_stat_effect.damage_estimate_item_effect_status`: the related `damage_estimate.item_effects.attacker_item.status`
- `species_stat_effect.raw_damage_rolls_changed`: `false`
- `species_stat_effect.ko_context_changed`: `false`
- `species_stat_effect.species_stat_adjusted_ko_integrated`: `false`
- `species_stat_effect.species_stat_adjusted_ohko_2hko_integrated`: `false`
- `species_stat_effect.final_stats_inferred`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `damage_estimate_missing`
- `move_category_missing_or_unsupported`
- `no_species_stat_item`
- `item_not_user_confirmed`
- `not_species_stat_item`
- `blocked_by_legal_item_coverage`
- `species_stat_metadata_missing`
- `supported_species_missing`
- `holder_species_missing`
- `holder_species_not_supported`
- `boosted_stats_missing`

When `species_stat_item_context.available` is true, the LLM should say Light Ball is a Pikachu-specific offensive item context and may boost Pikachu's offensive stats in the underlying calculation when `damage_estimate.item_effects` marks the supported modifier as applied. It should not say Light Ball is not included or not modeled when the available context is present. It should not generalize Light Ball to non-Pikachu holders, and it should not treat the context as final stat truth or a final KO guarantee.

The LLM must not say:

- "Light Ball is not included."
- "Light Ball is not modeled."
- "Light Ball guarantees KO."
- "Light Ball always doubles damage."
- "Confirmed OHKO because of Light Ball."
- "All Electric-type Pokemon benefit from Light Ball."
- "Light Ball works on any holder."
- "Final stats are fully known."
- "Exact EV/IV/nature-adjusted stats are known."

If `species_stat_item_context.available` is false in the enriched/debug payload, the default advice payload should omit `species_stat_item_context`. The unavailable reason is developer/debug/contract metadata only. The LLM should not mention Light Ball, non-Pikachu mismatch, unsupported reason, missing metadata, or not-modeled wording in default advice unless the user explicitly asks about that item.

## Survival Context Semantics

`survival_context` is an additive limited context next to a relevant `damage_estimate`. It does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, or item damage modifier math.

In v0.96, modeled survival contexts are limited Focus Sash and limited Focus Band context:

Shared rules:

- defender item profile must be `status: user_confirmed`
- defender item must pass Champions legal item coverage
- incoming raw damage must have `max >= current_hp` or an equivalent limited HP reference
- `min >= current_hp` is represented separately as `guaranteed_lethal_without_item`
- raw damage rolls are unchanged
- `ko_context` is unchanged
- KO/OHKO/2HKO estimates do not include survival item activation
- final survival probability is not calculated
- item consumption and turn sequencing are not modeled

Focus Sash-specific rules:

- defender item profile must be `status: user_confirmed`
- defender item id must be `focus-sash`
- defender HP must be full by exact HP or `hp_percent == 100`
- incoming damage must have `max >= current_hp`
- `min >= current_hp` is represented separately as `guaranteed_lethal_without_item`

Available Focus Sash context may include:

- `mode`: `limited_item_survival_context`
- `available`: `true`
- `defender_side`: `my_active` or `opponent_active`
- `item.item_id`: `focus-sash`
- `item.status`: `user_confirmed`
- `current_hp_is_full`: `true`
- `incoming_damage.could_be_lethal_without_item`
- `incoming_damage.guaranteed_lethal_without_item`
- `survival_effect.type`: `focus_sash`
- `survival_effect.may_survive_at_1_hp`: `true`
- `survival_effect.raw_damage_rolls_changed`: `false`
- `is_final_battle_truth`: `false`

Focus Band-specific rules:

- defender item id must be `focus-band`
- defender HP does not need to be full
- incoming raw damage must be potentially lethal without the item
- activation probability is not calculated
- final survival probability is not calculated
- Focus Band is not damage reduction and does not change KO probability

Available Focus Band context may include:

- `mode`: `limited_item_survival_context`
- `available`: `true`
- `defender_side`: `my_active` or `opponent_active`
- `item.item_id`: `focus-band`
- `item.status`: `user_confirmed`
- `incoming_damage.could_be_lethal_without_item`
- `incoming_damage.guaranteed_lethal_without_item`
- `incoming_damage.hp_reference_source`
- `survival_effect.type`: `focus_band`
- `survival_effect.effect_label`: `may_occasionally_survive_lethal_hit`
- `survival_effect.survival_is_not_guaranteed`: `true`
- `survival_effect.activation_probability_calculated`: `false`
- `survival_effect.final_survival_probability_integrated`: `false`
- `survival_effect.raw_damage_rolls_changed`: `false`
- `survival_effect.ko_context_changed`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_focus_sash`
- `item_not_user_confirmed`
- `hp_not_full`
- `hp_unknown`
- `damage_not_lethal`
- `multi_hit_not_supported`
- `damage_estimate_missing`
- `defender_max_hp_missing`
- `unsupported_turn_engine_required`

The LLM may say:

- "Focus Sash may allow survival at 1 HP if the Pokemon is at full HP, but this is limited context and does not change the raw damage estimate."
- "Without considering Focus Sash, the damage range could be lethal; with a user-confirmed Focus Sash and full HP, survival at 1 HP is possible under limited assumptions."
- "Focus Sash survival is limited context; multi-hit moves, hazards, chip damage, and exact turn sequencing are not modeled."
- "This Focus Sash note assumes single-hit damage from full HP; multi-hit, hazards, chip damage, and turn sequencing are not modeled."
- "Focus Band may occasionally let the Pokemon survive an otherwise lethal hit, but survival is not guaranteed."
- "Raw damage and KO estimates do not include Focus Band activation."
- "Focus Band activation probability and final survival probability are not calculated."

When `survival_context.available` is `true`, the LLM should include one concise limitation sentence. The limitation should stay short and should not become longer than the recommendation.

If `survival_context.available` is false, or no `survival_context` is present for a move, the LLM should not invent Focus Sash or Focus Band survival, should not mention unavailable reasons, and should not force the survival limitation sentence. The default advice payload should omit unavailable `survival_context`; enriched/debug payload may retain the reason.

The LLM must not say:

- "Focus Sash reduces the damage."
- "Focus Band reduces the damage."
- "The Pokemon definitely survives."
- "The Pokemon will survive."
- "Focus Sash guarantees survival in this turn."
- "Focus Band guarantees survival in this turn."
- "Focus Band confirms survival."
- "Focus Band means it is safe to take the hit."
- "Focus Band activation is included in KO chance."
- "The final survival probability is 10%."
- "Focus Sash applies when the item is unknown or unconfirmed."
- "Focus Band applies when the item is unknown or unconfirmed."
- "Focus Sash handles multi-hit moves, hazards, residual damage, weather/status chip, ability interactions, or exact turn sequencing."

Candidate moves do not receive `damage_estimate`, `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, `multi_hit_context`, `type_boost_context`, `species_stat_item_context`, `speed_order_context`, `resist_berry_context`, `chilan_berry_context`, or `ko_context`.

## Recovery Context Semantics

`recovery_context` is an additive limited context next to a relevant `damage_estimate`. It does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, or item damage modifier math.

`ko_context` is unchanged by `recovery_context`. KO/OHKO/2HKO estimates do not include recovery. The LLM may mention recovery as a follow-up limitation, but it must not say the raw KO chance already includes Sitrus Berry or Leftovers.

In v0.60, the only modeled recovery context is limited Sitrus Berry / Leftovers context:

- defender item profile must be `status: user_confirmed`
- defender item id must be `sitrus-berry` or `leftovers`
- defender max HP must be available
- recovery amount is max-HP formula based
- exact activation timing is not final battle truth
- item consumption is not tracked

Available Sitrus Berry context may include:

- `mode`: `limited_item_recovery_context`
- `available`: `true`
- `defender_side`: `my_active` or `opponent_active`
- `item.item_id`: `sitrus-berry`
- `item.status`: `user_confirmed`
- `recovery_effect.type`: `sitrus_berry`
- `recovery_effect.timing`: `threshold_or_after_damage_limited`
- `recovery_effect.estimated_recovery_hp`
- `recovery_effect.formula_label`: `floor(max_hp / 4)`
- `recovery_effect.raw_damage_rolls_changed`: `false`
- `recovery_effect.ko_context_changed`: `false`
- `is_final_battle_truth`: `false`

Available Leftovers context may include:

- `mode`: `limited_item_recovery_context`
- `available`: `true`
- `defender_side`: `my_active` or `opponent_active`
- `item.item_id`: `leftovers`
- `item.status`: `user_confirmed`
- `recovery_effect.type`: `leftovers`
- `recovery_effect.timing`: `end_of_turn_limited`
- `recovery_effect.estimated_recovery_hp`
- `recovery_effect.formula_label`: `floor(max_hp / 16)`
- `recovery_effect.raw_damage_rolls_changed`: `false`
- `recovery_effect.ko_context_changed`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_recovery_item`
- `item_not_user_confirmed`
- `defender_max_hp_missing`
- `unsupported_recovery_item`
- `damage_estimate_missing`
- `turn_engine_required`

The LLM may say:

- "Leftovers may affect follow-up KO/2HKO under limited assumptions, but exact end-of-turn recovery and sequencing are not modeled."
- "Sitrus Berry recovery is shown as limited context only and does not change the raw damage or KO estimate."
- "The raw KO estimate does not include recovery; recovery_context is a separate limited note."
- "This recovery note does not change the raw damage estimate or the limited KO context."

The LLM must not say:

- "This always becomes a 3HKO after Leftovers."
- "Sitrus definitely activates here."
- "The KO chance already includes recovery."
- "Leftovers has been fully simulated."
- "Recovery changes the raw damage rolls."
- "Recovery changes ko_context."
- "Recovery applies when the item is unknown or unconfirmed."

When `recovery_context.available` is true, the recovery note should stay concise, ideally one or two sentences, and should mention that exact activation timing, item consumption, and turn sequencing are not modeled. It should not become longer than the recommendation.

Candidate moves do not receive `damage_estimate`, `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, `multi_hit_context`, `speed_order_context`, or `ko_context`.

## Accuracy Context Semantics

`accuracy_context` is an additive limited context for move hit reliability. It is never nested inside `damage_estimate` or `ko_context`.

`accuracy_context` does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, item damage modifier math, or `ko_context`.

In v0.63, the only modeled accuracy context is limited Bright Powder context:

- defender item profile must be `status: user_confirmed`
- defender item id must be `bright-powder`
- move accuracy metadata must be available
- final hit probability is not calculated
- hit-adjusted KO probability is not calculated
- exact accuracy/evasion stage math is not modeled
- ability/weather interactions, multi-hit accuracy, and turn sequencing are not modeled
- raw damage and KO/OHKO/2HKO estimates do not include hit chance

Available Bright Powder context may include:

- `mode`: `limited_accuracy_context`
- `available`: `true`
- `defender_side`: `my_active` or `opponent_active`
- `item.item_id`: `bright-powder`
- `item.status`: `user_confirmed`
- `move_accuracy.base_accuracy`
- `move_accuracy.accuracy_source`: `move_metadata`
- `move_accuracy.accuracy_known`: `true`
- `accuracy_effect.type`: `bright_powder`
- `accuracy_effect.effect_label`: `may_reduce_hit_reliability`
- `accuracy_effect.formula_label`: `bright_powder_limited_modifier`
- `accuracy_effect.raw_damage_rolls_changed`: `false`
- `accuracy_effect.ko_context_changed`: `false`
- `accuracy_effect.hit_probability_integrated`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_bright_powder`
- `item_not_user_confirmed`
- `move_accuracy_missing`
- `unsupported_accuracy_item`
- `accuracy_engine_missing`
- `turn_engine_required`
- `damage_estimate_missing`

The LLM may say:

- "Bright Powder may reduce hit reliability under limited accuracy context, but the raw damage and KO estimates do not include hit chance."
- "The move can KO by raw damage rolls, but accuracy and Bright Powder effects are not integrated into that KO chance."
- "This is not a final hit probability; accuracy/evasion stages, ability interactions, weather, multi-hit accuracy, and turn sequencing are not modeled."
- "Final hit probability is not calculated, and hit-adjusted KO probability is not available."

The LLM must not say:

- "The damage is reduced by Bright Powder."
- "This move will miss."
- "This move is guaranteed to miss."
- "The KO chance already accounts for Bright Powder."
- "The final hit probability is confirmed."
- "The hit-adjusted KO chance is 70%."
- "Bright Powder applies when the item is unknown or unconfirmed."

When `accuracy_context.available` is true, the accuracy note should stay concise, ideally one or two sentences, and should mention that raw damage and KO/OHKO/2HKO estimates do not include hit chance. It should also include one concise limitation sentence that final hit probability, accuracy/evasion stages, ability/weather interactions, multi-hit accuracy, and turn sequencing are not modeled.

If `accuracy_context.available` is false, or no `accuracy_context` is present for a move, the LLM should not invent Bright Powder accuracy effects or force an accuracy limitation sentence.

Candidate moves do not receive `damage_estimate`, `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, `multi_hit_context`, `speed_order_context`, or `ko_context`.

## Critical Context Semantics

`critical_context` is an additive limited context for Scope Lens critical-hit likelihood. It is never nested inside `damage_estimate` or `ko_context`.

`critical_context` does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, item damage modifier math, or `ko_context`.

In v0.66, the only modeled critical-hit context is limited Scope Lens context:

- attacker item profile must be `status: user_confirmed`
- attacker item id must be `scope-lens`
- final critical-hit probability is not calculated
- crit-adjusted KO probability is not calculated
- critical-hit damage is not folded into raw damage estimates
- exact critical-hit stage math is not exposed in the LLM payload
- abilities, move-specific crit effects, and turn sequencing are not modeled
- raw damage and KO/OHKO/2HKO estimates do not include crit chance

Available Scope Lens context may include:

- `mode`: `limited_critical_context`
- `available`: `true`
- `attacker_side`: `my_active` or `opponent_active`
- `item.item_id`: `scope-lens`
- `item.status`: `user_confirmed`
- `critical_effect.type`: `scope_lens`
- `critical_effect.effect_label`: `may_increase_critical_hit_likelihood`
- `critical_effect.formula_label`: `scope_lens_limited_critical_modifier`
- `critical_effect.raw_damage_rolls_changed`: `false`
- `critical_effect.ko_context_changed`: `false`
- `critical_effect.crit_probability_integrated`: `false`
- `critical_effect.crit_adjusted_ko_integrated`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_scope_lens`
- `item_not_user_confirmed`
- `unsupported_critical_item`
- `critical_engine_missing`
- `move_crit_metadata_missing`
- `turn_engine_required`
- `damage_estimate_missing`

The LLM may say:

- "Scope Lens may increase critical-hit likelihood as limited critical context, but the raw damage and KO estimates do not include crit chance."
- "The raw KO chance is separate from any critical-hit possibility; crit-adjusted KO probability is not calculated."
- "This is not a final critical-hit probability; critical-hit stages, abilities, move-specific crit effects, and turn sequencing are not modeled."

The LLM must not say:

- "Scope Lens boosts the damage directly."
- "This move will crit."
- "This move is guaranteed to crit."
- "The KO chance already accounts for Scope Lens crit chance."
- "The final critical-hit probability is confirmed."
- "The crit-adjusted KO chance is 70%."
- "Scope Lens applies when the item is unknown or unconfirmed."

When `critical_context.available` is true, the critical-hit note should stay concise, ideally one or two sentences, and should mention that raw damage and KO/OHKO/2HKO estimates do not include crit chance. It should also state that final critical-hit probability and crit-adjusted KO probability are not calculated.

If `critical_context.available` is false, or no `critical_context` is present for a move, the LLM should not invent Scope Lens critical-hit effects or force a critical-hit limitation sentence.

Candidate moves do not receive `damage_estimate`, `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, `multi_hit_context`, `speed_order_context`, or `ko_context`.

## Flinch Context Semantics

`flinch_context` is an additive limited context for King's Rock flinch pressure. It is never nested inside `damage_estimate` or `ko_context`.

`flinch_context` does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, item damage modifier math, or `ko_context`.

In v0.70, the only modeled flinch context is limited King's Rock context:

- attacker item profile must be `status: user_confirmed`
- attacker item id must be `kings-rock`
- final flinch probability is not calculated
- flinch-adjusted turn or outcome probability is not calculated
- flinch pressure is not folded into raw damage estimates
- exact speed order, target action state, abilities, multi-hit handling, and turn sequencing are not modeled
- raw damage and KO/OHKO/2HKO estimates do not include flinch chance

Available King's Rock context may include:

- `mode`: `limited_flinch_context`
- `available`: `true`
- `attacker_side`: `my_active` or `opponent_active`
- `item.item_id`: `kings-rock`
- `item.status`: `user_confirmed`
- `flinch_effect.type`: `kings_rock`
- `flinch_effect.effect_label`: `may_add_flinch_pressure`
- `flinch_effect.formula_label`: `kings_rock_limited_flinch_modifier`
- `flinch_effect.raw_damage_rolls_changed`: `false`
- `flinch_effect.ko_context_changed`: `false`
- `flinch_effect.flinch_probability_integrated`: `false`
- `flinch_effect.turn_outcome_integrated`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_kings_rock`
- `item_not_user_confirmed`
- `unsupported_flinch_item`
- `flinch_engine_missing`
- `move_flinch_metadata_missing`
- `turn_engine_required`
- `damage_estimate_missing`

The LLM may say:

- "King's Rock may add flinch pressure as limited flinch context, but the raw damage and KO estimates do not include flinch chance."
- "The raw KO chance is separate from any King's Rock flinch possibility; flinch-adjusted turn or outcome probability is not calculated."
- "King's Rock flinch pressure is separate from the raw damage estimate; raw damage and raw `ko_context` are unchanged."
- "This is not a final flinch probability; speed order, target action state, abilities, multi-hit handling, and turn sequencing are not modeled."

The LLM must not say:

- "King's Rock boosts the damage directly."
- "This move will flinch the target."
- "The target cannot move."
- "This move is guaranteed to flinch."
- "The KO chance already accounts for King's Rock flinch chance."
- "The final flinch probability is confirmed."
- "The flinch-adjusted KO chance is 70%."
- "King's Rock applies when the item is unknown or unconfirmed."

When `flinch_context.available` is true, the flinch note should stay concise, ideally one or two sentences, and should mention that raw damage and KO/OHKO/2HKO estimates do not include flinch chance. It should also state that final flinch probability and flinch-adjusted turn or outcome probability are not calculated.

When `flinch_context.available` is true, the LLM should say the raw damage estimate is unchanged and raw `ko_context` is unchanged. It should include one concise limitation sentence that speed order, target action state, abilities, multi-hit handling, and turn sequencing are not modeled.

When `flinch_context.available` is true, prefer "raw damage estimate is unchanged" over awkward wording such as "damage modifier is not included." King's Rock is not a direct damage boost, and flinch context should be framed as separate pressure, not as damage modifier bookkeeping.

If `flinch_context.available` is false, or no `flinch_context` is present for a move, the LLM should not invent King's Rock flinch effects or force a flinch limitation sentence.

Candidate moves do not receive `damage_estimate`, `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, `multi_hit_context`, `speed_order_context`, or `ko_context`.

## Multi-hit Context Semantics

`multi_hit_context` is an additive limited context for Loaded Dice multi-hit reliability. It is never nested inside `damage_estimate` or `ko_context`.

`multi_hit_context` does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, item damage modifier math, or `ko_context`.

In v0.73, the only implemented multi-hit context helper is limited Loaded Dice context. In v0.80, Loaded Dice is blocked from user-facing modeled context until Champions legal coverage is confirmed:

- attacker item profile must be `status: user_confirmed`
- attacker item id must be `loaded-dice`
- attacker item id must also pass the Champions legal item gate
- move metadata must identify the move as multi-hit
- final hit count probability is not calculated
- multi-hit-adjusted KO probability is not calculated
- hit count changes are not folded into raw damage estimates
- raw damage and KO/OHKO/2HKO estimates do not include multi-hit count changes
- Focus Sash interaction, King's Rock interaction, accuracy/crit per-hit handling, and turn sequencing are not modeled

Available Loaded Dice context may include:

Note: while `loaded-dice` is absent from `data/static/champions_legal_items.json`, this available shape is future-only and should not appear in user-facing payloads.

- `mode`: `limited_multi_hit_context`
- `available`: `true`
- `attacker_side`: `my_active` or `opponent_active`
- `item.item_id`: `loaded-dice`
- `item.status`: `user_confirmed`
- `move_metadata.is_multi_hit`: `true`
- `move_metadata.metadata_source`: `move_metadata`
- `move_metadata.multi_hit_known`: `true`
- `multi_hit_effect.type`: `loaded_dice`
- `multi_hit_effect.effect_label`: `may_improve_multi_hit_reliability`
- `multi_hit_effect.formula_label`: `loaded_dice_limited_multihit_modifier`
- `multi_hit_effect.raw_damage_rolls_changed`: `false`
- `multi_hit_effect.ko_context_changed`: `false`
- `multi_hit_effect.hit_count_probability_integrated`: `false`
- `multi_hit_effect.multi_hit_adjusted_ko_integrated`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_loaded_dice`
- `item_not_user_confirmed`
- `blocked_by_legal_item_coverage`
- `unsupported_multi_hit_item`
- `move_not_multi_hit`
- `move_multihit_metadata_missing`
- `multi_hit_engine_missing`
- `turn_engine_required`
- `damage_estimate_missing`

The LLM may say:

- "Loaded Dice may improve multi-hit reliability as limited context, but the raw damage and KO estimates do not include multi-hit count changes."
- "The raw KO chance is separate from any Loaded Dice multi-hit possibility; multi-hit-adjusted KO probability is not calculated."
- "This is not a final hit count distribution; Focus Sash, King's Rock, accuracy, crit per-hit handling, and turn sequencing are not modeled."

The LLM must not say:

- "Loaded Dice directly boosts the damage."
- "This move will hit 5 times."
- "This guarantees 5 hits."
- "The KO chance already accounts for Loaded Dice hit count changes."
- "Loaded Dice breaks Focus Sash here."
- "The final hit count probability is confirmed."
- "The multi-hit-adjusted KO chance is 70%."
- "Loaded Dice applies when the item is unknown or unconfirmed."

When `multi_hit_context.available` is true, the multi-hit note should stay concise, ideally one or two sentences, and should mention that raw damage and KO/OHKO/2HKO estimates do not include multi-hit count changes. It should also state that final hit count probability and multi-hit-adjusted KO probability are not calculated.

If `multi_hit_context.available` is false, or no `multi_hit_context` is present for a move, the LLM should not invent Loaded Dice multi-hit effects or force a multi-hit limitation sentence.

If `multi_hit_context.available` is false because the item is blocked by legal coverage, the blocked reason is developer/debug/contract metadata. The default user-facing recommendation should stay quiet about Loaded Dice and should not say "Loaded Dice," "user-confirmed Loaded Dice," "Loaded Dice is not modeled," or "Loaded Dice's effect is not included" unless the user explicitly asks about Loaded Dice.

Candidate moves do not receive `damage_estimate`, `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, `multi_hit_context`, `type_boost_context`, `speed_order_context`, `resist_berry_context`, `chilan_berry_context`, or `ko_context`.

## Available Item Context Required Mention

When the default advice payload contains one or more item context fields with `available=true`, the prompt must include a required-mention guard. The guard lists the available item contexts and tells Gemini to mention each listed context at least once when it is directly relevant to the recommendation.

The guard is generated from the already-filtered default advice payload, not from the enriched/debug payload. Therefore it applies only to contexts still visible to ordinary advice. It must not reintroduce unavailable, deferred, blocked, unsupported, or non-triggered item names or reasons.

Available item contexts must not be described as unavailable, unmodeled, not included, not reflected, absent, or omitted. In particular, when any available item context is present, ordinary advice should avoid generic wording such as:

- "item is not included"
- "item is not modeled"
- "item is not reflected"
- "no item is considered"
- "assuming no item"
- "without item effects"
- "default no-item assumption"

This guard does not change raw calculations. Available item context wording must remain limited and must not become final KO odds, guaranteed survival, guaranteed move order, exact final stats, or final battle truth. Raw damage rolls and `ko_context` remain governed by their existing fields.

For Light Ball, an available `species_stat_item_context` should be mentioned as Pikachu-specific offensive item context. For Chilan Berry, an available `chilan_berry_context` should be mentioned as Normal-type limited context for a Normal-type damaging move.

## Unavailable Item Context Silence

Unavailable, deferred, blocked, unconfirmed, non-triggered, or absent item context reasons are developer/debug/contract metadata by default. They should not be surfaced in ordinary battle advice.

The default Gemini advice payload is filtered from the enriched/debug payload. Item context fields with `available=false` are removed from the default advice payload before prompt serialization, while the enriched/debug payload may retain the full context and `reason` for diagnostics and tests. This keeps unavailable/deferred reasons available to developers without giving Gemini default advice a reason to explain them.

In v1.0, the default-advice filtering policy is registry-backed. The contract-owned registry constants list the context keys that are allowed to participate in default advice filtering:

- `ADVICE_CONTEXT_KEYS`: all known advice context surfaces, including top-level `speed_context`
- `ADVICE_ITEM_CONTEXT_KEYS`: item context fields that are removed from default advice when `available=false`
- `ADVICE_CONTEXTS_REQUIRING_MOVE_LOCAL_ITEM_EFFECT_SCRUB`: context fields that also require local `damage_estimate.item_effects` scrubbing when unavailable
- `DEBUG_ONLY_REASON_PHRASES`: debug-only limitation wording removed from default advice payload limitations/notes

`build_ui_advice_payload()` delegates to the default-advice filtering helper so the same policy applies before prompt serialization. This is a cleanup only: it does not add item mechanics, change raw damage rolls, change `ko_context`, or change legal fixture behavior.

The default advice payload also strips debug-only limitation strings that contain unavailable/deferred/blocked wording such as "not modeled", "not reflected", "unsupported", "deferred", "blocked", "effect is not applied", or "item effect is not included". This applies to nested `limitations` lists as well, including otherwise legal raw contexts such as `ko_context`, so generic limitation wording does not leak unavailable item state into ordinary advice. The enriched/debug payload may keep those limitations for diagnostics.

The filtering applies to item context fields such as:

- `survival_context`
- `recovery_context`
- `accuracy_context`
- `critical_context`
- `flinch_context`
- `multi_hit_context`
- `type_boost_context`
- `species_stat_item_context`
- `speed_order_context`
- `resist_berry_context`
- `chilan_berry_context`
- future `charge_context`

Top-level `speed_context` is listed as an advice context but is not filtered as an item context. It keeps the existing Speed contract and remains raw/effective Speed comparison only. Choice Scarf effective Speed continues to live in `speed_context`, not `speed_order_context`, and Choice Scarf choice lock remains unmodeled.

When a user-confirmed item is absent from Champions legal coverage, default advice payloads also hide that non-legal item profile as unknown. This prevents blocked item names such as Loaded Dice or future-only items such as Power Herb from appearing in ordinary advice JSON. The enriched/debug payload may still retain the original item profile and blocked context reason.

This applies to unavailable item contexts such as:

- `blocked_by_legal_item_coverage`
- `future_only_until_legal_confirmed`
- `move_not_super_effective`
- `chilan_berry_deferred`
- `item_not_user_confirmed`
- `no_resist_berry`

Default user-facing advice must not say:

- "item effect is not included"
- "opponent's item effect is not included"
- "user-confirmed item effect is not included"
- "item is not modeled"
- "item effect is not applied"
- "not included in this estimate"
- "not reflected in the calculation"

Default user-facing advice should also avoid naming unavailable or deferred item effects. If the user explicitly asks about that item or reason, the response may briefly explain the relevant metadata state without implying that a final item-adjusted calculation exists.

## Resist Berry Context Semantics

`resist_berry_context` is an additive limited context for standard type-resist berries. It is never nested inside `damage_estimate` or `ko_context`.

`resist_berry_context` does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, item damage modifier math, or `ko_context`.

The first supported scope is the 17 standard type-resist berries whose `items_damage.json` metadata has a `resist_type` and does not set `always_resist=true`:

- `babiri-berry`
- `charti-berry`
- `chople-berry`
- `coba-berry`
- `colbur-berry`
- `haban-berry`
- `kasib-berry`
- `kebia-berry`
- `occa-berry`
- `passho-berry`
- `payapa-berry`
- `rindo-berry`
- `roseli-berry`
- `shuca-berry`
- `tanga-berry`
- `wacan-berry`
- `yache-berry`

The Normal-type always-resist berry edge case is handled separately by `chilan_berry_context` because `items_damage.json` marks it as `always_resist=true`, and that edge case is not the same as a super-effective trigger.

Available resist berry context requires:

- defender item profile must be `status: user_confirmed`
- defender item id must pass the Champions legal item gate
- defender item id must exist in `items_damage.json` `type_resist_berries`
- incoming move type must be known
- incoming move type must match the berry resisted type
- `damage_estimate.type_effectiveness` must identify the hit as super effective
- raw damage and KO/OHKO/2HKO estimates do not include berry reduction
- berry-adjusted damage is not calculated
- berry-adjusted KO probability is not calculated
- item consumption is not tracked
- multi-hit handling, abilities, weather, Tera, and turn sequencing are not modeled

Available context may include:

- `mode`: `limited_resist_berry_context`
- `available`: `true`
- `defender_side`: `my_active` or `opponent_active`
- `item.item_id`: the berry id
- `item.status`: `user_confirmed`
- `item.legal_status`: `legal_modeled`
- `resist_effect.berry_type`: resisted type from `items_damage.json`
- `resist_effect.incoming_move_type`: incoming move type
- `resist_effect.requires_super_effective_hit`: `true`
- `resist_effect.super_effective_match`: `true`
- `resist_effect.effect_label`: `may_reduce_qualifying_super_effective_hit`
- `resist_effect.formula_label`: `resist_berry_limited_damage_reduction`
- `resist_effect.raw_damage_rolls_changed`: `false`
- `resist_effect.ko_context_changed`: `false`
- `resist_effect.berry_adjusted_damage_integrated`: `false`
- `resist_effect.berry_adjusted_ko_integrated`: `false`
- `resist_effect.item_consumption_tracked`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_resist_berry`
- `item_not_user_confirmed`
- `blocked_by_legal_item_coverage`
- `incoming_move_type_missing`
- `berry_type_missing`
- `move_not_super_effective`
- `type_matchup_unknown`
- `chilan_berry_deferred`
- `resist_berry_engine_missing`
- `damage_estimate_missing`

The LLM may say:

- "Yache Berry may reduce a qualifying Ice-type super-effective hit as limited context, but the raw damage and KO estimates do not include berry reduction."
- "This is not a final survival prediction because item consumption and turn sequencing are not modeled."

The LLM must not say:

- "Yache Berry makes this always survive."
- "The KO chance already includes Yache Berry."
- "The damage range is reduced to X-Y."
- "The berry-adjusted KO chance is 70%."
- "The berry has already been consumed."
- "A deferred resist berry edge case is modeled" unless a future explicit field supports it.

When `resist_berry_context.available` is true, the resist berry note should stay concise, ideally one or two sentences, and should mention that raw damage and KO/OHKO/2HKO estimates do not include berry reduction. It should also state that berry-adjusted damage, berry-adjusted KO probability, and item consumption are not calculated.

When `resist_berry_context.available` is true, prefer wording such as "raw damage estimate is unchanged" and "raw ko_context is unchanged" over wording that implies the berry should have been part of the damage formula.

If `resist_berry_context.available` is false in the enriched/debug payload, the default advice payload should omit `resist_berry_context`. The unavailable reason is developer/debug/contract metadata only. The LLM should not invent resist berry effects, force a resist berry limitation sentence, or mention the unavailable berry name/effect/reason in default advice.

For unavailable resist berry context, the LLM must not say:

- "Yache Berry effect is not applied."
- "The berry effect is not included."
- "The berry is not modeled."
- "Yache Berry is unavailable because the move is not super effective."

If the user explicitly asks about that berry, the response may briefly explain that the current move does not have an available limited `resist_berry_context`, without claiming berry-adjusted damage or KO probability.

## Chilan Berry Context Semantics

`chilan_berry_context` is an additive limited context for Chilan Berry's Normal-type special case. It is separate from `resist_berry_context` because Chilan Berry does not use the standard super-effective trigger model.

`chilan_berry_context` does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, item modifier math, Q12 constants, or `ko_context`.

Available Chilan context requires:

- defender item profile must be `status: user_confirmed`
- defender item id must be `chilan-berry`
- defender item id must pass the Champions legal item gate
- `items_damage.json` metadata must identify `resist_type=normal`
- `items_damage.json` metadata must identify `always_resist=true`
- incoming move type must be known
- incoming move type must be `normal`
- incoming move must be damaging
- raw `damage_estimate` must be available

Available context may include:

- `mode`: `limited_chilan_berry_context`
- `available`: `true`
- `defender_side`: `my_active` or `opponent_active`
- `item.item_id`: `chilan-berry`
- `item.status`: `user_confirmed`
- `item.legal_status`: `legal_modeled`
- `normal_resist_effect.berry_type`: `normal`
- `normal_resist_effect.incoming_move_type`: `normal`
- `normal_resist_effect.requires_super_effective_hit`: `false`
- `normal_resist_effect.always_resist`: `true`
- `normal_resist_effect.effect_label`: `may_reduce_normal_type_hit`
- `normal_resist_effect.formula_label`: `chilan_berry_limited_normal_damage_reduction`
- `normal_resist_effect.raw_damage_rolls_changed`: `false`
- `normal_resist_effect.ko_context_changed`: `false`
- `normal_resist_effect.chilan_adjusted_damage_integrated`: `false`
- `normal_resist_effect.chilan_adjusted_ko_integrated`: `false`
- `normal_resist_effect.item_consumption_tracked`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `no_chilan_berry`
- `item_not_user_confirmed`
- `blocked_by_legal_item_coverage`
- `chilan_berry_metadata_missing`
- `incoming_move_type_missing`
- `move_type_not_normal`
- `move_not_damaging`
- `damage_estimate_missing`

When `chilan_berry_context.available` is true, the LLM should say Chilan Berry is a Normal-type limited context and may reduce damage from a Normal-type damaging move. It should also say this limited context is separate from raw damage rolls and is not integrated into final KO odds; raw damage rolls and `ko_context` remain based on the current calculator. It should not say Chilan Berry is not included or not modeled when the available context is present.

The LLM must not say:

- "Chilan Berry is not included."
- "Chilan Berry is not modeled."
- "Chilan Berry guarantees survival."
- "Confirmed live."
- "The Pokemon will survive because of Chilan Berry."
- "KO chance is reduced to X."
- "Final damage is halved."
- "Raw damage rolls already include Chilan Berry."
- "Chilan Berry applies to all move types."

If `chilan_berry_context.available` is false in the enriched/debug payload, the default advice payload should omit `chilan_berry_context`. The unavailable reason is developer/debug/contract metadata only. The LLM should not mention Chilan Berry, the Chilan effect, or the unavailable reason in default advice unless the user explicitly asks about that item.

## KO Context Semantics

`ko_context` is an additive limited context next to a relevant `damage_estimate`. It does not alter `damage_estimate.damage_range`, `damage_estimate.rolls`, type effectiveness, item modifiers, or `survival_context`.

In v0.57, KO context is limited damage-roll context:

- OHKO chance is based on raw damage rolls when rolls are available.
- `successful_rolls` counts rolls where `roll >= current_hp`.
- `chance` is `successful_rolls / total_rolls`.
- `ohko.guaranteed` is true only when every roll meets or exceeds current HP.
- If rolls are missing, min/max fallback may set possible/guaranteed booleans but must not invent a chance.
- 2HKO context uses limited min/max logic:
  - `min_damage * 2 >= current_hp` means guaranteed 2HKO under limited assumptions.
  - `max_damage * 2 >= current_hp` means possible 2HKO under limited assumptions.
  - roll-pair 2HKO probability is not exposed in v0.57.

Available KO context may include:

- `mode`: `limited_damage_roll_ko_context`
- `available`: `true`
- `target_hp.current_hp`
- `target_hp.max_hp`
- `target_hp.hp_percent`
- `damage.min`
- `damage.max`
- `damage.roll_count`
- `ohko.possible`
- `ohko.guaranteed`
- `ohko.chance`
- `ohko.successful_rolls`
- `ohko.total_rolls`
- `two_hko.possible`
- `two_hko.guaranteed`
- `two_hko.method`: `limited_min_max`
- `raw_damage_rolls_changed`: `false`
- `is_final_battle_truth`: `false`

Unavailable reason codes include:

- `hp_unknown`
- `damage_estimate_missing`

The LLM may say:

- "The raw damage rolls have a 6/16 chance to KO from the current HP, but this is limited damage-roll context."
- "This is a limited 2HKO estimate assuming the same move is used twice with no healing, switching, protection, or chip changes."
- "Raw damage could KO, but survival context is separate and may allow limited Focus Sash or Focus Band survival under its own assumptions."

The LLM must not say:

- "This guarantees the KO in battle."
- "This will always 2HKO."
- "The opponent cannot survive."
- "Focus Sash or Focus Band is included in the KO probability."
- "Accuracy, Speed order, priority, recovery, hazards, chip damage, switching, protection, or turn sequencing are modeled."

Candidate moves do not receive `damage_estimate`, `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, `multi_hit_context`, `speed_order_context`, or `ko_context`.

## Opponent Assumption Semantics

`opponent_assumptions` is a context-only risk section for possible opponent sample profiles.

It must not be treated like:

- `stat_profiles`
- `opponent_moves.known_moves`
- user-confirmed final stats
- damage calculation input
- Speed calculation input

The LLM may say:

- "Possible opponent samples include a fast physical Garchomp sample."
- "These are assumptions, not confirmed opponent stats."
- "The sample is context only and was not used directly for damage or speed calculation."
- "Prior probability is not available for this sentinel sample."
- "Garchomp has possible sample assumptions, but they are context only and not confirmed."
- "A possible fast physical Garchomp sample exists, but it was not used directly for damage or speed calculation."
- "The opponent's exact set is still unknown."

The LLM must not say:

- "The opponent is this sample."
- "The opponent definitely has 154 Speed."
- "This sample proves the opponent item."
- "prior_probability is null, so this set is impossible."
- "This sample confirms turn order, KO, or survival."

User-confirmed fields override possible sample assumptions. If a future payload marks conflicts between `user_confirmed_fields` and possible samples, conflicting samples must not drive advice.

When `opponent_assumptions.available` is `true` and `possible_samples` is non-empty, the LLM should briefly mention the existence of possible sample context when relevant, preferably as one short limitation sentence:

- "Possible opponent samples exist, but they are context-only and not confirmed."

This sentence is a visibility cue, not a calculation claim. The LLM must not say sample stats were used for damage, Speed, KO, survival, or final turn order unless a future payload explicitly provides that calculated field.

Concision guardrail:

- Do not dump `sample_id`, full stats, source metadata, `update_policy`, `coverage_probability`, or full Top-K sample lists into the response.
- Do not let sample context become longer than the main damage recommendation.
- If `opponent_assumptions.available` is `false`, do not invent samples or force a sample limitation.
- Do not enumerate role, archetype, or possible item metadata by default.
- `possible_items` are possible assumptions, not confirmed held items.

## Opponent Assumptions Debug Summary

The developer debug summary is a copy/export-ready view of `opponent_assumptions` only. It is not a full LLM payload export and must not be automatically inserted into the Gemini response.

Debug summary policy:

- developer-only
- `opponent_assumptions` summary only
- no full LLM payload export in v0.45
- no API keys, secrets, `.env` values, or token usage logs
- no full stats dump
- no full source metadata dump
- no `update_policy` dump
- no full Top-K metadata dump
- no UI debug panel in v0.45

The summary may include:

- opponent species id
- availability and unavailable reason
- `calculation_usage`
- `is_confirmed_information`
- possible sample count
- included Top-K count
- sample id
- sample species id
- role / archetype id when present
- confidence
- `is_user_confirmed`
- possible items
- `used_for_damage: false`
- `used_for_speed: false`
- guardrail booleans such as `not_confirmed`, `not_damage_input`, `not_speed_input`, `not_final_turn_order`, and `context_only`

If a future file export is added, it should write only to a git-ignored debug path such as `logs/debug_payloads/`. Debug exports remain outside commits.

v0.51 adds a developer CLI for this summary:

```powershell
uv run python scripts/debug_opponent_assumptions.py --species rotom-wash
```

The CLI prints the safe `opponent_assumptions` debug summary JSON to stdout. It does not call Gemini, does not write files, does not export the full LLM payload, and does not read or print API keys, `.env` values, secrets, or token logs. `--top-k` can be used to limit possible samples.

## Speed Context Semantics

`speed_context` is raw and supported effective Speed comparison only.

It may compare `stat_profiles.my_active.final_stats.spe` and `stat_profiles.opponent_active.final_stats.spe` only when both active Pokemon have `status: "user_confirmed_final_stats"`.

Effective Speed in v0.30 may include only:

- Choice Scarf speed modifier
- only when `item_profiles.*.status` is `user_confirmed`
- only when `item_profiles.*.item_id` is `choice-scarf`

Choice Scarf uses a `1.5` speed modifier in `speed_context.*.speed_modifiers`.

Choice Scarf choice lock is not modeled.

It does not model:

- priority
- Tailwind
- Trick Room
- paralysis
- Speed stages
- ability speed effects
- final turn order
- Turn Engine state

The LLM may say:

- "Based on raw Speed only, your Pokemon appears faster."
- "With the supported Choice Scarf speed modifier, your Pokemon appears faster by effective Speed estimate."
- "This does not confirm final turn order because priority, Tailwind, Trick Room, paralysis, Speed stages, and ability speed effects are not modeled."

The LLM must not say:

- "You will move first."
- "Choice Scarf guarantees you move first."
- "This guarantees turn order."

If `speed_context.available` is `false`, the LLM should not compare Speed and should mention that raw Speed comparison requires user-confirmed final Speed for both active Pokemon.

## Speed-Order Item Context Semantics

`speed_order_context` is an additive limited context for Quick Claw move-order pressure. It is never nested inside `speed_context`, `damage_estimate`, or `ko_context`.

In v0.98, modeled speed-order item context is limited to Quick Claw:

- `item_profiles.<attacker>.status` must be `user_confirmed`
- `item_profiles.<attacker>.item_id` must be `quick-claw`
- Champions legal item coverage must pass
- a selected/available/known move payload must exist

Available context may include:

- `mode`: `limited_speed_order_item_context`
- `available`: `true`
- `attacker_side`: `my_active` or `opponent_active`
- `item.item_id`: `quick-claw`
- `item.status`: `user_confirmed`
- `item.legal_status`: `legal_modeled`
- `speed_order_effect.type`: `quick_claw`
- `speed_order_effect.effect_label`: `may_affect_move_order`
- `speed_order_effect.activation_probability_calculated`: `false`
- `speed_order_effect.final_move_order_calculated`: `false`
- `speed_order_effect.speed_tie_resolved`: `false`
- `speed_order_effect.priority_integrated`: `false`
- `speed_order_effect.turn_engine_integrated`: `false`
- `is_final_battle_truth`: `false`

When `speed_order_context.available` is true, the LLM may say Quick Claw may affect move order or can occasionally affect move order. The LLM should also say move order is not fully modeled and should not treat the context as guaranteed priority.

The LLM must not say:

- "Quick Claw will move first."
- "Quick Claw guarantees outspeeding."
- "Confirmed first."
- "Always acts before."
- "Wins the speed interaction."
- "Safe because it moves first."
- "Quick Claw activation probability is X%."

The context does not calculate final move order, activation probability, speed ties, priority, Trick Room, Tailwind, paralysis, boosts, abilities, weather, item consumption, or turn sequencing.

If `speed_order_context.available` is false in the enriched/debug payload, the default advice payload should omit `speed_order_context`. The unavailable reason is developer/debug/contract metadata only. The LLM should not mention the unavailable Quick Claw item name, effect, or reason in default advice unless the user explicitly asks about that item.

Choice Scarf is not modeled through `speed_order_context`; keep Choice Scarf handling in top-level `speed_context`.

## Type Effectiveness Semantics

Damage estimates include explicit type effectiveness metadata:

```json
{
  "type_effectiveness": {
    "multiplier": 0.5,
    "label": "not_very_effective"
  }
}
```

Labels:

- `immune`: multiplier `0`
- `not_very_effective`: multiplier greater than `0` and less than `1`
- `neutral`: multiplier `1`
- `super_effective`: multiplier greater than `1`

The LLM must use this field when explaining type matchups. It must not call a move super effective, resisted, or immune from general Pokemon knowledge when this field says otherwise.

The LLM must not print raw labels such as `super_effective` or `not_very_effective` directly. It should convert labels to natural wording:

- `super_effective` -> "super effective"
- `not_very_effective` -> "not very effective" or "resisted"
- `immune` -> "immune" or "no effect"
- `neutral` -> "neutral"

## Explicitly Missing

The v0.18 payload does not contain:

- EV/IV/nature
- full battle item effect modeling beyond the legal `item_profiles` selector
- selected ability certainty
- weather
- terrain
- stat boosts
- exact current HP integer
- candidate move damage estimates
- OHKO/2HKO/KO chance
- final turn order
- speed tie
- status duration
- Turn Engine state

## LLM Guardrails

The LLM must not:

- assume unprovided EVs, IVs, nature, held items, boosts, weather, terrain, exact HP, move sets, or Tera types
- treat `base_stats` as final battle stats
- describe `damage_estimate` as final battle damage
- infer OHKO/2HKO, KO chance, survival, or speed order unless explicit calculated fields are present
- treat `speed_context` as final turn order
- claim a Pokemon will move first when `speed_context.is_final_turn_order` is `false`
- apply Choice Scarf speed unless `speed_context.*.speed_modifiers` marks it as applied from a user-confirmed item
- apply priority, Tailwind, Trick Room, paralysis, Speed stages, or ability speed effects from `speed_context`
- treat cache learnsets or unselected moves as available moves
- treat `opponent_moves.candidate_moves` as confirmed opponent moves
- treat `opponent_assumptions.possible_samples` as confirmed opponent sets
- treat `sample_assumed` opponent samples as user-confirmed information
- interpret `prior_probability: null` as zero probability
- claim Top-K omitted opponent sample archetypes are impossible
- say context-only samples changed `damage_estimate` or `speed_context`
- assume the opponent has a candidate move unless it appears in `opponent_moves.known_moves`
- claim candidate move damage, speed order, or turn order from v0.18 opponent move metadata
- describe opponent known move damage estimates as final battle damage
- ignore `assumption_profile` when explaining damage estimate confidence
- invent opponent item, selected ability, EVs, IVs, nature, boosts, speed order, turn outcome, or missing final stats
- infer EVs, IVs, nature, or item from user-confirmed final stats
- treat `unknown` item as `none`
- treat a selected legal item as modeled unless `damage_estimate.item_effects` marks its effect as `applied`
- present damage-supported non-legal/debug items as normal Champions legal selections
- claim item effects are applied unless `damage_estimate.item_effects` marks them as `applied`
- omit an applied attacker item modifier when explaining why one move did more damage
- describe an item-applied estimate as only default assumptions when `item_effects.attacker_item.status` is `applied`
- print raw `type_effectiveness` labels such as `super_effective` or `not_very_effective`
- claim choice lock, Life Orb recoil, Focus Sash survival, or Leftovers recovery is modeled
- mention choice lock for non-Choice items such as Charcoal, Mystic Water, Black Belt, Metal Coat, Sharp Beak, Fairy Feather, Light Ball, Leftovers, Focus Sash, or Focus Band
- describe a move as super effective, resisted, or immune unless `damage_estimate.type_effectiveness` supports that label
- consider Terastallization, which is banned in PoChamps

The LLM may:

- explain broad type or role risks at a non-damage-exact level
- discuss user-confirmed move metadata such as type, category, power, accuracy, and PP
- discuss `damage_estimate` only under its stated default assumptions
- discuss `assumption_profile` as the stat model used for an estimate
- discuss `damage_estimate.item_effects` as the item effect summary for that estimate
- discuss `damage_estimate.type_effectiveness` as the source for type matchup explanations
- discuss `speed_context` as raw and supported effective Speed comparison only when available
- say "based on raw Speed only" or "appears faster by raw Speed" when explaining `speed_context`
- discuss Choice Scarf as a supported effective Speed estimate only when `speed_context.*.speed_modifiers` marks it applied
- say choice lock is not modeled when Choice Scarf speed is applied
- distinguish raw Speed relation from effective Speed relation when they differ
- say a supported item damage modifier is applied only when `damage_estimate.item_effects` says `status: "applied"`
- mention applied attacker item damage modifiers when they are part of the damage estimate
- say Life Orb recoil or Choice item lock is not modeled when those effects appear in `unapplied_effects`
- convert `type_effectiveness` labels into natural wording such as "super effective", "not very effective", "immune", or "neutral"
- discuss user-confirmed final stats as user-provided stat values when `stat_profiles` says so
- discuss `opponent_moves.known_moves` as user-confirmed opponent moves
- discuss `opponent_moves.known_moves[*].damage_estimate` only as default-assumption damage against `my_active`
- discuss `opponent_moves.candidate_moves` only as possible, not confirmed, Champions moves
- discuss `opponent_assumptions.possible_samples` only as context-only possible profiles
- mention that possible samples are assumptions, not confirmed opponent sets
- mention that context-only samples were not used directly for damage or speed calculations
- mention candidate moves as possible threats only when they are labeled as unconfirmed
- use `my_available_moves[*].damage_estimate` to compare the user's own move options
- recommend a direction while naming the missing information that prevents a confident damage-based call
- ask for or point out missing final stats, items, field state, opponent moves, or damage estimates

## Damage Estimate Defaults

Each damage estimate includes this default assumption profile:

```json
{
  "id": "default_level50_ivs31_evs0_neutral_no_item",
  "label": "Default Level 50 / IV 31 / EV 0 / neutral nature / no item",
  "source": "system_default",
  "confidence": "rough_reference",
  "is_user_confirmed": false
}
```

When a supported damage item modifier is applied with default stats, the profile changes to:

```json
{
  "id": "default_level50_ivs31_evs0_neutral_with_damage_item",
  "label": "Default Level 50 / IV 31 / EV 0 / neutral nature / supported damage item",
  "source": "system_default_and_user_input",
  "confidence": "rough_reference_with_user_confirmed_item",
  "is_user_confirmed": false
}
```

Move damage estimates use:

- level 50
- IV 31 all
- EV 0 all
- neutral nature
- no item
- no boosts
- no weather
- no terrain
- no screens
- no critical hit
- singles / non-spread assumption
- no ability effects unless explicitly selected and connected

`percent_range` uses default defender max HP as the denominator. It is not exact current HP.

When `stat_profiles` provides six user-confirmed final stats for an active Pokemon, damage estimates may use those final stats. In that case the estimate uses this profile:

```json
{
  "id": "user_confirmed_final_stats_level50",
  "label": "User-confirmed final stats / Level 50",
  "source": "user_input",
  "confidence": "higher_confidence_reference",
  "is_user_confirmed": true
}
```

When user-confirmed final stats and a supported damage item modifier are both used, the profile changes to:

```json
{
  "id": "user_confirmed_final_stats_level50_with_damage_item",
  "label": "User-confirmed final stats / Level 50 / supported damage item",
  "source": "user_input",
  "confidence": "higher_confidence_reference",
  "is_user_confirmed": true
}
```

Even with user-confirmed final stats and supported damage item modifiers, `is_final_battle_damage` remains `false` because selected ability, boosts, weather, terrain, screens, exact current HP, non-damage item effects, and KO odds are not connected.

Unavailable statuses include:

- `unavailable_no_selected_move`
- `unavailable_no_known_move`
- `unavailable_status_move`
- `unavailable_missing_power`
- `unavailable_missing_pokemon`
- `unavailable_missing_base_stats`
- `unavailable_missing_type`
- `unavailable_unsupported_category`
- `unavailable_engine_error`

## Future Field Locations

Future versions may add candidate move threat scoring or opponent-to-my-active KO probability, but those require separate guardrails because candidate moves are not confirmed.

Turn Engine state should later enter a separate top-level `battle_state` section instead of being mixed into Pokemon identity metadata.
