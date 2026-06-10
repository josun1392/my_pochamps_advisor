# v0.97 Speed-Order Item Context Design

## Current State

- `speed_context` already exists as a top-level payload section.
- `speed_context` is raw/effective Speed comparison only, never final turn order.
- Choice Scarf can already be represented in `speed_context.*.speed_modifiers` when:
  - both active Pokemon have user-confirmed final Speed
  - the relevant item profile is `status=user_confirmed`
  - `item_id="choice-scarf"`
- Choice Scarf choice lock is not modeled.
- Quick Claw has no current modeled advice context.
- v0.92/v0.93 default advice payload filtering established the pattern:
  - available legal context can be shown in default advice
  - unavailable/blocked/deferred item context reasons stay debug/enriched only
- The advisor still has no Turn Engine.
- Final action order, priority, speed ties as final turn truth, Trick Room, Tailwind, paralysis, boosts, abilities, weather, and item activation timing are not modeled.

## Legal Fixture Findings

`data/static/champions_legal_items.json` confirms:

### Choice Scarf

- `item_id`: `choice-scarf`
- `name_en`: `Choice Scarf`
- `category`: `hold_item`
- `legal`: `true`
- `legality_status`: `legal`
- `effect_support_status`: `legal_but_not_modeled`
- `ui_status`: `recognized_not_modeled`
- `effect_support.speed_order`: `not_supported`
- `effect_support.choice_lock`: `not_supported`
- Notes include: `Speed/order effects are not modeled.`

Interpretation:
- The legal fixture does not itself mark Choice Scarf as fully modeled.
- The local payload already has a limited `speed_context` implementation for Choice Scarf effective Speed.
- The fixture and payload contract remain intentionally separate: legality does not equal final speed-order truth.

### Quick Claw

- `item_id`: `quick-claw`
- `name_en`: `Quick Claw`
- `category`: `hold_item`
- `legal`: `true`
- `legality_status`: `legal`
- `effect_support_status`: `legal_but_not_modeled`
- `ui_status`: `recognized_not_modeled`
- `effect_support.speed_order`: `not_supported`
- Notes include: `Speed/order effects are not modeled.`

Interpretation:
- Quick Claw is Champions legal in the fixture.
- Quick Claw currently has no modeled speed-order item context.
- A future implementation must treat Quick Claw as limited context only, not final move order.

## Problem Definition

Speed-order item effects are easy for Gemini to overstate. Even when an item can affect Speed or move order, the app does not model enough battle state to determine final action order.

Risky missing pieces include:

- priority brackets
- Trick Room
- Tailwind
- paralysis
- Speed stages
- ability speed effects
- weather or terrain speed effects
- Quick Claw activation state
- exact activation probability in the current ruleset
- speed ties as final action order
- move order after switching/protection/other turn-state effects
- Turn Engine state

Therefore, speed-order item advice must stay limited and must not say a Pokemon will move first.

## Design Options

### Option A - Keep Choice Scarf in `speed_context`, add Quick Claw to `speed_context`

Pros:
- One top-level Speed-related field.
- Existing prompt and contract already explain that `speed_context` is not final turn order.

Cons:
- Quick Claw is not an effective Speed stat modifier.
- Putting Quick Claw beside raw/effective Speed can imply it changes the Speed number.
- Activation is probabilistic and more turn-order-like than Speed-stat-like.

### Option B - Keep Choice Scarf in `speed_context`, add `speed_order_context` for Quick Claw

Pros:
- Preserves existing Choice Scarf behavior.
- Keeps probabilistic move-order pressure separate from Speed-stat math.
- Avoids implying Quick Claw changes raw/effective Speed.
- Matches recent additive context patterns such as `flinch_context`, `multi_hit_context`, and `resist_berry_context`.

Cons:
- Adds another context type.
- Requires new filtering, contract, prompt, and tests.

### Option C - Add a unified `speed_order_item_context` for Choice Scarf and Quick Claw

Pros:
- One item-specific speed-order surface.
- Could summarize both stat-modifier and probabilistic item effects.

Cons:
- Duplicates existing Choice Scarf `speed_context`.
- Could cause Gemini to mention the same Choice Scarf effect twice.
- Harder to keep raw/effective Speed comparison separate from probabilistic move-order effects.

## Recommendation

Use Option B.

- Keep Choice Scarf in existing `speed_context`.
- Do not create duplicate Choice Scarf advice context in v0.98.
- Add a future `speed_order_context` only for limited move-order item pressure such as Quick Claw.
- Make `speed_order_context` additive, top-level or active-side scoped, not nested in `speed_context`, `damage_estimate`, or `ko_context`.
- Preserve `speed_context.is_final_turn_order=false`.
- Preserve default advice filtering:
  - `available=true` `speed_order_context` can be shown
  - `available=false` reasons are debug/enriched only

## Proposed Payload Shape

Quick Claw available context candidate:

```json
{
  "available": true,
  "mode": "limited_speed_order_item_context",
  "holder_side": "my_active",
  "item": {
    "item_id": "quick-claw",
    "status": "user_confirmed",
    "legal_status": "legal_modeled"
  },
  "speed_order_effect": {
    "type": "quick_claw",
    "effect_label": "may_affect_move_order",
    "formula_label": "quick_claw_limited_speed_order_context",
    "activation_probability_calculated": false,
    "final_move_order_calculated": false,
    "speed_tie_resolved": false,
    "priority_integrated": false,
    "turn_engine_integrated": false
  },
  "limitations": [
    "Limited speed-order item context only.",
    "Final move order, activation probability, priority, Trick Room, Tailwind, paralysis, boosts, abilities, weather, and turn sequencing are not modeled."
  ],
  "is_final_battle_truth": false
}
```

Unavailable context candidate:

```json
{
  "available": false,
  "reason": "item_not_user_confirmed",
  "mode": "limited_speed_order_item_context",
  "is_final_battle_truth": false
}
```

Reason codes to consider:

- `no_speed_order_item`
- `item_not_user_confirmed`
- `blocked_by_legal_item_coverage`
- `unsupported_speed_order_item`
- `quick_claw_activation_not_modeled`
- `turn_engine_required`

## Available Conditions

For Quick Claw `speed_order_context.available=true`:

- item holder is an active Pokemon
- item profile is `status=user_confirmed`
- item id is `quick-claw`
- item passes Champions legal gate
- context is limited to "may affect move order"

Do not require confirmed Speed stats for Quick Claw context, because Quick Claw does not modify raw/effective Speed.

For Choice Scarf:

- keep existing `speed_context`
- require both active Pokemon to have user-confirmed final Speed for `speed_context.available=true`
- require user-confirmed `choice-scarf` before applying the 1.5 effective Speed modifier
- keep choice lock unmodeled

## Default Advice Payload Policy

- `available=true` `speed_order_context` may remain in default advice payload.
- `available=false` `speed_order_context` should be removed from default advice payload.
- Debug/enriched payload may retain reason codes.
- Legal but unsupported item profiles should not force user-facing caveats.
- Unknown/unconfirmed item should not be inferred.
- `item_profiles` should not leak blocked/non-legal speed-order items into default advice if no available context exists.

## LLM Guardrails

Allowed wording:

- "Quick Claw may affect move order as limited context."
- "Speed order is not fully modeled."
- "Final move order is not calculated."
- "Choice Scarf effective Speed may be included in `speed_context`, but this is not final turn order."

Forbidden wording:

- "will move first"
- "guaranteed outspeeds"
- "confirmed first"
- "always acts before"
- "Quick Claw guarantees priority"
- "Quick Claw activation probability is X%"
- "Choice Scarf guarantees turn order"
- "Speed tie is resolved"

Concision rule:
- If available, mention speed-order item context in one short caveat at most.
- Do not let speed-order caveats become longer than the move recommendation.

## Interaction With Existing Systems

`speed_context`:
- Remains raw/effective Speed comparison only.
- Choice Scarf effective Speed stays there.
- `is_final_turn_order` remains false.

`speed_order_context`:
- Proposed for Quick Claw-like move-order item pressure.
- Does not alter raw/effective Speed values.
- Does not resolve Speed ties.
- Does not integrate priority or Turn Engine.

`damage_estimate` and `ko_context`:
- Unchanged.
- Speed-order item context must not change damage rolls, KO chance, OHKO/2HKO, or recommendation math.

Item slot interactions:
- Choice Scarf and Quick Claw cannot both be held by one Pokemon in a normal item slot, but payload logic should not combine effects into final turn order.

## Tests Plan

Future v0.98 implementation tests:

- user-confirmed legal Quick Claw -> `speed_order_context.available=true`
- Quick Claw context includes `activation_probability_calculated=false`
- Quick Claw context includes `final_move_order_calculated=false`
- Quick Claw context includes `priority_integrated=false`
- Quick Claw context includes `turn_engine_integrated=false`
- unconfirmed Quick Claw -> unavailable reason in debug/enriched only
- blocked/non-legal speed-order item -> hidden from default advice payload
- `available=false` speed-order context removed from default advice payload
- default advice payload does not include unavailable reason strings
- Choice Scarf existing `speed_context` tests remain green
- Choice Scarf is not duplicated into `speed_order_context`
- raw damage estimate unchanged
- raw damage rolls unchanged
- `ko_context` unchanged
- prompt/contract forbids "will move first", "guaranteed outspeeds", and "always acts before"
- full pytest

## Proposed v0.98 Path

Recommended:

`v0.98 - Quick Claw Limited Speed-Order Context Implementation`

Scope:
- Add `speed_order_context` for Quick Claw only.
- User-confirmed Quick Claw only.
- Champions legal gate required.
- No activation probability.
- No final move order.
- No speed tie resolution.
- No priority, Trick Room, Tailwind, paralysis, boosts, abilities, weather, item consumption, or Turn Engine.
- Preserve Choice Scarf in existing `speed_context`.
- Update prompt, contract, docs, and tests.

Alternative:

`v0.98 - Speed Context Contract Polish`

Use if T1/T2 decide Quick Claw should wait and the next step should only clean up existing Choice Scarf wording.

## Out of Scope

- code implementation
- speed calculation implementation
- final move order calculation
- speed tie final resolution
- priority integration
- Trick Room integration
- Tailwind integration
- paralysis integration
- Speed stage integration
- ability/weather interaction
- choice lock implementation
- Quick Claw activation probability calculation
- Turn Engine
- damage formula changes
- raw damage roll changes
- `ko_context` changes
- legal fixture mutation
- UI changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits

## T1/T2 Decision Points

- Approve keeping Choice Scarf in existing `speed_context`.
- Approve adding separate `speed_order_context` for Quick Claw.
- Confirm v0.98 should implement Quick Claw limited context or defer to wording polish.
- Confirm final move order, speed tie resolution, priority, and Turn Engine remain out of scope.
