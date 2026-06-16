# v7.17 Turn Order UI Integration Closure

## Purpose

v7.17 closes the Turn Order UI Integration phase that ran from v7.1 through v7.16.

The phase brought `turn_order_context` from design to controlled UI Gemini smoke:

- v7.1 designed deterministic turn-order context as limited planning context.
- v7.2 locked the payload contract.
- v7.3 added the deterministic helper.
- v7.4 added the optional payload adapter.
- v7.5 designed prompt integration.
- v7.6 locked prompt guard tests.
- v7.7 wired the guard into prompt construction.
- v7.8 added an offline advice fixture.
- v7.9 designed UI flag integration.
- v7.10 connected the existing UI dev flag.
- v7.11 verified the UI flag path offline.
- v7.12 designed the controlled UI Gemini smoke.
- v7.13 attempted the smoke and stopped before provider call.
- v7.14 triaged the smoke harness guard.
- v7.15 aligned the smoke harness.
- v7.16 retried the controlled UI Gemini smoke and passed.

Summary:

```text
turn_order_context helper -> payload adapter -> prompt guard -> UI flag -> offline E2E -> controlled Gemini smoke PASS
```

## Current Supported Behavior

- The existing UI checkbox `턴 이벤트 후보 포함` remains the only UI flag.
- The checkbox defaults unchecked.
- Checkbox off:
  - no top-level `turn_pipeline`
  - no top-level `turn_order_context`
  - no TurnPipeline prompt guard
  - no turn-order context prompt guard
- Checkbox on:
  - `turn_pipeline` is included when its source context is available.
  - `turn_order_context` is included when its source context is available.
  - prompt includes the TurnPipeline limited-context guard.
  - prompt includes the turn-order limited-planning guard.
- Checkbox toggle alone does not call Gemini.
- Advice generation still happens only through the existing advice request path.
- Controlled UI Gemini smoke passed in v7.16.

## Current Unsupported Behavior

This phase did not implement a full Turn Engine.

Unsupported boundaries:

- no full Turn Engine
- no resolved final move order
- no speed tie resolution
- no RNG resolution
- no Quick Claw activation resolution
- no item consumption
- no post-turn HP update
- no opponent set inference
- no EV/IV/nature inference
- no exact trigger resolution

`turn_order_context` is a limited planning hint. It is not battle truth and is not a resolved turn simulation.

## Quick Claw Boundary

Quick Claw is an unresolved candidate modifier.

Allowed wording:

- may activate
- could affect move order
- possible
- unresolved candidate
- activation is not guaranteed

Forbidden wording:

- Quick Claw will activate
- Quick Claw activates
- Quick Claw makes it move first
- Quick Claw activation is confirmed

The UI, payload, prompt guard, offline fixtures, and controlled smoke all keep Quick Claw as possible/unresolved context rather than confirmed activation.

## Smoke Result Summary

v7.16 controlled UI Gemini smoke retry:

- actual Gemini call count: 1
- retry count: 0
- Vertex AI call count: 0
- stop condition: none
- result: PASS

Response safety:

- Gemini treated `turn_pipeline` as limited candidate/debug context.
- Gemini treated `turn_order_context` as limited planning context.
- no exact final move order claim
- no speed tie resolution claim
- no Quick Claw activation confirmed claim
- no item consumption claim
- no post-turn HP claim
- no full turn simulation claim
- no `damage_estimate` / `ko_context` conflict

Safe response summary:

```text
Garchomp appeared faster based on raw Speed, while Charizard's user-confirmed Quick Claw was described only as something that may occasionally affect move order.
```

This was not presented as resolved final turn order.

## Test Summary

Latest recorded test results:

- `uv run pytest tests/test_advisor_payload_contract.py -q`: 127 passed
- `uv run pytest tests/test_advisor_turn_order_context.py -q`: 10 passed
- `uv run pytest tests/test_advisor_turn_events.py -q`: 27 passed
- `uv run pytest tests/test_turn_event.py -q`: 15 passed
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed
- `uv run pytest -q`: 1067 passed, 2 deselected

## Known Limitations

- Move priority is still often unknown in the UI-selected path.
- Opponent move priority and source extraction remain limited.
- `turn_order_context` is mostly a raw/base Speed hint unless confirmed final Speed is available.
- If final Speed is absent, base Speed only provides a cautious planning hint.
- Quick Claw and other RNG order modifiers remain unresolved candidates.
- The prompt can mention likely ordering only with caveats.
- No full battle resolution exists yet.
- No post-turn state is computed.

## Next Big Phase Candidates

### Option A: v8.0 Battle State / Opponent Move Context Expansion Design

Goal:

```text
Expand opponent move, state, field, priority, and Speed source context to improve advice quality.
```

Why this is recommended:

- The largest current advice-quality limit is missing opponent context.
- It is safer than jumping into full Turn Engine implementation.
- Turn order hints become more useful when opponent move and priority context are better known.
- Quick Claw, Speed, and order advice all benefit from better battle-state source context.

### Option B: v8.0 Deterministic Damage Application Preview Design

Goal:

```text
Design a limited HP preview based on damage_estimate without implementing post-turn state update.
```

This may be useful later, but it is closer to state transition logic and should keep strict boundaries.

### Option C: v8.0 Turn Engine Prototype Scope Split

Goal:

```text
Before building a full Turn Engine, split resolved vs unresolved behavior again and define staged implementation.
```

This is valuable, but the current safer next step is improving source context before resolved simulation.

## Recommendation

Recommended next:

```text
v8.0 Battle State / Opponent Move Context Expansion Design
```

The v7 turn-order UI integration phase is closed after controlled Gemini smoke PASS.

## Safety Statement

- No actual Gemini call was made in v7.17.
- No retry was made in v7.17.
- No Vertex AI call was made in v7.17.
- No production code was changed in v7.17.
- No UI checkbox behavior was changed in v7.17.
- No saved setting auto-enable was added.
- No full Turn Engine was implemented.
- No resolved turn order, speed tie resolver, RNG resolver, Quick Claw activation resolution, item consumption, post-turn HP update, opponent set inference, or EV/IV/nature inference was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- Quick Claw activation certainty remains forbidden.
