# v0.27 Speed / Turn Order Design

Status: design only  
Date: 2026-05-27

## 1. Current State

The advisor now has enough structured data to start thinking about Speed, but it does not yet have enough data to make final turn-order claims.

Current relevant state:

- `stat_profiles.my_active` and `stat_profiles.opponent_active` exist.
- Final stats can be user-confirmed for active Pokemon.
- `final_stats.spe` can represent a user-provided raw Speed stat.
- `item_profiles.my_active` and `item_profiles.opponent_active` exist.
- The legal item selector is backed by `ChampionsItemRepository`.
- Legal-but-not-modeled items such as `choice-scarf` can be selected.
- Choice Scarf is represented as legal, but its speed effect is not modeled.
- Damage estimates can use final stats and supported item damage modifiers.
- Speed order and turn order are not implemented.
- Turn Engine state is not implemented.

Current contract guardrails already prohibit claiming speed order or turn order unless explicit calculated fields are present.

## 2. Problem Definition

Raw final Speed is useful, but it is not the same as actual turn order.

Actual action order can depend on:

- move priority
- Trick Room
- Tailwind
- paralysis
- Speed stages
- Choice Scarf
- abilities that modify Speed or action order
- weather-based abilities
- terrain/field effects
- speed ties
- action type, such as switching or Protect-like moves
- future Turn Engine state

If the app compares only `final_stats.spe` and lets the LLM say "you will move first", it can overclaim. A safe design must separate raw Speed reference from final action order.

Therefore v0.27 should design the boundary, and v0.28 should only consider a narrow raw Speed comparison payload if approved.

## 3. Concept Separation

### A. raw_speed

`raw_speed` is the displayed/final Speed stat before battle-order modifiers.

Possible sources:

- `user_confirmed_final_stats`: use `stat_profiles.*.final_stats.spe`.
- `default_assumption`: derive from the existing default stat assumptions if a default fallback is explicitly approved.
- `unavailable`: no raw Speed should be emitted if neither side has a reliable source and default fallback is not approved.

Raw Speed is a comparison input, not a turn-order result.

### B. effective_speed

`effective_speed` is raw Speed after applying battle modifiers.

Examples:

- Speed stages
- Choice Scarf
- paralysis
- Tailwind
- abilities
- field/weather effects

This is a v0.29+ candidate because it needs more assumption/input state than the app currently has.

### C. move_priority

`move_priority` is the move's priority bracket.

The current `MoveView` and move payload include:

- `move_id`
- `name_en`
- `name_ko`
- `type`
- `category`
- `power`
- `accuracy`
- `pp`

They do not currently expose priority. Existing `MainWindow._move_payload` also does not include priority. Priority should remain excluded from v0.28 unless move metadata is expanded in a separate milestone.

### D. action_order

`action_order` is the actual in-turn ordering of selected actions.

It requires at least:

- priority bracket comparison
- effective Speed comparison
- Trick Room handling
- speed tie handling
- action type handling
- future Turn Engine state

Action order should not be emitted as final until a Turn Engine or explicit action-order model exists.

## 4. Option Comparison

### Option A - No Speed Order, Guardrail Only

Keep the current state and only preserve guardrails.

Pros:

- Safest.
- No new payload or LLM interpretation risk.
- No accidental turn-order claims.

Cons:

- Does not use user-confirmed final Speed.
- Leaves a useful tactical signal unavailable.

### Option B - Raw Final Spe Comparison Only

Add a top-level `speed_context` that compares raw Speed only.

Scope:

- Use `stat_profiles.my_active.final_stats.spe`.
- Use `stat_profiles.opponent_active.final_stats.spe`.
- Emit raw relation and margin.
- Keep `is_final_turn_order: false`.
- Do not apply Choice Scarf, Tailwind, Trick Room, paralysis, stages, abilities, or priority.

Pros:

- Small and useful.
- Fits the existing final stats feature.
- Keeps final turn-order guardrails intact.
- Good v0.28 candidate.

Cons:

- Can still be misread if wording is weak.
- Requires explicit LLM instructions not to say "will move first".
- Needs a decision on default Speed fallback.

### Option C - Effective Speed Assumptions

Add some modifiers such as Choice Scarf, paralysis, Tailwind, or Speed stages.

Pros:

- More realistic than raw Speed.
- Starts toward actual battle order.

Cons:

- Needs new UI/input state.
- Choice Scarf also has choice-lock implications.
- Tailwind, Trick Room, and paralysis need field/status state.
- Still not full action order without priority.

This should be v0.29+ at earliest.

### Option D - Full Turn Engine

Model action order across priority, Speed, field effects, statuses, abilities, items, switching, Protect-like moves, and selected actions.

Pros:

- Correct long-term direction.
- Enables future KO/turn outcome logic.

Cons:

- Too broad now.
- Requires state and rules that the current app intentionally does not model.

This should remain a later major milestone.

## 5. Recommended Direction

T3 recommendation:

- v0.27: design only.
- v0.28: implement Option B as `Raw Speed Comparison Payload` if T1/T2 approve.
- Do not claim final turn order.
- Do not model Choice Scarf speed yet.
- Do not model move priority yet.
- Do not add a Speed UI in v0.28.

Default fallback recommendation:

- Prefer user-confirmed final stats only for the first v0.28 implementation.
- If default fallback is allowed, mark it clearly as `source: default_assumption` and `is_user_confirmed: false`.
- Never mix default raw Speed into confident turn-order language.

## 6. Payload Schema Proposal

Top-level candidate:

```json
{
  "speed_context": {
    "mode": "raw_speed_comparison_v0.28_candidate",
    "my_active": {
      "raw_speed": 167,
      "source": "user_confirmed_final_stats",
      "is_user_confirmed": true
    },
    "opponent_active": {
      "raw_speed": 154,
      "source": "user_confirmed_final_stats",
      "is_user_confirmed": true
    },
    "comparison": {
      "raw_speed_relation": "my_active_faster",
      "speed_margin": 13,
      "speed_tie": false
    },
    "limitations": [
      "This is raw Speed comparison only.",
      "Priority moves are not modeled.",
      "Choice Scarf speed is not modeled.",
      "Tailwind is not modeled.",
      "Trick Room is not modeled.",
      "Speed stages are not modeled.",
      "Paralysis is not modeled.",
      "Ability speed effects are not modeled."
    ],
    "is_final_turn_order": false
  }
}
```

Suggested relation values:

- `my_active_faster`
- `opponent_active_faster`
- `speed_tie`
- `unavailable`

Suggested source values:

- `user_confirmed_final_stats`
- `default_assumption`
- `unavailable`

If only one side has raw Speed:

```json
{
  "speed_context": {
    "mode": "raw_speed_comparison_v0.28_candidate",
    "my_active": {
      "raw_speed": 167,
      "source": "user_confirmed_final_stats",
      "is_user_confirmed": true
    },
    "opponent_active": {
      "raw_speed": null,
      "source": "unavailable",
      "is_user_confirmed": false
    },
    "comparison": {
      "raw_speed_relation": "unavailable",
      "speed_margin": null,
      "speed_tie": false
    },
    "limitations": [
      "Both active Pokemon need raw Speed values for comparison.",
      "This does not determine final turn order."
    ],
    "is_final_turn_order": false
  }
}
```

## 7. Guardrail Design

LLM guardrails should be updated before or with any `speed_context` implementation.

Required guardrails:

- Do not confuse raw Speed comparison with final turn order.
- If `speed_context.is_final_turn_order` is false, do not say "will move first" or "guarantees moving first".
- Use wording such as "based on raw Speed only" or "appears faster by raw Speed".
- If Choice Scarf is selected but its speed effect is not modeled, do not say it makes the Pokemon faster.
- Do not infer Trick Room, Tailwind, paralysis, Speed boosts, ability effects, or priority if the payload does not calculate them.
- If `speed_tie` is true, mention uncertainty.
- Do not connect raw Speed comparison to KO chance, survival, or final battle outcome.

Allowed examples:

- "Based on raw Speed only, your Pokemon appears faster."
- "This does not confirm final turn order because priority, Choice Scarf, Tailwind, Trick Room, and Speed stages are not modeled."
- "The two active Pokemon have the same raw Speed, so this raw comparison is a speed tie and does not resolve action order."

Disallowed examples:

- "You will move first."
- "Choice Scarf makes you faster."
- "This guarantees turn order."
- "You outspeed, so this is a guaranteed KO."

## 8. UI Design Direction

v0.28 should avoid new UI if possible.

Recommended v0.28 UI behavior:

- Use existing `StatProfileDialog` final Spe values.
- Do not add a Speed dialog.
- Do not add Choice Scarf modeling toggles.
- Let the payload/LLM explain raw Speed only.

Future v0.29+ UI candidate:

- `SpeedAssumptionDialog`
- Speed stage input
- paralysis toggle
- Tailwind toggle per side
- Trick Room field toggle
- Choice Scarf modeled toggle only after deciding how choice lock is represented
- ability speed effect selection only after ability support exists

Until a Turn Engine exists, any UI should keep "raw/effective Speed assumptions" separate from "final turn order".

## 9. Data Source / Helper Design

### Final stats

`stat_profiles` is the cleanest source for v0.28:

- `stat_profiles.my_active.final_stats.spe`
- `stat_profiles.opponent_active.final_stats.spe`

Only profiles with `status: user_confirmed_final_stats` should be treated as user-confirmed.

### Default stats

The damage helper can currently compute default stats through existing stat helpers, but a speed feature should not silently become confident. If T1/T2 allow default fallback, it should be clearly marked as default-assumption raw Speed.

### Items

`item_profiles` may include legal-but-not-modeled speed items:

- `choice-scarf`
- `quick-claw`

For v0.28 these should be read only for limitations/guardrails, not for numeric Speed changes.

### Move priority

The current `MoveView` does not expose priority. The current move payload does not include priority. Move priority should remain out of scope for v0.28.

### Candidate helper shape

Possible helper names for v0.28:

- `build_speed_context(battle_input)`
- `_raw_speed_from_stat_profile(stat_profiles, key)`
- `_raw_speed_relation(my_speed, opponent_speed)`

These helpers should live near payload building or in a small LLM helper module, not in the damage engine.

## 10. Test Plan

Future implementation tests should include:

- No stat profiles: `speed_context` is unavailable or omitted, depending on final decision.
- One side missing Spe: relation is unavailable.
- Both sides user-confirmed Spe: `speed_context` is created.
- my faster relation.
- opponent faster relation.
- raw speed tie relation.
- speed margin is correct.
- `speed_context.is_final_turn_order` is false.
- Choice Scarf selected but not modeled.
- legal-but-not-modeled item does not change raw Speed.
- Priority not modeled guardrail remains present.
- Trick Room not modeled guardrail remains present.
- Tailwind not modeled guardrail remains present.
- paralysis not modeled guardrail remains present.
- existing damage estimate tests remain unchanged.
- existing item selector tests remain unchanged.
- payload contract tests cover raw Speed wording limits.

## 11. v0.28 Candidate

Recommended next implementation candidate:

`v0.28 - Raw Speed Comparison Payload`

Include:

- Extract Spe from `stat_profiles`.
- Add top-level `speed_context`.
- Compute raw Speed relation.
- Compute speed margin.
- Mark `is_final_turn_order: false`.
- Add LLM prompt/contract guardrails.
- Keep UI unchanged.

Exclude:

- Choice Scarf speed.
- Tailwind.
- Trick Room.
- paralysis.
- Speed boost/stage.
- move priority.
- ability speed effects.
- full Turn Engine.
- KO/OHKO/2HKO.
- damage/probability engine changes.

Open decision for v0.28:

- User-confirmed final stats only, or allow default Speed fallback?

T3 recommendation:

- Start with user-confirmed final stats only.
- If one or both sides are default, either omit comparison or mark it unavailable.
- This avoids making the current default-stat assumptions look like a speed-order feature.

## 12. Out of Scope

Explicitly excluded from v0.27:

- code implementation
- UI implementation
- Speed calculation implementation
- Choice Scarf speed implementation
- Tailwind implementation
- Trick Room implementation
- paralysis implementation
- Speed stage implementation
- priority move implementation
- ability speed effects
- Turn Engine
- KO/OHKO/2HKO
- damage/probability engine changes
- item effect additions
- logs, `.env`, secrets, API keys, or handoff capsule commits

