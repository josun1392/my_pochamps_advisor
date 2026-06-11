# v2.9 Light Ball Payload Conflict Analysis

## Purpose

v2.8.1 verified that Light Ball still fails actual Gemini wording even after the v2.8 no-item residue guard.

Observed v2.8.1 result:

- `species_stat_item_context.available=true`
- holder species: `pikachu`
- required mention guard present
- Light Ball-specific no-item residue guard present
- actual Gemini response generated
- Gemini mentioned Light Ball as a Pikachu-specific offensive item context
- Gemini still described the damage estimate with `no item` default assumptions and said the Light Ball boost was not applied

This spike does not run Gemini. It inspects local code and default advice payload shape only.

## Summary

The likely root cause is a payload-level semantic conflict:

- `species_stat_item_context` says Light Ball is available as limited explanatory context.
- `damage_estimate.assumption_profile` still says `Default Level 50 / IV 31 / EV 0 / neutral nature / no item`.
- `damage_estimate.assumptions.item` is still `none`.
- `species_stat_item_context.species_stat_effect.damage_estimate_item_effect_status` is `not_applied`.
- the top-level Light Ball profile still says `effect_support_status=legal_but_not_modeled` and `damage_modifier_status=not_applied`.

So Gemini is receiving both:

- positive context: Light Ball exists and is Pikachu-specific
- negative/default context: the damage estimate is no-item / Light Ball is not applied

The v2.8 prompt guard fights the symptom, but the payload still gives Gemini a concrete reason to say the boost is not applied.

## Light Ball Effect Application

Light Ball has local metadata:

- `data/static/items_damage.json` includes `species_stat_items.light-ball`
- metadata marks:
  - `species=["pikachu"]`
  - `stats=["atk", "spa"]`
  - `multiplier_q12=8192`

The core damage engine has a species-stat item hook:

- `advisor/damage/item_modifiers.py` doubles the attacking stat for `light-ball` when `species == "pikachu"`.

However, the LLM advisor damage estimate builder does not currently pass Light Ball into the damage context as the applied attacker item:

- `llm/advisor_damage_estimate.py` uses `_attacker_item_for_damage(...)`.
- That helper applies catalog type-boost items and items in `SUPPORTED_ATTACKER_DAMAGE_ITEMS`.
- `SUPPORTED_ATTACKER_DAMAGE_ITEMS` includes Choice Band, Choice Specs, Life Orb, Muscle Band, and Wise Glasses.
- It does not include Light Ball or species-stat items.

Therefore, for the Light Ball advice payload:

- the raw damage estimate is not Light-Ball-adjusted
- `item_effects.attacker_item.status` is not `applied`
- `assumption_profile` remains the no-item default profile
- `species_stat_item_context.available=true` is explanatory context, not proof that raw damage rolls include Light Ball

This means the current payload does not cleanly support wording like "the damage estimate includes Light Ball" unless a future implementation changes the damage estimate path.

## No-Item Residue Sources

Local payload preflight for Pikachu + user-confirmed Light Ball with a damaging physical move found these relevant fields in the default advice payload.

### Top-Level Item Profile

`item_profiles.my_active` remains visible because Light Ball context is available:

```json
{
  "status": "user_confirmed",
  "item_id": "light-ball",
  "name_en": "Light Ball",
  "effects_scope": ["species_stat"],
  "legal": true,
  "legality_status": "legal",
  "effect_support_status": "legal_but_not_modeled",
  "damage_modifier_status": "not_applied"
}
```

Conflict:

- user-confirmed Light Ball is visible
- but the same profile says it is legal-but-not-modeled and not applied as a damage modifier

### Damage Estimate

`damage_estimate.assumption_profile` remains:

```json
{
  "id": "default_level50_ivs31_evs0_neutral_no_item",
  "label": "Default Level 50 / IV 31 / EV 0 / neutral nature / no item",
  "source": "system_default",
  "confidence": "rough_reference",
  "is_user_confirmed": false
}
```

`damage_estimate.assumptions.item` remains:

```json
"item": "none"
```

Conflict:

- this is the most direct source of Gemini's `no item` wording
- it is also technically accurate for the current raw damage estimate if Light Ball is not applied

### Damage Estimate Item Effects

In the default advice payload, the attacker item effect is scrubbed to:

```json
{
  "item_id": null,
  "status": "advice_payload_hidden",
  "applied_effects": [],
  "unapplied_effects": []
}
```

This avoids leaking unavailable debug reasons, but it does not give Gemini a positive `applied` status for Light Ball.

### Species Stat Item Context

`species_stat_item_context` remains available:

```json
{
  "available": true,
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
    "damage_estimate_item_effect_status": "not_applied",
    "raw_damage_rolls_changed": false,
    "ko_context_changed": false,
    "species_stat_adjusted_ko_integrated": false
  }
}
```

Conflict:

- available context says Light Ball is relevant
- `damage_estimate_item_effect_status=not_applied` tells Gemini the current estimate did not apply it
- `raw_damage_rolls_changed=false` and `ko_context_changed=false` are intended safety boundaries, but they also reinforce that Light Ball is not integrated into the estimate

## Filter and Prompt Interaction

The default advice filtering is not the primary bug:

- unavailable/deferred/blocked context filtering remains correct
- Light Ball is intentionally retained because `species_stat_item_context.available=true`
- there is no observed payload leak from unavailable Light Ball reasons

The issue is not that debug payload is leaking. The issue is that the allowed default advice payload contains mutually awkward facts:

1. Light Ball context is available.
2. The raw estimate still uses a no-item assumption profile.
3. The Light Ball-related item effect status is not applied.
4. The prompt says item effects are included only when `damage_estimate.item_effects` marks them as applied.

Gemini follows item_effects / assumption_profile more strongly than the limited context guard.

## Root Cause Candidates

### Candidate A: True Estimation Mismatch

The damage estimate is genuinely no-item for Light Ball because the advisor path does not pass species-stat items into `DamageContext.attacker_item`.

Evidence:

- `SUPPORTED_ATTACKER_DAMAGE_ITEMS` omits Light Ball.
- `_attacker_item_for_damage` does not include species-stat items.
- `damage_estimate.item_effects.attacker_item` is not `applied`.
- `assumption_profile.id` is `default_level50_ivs31_evs0_neutral_no_item`.

This is the strongest root cause.

### Candidate B: Context Overstates Underlying Calculation

The context wording currently says Light Ball may boost Pikachu's offensive stats in the underlying calculation when `item_effects` marks the supported modifier as applied.

But in the observed payload, `item_effects` does not mark it applied.

So Gemini can reasonably say Light Ball is not applied, even while acknowledging it is a Pikachu-specific context.

### Candidate C: Top-Level Profile Conflict

The top-level item profile remains user-confirmed Light Ball but also says:

- `effect_support_status=legal_but_not_modeled`
- `damage_modifier_status=not_applied`

This gives Gemini another route to infer that the Light Ball effect is selected but not applied.

### Candidate D: Prompt Guard Is Fighting Data

The v2.8 prompt says not to use no-item residue, but the JSON still contains no-item assumption/profile fields. The model is being asked not to say what the payload visibly says.

This is why further prompt hardening alone is unlikely to be robust.

## Recommended Fix Options

### Option A: Apply Light Ball in Advisor Damage Estimate

Teach `_attacker_item_for_damage` / item-effect summary to treat user-confirmed legal Light Ball on Pikachu as an applied species-stat damage item for physical and special damaging moves.

Pros:

- aligns `species_stat_item_context.available=true` with `damage_estimate.item_effects.attacker_item.status=applied`
- allows `assumption_profile` to switch to a supported-item profile
- removes the strongest reason for Gemini to say no item / not applied
- matches the existing core engine support for Light Ball in `attack_stat_item_mod`

Cons / risks:

- this is no longer explanatory-only context; it changes raw damage rolls
- requires careful regression tests for raw damage, Q12, and `ko_context`
- conflicts with prior v1.3/v2.x boundary that Light Ball context should not create new damage formula paths
- should be a separately approved implementation, not a v2.9 spike change

### Option B: Keep Raw Estimate No-Item, Reword Context as Explicitly Not Integrated

Change Light Ball advice contract so it says Light Ball is user-confirmed species-specific context, but raw damage rolls do not include it yet.

Pros:

- honest with the current payload
- avoids Gemini fighting `assumption_profile=no item`
- keeps raw damage / rolls / Q12 / `ko_context` unchanged
- smallest behavioral risk

Cons / risks:

- this likely means actual Gemini PASS criteria must change
- advice will not say Light Ball may boost the underlying calculation unless calculation actually applies it
- T1/T2 may decide this is less useful advice

### Option C: Specialize Assumption Profile Without Changing Raw Rolls

When Light Ball context is available, replace generic `no item` labels with a label such as:

- `Default stats / Light Ball context not integrated into raw rolls`
- `Raw damage estimate without species-stat adjustment; Light Ball context provided separately`

Pros:

- reduces misleading generic no-item residue
- keeps raw damage unchanged
- makes the payload conflict explicit instead of contradictory

Cons / risks:

- still tells Gemini Light Ball is not integrated
- may still fail if PASS requires positive "may boost underlying calculation" wording
- requires payload/contract changes and tests

### Option D: Remove `damage_estimate_item_effect_status` From Default Advice Context

Keep `damage_estimate_item_effect_status` in enriched/debug payload but omit it from default advice when status is not `applied`.

Pros:

- reduces one negative cue inside the available context
- preserves debug diagnostics
- narrow filtering change

Cons / risks:

- does not remove `assumption_profile=no item` or `assumptions.item=none`
- may hide useful source-of-truth information from the default advice payload
- still likely insufficient by itself

### Option E: Add a Distinct `species_stat_context_integrated=false` Field and Change PASS Criteria

Expose a clear field that says Light Ball is recognized and legal for Pikachu, but not integrated into raw damage rolls / KO context.

Pros:

- makes the current model honest and explicit
- prevents "not modeled" leak phrasing while preserving the actual limitation
- helps Gemini give safer advice

Cons / risks:

- would require T2 to redefine desired Light Ball wording from "may boost underlying calculation" to "recognized but not integrated"
- still not a damage application fix

## Recommendation

Do not add another prompt-only guard.

The next design decision should choose between two product meanings:

1. Light Ball should affect the shown damage estimates.
   - Then implement Option A as a separate, carefully tested damage-estimate integration task.
   - This will intentionally change raw damage rolls and must be reviewed as a mechanics/damage change.

2. Light Ball should remain explanatory-only and not affect shown damage estimates.
   - Then implement Option B/C/E as a payload/contract clarification task.
   - Update the actual Gemini PASS criteria so Gemini may say Light Ball is recognized but not integrated into raw rolls, without using generic no-item wording.

Current v2.x requirements are internally tense: they ask Gemini to positively mention Light Ball while the payload still says the estimate is no-item and the Light Ball effect is not applied.

## Boundaries Maintained

- actual Gemini call: not run in v2.9
- Vertex AI call: not run
- code changes: none
- payload filtering changes: none
- raw damage formula changed: no
- raw damage rolls changed: no
- Q12 multiplier changed: no
- `ko_context` changed: no
- new item implementation: no
- threshold/skip/xfail changes: none
