# v0.74 Power Herb / Charge-turn Context Design

## Current State

The advisor currently exposes several additive battle-context layers:

- `damage_estimate` provides raw damage min/max/rolls under stated assumptions.
- `ko_context` provides limited damage-roll KO/OHKO/2HKO context.
- `survival_context` provides limited Focus Sash survival context.
- `recovery_context` provides limited Sitrus Berry / Leftovers recovery context.
- `accuracy_context` provides limited Bright Powder hit reliability context.
- `critical_context` provides limited Scope Lens critical-hit context.
- `flinch_context` provides limited King's Rock flinch pressure context.
- `multi_hit_context` provides limited Loaded Dice multi-hit reliability context.
- Type boosting items can modify raw damage only through the supported damage item modifier path.
- Choice Scarf can affect `speed_context`.
- `opponent_assumptions` remains context-only and does not feed damage, Speed, KO, survival, recovery, accuracy, critical-hit, flinch, or multi-hit calculations.

Power Herb is not connected to the LLM payload path as charge-turn context. The advisor does not currently expose `charge_context`, final charge-turn sequencing, item consumption state, or charge-turn-adjusted KO probability.

The current repo shape also does not provide an LLM-facing charge move metadata system. `data/static/items.json` documents some special non-damage item behavior such as Loaded Dice, but Power Herb was not found in the inspected static item files. That means v0.75 needs either a small charge-move metadata source, an explicit unavailable policy, or a rule validation pass before implementation.

Turn Engine state is absent. There is no once-per-battle item consumption tracking, switching state, weather timing, protection state, or final turn sequencing.

## Problem Definition

Power Herb is not a direct damage modifier. It is related to charge move usability: for eligible charge moves, it may allow the move to skip the charging turn.

Charge-turn context is tightly coupled to battle sequencing:

- move eligibility, such as Solar Beam, Meteor Beam, Sky Attack, or other charge-turn moves
- item consumption and whether Power Herb has already been used
- weather-specific exceptions or interactions
- speed order and whether the move user acts before the target
- switching, Protect, Substitute, and other action-state effects
- final KO or survival outcome across the turn

If Power Herb is mixed directly into `damage_estimate` or `ko_context`, the LLM may imply that:

- raw damage already includes charge-turn usability
- KO/OHKO/2HKO chance already includes turn sequencing
- Power Herb has definitely been consumed or is definitely still available
- the move definitely resolves immediately
- final one-turn outcome has been simulated

That would be too strong for the current payload. The safer path is a separate limited `charge_context` that can warn about charge-move usability while preserving raw damage and raw KO context unchanged.

## Item Behavior Summary

Power Herb should be treated as a charge-move usability item.

Design stance:

- Treat Power Herb as limited charge-move context first.
- Require user-confirmed item state before modeling.
- Do not infer Power Herb from legal item candidates, possible samples, or unknown held items.
- Do not treat Power Herb as a direct damage boost.
- Do not track item consumption in the first LLM payload version.
- Do not calculate final turn outcome in the first LLM payload version.
- Do not calculate charge-turn-adjusted KO probability in the first LLM payload version.
- Confirm move eligibility, charge metadata availability, and Champions/PoChamps rule compatibility before exposing stronger claims.

Until that LLM-facing rule support is explicitly approved, the advisor should prefer wording such as "may allow an eligible charge move to skip the charging turn under limited context" instead of claiming that the move definitely fires instantly.

## Scope

Recommended v0.75 scope:

- attacker item is user-confirmed `power-herb`
- additive `charge_context`
- move-level sibling placement when practical
- attach to my selected/available moves when my active Pokemon is the attacker
- attach to opponent known moves when opponent active Pokemon is the attacker
- candidate moves excluded
- move metadata can identify whether a move is a charge move
- known charge move -> available limited context
- non-charge move -> unavailable `move_not_charge_move` or absent
- missing charge metadata -> unavailable `move_charge_metadata_missing` or limited unknown metadata, depending on implementation confidence
- raw `damage_estimate.damage_range` unchanged
- raw `damage_estimate.rolls` unchanged
- raw `ko_context` unchanged
- no item consumption tracking
- no final turn outcome
- no charge-turn-adjusted KO probability
- no weather interaction
- no Turn Engine

Out of first implementation scope:

- exact item consumption tracking
- final turn sequencing
- weather interaction
- charge move damage modification
- full move eligibility table
- Protect / Substitute / switching integration
- Turn Engine
- final outcome simulation
- KO probability modification

## Proposed Payload Shape

Recommended field name: `charge_context`.

`charge_move_context` is also understandable, but `charge_context` is shorter and matches existing sibling naming such as `accuracy_context`, `critical_context`, `flinch_context`, and `multi_hit_context`.

Recommended available shape:

```json
{
  "available": true,
  "mode": "limited_charge_move_context",
  "scope": "selected_move_only",
  "attacker_side": "my_active",
  "item": {
    "item_id": "power-herb",
    "status": "user_confirmed"
  },
  "move_metadata": {
    "is_charge_move": true,
    "metadata_source": "move_metadata",
    "charge_move_known": true
  },
  "charge_effect": {
    "type": "power_herb",
    "effect_label": "may_skip_charge_turn_for_eligible_move",
    "formula_label": "power_herb_limited_charge_modifier",
    "charge_move_usability_note": "Power Herb may allow an eligible charge move to skip its charging turn under limited assumptions.",
    "raw_damage_rolls_changed": false,
    "ko_context_changed": false,
    "turn_sequence_integrated": false,
    "item_consumption_tracked": false
  },
  "limitations": [
    "Limited charge-move context only.",
    "Exact item consumption, move eligibility edge cases, weather, switching, protection, and turn sequencing are not modeled."
  ],
  "is_final_battle_truth": false
}
```

Unavailable shape:

```json
{
  "available": false,
  "mode": "limited_charge_move_context",
  "reason": "move_charge_metadata_missing",
  "is_final_battle_truth": false
}
```

Reason code candidates:

- `no_power_herb`
- `item_not_user_confirmed`
- `unsupported_charge_item`
- `move_not_charge_move`
- `move_charge_metadata_missing`
- `charge_engine_missing`
- `turn_engine_required`
- `damage_estimate_missing`

## Placement Options

### Option A - move-level sibling field

Add `charge_context` as a sibling on the relevant move payload, beside `damage_estimate`, `ko_context`, `accuracy_context`, `critical_context`, `flinch_context`, `multi_hit_context`, `recovery_context`, and `survival_context`.

Pros:

- Keeps charge context tied to a specific move.
- Keeps charge-turn semantics separate from raw damage and raw KO fields.
- Matches the current move-level sibling pattern used by `accuracy_context`, `critical_context`, `flinch_context`, and `multi_hit_context`.
- Leaves room for future move eligibility metadata and per-move charge policy.

Cons:

- The move payload grows as more limited contexts are added.
- The LLM prompt must keep context notes concise.
- Charge context may repeat across moves if several charge moves are present.

### Option B - `damage_estimate` sibling

Attach `charge_context` near the same move's `damage_estimate`.

Pros:

- Easy to implement if the current code attaches all damage-adjacent contexts together.
- Easy for the LLM to see raw damage, KO, and charge notes in one local move block.

Cons:

- Placement near damage can make it easier to misread as included in raw damage.
- Requires strong guardrails that raw damage and KO context are unchanged.

### Option C - top-level charge context

Add top-level `charge_context` keyed by side or active attacker.

Pros:

- Separates item state from move payload details.
- Avoids repeated Power Herb notes across moves.

Cons:

- Harder to connect to individual move eligibility.
- Awkward for selected/available move comparisons.
- Less consistent with existing move-level context placement.

Recommendation:

- Prefer **Option A** for v0.75: a move-level sibling field.
- If implementation structure makes that awkward, Option B is acceptable as an additive sibling beside the move's `damage_estimate`.
- Do not put `charge_context` inside `damage_estimate`.
- Do not put `charge_context` inside `ko_context`.

## Charge Amount / Rule Policy

Power Herb should start as label/formula context, not numeric probability.

Recommended v0.75 policy:

- Use `effect_label: may_skip_charge_turn_for_eligible_move`.
- Use `formula_label: power_herb_limited_charge_modifier`.
- Do not calculate a numeric final turn probability.
- Do not calculate charge-turn-adjusted KO probability.
- Do not track whether Power Herb has already been consumed.
- Do not expose item consumption state unless future Turn Engine or battle-state tracking provides it.
- Require explicit move charge metadata to mark a move available.
- If charge metadata is absent, return unavailable `move_charge_metadata_missing` or omit the field, depending on implementation pattern.
- If the move is known not to be a charge move, return unavailable `move_not_charge_move` or omit the field.

Champions/PoChamps rule compatibility should be validated before stronger claims:

- Is Power Herb legal/selectable in the relevant item repository?
- Which charge moves are present in the move repository?
- Is move charge metadata already available, or does v0.75 need a small local allowlist?
- Are weather exceptions such as Solar Beam in sun in scope? Recommendation: no for v0.75.
- Does Meteor Beam's stat-change behavior need a separate context? Recommendation: no for v0.75.

## LLM Guardrail

The LLM should treat `charge_context` as limited context only.

Required wording principles:

- Power Herb may allow an eligible charge move to skip the charging turn.
- Raw damage estimates are unchanged.
- Raw `ko_context` is unchanged.
- KO/OHKO/2HKO estimates do not include charge-turn sequencing.
- Item consumption is not tracked.
- Final turn outcome is not calculated.
- Do not infer Power Herb if item is unknown or unconfirmed.
- Do not claim Power Herb boosts damage directly.
- Do not claim the move definitely resolves in one turn unless eligibility and item state are explicitly modeled.
- Exact item consumption, move eligibility edge cases, weather, switching, protection, and turn sequencing are not modeled.

Good wording examples:

- "Power Herb may allow this eligible charge move to skip its charging turn as limited context, but raw damage and KO estimates do not include turn sequencing."
- "Item consumption is not tracked, so this is not a final turn outcome prediction."
- "The raw KO chance is separate from Power Herb charge-turn usability."

Bad wording examples:

- "Power Herb directly boosts the damage."
- "This guarantees the move fires instantly."
- "The KO chance includes Power Herb turn skipping."
- "Power Herb has already been consumed."
- "This is a final one-turn KO because Power Herb is present."

When `charge_context.available` is false, or no `charge_context` is present for a move, the LLM should not invent Power Herb charge-turn effects or force a charge-turn limitation sentence.

## Tests Plan

Future v0.75 implementation tests should cover:

- user-confirmed Power Herb + charge move metadata -> `charge_context.available=true`
- Power Herb unknown or unconfirmed -> unavailable `item_not_user_confirmed` or absent
- no Power Herb -> unavailable `no_power_herb` or absent
- move not charge move -> unavailable `move_not_charge_move` or absent
- missing charge metadata -> unavailable `move_charge_metadata_missing`
- `charge_context` includes `turn_sequence_integrated=false`
- `charge_context` includes `item_consumption_tracked=false`
- `charge_context` includes `raw_damage_rolls_changed=false`
- `charge_context` includes `ko_context_changed=false`
- raw damage min/max/rolls unchanged
- `ko_context` unchanged
- `charge_context` does not alter OHKO chance
- my selected/available move direction
- opponent known move direction
- candidate moves excluded
- prompt guardrails
- existing Loaded Dice multi-hit regression
- existing King's Rock flinch regression
- existing Scope Lens critical regression
- existing Bright Powder accuracy regression
- existing recovery context regression
- existing KO context regression
- full pytest

## Interaction With Existing Systems

`charge_context` and `damage_estimate`:

- `charge_context` must not alter raw damage min/max/rolls.
- Power Herb is not a direct damage boost.
- Charge-turn usability is separate from type effectiveness and item damage modifiers.

`charge_context` and `ko_context`:

- `ko_context` remains limited raw damage-roll context.
- KO/OHKO/2HKO estimates do not include charge-turn sequencing.
- Do not expose charge-turn-adjusted KO probability in v0.75.

`charge_context` and `speed_context`:

- Speed comparison is not final turn order.
- Power Herb usability does not imply the user moves first or that the target cannot act.
- Speed/order integration requires Turn Engine and remains out of scope.

`charge_context` and other limited contexts:

- `accuracy_context`: hit reliability remains separate.
- `critical_context`: crit likelihood remains separate.
- `flinch_context`: King's Rock pressure remains separate.
- `multi_hit_context`: Loaded Dice hit-count reliability remains separate.
- `recovery_context`: recovery timing remains separate.
- `survival_context`: Focus Sash survival remains separate.

Power Herb with weather, move metadata, or item consumption:

- Weather exceptions and move-specific charge rules are future work.
- Item consumption and once-per-battle state are future work.
- Turn Engine is required before final outcome claims.

`opponent_assumptions`:

- No interaction. Possible samples must not create confirmed Power Herb or confirmed charge move effects.

## v0.75 Candidate

Recommended:

`v0.75 - Power Herb Limited Charge Context Implementation`

Include:

- user-confirmed Power Herb only
- additive move-level `charge_context`
- charge move metadata required for available context
- raw damage/ko_context unchanged
- `turn_sequence_integrated=false`
- `item_consumption_tracked=false`
- no turn-sequence-adjusted KO probability
- no item consumption tracking
- tests/docs
- no Turn Engine

Alternative:

`v0.75 - Charge Move Rule Validation Design`

Choose this if T1/T2 want to validate Power Herb legality, move eligibility, charge metadata availability, and weather exceptions before adding any LLM payload field.

T3 recommendation:

- Proceed with `v0.75 - Power Herb Limited Charge Context Implementation` only if a small, explicit charge move metadata source can be safely defined without fixture churn.
- If that metadata source is uncertain, do `v0.75 - Charge Move Rule Validation Design` first.
- Keep `charge_context` as a move-level sibling.
- Keep Power Herb as label/formula context.
- Continue excluding item consumption tracking and charge-turn-adjusted KO probability.

## Out of Scope

The v0.74 design excludes:

- code implementation
- `charge_context` implementation
- item consumption tracking
- turn-sequence-adjusted KO probability
- Turn Engine
- charge move damage modification
- weather interaction
- Protect / Substitute / switching integration
- KO context modification
- raw damage roll modification
- UI changes
- fixture changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits
