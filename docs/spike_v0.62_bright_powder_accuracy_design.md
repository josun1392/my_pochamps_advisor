# v0.62 Bright Powder Accuracy Design

## Current State

The advisor now has several additive, limited battle-context layers:

- `damage_estimate` provides raw damage min/max/rolls.
- `ko_context` provides limited damage-roll KO/OHKO/2HKO context.
- `survival_context` provides limited Focus Sash survival context.
- `recovery_context` provides limited Sitrus Berry / Leftovers recovery context.
- Type boosting items can modify raw damage when explicitly supported.
- Choice Scarf can affect `speed_context`.
- `opponent_assumptions` remains context-only and does not feed damage, Speed, KO, survival, or recovery.

Bright Powder is recognized as a legal held item in `data/static/champions_legal_items.json`, but its effect is still marked as not modeled:

- `effect_support_status`: `legal_but_not_modeled`
- `ui_status`: `recognized_not_modeled`
- `effect_support.utility_effect`: `not_supported`

There is no general accuracy/evasion engine yet. Existing multi-hit code contains post-connect and multiaccuracy mechanics for specific damage-engine paths, but the LLM payload does not currently model move hit probability, evasion stages, compound accuracy modifiers, or final hit chance.

Turn Engine state is also absent, so accuracy, action order, switching, protection, and final turn outcomes cannot be fully simulated.

## Problem Definition

Bright Powder does not reduce damage. It can affect whether an incoming move hits, which is adjacent to but separate from damage rolls.

If Bright Powder is mixed directly into `damage_estimate`, the advisor could imply that raw damage is lower. If it is mixed into `ko_context`, the advisor could imply that raw KO/OHKO/2HKO odds already include hit chance. Both are unsafe before an accuracy engine exists.

The safer design is a separate limited `accuracy_context`:

- It can warn that hit reliability may be lower.
- It can say Bright Powder is user-confirmed.
- It can preserve raw damage and raw KO context unchanged.
- It can avoid claiming a final hit probability or final KO result.

## Item Behavior Summary

Bright Powder should be treated as an accuracy/evasion-related held item.

Design stance:

- Treat Bright Powder as a limited accuracy risk context first.
- Require user-confirmed item state before modeling.
- Do not infer Bright Powder from sample items, legal item candidates, or unknown held items.
- Do not calculate a final hit-adjusted KO probability in the first version.
- Confirm the exact modifier, application order, and Champions/PoChamps rule compatibility before exposing numeric hit probability.

Until rule support is confirmed, the advisor should prefer wording such as "may reduce hit reliability" instead of claiming a precise miss chance.

## Scope

Recommended v0.63 scope:

- defender item is user-confirmed `bright-powder`
- attacker move accuracy is present in the move payload
- additive `accuracy_context`
- raw `damage_estimate.damage_range` unchanged
- raw `damage_estimate.rolls` unchanged
- raw `ko_context` unchanged
- no hit-adjusted KO probability
- no final hit probability unless explicitly calculated and approved later

If move accuracy is missing, return unavailable or a limited unknown-accuracy state instead of guessing.

Out of first implementation scope:

- exact hit probability integration into KO chance
- accuracy stage calculation
- evasion stage calculation
- compound accuracy modifiers
- weather, ability, and other item interactions
- multi-hit accuracy modeling
- Protect, Substitute, or switching
- Turn Engine
- final hit/KO simulation

## Proposed Payload Shape

Recommended common wrapper:

```json
{
  "available": true,
  "mode": "limited_accuracy_context",
  "scope": "selected_move_only",
  "defender_side": "opponent_active",
  "item": {
    "item_id": "bright-powder",
    "status": "user_confirmed"
  },
  "move_accuracy": {
    "base_accuracy": 90,
    "accuracy_source": "move_metadata",
    "accuracy_known": true
  },
  "accuracy_effect": {
    "type": "bright_powder",
    "estimated_modifier": "limited_evasion_modifier",
    "accuracy_risk_note": "Bright Powder may reduce hit reliability under limited assumptions.",
    "raw_damage_rolls_changed": false,
    "ko_context_changed": false,
    "hit_probability_integrated": false
  },
  "limitations": [
    "Limited accuracy context only.",
    "Accuracy/evasion stages, ability interactions, weather, multi-hit accuracy, and turn sequencing are not modeled."
  ],
  "is_final_battle_truth": false
}
```

Unavailable shape:

```json
{
  "available": false,
  "mode": "limited_accuracy_context",
  "reason": "move_accuracy_missing",
  "is_final_battle_truth": false
}
```

Reason code candidates:

- `no_bright_powder`
- `item_not_user_confirmed`
- `move_accuracy_missing`
- `unsupported_accuracy_item`
- `accuracy_engine_missing`
- `turn_engine_required`

## Placement Options

### Option A - `damage_estimate` sibling

Add `accuracy_context` beside the relevant move's `damage_estimate`, `ko_context`, `survival_context`, and `recovery_context`.

Pros:

- Easy for the LLM to interpret alongside damage and KO context.
- Consistent with `ko_context`, `survival_context`, and `recovery_context`.
- Works for my selected/available moves and opponent known moves.

Cons:

- Placement near damage can make it easier to misread as part of raw damage.
- Requires strong guardrails that raw damage and raw KO context are unchanged.

### Option B - move-level sibling field

Attach `accuracy_context` as a sibling at the move level, not inside `damage_estimate` or `ko_context`.

Pros:

- Keeps accuracy separate from raw damage and raw KO fields.
- Still keeps context tied to the relevant move.
- Best semantic fit for a future hit-probability layer.

Cons:

- Requires confirming the exact current move payload shape before implementation.
- May be functionally similar to Option A if existing move objects already keep all contexts as siblings.

### Option C - top-level accuracy context

Add top-level `accuracy_context` keyed by side or active matchup.

Pros:

- Cleanly separates item state from damage and KO.
- Reduces repeated Bright Powder notes across moves.

Cons:

- Harder to connect to individual move accuracy.
- Less consistent with the current additive move-context pattern.

Recommendation:

- Prefer **Option B in spirit**: a move-level sibling field that is never nested inside `damage_estimate` or `ko_context`.
- If the existing implementation pattern treats all move-side contexts as siblings beside `damage_estimate`, Option A is acceptable.
- Do not use Option C for v0.63 unless repeated context noise becomes a bigger problem.
- Never calculate or display hit-adjusted KO probability in the first implementation.

## Accuracy Amount Policy

Initial implementation should not silently guess Bright Powder rules.

Recommended policy:

- Require user-confirmed Bright Powder.
- Require known move accuracy.
- Include `base_accuracy` and `accuracy_source` when available.
- Include `estimated_modifier` as a label first, such as `limited_evasion_modifier`.
- Include `accuracy_risk_note` or `estimated_hit_reliability_note` rather than final hit probability.
- Add a rule verification note if numeric modifier support is not confirmed.

Possible future fields after rule validation:

- `modifier_label`
- `modifier_value`
- `final_hit_probability`
- `modifier_source`
- `rule_verification_status`

Do not expose numeric final hit chance until Champions/PoChamps rule compatibility and modifier order are verified. Do not combine Bright Powder with accuracy/evasion stages, weather, ability, or other item effects in v0.63.

## LLM Guardrails

Required guardrails:

- `accuracy_context` is limited context only.
- Raw damage estimates are unchanged.
- Raw `ko_context` is unchanged.
- KO/OHKO/2HKO estimates do not include hit chance.
- Bright Powder is not damage reduction.
- Do not claim the move will miss.
- Do not claim final hit probability unless explicitly calculated.
- Do not infer Bright Powder if the item is unknown or unconfirmed.
- Use wording like "may reduce hit reliability."

Good wording:

- "Bright Powder may reduce hit reliability under limited accuracy context, but the raw damage and KO estimates do not include hit chance."
- "The move can KO by raw damage rolls, but accuracy and Bright Powder effects are not integrated into that KO chance."
- "This is not a final hit probability; accuracy/evasion stages and turn sequencing are not modeled."

Bad wording:

- "The damage is reduced by Bright Powder."
- "This move will miss."
- "The KO chance already accounts for Bright Powder."
- "The final hit probability is confirmed."
- "Bright Powder guarantees the opponent survives."

## Tests Plan

Future implementation tests should cover:

- user-confirmed Bright Powder plus known move accuracy -> `accuracy_context.available=true`
- Bright Powder unknown or unconfirmed -> unavailable `item_not_user_confirmed` or absent
- no Bright Powder -> unavailable `no_bright_powder` or absent
- move accuracy missing -> unavailable `move_accuracy_missing`
- raw damage min/max/rolls unchanged
- raw `ko_context` unchanged
- `accuracy_context` does not alter OHKO chance
- my selected/available move direction targets `opponent_active`
- opponent known move direction targets `my_active`
- candidate moves excluded or explicitly documented
- prompt guardrails for no damage reduction, no final miss claim, and no hit-adjusted KO
- existing Focus Sash regression
- existing KO context regression
- existing recovery context regression
- existing type item regression
- existing Choice Scarf speed context regression
- existing opponent assumptions regression
- full pytest

## Interaction With Existing Systems

`accuracy_context` and `damage_estimate`:

- Bright Powder does not change damage min/max/rolls.
- Damage remains raw on-hit damage under existing assumptions.

`accuracy_context` and `ko_context`:

- `ko_context` remains raw damage-roll context.
- KO/OHKO/2HKO estimates do not include hit chance.
- A later hit-adjusted KO probability should be a separate, explicitly versioned feature.

`accuracy_context`, `survival_context`, and `recovery_context`:

- Focus Sash survival and Sitrus/Leftovers recovery remain separate limited contexts.
- Bright Powder plus Focus Sash or recovery interactions are deferred.
- The LLM should not combine these contexts into final battle truth.

Other systems:

- `opponent_assumptions` is unrelated and remains context-only.
- Choice Scarf `speed_context` is unrelated.
- Turn Engine remains absent.
- Existing multi-hit post-connect logic does not provide a general accuracy engine.

## v0.63 Candidate

Recommended:

`v0.63 - Bright Powder Limited Accuracy Context Implementation`

Include:

- helper for limited accuracy context
- user-confirmed Bright Powder only
- known move accuracy only
- additive move-level `accuracy_context`
- raw damage unchanged
- raw `ko_context` unchanged
- no hit-adjusted KO probability
- tests and docs
- no Turn Engine

Alternative:

`v0.63 - Accuracy Item Rule Validation Design`

Choose this if T1/T2 want to validate Bright Powder modifier rules, source compatibility, and exact modifier order before any payload field is added.

T3 recommendation:

- Proceed with v0.63 implementation only if T1/T2 accept label-first accuracy context without numeric final hit probability.
- If exact numeric Bright Powder behavior is required, run rule validation first.
- In either path, keep accuracy separate from raw damage and raw KO context.

## Out of Scope

- code implementation
- `accuracy_context` implementation
- hit-adjusted KO probability
- Turn Engine
- accuracy/evasion stage system
- ability/weather/item interaction modeling
- KO context modification
- raw damage roll modification
- Focus Sash / Sitrus / Leftovers interaction implementation
- UI changes
- fixture changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits
