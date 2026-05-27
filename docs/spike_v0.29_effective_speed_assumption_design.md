# v0.29 Effective Speed Assumption Design

Status: design only  
Date: 2026-05-27

## 1. Current State

v0.28 added a top-level `speed_context` payload.

Current behavior:

- Raw Speed comparison exists.
- Raw Speed comparison is created only when both active Pokemon have user-confirmed final stats.
- `stat_profiles.*.final_stats.spe` is the only Speed source.
- Default Speed fallback is not used.
- `speed_context.is_final_turn_order` is always `false`.
- Effective Speed is not implemented.
- Final turn order is not implemented.
- Choice Scarf is selectable through the legal item selector.
- Choice Scarf currently remains legal-but-not-modeled for speed.
- Priority, Tailwind, Trick Room, paralysis, Speed stages, and ability speed effects are not implemented.
- Turn Engine state does not exist.

The current `MoveView` and move payload do not expose move priority. Current item data marks Choice Scarf `speed_order` as `not_supported`.

## 2. Problem Definition

Raw Speed, effective Speed, and final action order are different concepts.

Raw Speed can say:

- "Garchomp has 169 Speed."
- "Garchomp's raw Speed is higher than Charizard's raw Speed."

Effective Speed can say:

- "Charizard's estimated effective Speed is higher if the supported Choice Scarf speed modifier is applied."

Final action order would require more:

- move priority
- Trick Room
- Tailwind
- paralysis
- Speed stages
- ability effects
- selected action type
- speed tie handling
- future Turn Engine state

Even adding Choice Scarf does not prove final move order. A Choice Scarf Pokemon can still move after a priority move, under Trick Room, or in other unmodeled states. Therefore effective Speed must remain a limited estimate, not a turn-order guarantee.

The implementation should be staged:

1. Keep raw Speed comparison as the baseline.
2. Add one supported effective Speed modifier only when user-confirmed.
3. Keep final action order out of scope until priority and field rules are modeled.

## 3. Concept Separation

### A. raw_speed

Raw Speed is the final Spe stat from `stat_profiles`.

Status:

- Implemented in v0.28.
- Requires both active Pokemon to have user-confirmed final stats.
- Does not use default fallback.
- Does not include item/status/field/stage/ability modifiers.

### B. effective_speed

Effective Speed is raw Speed after applying supported speed modifiers.

Potential modifiers:

- Choice Scarf
- paralysis
- Tailwind
- Speed stages
- ability speed effects

v0.30 should consider only Choice Scarf, and only when it is user-confirmed.

### C. priority_bracket

Priority bracket is move-priority ordering.

Examples:

- Quick Attack-like priority moves
- Protect-like moves

Current status:

- Move priority is not in `MoveView`.
- Move priority is not in `_move_payload`.
- Priority should not be part of v0.30.

### D. field_speed_rule

Field speed rules can change how effective Speed is interpreted.

Examples:

- Trick Room reverses normal speed order.
- Tailwind modifies side speed.

Current status:

- No field state UI.
- No Trick Room field payload.
- No Tailwind payload.

### E. final_action_order

Final action order is the real in-turn ordering after priority, effective Speed, field rules, speed ties, and action type are resolved.

Current status:

- Not implemented.
- Must remain out of scope before a Turn Engine or explicit action-order model exists.

## 4. Option Comparison

### Option A - Keep Raw Speed Only

Keep v0.28 as-is.

Pros:

- Safest.
- No new overclaiming surface.
- No item effect status migration.

Cons:

- User-confirmed Choice Scarf remains unused.
- T1 can select a speed item but the payload cannot reflect its speed implication.

### Option B - Choice Scarf Only Effective Speed

Add Choice Scarf as the first supported speed modifier.

Scope:

- Require both active Pokemon to have user-confirmed final Spe.
- Read `item_profiles.my_active` and `item_profiles.opponent_active`.
- Apply `1.5x` effective Speed only when Choice Scarf is user-confirmed.
- Keep choice lock unmodeled.
- Keep `is_final_turn_order: false`.

Pros:

- Smallest useful effective Speed step.
- Uses existing ItemProfileDialog and StatProfileDialog data.
- No new UI is required.
- Keeps speed effect separate from final turn order.

Cons:

- Requires changing Choice Scarf speed support from not modeled to supported in the payload layer or item metadata.
- Still cannot account for priority, Trick Room, Tailwind, paralysis, stages, or abilities.

### Option C - Choice Scarf + Paralysis + Tailwind + Speed Stages

Add common Speed mechanics together.

Pros:

- More battle-realistic.
- Starts to cover common practical cases.

Cons:

- Needs new UI/input state.
- Tailwind and Trick Room are field/side states.
- Stages and paralysis require status tracking.
- More likely to be mistaken for final turn order.

This should be v0.31+.

### Option D - Effective Speed + Priority

Add priority brackets along with effective Speed.

Pros:

- Closer to real action order.
- Can prevent obvious false "faster" claims when priority exists.

Cons:

- Requires move priority metadata.
- Requires selected move/action semantics.
- Starts to become an action-order model.

This should wait until move metadata and action semantics are designed.

### Option E - Full Turn Engine

Model all ordering rules together.

Pros:

- Correct long-term architecture.

Cons:

- Too broad now.
- Requires field, status, item, ability, priority, switch/action state, and speed tie rules.

This remains a later milestone.

## 5. Recommended Direction

T3 recommendation:

- v0.29: design only.
- v0.30: Option B, `Choice Scarf Effective Speed Payload`.
- Keep v0.30 payload/helper-only if possible.
- Do not add Speed UI in v0.30.
- Do not implement final turn order.
- Do not implement priority, Tailwind, Trick Room, paralysis, Speed stages, or ability speed effects yet.

## 6. v0.30 Candidate Design

Recommended candidate:

`v0.30 - Choice Scarf Effective Speed Payload`

Include:

- Require both sides to have user-confirmed final Spe.
- Compute raw Speed as v0.28 does.
- Detect Choice Scarf from `item_profiles`.
- Apply Choice Scarf only when:
  - `status == "user_confirmed"`
  - `item_id == "choice-scarf"`
  - item legality is legal or repository-backed
  - v0.30 explicitly treats Choice Scarf speed as supported
- Compute `effective_speed = floor(raw_speed * 1.5)` or use an integer modifier convention documented in tests.
- Preserve raw Speed relation.
- Add effective Speed relation.
- Preserve `is_final_turn_order: false`.
- Add limitation that choice lock is not modeled.

Exclude:

- paralysis
- Tailwind
- Trick Room
- Speed stages
- priority
- ability speed effects
- full Turn Engine

Open implementation detail:

- Whether to use integer floor, rounded integer, or rational/Q-style modifier representation.

T3 recommendation:

- Use integer floor for v0.30 if matching Pokemon stat modifier conventions in local helpers.
- Also record the source modifier as `modifier: 1.5` so the LLM can explain it.

## 7. Payload Schema Proposal

### A. Extend `speed_context`

Recommended.

Pros:

- Keeps raw and effective Speed in one section.
- Avoids creating two competing speed sections.
- Lets the LLM compare raw and effective relations directly.
- Preserves the existing top-level contract.

Example:

```json
{
  "speed_context": {
    "mode": "choice_scarf_effective_speed_v0.30_candidate",
    "available": true,
    "my_active": {
      "raw_speed": 132,
      "effective_speed": 198,
      "source": "user_confirmed_final_stats",
      "is_user_confirmed": true,
      "speed_modifiers": [
        {
          "source": "item",
          "item_id": "choice-scarf",
          "name_en": "Choice Scarf",
          "modifier": 1.5,
          "applied": true,
          "modeled_effects": ["speed_modifier"],
          "unmodeled_effects": ["choice_lock"],
          "limitations": ["Choice lock is not modeled."]
        }
      ]
    },
    "opponent_active": {
      "raw_speed": 134,
      "effective_speed": 134,
      "source": "user_confirmed_final_stats",
      "is_user_confirmed": true,
      "speed_modifiers": []
    },
    "comparison": {
      "raw_speed_relation": "opponent_active_faster",
      "effective_speed_relation": "my_active_faster",
      "raw_speed_margin": 2,
      "effective_speed_margin": 64,
      "raw_speed_tie": false,
      "effective_speed_tie": false
    },
    "is_final_turn_order": false,
    "limitations": [
      "Effective Speed includes only supported speed modifiers.",
      "Choice Scarf speed may be applied only when user-confirmed and supported.",
      "Choice lock is not modeled.",
      "This does not confirm final turn order.",
      "Priority moves are not modeled.",
      "Trick Room is not modeled.",
      "Tailwind is not modeled.",
      "Paralysis is not modeled.",
      "Speed stages are not modeled.",
      "Ability speed effects are not modeled."
    ]
  }
}
```

Unavailable example:

```json
{
  "speed_context": {
    "mode": "choice_scarf_effective_speed_v0.30_candidate",
    "available": false,
    "reason": "insufficient_confirmed_final_stats",
    "limitations": [
      "Effective Speed comparison requires user-confirmed final Speed for both active Pokemon.",
      "Default Speed fallback is not used.",
      "This does not confirm final turn order."
    ],
    "is_final_turn_order": false
  }
}
```

### B. Add a new `effective_speed_context`

Not recommended for v0.30.

Pros:

- Keeps raw Speed payload untouched.

Cons:

- Duplicates Speed data.
- Makes LLM interpretation more complex.
- Risks raw/effective contradictions across sections.

## 8. Guardrail Design

Required LLM guardrails:

- Effective Speed is not final turn order.
- If `is_final_turn_order` is false, do not say "will move first".
- Use "appears faster by supported effective Speed estimate" rather than "outspeeds" as a guarantee.
- If Choice Scarf is applied, say it is a supported effective Speed modifier.
- If Choice Scarf is applied, say choice lock is not modeled.
- Do not apply Choice Scarf unless the payload marks its speed modifier as applied.
- Do not infer priority, Trick Room, Tailwind, paralysis, Speed stages, or ability effects.
- If raw Speed and effective Speed disagree, explain the difference.
- Do not link effective Speed to KO/OHKO/2HKO or final battle outcome.

Good examples:

- "With the supported Choice Scarf speed modifier, Charizard appears faster by effective Speed estimate."
- "This still does not guarantee final move order because priority, Trick Room, Tailwind, paralysis, and Speed stages are not modeled."
- "Raw Speed favors the opponent, but the supported Choice Scarf effective Speed estimate favors your Pokemon."

Bad examples:

- "Charizard will move first."
- "This guarantees outspeed."
- "Choice lock is handled."
- "This confirms the KO before the opponent can act."

## 9. UI Direction

v0.30 can likely avoid UI changes.

Existing UI already provides:

- `StatProfileDialog` for final Spe.
- `ItemProfileDialog` for legal item selection.
- Choice Scarf as a selectable legal item.

Therefore v0.30 can be payload/helper only:

- no new Speed input UI
- no new item UI
- no Tailwind/Trick Room/status UI

Future UI candidate:

- `SpeedAssumptionDialog`
- paralysis toggle
- Tailwind side toggle
- Trick Room field toggle
- Speed stage selector
- ability speed effect selector

Do not add this before deciding how effective Speed should coexist with final action order.

## 10. Data / Helper Design

Future helper concerns:

- Detect user-confirmed Choice Scarf from `item_profiles`.
- Do not apply unknown item.
- Do not apply `system_default_none` or `none`.
- Do not apply unconfirmed candidate item data.
- Keep speed item effects separate from damage item effects.
- Keep `damage_estimate.item_effects` as damage-specific.
- Put speed modifiers under `speed_context.*.speed_modifiers`.

Potential helper names:

- `_speed_context_payload(stat_profiles, item_profiles)`
- `_confirmed_raw_speed(profile)`
- `_speed_modifier_for_item(profile)`
- `_effective_speed(raw_speed, modifiers)`

Choice Scarf support status question:

- Current legal fixture records Choice Scarf as `legal_but_not_modeled` and `speed_order: not_supported`.
- v0.30 would need either:
  - a payload-layer allowlist that treats Choice Scarf speed as supported without changing the fixture, or
  - a fixture/repository update that marks `speed_modifier` as supported while keeping `choice_lock` not supported.

T3 recommendation:

- Prefer a small repository/fixture status update in v0.30 if the project wants source-of-truth consistency.
- Use a separate speed effect support field rather than overloading `damage_modifier_status`.
- Keep `choice_lock` explicitly unmodeled.

## 11. Tests Plan

Future v0.30 tests should include:

- no final stats -> unavailable
- one side final stats only -> unavailable
- both final stats + no item -> raw and effective Speed are the same
- my Choice Scarf -> my effective Speed is raw Speed times 1.5
- opponent Choice Scarf -> opponent effective Speed is raw Speed times 1.5
- Choice Scarf selected but not user-confirmed -> not applied
- unknown item -> not applied
- none/system_default_none item -> not applied
- Choice Scarf changes effective relation while `is_final_turn_order` remains false
- raw Speed relation and effective Speed relation both present
- choice lock limitation present
- priority limitation present
- Trick Room limitation present
- Tailwind limitation present
- paralysis limitation present
- Speed stages limitation present
- existing damage regression maintained
- existing item selector regression maintained
- existing payload contract regression maintained

## 12. Out of Scope

Explicitly excluded from v0.29:

- code implementation
- UI implementation
- effective Speed calculation implementation
- Choice Scarf speed implementation
- paralysis implementation
- Tailwind implementation
- Trick Room implementation
- Speed stage implementation
- priority implementation
- ability speed effect implementation
- final turn order implementation
- Turn Engine implementation
- KO/OHKO/2HKO implementation
- damage/probability engine changes
- logs, `.env`, secrets, API keys, or handoff capsule commits

