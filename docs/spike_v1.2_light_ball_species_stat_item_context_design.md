# v1.2 Light Ball Limited Species Stat Item Context Design

## Current State

`light-ball` is present in `data/static/champions_legal_items.json`:

- `item_id`: `light-ball`
- `category`: `hold_item`
- `legal`: `true`
- `legality_status`: `legal`
- `effect_support_status`: `legal_but_not_modeled`

`data/static/items_damage.json` also contains species-stat metadata:

- `species_stat_items.light-ball`
- `species`: `pikachu`
- `stats`: `atk`, `spa`
- `multiplier_q12`: `8192`

The damage helper already has Light Ball calculation support:

- `advisor/damage/items.py` loads `species_stat_items` as `ItemEffect(kind="species_stat")`.
- `advisor/damage/item_modifiers.py` applies `M_DOUBLE` in `attack_stat_item_mod()` when:
  - `item.item_id == "light-ball"`
  - `species == "pikachu"`

This means the next work should not create a new damage formula. The potential gap is advice visibility: Gemini can receive a small, additive, limited context explaining when the supported species-specific item relationship is relevant.

## Design Goal

Add a design for Light Ball as a limited explanatory context, not a mechanics expansion.

The context should:

- surface existing legal + metadata + helper support
- be species-specific to Pikachu
- only appear when the item profile is user-confirmed
- stay separate from raw `damage_estimate`, raw rolls, Q12 constants, and `ko_context`
- avoid implying exact final stats, exact EV/IV/nature-adjusted stats, final KO truth, or universal Light Ball behavior

## Recommended Context Name

Recommended:

- `species_stat_item_context`

Rationale:

- It matches the `items_damage.json` category `species_stat_items`.
- It can support Light Ball first while leaving room for future species-stat items if they ever become legal and safe.
- It avoids over-specializing the payload to `light_ball_context`.
- It communicates that this is item + species + stat metadata, not a final battle-state context.

Alternative:

- `light_ball_context`

This is simpler but less extensible. It is not recommended unless T1/T2 prefer a one-item-only surface for maximum explicitness.

## Available Conditions

`species_stat_item_context.available=true` only when all of the following are true:

1. The relevant holder item profile is `status: user_confirmed`.
2. `item_id` normalizes to `light-ball`.
3. `light-ball` passes Champions legal fixture coverage.
4. `items_damage.json` contains `species_stat_items.light-ball`.
5. The local item metadata has:
   - `kind == "species_stat"`
   - `species_lock` containing `pikachu`
   - boosted stats containing `atk` and/or `spa`
6. Holder species normalizes to `pikachu`.
7. The move is a damaging move with a known category that can use Attack or Special Attack.

Initial scope should be attacker-side only:

- user move estimates where `my_active` holds user-confirmed Light Ball
- opponent known move estimates where `opponent_active` holds user-confirmed Light Ball

Candidate moves should remain excluded.

## Unavailable / Hidden Conditions

`species_stat_item_context.available=false` may exist in enriched/debug payload with reason codes such as:

- `no_species_stat_item`
- `item_not_user_confirmed`
- `blocked_by_legal_item_coverage`
- `not_species_stat_item`
- `species_stat_metadata_missing`
- `holder_species_missing`
- `holder_species_not_supported`
- `move_category_missing`
- `move_not_damaging`

Default Gemini advice payload policy:

- keep `species_stat_item_context` only when `available=true`
- remove `available=false` contexts before default prompt serialization
- hide non-Pikachu holder reasons from default advice
- hide unsupported/missing metadata reasons from default advice
- hide blocked/deferred reasons from default advice
- keep debug/enriched reasons available for tests and diagnostics

This should use the existing registry/filtering approach from v1.0:

- add `species_stat_item_context` to item context registry only during implementation
- default advice filtering removes unavailable contexts
- item profile / `damage_estimate.item_effects` leak tests should be added if the unavailable item id can appear elsewhere

## Proposed Payload Shape

Available example:

```json
{
  "available": true,
  "mode": "limited_species_stat_item_context",
  "attacker_side": "my_active",
  "item": {
    "item_id": "light-ball",
    "status": "user_confirmed",
    "legal_status": "legal_modeled"
  },
  "species_stat_effect": {
    "holder_species_id": "pikachu",
    "supported_species": ["pikachu"],
    "boosted_stats": ["atk", "spa"],
    "effect_label": "may_boost_pikachu_offensive_stats",
    "formula_label": "species_stat_item_limited_modifier_context",
    "damage_estimate_item_effect_status": "applied",
    "raw_damage_rolls_changed": false,
    "ko_context_changed": false,
    "species_stat_adjusted_ko_integrated": false,
    "species_stat_adjusted_ohko_2hko_integrated": false
  },
  "limitations": [
    "Limited species-specific item context only.",
    "Do not generalize Light Ball to non-Pikachu holders.",
    "Raw KO context remains separate from this context.",
    "Final EV/IV/nature-adjusted stat truth is not inferred."
  ],
  "is_final_battle_truth": false
}
```

Unavailable example for debug/enriched only:

```json
{
  "available": false,
  "mode": "limited_species_stat_item_context",
  "reason": "holder_species_not_supported",
  "item": {
    "item_id": "light-ball",
    "status": "user_confirmed"
  },
  "debug": {
    "holder_species_id": "raichu",
    "supported_species": ["pikachu"]
  }
}
```

The unavailable example must not be present in the default Gemini advice payload.

## Relationship To Existing Damage Helper

The existing damage helper is the source of calculation behavior:

- `attack_stat_item_mod()` returns `M_DOUBLE` for Light Ball only when the holder species is `pikachu`.
- The context should not duplicate this calculation.
- The context should not introduce a new multiplier.
- The context should not change Q12 constants.
- The context should not change raw damage rolls.
- The context should not add a Light-Ball-adjusted KO/OHKO/2HKO layer.

The context is explanatory, similar to `type_boost_context`:

- if the damage estimate already applied the supported modifier, the context can explain why
- if conditions do not match, the default advice payload stays quiet
- `damage_estimate.item_effects` remains the source of truth for whether a supported item modifier was applied to a specific estimate

## Gemini Wording

Allowed:

- "Light Ball may boost Pikachu's offensive stats in the underlying calculation."
- "This is species-specific to Pikachu."
- "Do not generalize this item to non-Pikachu holders."
- "Do not treat this as a final KO guarantee."
- "The raw `ko_context`, if present, remains separate from this limited item context."

Forbidden:

- "guaranteed KO"
- "always doubles damage"
- "confirmed OHKO because of Light Ball"
- "all Electric-type Pokemon benefit from Light Ball"
- "Light Ball works on any holder"
- "final stats are fully known"
- "exact EV/IV/nature-adjusted stats are known"
- "Light Ball proves the KO"
- "Light Ball changes final KO probability"

When unavailable:

- do not mention Light Ball, non-Pikachu mismatch, unsupported reason, missing metadata, or "not modeled" in default advice
- only explain the reason if the user explicitly asks about Light Ball

## v1.3 Implementation Proposal

Recommended:

**v1.3 - Light Ball Limited Species Stat Item Context Implementation**

Implementation scope:

- add `llm/advisor_species_stat_item_context.py`
- attach move-level `species_stat_item_context` next to relevant damage estimates
- support Light Ball only
- attacker-side only
- user-confirmed item only
- Champions legal fixture gate required
- local `items_damage.json` metadata required
- holder species must be Pikachu
- default advice payload includes only `available=true`
- debug/enriched payload may retain unavailable reasons
- add registry key `species_stat_item_context`
- update prompt/contract docs and tests

Tests:

- Pikachu + user-confirmed Light Ball + physical move -> context available
- Pikachu + user-confirmed Light Ball + special move -> context available
- non-Pikachu + user-confirmed Light Ball -> unavailable in enriched/debug, hidden from default advice
- unknown/unconfirmed Light Ball -> hidden from default advice
- non-legal/debug species-stat item -> hidden from default advice
- `damage_estimate.item_effects` remains the source of applied modifier truth
- unavailable item id/reason does not leak through default advice payload string
- type-boost context regression
- Choice Scarf `speed_context` regression
- raw damage formula unchanged
- raw damage rolls unchanged
- Q12 unchanged
- `ko_context` unchanged
- full pytest

## Deferred / Out Of Scope

Do not include in v1.3:

- new damage formula implementation
- raw damage roll changes
- Q12 multiplier changes
- `ko_context` calculation changes
- final stat truth calculation
- EV/IV/nature inference
- final KO probability calculation
- Light-Ball-adjusted KO/OHKO/2HKO context
- Turn Engine
- item consumption
- Mega Evolution
- ability/weather/terrain interaction
- UI changes
- sample additions
- Fairy Feather support
- non-Light-Ball species-stat items
- non-Pikachu Light Ball support

## Policy

Maintain these rules:

- Champions legal fixture is required for user-facing modeled item context.
- `items_damage.json` metadata is required but is not legal coverage by itself.
- existing damage helper support is required but is not legal coverage by itself.
- default advice payload includes only available legal contexts.
- unavailable/deferred/blocked reasons remain debug/enriched metadata only.
- raw `damage_estimate` and raw `ko_context` remain separate from explanatory item context.
- Gemini must not infer final KO, final stats, EV/IV/nature, or broader holder support from Light Ball context.
