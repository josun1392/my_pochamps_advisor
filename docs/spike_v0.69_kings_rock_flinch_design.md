# v0.69 King's Rock Flinch Design

## Current State

The advisor currently has several additive battle-context layers:

- `damage_estimate` provides raw damage min/max/rolls under stated assumptions.
- `ko_context` provides limited damage-roll KO/OHKO/2HKO context.
- `survival_context` provides limited Focus Sash survival context.
- `recovery_context` provides limited Sitrus Berry / Leftovers recovery context.
- `accuracy_context` provides limited Bright Powder hit reliability context.
- `critical_context` provides limited Scope Lens critical-hit likelihood context.
- Type boosting items can modify raw damage only through the supported damage item modifier path.
- Choice Scarf can affect `speed_context`.
- `opponent_assumptions` remains context-only and does not feed damage, Speed, KO, survival, recovery, accuracy, or critical-hit calculations.

King's Rock is recognized as a legal held item in `data/static/champions_legal_items.json`, but its local utility effect is not modeled:

- `item_id`: `kings-rock`
- `legal`: `true`
- `effect_support_status`: `legal_but_not_modelled`
- `ui_status`: `recognized_not_modelled`

The lower-level move secondary-effect helper in `advisor/damage/move_categories.py` explicitly treats item-added effects such as King's Rock flinch chance as outside its scope. That helper is a turn-engine predicate and does not mutate battle state. There is no current LLM payload field for flinch pressure, final flinch probability, flinch-adjusted KO probability, target action state, or exact turn sequencing.

## Problem Definition

King's Rock is not a direct damage boost. It is a flinch pressure item.

Flinch pressure is useful advice context, but it depends on battle facts that the current advisor does not model:

- whether the move hits
- whether the target can flinch
- whether the target would still act after being hit
- speed/order and priority
- move eligibility and multi-hit behavior
- abilities, items, and field interactions
- exact turn sequencing

If King's Rock is mixed into `damage_estimate` or `ko_context`, the advisor may imply that raw damage, KO chance, or final battle outcome already includes flinch odds. That would overstate the current model. The safer design is a separate limited `flinch_context` that can warn about possible flinch pressure while leaving raw damage and raw KO context unchanged.

## King's Rock Item Behavior

Design stance:

- Treat King's Rock as a flinch pressure item.
- Require user-confirmed item state before modeling.
- Do not infer King's Rock from legal item candidates, possible samples, or unknown held items.
- Do not treat King's Rock as direct damage boost.
- Do not calculate final flinch probability in the first LLM payload version.
- Do not calculate flinch-adjusted KO or outcome probability in the first LLM payload version.
- Confirm exact modifier, move eligibility, multi-hit handling, and Champions/PoChamps rule compatibility before exposing numeric flinch probability.

Until rule support is explicitly approved, the advisor should prefer wording such as "may add flinch pressure" rather than claiming a precise chance or final action denial.

## Flinch Context Scope

Recommended v0.70 scope:

- attacker item is user-confirmed `kings-rock`
- additive `flinch_context`
- move-level sibling placement when practical
- attach to my selected/available moves when my active Pokemon is the attacker
- attach to opponent known moves when opponent active Pokemon is the attacker
- candidate moves excluded
- raw `damage_estimate.damage_range` unchanged
- raw `damage_estimate.rolls` unchanged
- raw `ko_context` unchanged
- no final flinch probability
- no flinch-adjusted outcome probability
- no target action state
- no speed/order integration
- no multi-hit handling
- no Turn Engine

Out of first implementation scope:

- final flinch probability calculation
- flinch-adjusted KO probability
- flinch-adjusted recommendation ranking
- speed/order integration
- target action state
- move eligibility engine
- multi-hit flinch handling
- ability, weather, and item interaction modeling
- Protect, Substitute, switching, or final turn simulation

## Proposed Payload Shape

Recommended common wrapper:

```json
{
  "available": true,
  "mode": "limited_flinch_context",
  "scope": "selected_move_only",
  "attacker_side": "my_active",
  "item": {
    "item_id": "kings-rock",
    "status": "user_confirmed"
  },
  "flinch_effect": {
    "type": "kings_rock",
    "effect_label": "may_add_flinch_pressure",
    "formula_label": "kings_rock_limited_flinch_modifier",
    "flinch_pressure_note": "King's Rock may add flinch pressure under limited assumptions.",
    "raw_damage_rolls_changed": false,
    "ko_context_changed": false,
    "final_flinch_probability_integrated": false,
    "flinch_adjusted_outcome_integrated": false,
    "requires_turn_engine": true
  },
  "limitations": [
    "Limited flinch context only.",
    "Final flinch probability, speed/order, target action state, ability interactions, multi-hit handling, and turn sequencing are not modeled."
  ],
  "is_final_battle_truth": false
}
```

Unavailable shape:

```json
{
  "available": false,
  "mode": "limited_flinch_context",
  "reason": "no_kings_rock",
  "is_final_battle_truth": false
}
```

Reason code candidates:

- `no_kings_rock`
- `item_not_user_confirmed`
- `unsupported_flinch_item`
- `damage_estimate_missing`
- `move_flinch_eligibility_unknown`
- `target_action_state_missing`
- `turn_engine_required`

## Placement Options

### Option A - move-level sibling field

Add `flinch_context` as a sibling on the relevant move payload, beside `damage_estimate`, `ko_context`, `accuracy_context`, `critical_context`, `recovery_context`, and `survival_context`.

Pros:

- Keeps flinch pressure tied to a move.
- Keeps flinch semantics separate from raw damage and raw KO fields.
- Matches the current move-level sibling pattern used by `accuracy_context` and `critical_context`.
- Leaves room for future move eligibility metadata.

Cons:

- The move payload grows as more limited contexts are added.
- Prompt guardrails must keep context notes concise.

### Option B - `damage_estimate` sibling

Attach `flinch_context` near the same move's `damage_estimate`.

Pros:

- Easy to implement if the current code attaches all damage-adjacent contexts together.
- Easy for the LLM to see raw damage, KO, accuracy, critical, and flinch context in one local move block.

Cons:

- Placement near damage can make it easier to misread as included in raw damage.
- Requires strong guardrails that raw damage and KO context are unchanged.

### Option C - top-level flinch context

Add top-level `flinch_context` keyed by side or active attacker.

Pros:

- Separates item state from damage estimates.
- Avoids repeated King's Rock notes across moves.

Cons:

- Harder to connect to individual move context.
- Awkward for future move eligibility, contact, hit-count, or already-has-flinch rules.
- Less consistent with selected/available move and opponent known move context placement.

Recommendation:

- Prefer **Option A** for v0.70: a move-level sibling field.
- If implementation structure makes that awkward, Option B is acceptable as an additive sibling beside the move's `damage_estimate`.
- Do not put `flinch_context` inside `damage_estimate`.
- Do not put `flinch_context` inside `ko_context`.
- Do not expose final flinch probability or flinch-adjusted outcome probability in the first implementation.

## Flinch Amount Policy

Initial implementation should not expose a numeric final flinch probability.

Recommended policy:

- Require user-confirmed King's Rock.
- Include `effect_label`: `may_add_flinch_pressure`.
- Include `formula_label`: `kings_rock_limited_flinch_modifier`.
- Include `flinch_pressure_note` or equivalent.
- Include `final_flinch_probability_integrated=false`.
- Include `flinch_adjusted_outcome_integrated=false`.
- Include `raw_damage_rolls_changed=false`.
- Include `ko_context_changed=false`.
- Do not include `final_flinch_probability`.
- Do not include `flinch_adjusted_ko_chance`.
- Do not include `target_cannot_act_probability`.

Rule validation notes:

- Exact King's Rock modifier, move eligibility, interaction with existing move flinch effects, multi-hit behavior, ability interactions, and Champions/PoChamps compatibility need separate validation.
- `advisor/damage/move_categories.py` currently avoids item-added King's Rock flinch modeling, reinforcing that this belongs outside raw damage.
- A future Turn Engine or probability model should own numeric flinch and outcome probability.

Possible future fields after rule validation:

- `flinch_chance_bonus`
- `base_flinch_chance`
- `effective_flinch_chance`
- `move_flinch_eligible`
- `hit_count_policy`
- `target_can_flinch`
- `probability_source`
- `rule_verification_status`

## LLM Guardrails

Required guardrails:

- `flinch_context` is limited context only.
- King's Rock may add flinch pressure.
- Raw damage estimates are unchanged.
- Raw `ko_context` is unchanged.
- KO/OHKO/2HKO estimates do not include flinch chance.
- Final flinch probability is not calculated.
- Flinch-adjusted outcome probability is not calculated.
- Do not claim the target will flinch.
- Do not claim the target cannot move.
- Do not claim final action denial unless a future Turn Engine explicitly calculates it.
- Do not infer King's Rock if the item is unknown or unconfirmed.
- Do not describe King's Rock as a direct damage boost.
- Speed/order, target action state, ability interactions, multi-hit handling, and turn sequencing are not modeled.

Good wording:

- "King's Rock may add flinch pressure as limited context, but raw damage and KO estimates do not include flinch chance."
- "The raw KO chance is separate from any King's Rock flinch possibility; flinch-adjusted outcome probability is not calculated."
- "This is not a final flinch probability; speed/order, target action state, ability interactions, multi-hit handling, and turn sequencing are not modeled."

Bad wording:

- "King's Rock boosts the damage."
- "This move will flinch the target."
- "The target cannot move."
- "The KO chance includes King's Rock flinch chance."
- "The final flinch probability is confirmed."
- "King's Rock guarantees the safer play."

When `flinch_context.available` is false, or no `flinch_context` is present for a move, the LLM should not invent King's Rock flinch effects or force a flinch limitation sentence.

## Tests Plan

Future implementation tests should cover:

- user-confirmed King's Rock -> `flinch_context.available=true`
- King's Rock unknown or unconfirmed -> unavailable `item_not_user_confirmed` or absent
- no King's Rock -> unavailable `no_kings_rock` or absent
- unsupported flinch item -> unavailable `unsupported_flinch_item`
- missing damage estimate -> unavailable `damage_estimate_missing`
- move flinch eligibility unknown policy documented
- `flinch_context` includes `final_flinch_probability_integrated=false`
- `flinch_context` includes `flinch_adjusted_outcome_integrated=false`
- raw damage min/max/rolls unchanged
- raw `ko_context` unchanged
- `flinch_context` does not alter OHKO chance
- my selected/available move direction uses `attacker_side: my_active`
- opponent known move direction uses `attacker_side: opponent_active`
- candidate moves excluded
- prompt guardrails for no direct damage boost, no will-flinch claim, no target-cannot-act claim, and no flinch-adjusted outcome
- existing Scope Lens critical regression
- existing Bright Powder accuracy regression
- existing recovery context regression
- existing KO context regression
- existing Focus Sash regression
- existing type item regression
- existing Choice Scarf speed context regression
- existing opponent assumptions regression
- full pytest

## Interaction With Existing Systems

`flinch_context` and `damage_estimate`:

- King's Rock does not change damage min/max/rolls.
- Raw damage remains the current non-final damage estimate.
- Flinch chance is not folded into raw damage in v0.70.

`flinch_context` and `ko_context`:

- `ko_context` remains raw damage-roll context.
- KO/OHKO/2HKO estimates do not include flinch chance.
- A later flinch-adjusted outcome probability should be a separate, explicitly versioned feature.

`flinch_context` and `accuracy_context`:

- Bright Powder hit reliability and King's Rock flinch pressure are separate limited contexts.
- A flinch requires a hit, but v0.70 should not multiply accuracy and flinch chance into final outcome probability.

`flinch_context` and `critical_context`:

- Scope Lens critical-hit likelihood and King's Rock flinch pressure are separate limited contexts.
- Critical-hit chance and flinch chance should not be combined without a future probability model.

`flinch_context`, `recovery_context`, and `survival_context`:

- Focus Sash, Sitrus Berry, Leftovers, and King's Rock remain separate limited contexts.
- King's Rock plus Focus Sash, recovery, or Bright Powder interactions are deferred.
- The LLM should not combine these contexts into final battle truth.

Speed and Turn Engine:

- Choice Scarf `speed_context` is raw/effective Speed comparison only and is not final turn order.
- Do not use `speed_context` to claim a King's Rock flinch will occur before the target acts.
- Target action state and exact turn sequencing require future Turn Engine work.

Other systems:

- `opponent_assumptions` is unrelated and remains context-only.
- Existing move secondary-effect helpers do not model item-added King's Rock flinch effects.

## v0.70 Candidate

Recommended:

`v0.70 - King's Rock Limited Flinch Context Implementation`

Include:

- helper for limited flinch context
- user-confirmed King's Rock only
- additive move-level `flinch_context`
- label/formula based flinch pressure note
- raw damage unchanged
- raw `ko_context` unchanged
- no final flinch probability
- no flinch-adjusted outcome probability
- tests and docs
- no Turn Engine

Alternative:

`v0.70 - Flinch Rule Validation Design`

Choose this if T1/T2 want to validate exact King's Rock modifier, move eligibility, multi-hit behavior, and Champions/PoChamps compatibility before any payload field is added.

T3 recommendation:

- Proceed with v0.70 implementation only if T1/T2 accept label-first flinch context without numeric final flinch probability.
- If exact flinch chance is required, run rule validation first.
- In either path, keep flinch pressure separate from raw damage and raw KO context.

## Out of Scope

- code implementation
- `flinch_context` implementation
- final flinch probability
- flinch-adjusted outcome probability
- Turn Engine
- speed/order integration
- target action state
- ability/weather/item interaction modeling
- multi-hit handling
- KO context modification
- raw damage roll modification
- Focus Sash / Sitrus / Bright Powder / Scope Lens interaction implementation
- UI changes
- fixture changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits
