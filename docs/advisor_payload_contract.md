# Advisor Payload Contract

**Milestone:** v0.38 - Opponent Possible Sample Payload
**Payload mode:** `ui-selected-pokemon-v0.18`
**Status:** Current contract for the PySide6 UI to Gemini LLM advisor path.

## Purpose

The advisor payload is the boundary between deterministic UI / engine state and the Gemini natural-language recommendation layer. This contract prevents the LLM from treating incomplete UI metadata as confirmed battle math.

The current app can send selected Pokemon identity, HP percent, user-confirmed move metadata, optional user-confirmed final stats for the active Pokemon, top-level item profiles, context-only opponent sample assumptions, raw/effective Speed comparison context, damage estimates for the user's confirmed moves, explicitly labeled opponent move information, and damage estimates for user-confirmed opponent known moves. Every damage estimate includes an `assumption_profile` describing the stat/item model used. Supported attacker-side damage items may be applied only when `damage_estimate.item_effects` marks them as applied. v0.23 connects the normal item selector to the Champions legal item repository: normal UI options include Unknown, No item, and legal fixture items. Damage-supported but non-legal/debug items such as Choice Band, Choice Specs, and Life Orb are not normal selector options. v0.28 adds `speed_context` for raw Speed comparison only when both active Pokemon have user-confirmed final Speed. v0.30 extends `speed_context` with Choice Scarf effective Speed when Choice Scarf is user-confirmed. v0.38 adds `opponent_assumptions` as context-only possible opponent sample profiles. The app does not yet send EV/IV/nature breakdowns, KO odds, final turn order, candidate move damage estimates, sample-based damage or Speed calculations, or Turn Engine state.

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
- `available`: `true`
- `scope`: `opponent_active`
- `is_confirmed_information`: always `false`
- `calculation_usage`: `context_only`
- `opponent_active.species_id`
- `opponent_active.known_status`: currently `not_confirmed`
- `opponent_active.is_user_confirmed`: `false`
- `opponent_active.user_confirmed_fields`: currently `{}`
- `opponent_active.possible_samples`
- `opponent_active.samples_meta`
- `opponent_active.observation_history`: currently `[]`
- `opponent_active.update_policy.mode`: `static`
- `limitations`

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
- `possible_stats`
- `limitations`

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
- Focus Sash survival
- Leftovers/Sitrus recovery
- Choice lock
- Life Orb recoil
- candidate move damage
- KO/OHKO/2HKO

Legal item modeling examples:

- Choice Scarf: selectable; its supported speed modifier may be applied in `speed_context` when user-confirmed, but speed order and choice lock are not modeled.
- Focus Sash: selectable, but survival is not modeled.
- Leftovers / Sitrus Berry: selectable, but recovery and turn sequencing are not modeled.

`damage_estimate.item_effects` is the source of truth for whether an item effect was applied to a specific calculation.

When `damage_estimate.item_effects.attacker_item.status` is `applied`, the LLM should explicitly mention that the supported item damage modifier is included in that estimate. It should describe the number as being calculated under the stated assumptions plus the supported item modifier, not as only default assumptions. Non-damage item effects remain unmodeled.

If Life Orb is applied, the LLM should say the damage modifier is applied and Life Orb recoil is not modeled. If Choice Band or Choice Specs is applied, the LLM should say the relevant damage modifier is applied and choice lock is not modeled.

For type boosting items, the LLM should say the damage modifier is included only when `damage_estimate.item_effects.attacker_item.status` is `applied`. It must not say the item boosted damage when the move type does not match, when the item is unsupported, or merely because the item is legal. Fairy Feather should be described as legal but not damage-modeled until a catalog-backed modifier exists.

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

The LLM must not say:

- "The opponent is this sample."
- "The opponent definitely has 154 Speed."
- "This sample proves the opponent item."
- "prior_probability is null, so this set is impossible."
- "This sample confirms turn order, KO, or survival."

User-confirmed fields override possible sample assumptions. If a future payload marks conflicts between `user_confirmed_fields` and possible samples, conflicting samples must not drive advice.

## Speed Context Semantics

`speed_context` is raw and supported effective Speed comparison only.

It may compare `stat_profiles.my_active.final_stats.spe` and `stat_profiles.opponent_active.final_stats.spe` only when both active Pokemon have `status: "user_confirmed_final_stats"`.

Effective Speed in v0.30 may include only:

- Choice Scarf speed modifier
- only when `item_profiles.*.status` is `user_confirmed`
- only when `item_profiles.*.item_id` is `choice-scarf`

Choice Scarf uses a `1.5` speed modifier in `speed_context.*.speed_modifiers`.

Choice lock is not modeled.

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
- claim Choice lock, Life Orb recoil, Focus Sash survival, or Leftovers recovery is modeled
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
- say Life Orb recoil or Choice lock is not modeled when those effects appear in `unapplied_effects`
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
