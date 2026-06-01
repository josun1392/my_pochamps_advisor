# v0.65 Scope Lens Critical Hit Design

## Current State

The advisor now has several additive battle-context layers:

- `damage_estimate` provides raw damage min/max/rolls under stated assumptions.
- `ko_context` provides limited damage-roll KO/OHKO/2HKO context.
- `survival_context` provides limited Focus Sash survival context.
- `recovery_context` provides limited Sitrus Berry / Leftovers recovery context.
- `accuracy_context` provides limited Bright Powder hit reliability context.
- Type boosting items can modify raw damage only through the supported damage item modifier path.
- Choice Scarf can affect `speed_context`.
- `opponent_assumptions` remains context-only and does not feed damage, Speed, KO, survival, recovery, or accuracy.

Scope Lens is recognized as a legal held item in `data/static/champions_legal_items.json`, but its local utility effect is still not modeled:

- `item_id`: `scope-lens`
- `legal`: `true`
- `effect_support_status`: `legal_but_not_modeled`
- `ui_status`: `recognized_not_modeled`
- `effect_support.utility_effect`: `not_supported`

Lower-level critical-hit utilities already exist in `advisor/damage/crit.py`:

- `resolve_crit_stage()` can account for Scope Lens as a +1 critical-hit stage item.
- `crit_probability()` can map stages to Gen 9 probability fractions.
- `apply_crit_modifier()` and `resolve_crit_multiplier()` can apply critical-hit damage modifiers.

However, those lower-level pieces are not exposed as an LLM payload context. The current advisor payload does not include Scope Lens critical-hit context, final critical-hit probability, crit-adjusted damage, or crit-adjusted KO probability. Turn Engine state is also absent.

## Problem Definition

Scope Lens is not a direct always-on damage boost. It affects critical-hit likelihood.

The current `damage_estimate` is raw non-final damage context. It does not expose crit chance as part of the damage range, and `ko_context` is raw damage-roll KO context. If Scope Lens is mixed directly into either field, the advisor may imply that:

- raw damage already includes critical hits
- KO/OHKO/2HKO chance already includes critical-hit chance
- Scope Lens directly boosts damage
- a critical hit or final crit probability is known

That would be too strong without an explicit critical-hit payload contract. The safer path is a separate limited `critical_context` that can warn about crit opportunity/risk while preserving raw damage and raw KO context unchanged.

## Item Behavior Summary

Scope Lens should be treated as a critical-hit likelihood item.

Design stance:

- Treat Scope Lens as a limited critical-hit risk/opportunity context first.
- Require user-confirmed item state before modeling.
- Do not infer Scope Lens from legal item candidates, possible samples, or unknown held items.
- Do not calculate final critical-hit probability in the first LLM payload version.
- Do not calculate crit-adjusted KO probability in the first LLM payload version.
- Confirm critical-hit stage policy, move-specific crit effects, and Champions/PoChamps rule compatibility before exposing numeric final crit probability.

Until that rule support is explicitly approved, the advisor should prefer wording such as "may increase critical-hit likelihood" instead of claiming a precise crit chance.

## Scope

Recommended v0.66 scope:

- attacker item is user-confirmed `scope-lens`
- additive `critical_context`
- move-level sibling placement when practical
- raw `damage_estimate.damage_range` unchanged
- raw `damage_estimate.rolls` unchanged
- raw `ko_context` unchanged
- no final critical-hit probability
- no crit-adjusted KO probability
- no crit damage integration into the LLM damage estimate

If move crit metadata is absent, the first implementation can still provide a generic Scope Lens context, or it can return unavailable with `move_crit_metadata_missing`. T3 recommends a label-first generic context for user-confirmed Scope Lens, while keeping final probability unavailable.

Out of first implementation scope:

- final critical-hit probability calculation
- critical-hit damage integration
- crit-adjusted KO probability
- critical-hit stage system in the LLM payload
- high-crit move interaction
- ability, weather, and item interaction modeling
- Focus Energy or battle-state tracking
- multi-hit critical-hit handling
- Turn Engine
- final outcome simulation

## Proposed Payload Shape

Recommended common wrapper:

```json
{
  "available": true,
  "mode": "limited_critical_context",
  "scope": "selected_move_only",
  "attacker_side": "my_active",
  "item": {
    "item_id": "scope-lens",
    "status": "user_confirmed"
  },
  "critical_effect": {
    "type": "scope_lens",
    "effect_label": "may_increase_critical_hit_likelihood",
    "formula_label": "scope_lens_limited_critical_modifier",
    "critical_risk_note": "Scope Lens may increase critical-hit likelihood under limited assumptions.",
    "raw_damage_rolls_changed": false,
    "ko_context_changed": false,
    "crit_probability_integrated": false,
    "crit_adjusted_ko_integrated": false
  },
  "limitations": [
    "Limited critical-hit context only.",
    "Critical-hit stages, abilities, move-specific crit effects, and turn sequencing are not modeled."
  ],
  "is_final_battle_truth": false
}
```

Unavailable shape:

```json
{
  "available": false,
  "mode": "limited_critical_context",
  "reason": "no_scope_lens",
  "is_final_battle_truth": false
}
```

Reason code candidates:

- `no_scope_lens`
- `item_not_user_confirmed`
- `unsupported_critical_item`
- `critical_engine_missing`
- `move_crit_metadata_missing`
- `turn_engine_required`

## Placement Options

### Option A - move-level sibling field

Add `critical_context` as a sibling on the relevant move payload, beside `damage_estimate`, `ko_context`, `accuracy_context`, `recovery_context`, and `survival_context`.

Pros:

- Keeps critical-hit context tied to a move.
- Keeps crit semantics separate from raw damage and raw KO fields.
- Matches the current move-level sibling pattern used by `accuracy_context`.
- Creates room for future high-crit move metadata without changing raw damage.

Cons:

- The move payload grows as more limited contexts are added.
- The LLM prompt must keep these contexts concise.

### Option B - `damage_estimate` sibling

Attach `critical_context` next to the same move's `damage_estimate`.

Pros:

- Easy to implement if the current code attaches all damage-adjacent contexts together.
- Easy for the LLM to see raw damage and crit context in one place.

Cons:

- Placement near damage can make it easier to misread as included in raw damage.
- Requires strong guardrails that raw damage is unchanged.

### Option C - top-level critical context

Add top-level `critical_context` keyed by side or active attacker.

Pros:

- Cleanly separates item state from damage estimates.
- Avoids repeated Scope Lens notes across moves.

Cons:

- Harder to connect to individual move context.
- Less consistent with selected/available move and opponent known move context placement.
- Awkward for future high-crit move interactions.

Recommendation:

- Prefer **Option A** for v0.66: a move-level sibling field.
- If implementation structure makes that awkward, Option B is acceptable as an additive sibling beside the move's `damage_estimate`.
- Do not put `critical_context` inside `damage_estimate`.
- Do not put `critical_context` inside `ko_context`.
- Do not expose crit-adjusted KO probability in the first implementation.

## Critical Amount Policy

Initial implementation should not silently expose a numeric final crit probability.

Recommended policy:

- Require user-confirmed Scope Lens.
- Include `effect_label`: `may_increase_critical_hit_likelihood`.
- Include `formula_label`: `scope_lens_limited_critical_modifier`.
- Include `critical_risk_note` or `critical_opportunity_note`.
- Include `crit_probability_integrated=false`.
- Include `crit_adjusted_ko_integrated=false`.
- Do not include `final_crit_probability`.
- Do not include `crit_adjusted_ko_chance`.

Rule validation notes:

- `advisor/damage/crit.py` already treats `scope-lens` as a +1 critical-hit stage item.
- The LLM payload should still avoid final probability until T1/T2 approve exposing critical-hit stage semantics.
- Champions/PoChamps legality and rule compatibility should be checked before numeric probability display.

Possible future fields after rule validation:

- `critical_stage_delta`
- `base_crit_stage`
- `effective_crit_stage`
- `final_crit_probability`
- `probability_source`
- `rule_verification_status`

## LLM Guardrails

Required guardrails:

- `critical_context` is limited context only.
- Scope Lens may increase critical-hit likelihood.
- Raw damage estimates are unchanged.
- Raw `ko_context` is unchanged.
- KO/OHKO/2HKO estimates do not include crit chance.
- Crit-adjusted KO probability is not calculated.
- Do not claim a critical hit will occur.
- Do not claim final crit probability unless explicitly calculated.
- Do not infer Scope Lens if the item is unknown or unconfirmed.
- Do not describe Scope Lens as a direct damage boost.

Good wording:

- "Scope Lens may increase critical-hit likelihood as limited critical context, but the raw damage and KO estimates do not include crit chance."
- "The raw KO chance is separate from any critical-hit possibility; crit-adjusted KO probability is not calculated."
- "This is not a final critical-hit probability; critical-hit stages, abilities, move-specific crit effects, and turn sequencing are not modeled."

Bad wording:

- "Scope Lens boosts the damage directly."
- "This move will crit."
- "The KO chance includes Scope Lens crit chance."
- "The final critical probability is confirmed."
- "Scope Lens guarantees the KO."

When `critical_context.available` is false, or no `critical_context` is present for a move, the LLM should not invent Scope Lens critical-hit effects or force a crit limitation sentence.

## Tests Plan

Future implementation tests should cover:

- user-confirmed Scope Lens -> `critical_context.available=true`
- Scope Lens unknown or unconfirmed -> unavailable `item_not_user_confirmed` or absent
- no Scope Lens -> unavailable `no_scope_lens` or absent
- unsupported critical item -> unavailable `unsupported_critical_item`
- missing crit metadata policy is documented, either generic limited context or unavailable `move_crit_metadata_missing`
- `critical_context` includes `crit_probability_integrated=false`
- `critical_context` includes `crit_adjusted_ko_integrated=false`
- raw damage min/max/rolls unchanged
- raw `ko_context` unchanged
- `critical_context` does not alter OHKO chance
- my selected/available move direction targets `my_active` as attacker
- opponent known move direction targets `opponent_active` as attacker
- candidate moves excluded or explicitly documented
- prompt guardrails for no direct damage boost, no will-crit claim, and no crit-adjusted KO
- existing Bright Powder accuracy regression
- existing recovery context regression
- existing KO context regression
- existing Focus Sash regression
- existing type item regression
- existing Choice Scarf speed context regression
- existing opponent assumptions regression
- full pytest

## Interaction With Existing Systems

`critical_context` and `damage_estimate`:

- Scope Lens does not change damage min/max/rolls.
- Raw damage remains the current non-final damage estimate.
- Crit damage is not folded into raw damage in v0.66.

`critical_context` and `ko_context`:

- `ko_context` remains raw damage-roll context.
- KO/OHKO/2HKO estimates do not include critical-hit chance.
- A later crit-adjusted KO probability should be a separate, explicitly versioned feature.

`critical_context` and `accuracy_context`:

- Bright Powder hit reliability and Scope Lens critical-hit likelihood are separate limited contexts.
- Accuracy and crit chance should not be multiplied together into final outcome probability without a future probability model.

`critical_context`, `recovery_context`, and `survival_context`:

- Focus Sash, Sitrus Berry, Leftovers, and Scope Lens remain separate limited contexts.
- Scope Lens plus Focus Sash, recovery, or Bright Powder interactions are deferred.
- The LLM should not combine these contexts into final battle truth.

Other systems:

- `opponent_assumptions` is unrelated and remains context-only.
- Choice Scarf `speed_context` is unrelated.
- Turn Engine remains absent.
- Existing lower-level crit utilities are useful implementation inputs, but v0.66 should still keep LLM-facing probability claims limited.

## v0.66 Candidate

Recommended:

`v0.66 - Scope Lens Limited Critical Context Implementation`

Include:

- helper for limited critical context
- user-confirmed Scope Lens only
- additive move-level `critical_context`
- label/formula based critical-hit likelihood note
- raw damage unchanged
- raw `ko_context` unchanged
- no final critical-hit probability
- no crit-adjusted KO probability
- tests and docs
- no Turn Engine

Alternative:

`v0.66 - Critical Hit Rule Validation Design`

Choose this if T1/T2 want to validate exact Scope Lens critical-hit stage, move-specific crit behavior, and Champions/PoChamps rule compatibility before any payload field is added.

T3 recommendation:

- Proceed with v0.66 implementation only if T1/T2 accept label-first critical context without numeric final crit probability.
- If exact numeric crit chance is required, run rule validation first.
- In either path, keep crit likelihood separate from raw damage and raw KO context.

## Out of Scope

- code implementation
- `critical_context` implementation
- final critical-hit probability
- crit-adjusted KO probability
- Turn Engine
- critical-hit stage system in the LLM payload
- ability/weather/item interaction modeling
- KO context modification
- raw damage roll modification
- Focus Sash / Sitrus / Bright Powder interaction implementation
- UI changes
- fixture changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits
