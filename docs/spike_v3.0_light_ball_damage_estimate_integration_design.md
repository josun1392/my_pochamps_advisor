# v3.0 Light Ball Damage Estimate Integration Design

## Purpose

Design how Light Ball should be integrated into the advisor damage estimate after the v2.8.1/v2.9 failure analysis.

This is a design-only spike:

- no implementation
- no actual Gemini call
- no Vertex AI call
- no damage formula change
- no raw roll change
- no `ko_context` change
- no payload filtering change

## Background

Current actual Gemini verification status:

- Focus Band: PASS
- Quick Claw: PASS
- Chilan Berry: PASS
- Light Ball: FAIL

v2.9 found that Light Ball failure is not just prompt wording. The default advice payload gives Gemini conflicting signals:

- `species_stat_item_context.available=true`
- holder species is `pikachu`
- Light Ball context is visible and labeled as Pikachu-specific
- but `damage_estimate.assumption_profile.label` still says `no item`
- `damage_estimate.assumptions.item` is still `none`
- the top-level Light Ball item profile still has `damage_modifier_status=not_applied`
- `species_stat_item_context.species_stat_effect.damage_estimate_item_effect_status=not_applied`

So Gemini reasonably concludes that Light Ball exists but is not applied to the estimate.

T2 direction for v3.x:

- Prefer integrating user-confirmed Pikachu + Light Ball into the advisor damage estimate rather than keeping it explanatory-only.
- Because this intentionally changes raw damage rolls and `ko_context` for a narrow case, design first and implement later.

## Current Code Facts

### Metadata

`data/static/items_damage.json` contains:

- `species_stat_items.light-ball`
- `species=["pikachu"]`
- `stats=["atk", "spa"]`
- `multiplier_q12=8192`

`data/static/champions_legal_items.json` marks Light Ball legal, but the fixture's current effect support label is still `legal_but_not_modelled`/`legal_but_not_modeled` style metadata depending on source field spelling. The implementation should treat Champions legal status and local damage support as separate checks.

### Existing Damage Engine Support

`advisor/damage/item_modifiers.py` contains `attack_stat_item_mod(...)`, which can return a double offensive stat modifier for:

- `item.item_id == "light-ball"`
- `species == "pikachu"`

Important nuance:

- `advisor/damage/formula.py` currently imports `get_atk_item_modifier`, `get_spa_item_modifier`, and `get_final_atk_item_modifier`.
- The observed `calc_damage_rolls()` attack-stat modifier chain uses `get_atk_item_modifier(...)` / `get_spa_item_modifier(...)` by item id.
- The Light Ball-aware helper `attack_stat_item_mod(...)` exists, but the current formula path does not appear to call it directly.

Therefore, simply passing `get_item("light-ball")` into `DamageContext.attacker_item` may not be sufficient unless v3.1 verifies the formula path actually applies the species-stat modifier. The implementation must either:

1. route the formula attack-stat item modifier through `attack_stat_item_mod(...)`, or
2. pre-adjust the advisor attack stat using a shared helper before building `DamageContext`, while making that choice explicit and tested.

The preferred design is to use the shared damage-engine helper in the formula path rather than duplicating Light Ball stat math inside the advisor layer.

## Proposed Scope

Integrate Light Ball only into advisor damage estimates under strict conditions.

Do not add a general species-stat item framework in v3.1 unless needed for clean code. The first implementation should support only Light Ball on Pikachu.

## Light Ball Application Conditions

Apply Light Ball to the advisor damage estimate only when all conditions are true:

1. Attacker item profile exists and has `status == "user_confirmed"`.
2. Attacker item id normalizes to `light-ball`.
3. Attacker species normalizes to `pikachu`.
4. Champions legal fixture says `light-ball` is legal.
5. `items_damage.json` has `species_stat_items.light-ball`.
6. The metadata kind resolves to `species_stat`.
7. The metadata supported species includes `pikachu`.
8. The selected/available/known move is damaging.
9. Move category is `physical` or `special`.
10. The category uses a real offensive stat:
    - physical uses Atk
    - special uses SpA

Do not apply Light Ball when:

- holder is not Pikachu
- item is unconfirmed, unknown, none, or system default
- item is blocked by legal fixture
- species-stat metadata is missing
- move is status category
- move category is missing or unsupported
- Light Ball is on the defender side for an attacker damage estimate
- the item appears only in opponent assumptions or candidate move metadata

## Damage Estimate Integration

### Raw Damage Formula

For the narrow Light Ball-eligible case, the damage estimate should use Light Ball's species-stat modifier in the same raw damage calculation used for all estimates.

Expected implementation shape:

- `llm/advisor_damage_estimate._attacker_item_for_damage(...)` should return `get_item("light-ball")` for user-confirmed legal Pikachu + Light Ball.
- The damage formula path should apply the species-stat modifier for that `ItemEffect`.
- If the current formula path does not call `attack_stat_item_mod(...)`, v3.1 must patch that formula-level modifier path or deliberately pre-adjust the stat in the advisor layer with tests.

Preferred formula-level approach:

- Replace or augment the direct `get_atk_item_modifier` / `get_spa_item_modifier` chain with `attack_stat_item_mod(ctx.attacker_item, ctx.is_physical, ctx.attacker_species, ctx.attacker_is_transformed)`.
- Preserve existing Choice Band / Choice Specs behavior because `attack_stat_item_mod(...)` delegates to `get_atk_item_modifier` / `get_spa_item_modifier` first.
- Confirm no regression for type plates, Choice items, and normal item modifier flow.

### Raw Damage Rolls

When Light Ball is applied:

- raw damage rolls should change for eligible Pikachu physical and special damaging moves.
- physical moves should use the Atk boost.
- special moves should use the SpA boost.
- status moves should still have no estimate.
- non-Pikachu holders should remain unchanged.

This is an intentional raw-roll change under the narrow application conditions.

### `damage_estimate.assumption_profile`

For applied Light Ball:

- `assumption_profile.id` should not be `default_level50_ivs31_evs0_neutral_no_item`.
- use the existing supported damage item profile if acceptable:
  - `default_level50_ivs31_evs0_neutral_with_damage_item`
- or add a clearer species-stat item profile in v3.1 if T2 wants precision:
  - `default_level50_ivs31_evs0_neutral_with_species_stat_item`

Conservative recommendation:

- reuse the existing "with damage item" profile first if tests and docs can make it clear that Light Ball is a supported item modifier in the estimate.
- consider a more specific profile only if the wording remains ambiguous.

### `damage_estimate.assumptions.item`

When Light Ball is applied:

- `damage_estimate.assumptions.item` should become `supported_attacker_damage_item_applied` or a new more precise value such as `supported_species_stat_item_applied`.
- It must not remain `none`.

Conservative recommendation:

- reuse `supported_attacker_damage_item_applied` for consistency with existing item-applied paths.
- document that this includes supported attacker-side species-stat items when `item_effects.attacker_item.status == "applied"`.

### `damage_estimate.item_effects`

When Light Ball is applied:

`damage_estimate.item_effects.attacker_item` should be explicit:

```json
{
  "item_id": "light-ball",
  "name_en": "Light Ball",
  "effect_type": "species_stat_item_modifier",
  "boosted_stats": ["atk", "spa"],
  "modifier": 2.0,
  "status": "applied",
  "applied_effects": ["species_stat_modifier"],
  "unapplied_effects": [],
  "reason": "Holder species is Pikachu and move category uses a boosted offensive stat."
}
```

Exact field names can follow existing style, but tests should assert:

- `status == "applied"`
- `item_id == "light-ball"`
- effect type identifies species-stat behavior
- boosted stat matches move category or includes metadata list
- no "not_applied" status in the default advice payload for the eligible case

For non-Pikachu or unconfirmed cases:

- `item_effects` should remain not applied or hidden according to existing filtering rules.
- `species_stat_item_context` should be unavailable/hidden in default advice.

### `ko_context`

`ko_context` is built from the damage estimate.

If Light Ball changes `damage_estimate.rolls`, then `ko_context` should naturally reflect the Light-Ball-adjusted rolls:

- OHKO chance is based on the adjusted rolls.
- 2HKO limited min/max context is based on the adjusted damage range.
- `ko_context` remains limited damage-roll context only.
- It still does not model accuracy, speed order, priority, recovery, hazards, chip, switching, protection, Turn Engine, or item consumption.

Do not add a separate Light-Ball-adjusted KO probability field. The existing `ko_context` should simply consume the adjusted raw rolls when the estimate itself is adjusted.

## `species_stat_item_context` Role

### Option A: Applied Sibling Context

Light Ball context becomes a sibling explanation of an applied `damage_estimate.item_effects` modifier.

Under this option:

- `species_stat_item_context.available=true` aligns with `damage_estimate.item_effects.attacker_item.status=applied`.
- `species_stat_effect.damage_estimate_item_effect_status` becomes `applied`.
- `raw_damage_rolls_changed` should be reconsidered:
  - current field says `false`
  - after integration, that is no longer true for eligible Light Ball moves
  - either change it to `true`, rename it, or remove it from default advice
- `ko_context_changed` should also be reconsidered:
  - if `ko_context` is derived from adjusted rolls, then it is changed relative to no-item baseline
  - the safer wording is that `ko_context` is based on the current adjusted damage estimate, still not final battle truth

Pros:

- eliminates the current Gemini conflict
- makes Light Ball advice useful and consistent
- aligns context, item_effects, assumption profile, and raw rolls

Cons:

- intentionally changes raw damage rolls for a user-visible case
- requires updating old v1.3/v2.x docs/tests that said the context never changed rolls
- requires careful regression around `ko_context`

### Option B: Honest Explanatory-Only Context

Light Ball context remains explanatory-only and does not imply application to raw rolls.

Under this option:

- `species_stat_item_context.available` might become a weaker status such as `available=false` or `integrated=false`.
- wording should say Light Ball is recognized but not integrated into the raw damage estimate.
- PASS criteria should allow "not integrated" but avoid generic "no item" phrasing.

Pros:

- no raw damage/KO changes
- lower implementation risk
- honest with the current payload

Cons:

- T2 has already indicated Option A is preferred
- advice remains less useful
- still requires payload/contract changes to avoid "not modeled" failure wording

### Recommendation

Use Option A for v3.1, but treat it as a narrow damage-estimate integration task, not a prompt polish task.

## Gemini Wording After Integration

Allowed wording:

- "Light Ball is applied for Pikachu in the damage estimate."
- "Light Ball is Pikachu-specific."
- "The damage estimate uses default stat assumptions plus the supported Light Ball modifier."
- "Do not treat this as a guaranteed KO."
- "Exact EV/IV/nature-adjusted final stats are still not known."

Forbidden wording:

- "no item effects"
- "assuming no item"
- "Light Ball not applied"
- "Light Ball works on any holder"
- "all Electric-type Pokemon benefit"
- "guaranteed KO"
- "confirmed OHKO"
- "exact final stats are known"

The prompt should no longer need to fight visible no-item payload fields for the eligible Light Ball case.

## v3.1 Implementation Plan

1. Add a narrow Light Ball species-stat item application helper in `llm/advisor_damage_estimate.py`.
   - Check user-confirmed item profile.
   - Check normalized item id.
   - Check attacker species.
   - Check Champions legal fixture.
   - Check `items_damage.json` metadata.
   - Check physical/special damaging category.
2. Decide modifier layer:
   - preferred: route formula attack-stat item modifier through `attack_stat_item_mod(...)`
   - fallback: pre-adjust the advisor attack stat using the shared helper before building `DamageContext`
3. Mark `damage_estimate.item_effects.attacker_item.status=applied` for eligible Light Ball.
4. Set `damage_estimate.assumptions.item` away from `none`.
5. Set `assumption_profile` to a supported item profile.
6. Update `species_stat_item_context`:
   - align `damage_estimate_item_effect_status` with applied state
   - update or remove stale `raw_damage_rolls_changed=false` and `ko_context_changed=false`
   - keep final stat truth and final KO guarantee guards
7. Update default advice prompt/contract wording:
   - Light Ball is applied for Pikachu in the damage estimate when item_effects marks applied
   - exact final EV/IV/nature-adjusted stats remain unknown
   - no guaranteed KO
8. Update docs.
9. Run full regression and then a separate actual Gemini verification after implementation approval.

## Required v3.1 Tests

### Damage Estimate Tests

1. Pikachu + user-confirmed Light Ball + physical damaging move:
   - damage range is greater than no-item baseline
   - `item_effects.attacker_item.status == "applied"`
   - `assumptions.item != "none"`
   - assumption profile is a supported item profile
2. Pikachu + user-confirmed Light Ball + special damaging move:
   - damage range is greater than no-item baseline
   - applied item status is present
3. Pikachu + user-confirmed Light Ball + status move:
   - no damage estimate
   - no misleading applied item effect
4. Non-Pikachu + user-confirmed Light Ball:
   - damage range equals no-item baseline
   - `species_stat_item_context` is unavailable in enriched/debug
   - default advice payload hides the context/reason
5. Pikachu + unconfirmed Light Ball:
   - damage range equals no-item baseline
   - default advice hides Light Ball context
6. Defender-side Light Ball:
   - not applied to attacker damage

### Payload Contract Tests

7. Default advice payload for eligible Pikachu + Light Ball:
   - no `no item` assumption profile label
   - no `assumptions.item=none`
   - `species_stat_item_context.available=true`
   - `damage_estimate_item_effect_status=applied`
   - no generic not-applied/no-item residue
8. Candidate moves remain excluded from damage/context fields.
9. Existing unavailable/deferred/blocked filtering remains unchanged.

### `ko_context` Tests

10. `ko_context.ohko` and `two_hko` use the adjusted damage rolls.
11. `ko_context` remains limited and does not claim final battle truth.
12. No new Light-Ball-specific KO probability field is introduced.

### Regression Tests

13. Existing Focus Band `survival_context` PASS behavior unchanged.
14. Quick Claw `speed_order_context` unchanged.
15. Chilan Berry `chilan_berry_context` unchanged.
16. Type-boost item_effects scrub unchanged.
17. Standard resist berry behavior unchanged.
18. Choice Scarf remains in `speed_context`, not `speed_order_context`.
19. Existing Choice Band / Choice Specs / Life Orb / Muscle Band / Wise Glasses tests unchanged except where formula helper routing requires expectation updates.

## Risks

### Raw Damage Roll Changes

Eligible Pikachu + Light Ball moves should change raw rolls. This is intended but must be explicitly scoped.

Risk:

- tests or docs that previously asserted Light Ball did not change raw rolls must be updated.

### `ko_context` Shift

Since `ko_context` derives from rolls, it should shift when rolls shift.

Risk:

- if tests assert old no-item `ko_context` behavior, they must be changed only for eligible Light Ball.

### Formula Hook Accuracy

The Light Ball-aware helper exists, but current formula code may not call it.

Risk:

- passing Light Ball into `DamageContext` may not be enough.
- v3.1 must verify actual roll deltas, not only item_effect status.

### Category Handling

Light Ball affects Atk and SpA, so both physical and special damaging moves should work.

Risk:

- accidental physical-only or special-only implementation.

### Species Matching

Current context normalizes species names. Formula currently receives `attacker_species=str(attacker.get("name_en", ""))`.

Risk:

- capitalization or form names may break Light Ball matching.
- v3.1 should normalize species ids consistently for `pikachu`.

### Item Profile Source of Truth

Champions legal fixture still carries "legal but not modeled" style effect-support metadata.

Risk:

- implementation must distinguish legal fixture status from local damage support.
- local `items_damage.json` and engine support should define damage support for Light Ball.

### Duplication Between `item_effects` and Context

After integration, both `item_effects` and `species_stat_item_context` will describe Light Ball.

Risk:

- duplicate or contradictory wording.
- resolve by making `item_effects` the source of applied math and `species_stat_item_context` the limited explanation sibling.

## Non-Goals

- no final EV/IV/nature inference
- no final stat truth calculation
- no final KO probability
- no Turn Engine
- no item consumption
- no Mega Evolution
- no ability/weather/terrain expansion
- no UI/sample changes
- no broad species-stat item rollout beyond Light Ball unless separately approved

## Boundaries Maintained in v3.0

- actual Gemini call: not run
- Vertex AI call: not run
- code changes: none
- raw damage formula changed: no
- raw damage rolls changed: no
- Q12 multiplier changed: no
- `ko_context` changed: no
- payload filtering changed: no
