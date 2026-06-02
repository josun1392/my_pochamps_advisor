# v0.72 Loaded Dice / Multi-hit Context Design

## Current State

The advisor currently exposes several additive battle-context layers:

- `damage_estimate` provides raw damage min/max/rolls under stated assumptions.
- `ko_context` provides limited damage-roll KO/OHKO/2HKO context.
- `survival_context` provides limited Focus Sash survival context.
- `recovery_context` provides limited Sitrus Berry / Leftovers recovery context.
- `accuracy_context` provides limited Bright Powder hit reliability context.
- `critical_context` provides limited Scope Lens critical-hit context.
- `flinch_context` provides limited King's Rock flinch pressure context.
- Type boosting items can modify raw damage only through the supported damage item modifier path.
- Choice Scarf can affect `speed_context`.
- `opponent_assumptions` remains context-only and does not feed damage, Speed, KO, survival, recovery, accuracy, critical-hit, or flinch calculations.

Loaded Dice is not connected to the LLM payload path as a multi-hit context. The advisor does not currently expose a `multi_hit_context`, final hit count distribution, multi-hit-adjusted damage estimate, or multi-hit-adjusted KO probability.

There is lower-level multi-hit support elsewhere in the repo:

- `advisor/damage/multihit.py` contains multi-hit move metadata and hit-count resolution for moves such as Bullet Seed, Rock Blast, Icicle Spear, Triple Axel, Triple Kick, and Population Bomb.
- `advisor/probability/multi_hit.py` can compute hit-count and damage distributions, including Loaded Dice behavior for Tier A and Tier C multi-hit move families.
- `data/static/items.json` describes `loaded-dice` as a `multihit_modifier`.

Those lower-level mechanics are useful future inputs, but they are not yet part of `llm/advisor_damage_estimate.py`, `ko_context`, or the LLM payload contract. Turn Engine state is also absent.

## Problem Definition

Loaded Dice is not a direct damage modifier. It changes multi-hit move reliability by affecting hit count behavior for eligible moves.

Multi-hit context is more complex than the previous limited item contexts because it touches several other systems at once:

- raw damage roll aggregation
- hit count distribution
- move eligibility
- KO/OHKO/2HKO probability
- Focus Sash survival behavior
- King's Rock flinch pressure
- move accuracy and multiaccuracy
- critical-hit handling per hit
- target current HP
- future turn or action state

If Loaded Dice is mixed directly into `damage_estimate` or `ko_context`, the LLM may imply that:

- raw damage already includes multi-hit count changes
- KO/OHKO/2HKO chance already includes hit-count reliability
- Focus Sash or King's Rock interactions are already resolved
- a specific number of hits is known
- final multi-hit outcome has been simulated

That would be too strong for the current LLM payload. The safer path is a separate limited `multi_hit_context` that can warn about multi-hit reliability while preserving raw damage and raw KO context unchanged.

## Item Behavior Summary

Loaded Dice should be treated as a multi-hit reliability item.

Design stance:

- Treat Loaded Dice as limited multi-hit reliability context first.
- Require user-confirmed item state before modeling.
- Do not infer Loaded Dice from legal item candidates, possible samples, or unknown held items.
- Do not treat Loaded Dice as direct damage boost.
- Do not calculate final hit count probability in the first LLM payload version.
- Do not calculate multi-hit-adjusted KO probability in the first LLM payload version.
- Do not fold multi-hit damage aggregation into raw `damage_estimate`.
- Confirm move eligibility, hit-count tiers, and Champions/PoChamps rule compatibility before exposing numeric final hit-count probabilities.

Until that LLM-facing rule support is explicitly approved, the advisor should prefer wording such as "may improve multi-hit reliability for eligible moves" instead of claiming a precise hit count or final KO chance.

## Scope

Recommended v0.73 scope:

- attacker item is user-confirmed `loaded-dice`
- additive `multi_hit_context`
- move-level sibling placement when practical
- attach to my selected/available moves when my active Pokemon is the attacker
- attach to opponent known moves when opponent active Pokemon is the attacker
- candidate moves excluded
- move metadata can identify whether a move is multi-hit
- known multi-hit move -> available limited context
- non-multi-hit move -> unavailable `move_not_multi_hit` or absent
- missing move multi-hit metadata -> unavailable `move_multihit_metadata_missing` or limited unknown metadata, depending on implementation confidence
- raw `damage_estimate.damage_range` unchanged
- raw `damage_estimate.rolls` unchanged
- raw `ko_context` unchanged
- no final hit count probability
- no multi-hit-adjusted KO probability
- no Focus Sash multi-hit interaction
- no King's Rock multi-hit flinch interaction
- no per-hit accuracy or crit modeling
- no Turn Engine

Out of first implementation scope:

- final hit count probability calculation
- multi-hit damage aggregation in the LLM payload
- multi-hit-adjusted KO probability
- Focus Sash multi-hit interaction
- King's Rock multi-hit flinch interaction
- Bright Powder / accuracy per-hit modeling
- Scope Lens / critical-hit per-hit modeling
- move-specific hit-count table expansion beyond available metadata
- target action state
- final outcome simulation

## Proposed Payload Shape

Recommended common wrapper:

```json
{
  "available": true,
  "mode": "limited_multi_hit_context",
  "scope": "selected_move_only",
  "attacker_side": "my_active",
  "item": {
    "item_id": "loaded-dice",
    "status": "user_confirmed"
  },
  "move_metadata": {
    "is_multi_hit": true,
    "metadata_source": "move_metadata",
    "multi_hit_known": true
  },
  "multi_hit_effect": {
    "type": "loaded_dice",
    "effect_label": "may_improve_multi_hit_reliability",
    "formula_label": "loaded_dice_limited_multihit_modifier",
    "multi_hit_reliability_note": "Loaded Dice may improve multi-hit reliability for eligible moves under limited assumptions.",
    "raw_damage_rolls_changed": false,
    "ko_context_changed": false,
    "hit_count_probability_integrated": false,
    "multi_hit_adjusted_ko_integrated": false
  },
  "limitations": [
    "Limited multi-hit context only.",
    "Final hit count distribution, per-hit damage, Focus Sash interaction, King's Rock interaction, accuracy/crit per-hit modeling, and turn sequencing are not modeled."
  ],
  "is_final_battle_truth": false
}
```

Unavailable shape:

```json
{
  "available": false,
  "mode": "limited_multi_hit_context",
  "reason": "move_multihit_metadata_missing",
  "is_final_battle_truth": false
}
```

Reason code candidates:

- `no_loaded_dice`
- `item_not_user_confirmed`
- `unsupported_multi_hit_item`
- `move_not_multi_hit`
- `move_multihit_metadata_missing`
- `multi_hit_engine_missing`
- `turn_engine_required`
- `damage_estimate_missing`

## Placement Options

### Option A - move-level sibling field

Add `multi_hit_context` as a sibling on the relevant move payload, beside `damage_estimate`, `ko_context`, `accuracy_context`, `critical_context`, `flinch_context`, `recovery_context`, and `survival_context`.

Pros:

- Keeps multi-hit context tied to a specific move.
- Keeps hit-count semantics separate from raw damage and raw KO fields.
- Matches the current move-level sibling pattern used by `accuracy_context`, `critical_context`, and `flinch_context`.
- Leaves room for future move eligibility metadata and per-move hit-count policy.

Cons:

- The move payload grows as more limited contexts are added.
- The LLM prompt must keep context notes concise.
- Multi-hit context may repeat across moves if several moves are present.

### Option B - `damage_estimate` sibling

Attach `multi_hit_context` near the same move's `damage_estimate`.

Pros:

- Easy to implement if the current code attaches all damage-adjacent contexts together.
- Easy for the LLM to see raw damage, KO, and multi-hit notes in one local move block.

Cons:

- Placement near damage can make it easier to misread as included in raw damage.
- Requires strong guardrails that raw damage and KO context are unchanged.

### Option C - top-level multi-hit context

Add top-level `multi_hit_context` keyed by side or active attacker.

Pros:

- Separates item state from move payload details.
- Avoids repeated Loaded Dice notes across moves.

Cons:

- Harder to connect to individual move eligibility.
- Awkward for selected/available move comparisons.
- Less consistent with existing move-level context placement.

Recommendation:

- Prefer **Option A** for v0.73: a move-level sibling field.
- If implementation structure makes that awkward, Option B is acceptable as an additive sibling beside the move's `damage_estimate`.
- Do not put `multi_hit_context` inside `damage_estimate`.
- Do not put `multi_hit_context` inside `ko_context`.
- Do not expose final hit count probability or multi-hit-adjusted KO probability in the first implementation.

## Multi-hit Amount Policy

Initial implementation should not expose a numeric final hit count probability.

Recommended policy:

- Require user-confirmed Loaded Dice.
- Include `effect_label`: `may_improve_multi_hit_reliability`.
- Include `formula_label`: `loaded_dice_limited_multihit_modifier`.
- Include `multi_hit_reliability_note` or equivalent.
- Include `hit_count_probability_integrated=false`.
- Include `multi_hit_adjusted_ko_integrated=false`.
- Include `raw_damage_rolls_changed=false`.
- Include `ko_context_changed=false`.
- Do not include `final_hit_count_probability`.
- Do not include `multi_hit_adjusted_ko_chance`.
- Do not include `guaranteed_hit_count`.

Rule validation notes:

- Lower-level code already distinguishes Tier A range multi-hit moves and Tier C multiaccuracy moves.
- `advisor/probability/multi_hit.py` can compute exact distributions, including Loaded Dice 4/5 for Tier A and 4..10 uniform for Tier C.
- The LLM payload should still avoid numeric final probability until T1/T2 approve exposing that rule layer in advisor responses.
- Champions/PoChamps legality, selected move metadata, and move eligibility should be checked before numeric probability display.

Possible future fields after rule validation:

- `move_multihit_tier`
- `base_hit_count_range`
- `loaded_dice_hit_count_range`
- `hit_count_distribution`
- `final_hit_count_probability`
- `multi_hit_adjusted_damage_distribution`
- `multi_hit_adjusted_ko_probability`
- `probability_source`
- `rule_verification_status`

## LLM Guardrails

Required guardrails:

- `multi_hit_context` is limited context only.
- Loaded Dice may improve multi-hit reliability for eligible moves.
- Raw damage estimates are unchanged.
- Raw `ko_context` is unchanged.
- KO/OHKO/2HKO estimates do not include multi-hit count changes.
- Final hit count probability is not calculated.
- Multi-hit-adjusted KO probability is not calculated.
- Do not claim a specific number of hits will occur.
- Do not claim Loaded Dice breaks Focus Sash unless a future field explicitly models that interaction.
- Do not claim King's Rock flinch pressure includes multi-hit behavior.
- Do not infer Loaded Dice if the item is unknown or unconfirmed.
- Do not describe Loaded Dice as a direct damage boost.
- Focus Sash, King's Rock, accuracy, crit per-hit effects, and turn sequencing are not modeled.

Good wording:

- "Loaded Dice may improve multi-hit reliability as limited context, but the raw damage and KO estimates do not include multi-hit count changes."
- "The raw KO chance is separate from any Loaded Dice multi-hit possibility; multi-hit-adjusted KO probability is not calculated."
- "This is not a final hit count probability; per-hit damage, Focus Sash, King's Rock, accuracy, crit interactions, and turn sequencing are not modeled."

Bad wording:

- "Loaded Dice directly boosts the damage."
- "This move will hit 5 times."
- "The KO chance includes Loaded Dice hit count changes."
- "Loaded Dice breaks Focus Sash here."
- "King's Rock flinch chance includes Loaded Dice multi-hit behavior."
- "The final hit count probability is confirmed."

When `multi_hit_context.available` is false, or no `multi_hit_context` is present for a move, the LLM should not invent Loaded Dice multi-hit effects or force a multi-hit limitation sentence.

## Tests Plan

Future implementation tests should cover:

- user-confirmed Loaded Dice + known multi-hit move metadata -> `multi_hit_context.available=true`
- Loaded Dice unknown or unconfirmed -> unavailable `item_not_user_confirmed` or absent
- no Loaded Dice -> unavailable `no_loaded_dice` or absent
- no multi-hit item but multi-hit move -> unavailable or absent
- move not multi-hit -> unavailable `move_not_multi_hit` or absent
- missing multi-hit metadata -> unavailable `move_multihit_metadata_missing`
- unsupported multi-hit item -> unavailable `unsupported_multi_hit_item`
- `multi_hit_context` includes `hit_count_probability_integrated=false`
- `multi_hit_context` includes `multi_hit_adjusted_ko_integrated=false`
- raw damage min/max/rolls unchanged
- raw `ko_context` unchanged
- `multi_hit_context` does not alter OHKO chance
- my selected/available move direction uses `attacker_side: my_active`
- opponent known move direction uses `attacker_side: opponent_active`
- candidate moves excluded or explicitly documented
- prompt guardrails for no direct damage boost, no guaranteed hit count, and no multi-hit-adjusted KO
- existing King's Rock flinch regression
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

`multi_hit_context` and `damage_estimate`:

- Loaded Dice does not change raw damage min/max/rolls in the first LLM payload version.
- Raw damage remains the current single damage-estimate path unless an explicitly versioned future multi-hit damage field is added.
- Multi-hit damage aggregation is not folded into raw damage in v0.73.

`multi_hit_context` and `ko_context`:

- `ko_context` remains raw damage-roll context.
- KO/OHKO/2HKO estimates do not include hit-count changes.
- A later multi-hit-adjusted KO probability should be a separate, explicitly versioned feature.

`multi_hit_context` and `flinch_context`:

- King's Rock flinch pressure and Loaded Dice multi-hit reliability are separate limited contexts.
- Multi-hit flinch behavior is not modeled.
- Do not combine King's Rock and Loaded Dice into final target-action denial claims.

`multi_hit_context` and `survival_context`:

- Focus Sash currently treats multi-hit moves as unsupported in `survival_context`.
- Loaded Dice does not change Focus Sash survival handling in this design.
- Do not claim Loaded Dice breaks Focus Sash until a future survival/multi-hit interaction field exists.

`multi_hit_context` and `accuracy_context`:

- Bright Powder hit reliability and Loaded Dice hit-count reliability are separate limited contexts.
- Tier C multiaccuracy mechanics exist in lower-level code, but the LLM payload should not expose final hit probability or per-hit accuracy modeling in v0.73.

`multi_hit_context` and `critical_context`:

- Scope Lens critical-hit likelihood and Loaded Dice multi-hit reliability are separate limited contexts.
- Per-hit crit modeling is deferred.

Other systems:

- `opponent_assumptions` is unrelated and remains context-only.
- Choice Scarf `speed_context` is unrelated.
- Turn Engine remains absent.

## v0.73 Candidate

Recommended:

`v0.73 - Loaded Dice Limited Multi-hit Context Implementation`

Include:

- helper for limited multi-hit context
- user-confirmed Loaded Dice only
- additive move-level `multi_hit_context`
- known multi-hit move metadata when available
- label/formula based multi-hit reliability note
- raw damage unchanged
- raw `ko_context` unchanged
- no final hit count probability
- no multi-hit-adjusted KO probability
- tests and docs
- no Turn Engine

Alternative:

`v0.73 - Multi-hit Rule Validation Design`

Choose this if T1/T2 want to validate Loaded Dice rule exposure, move eligibility, and multi-hit metadata before any LLM payload field is added.

T3 recommendation:

- Proceed with v0.73 implementation only if T1/T2 accept label-first multi-hit context without numeric final hit count probability.
- If exact hit count distribution should be user-facing, run rule validation first.
- In either path, keep multi-hit reliability separate from raw damage and raw KO context.

## Out of Scope

- code implementation
- `multi_hit_context` implementation
- final hit count probability
- multi-hit-adjusted KO probability
- Turn Engine
- multi-hit damage aggregation in the LLM payload
- Focus Sash / King's Rock interaction implementation
- accuracy/crit per-hit modeling
- KO context modification
- raw damage roll modification
- UI changes
- fixture changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits
