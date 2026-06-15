# v7.5 Turn Order Context Prompt Integration Design

## Purpose

v7.5 designs how optional `turn_order_context` should be represented in the LLM prompt.

This is design-only work. It does not implement prompt integration, does not call Gemini, and does not implement resolved turn order or full Turn Engine behavior.

## Current State

v7.4 added an explicit-only payload adapter:

- `build_ui_advice_payload(..., turn_order_context=..., enable_turn_order_context=True)`
- top-level `turn_order_context`
- default-off when omitted, disabled, or no context is supplied
- independent coexistence with top-level `turn_pipeline`
- no prompt integration yet

`turn_order_context` remains limited planning context:

- priority relation
- Speed relation
- unknown handling
- tie candidate labeling
- unresolved candidate modifiers
- unsupported boundaries

It does not provide final move order.

## Prompt Placement

Recommended placement:

- include `turn_order_context` in the same optional-context instruction area as `turn_pipeline`
- place the `turn_order_context` guard immediately after the `turn_pipeline` guard when both are present
- keep the guard near the top of `_build_ui_selected_prompt(...)`, before damage / KO / item-context explanation

Rationale:

- optional context is currently guarded near the top of the prompt
- `turn_pipeline` already has conditional guard wording
- `turn_order_context` needs similarly conditional guard wording
- placing the guard near the payload mention reduces the chance that the LLM treats the context as final battle truth

Alternative placements considered:

- known limitations area: useful, but less direct than a conditional prompt guard
- battle context summary after payload JSON: possible, but later in the prompt and easier to miss
- generic optional contexts section: acceptable if it stays adjacent to the actual context and guard

Recommended future implementation shape:

```python
turn_order_context_guard = _build_turn_order_context_prompt_guard(advice_payload)
...
f"{turn_pipeline_guard}"
f"{turn_order_context_guard}"
```

## Safety Wording

English prompt wording draft:

```text
If turn_order_context is present, treat it as limited planning context, not a resolved move order. Use it only as a cautious hint when priority and Speed data are available. Do not claim exact final move order, speed tie resolution, RNG item activation, item consumption, or post-turn HP from turn_order_context.
```

Expanded wording anchors for tests:

- `limited planning context`
- `not a resolved move order`
- `Do not claim exact final move order`
- `Do not claim speed ties are resolved`
- `Do not claim RNG items activate`
- `Do not infer item consumption`
- `Do not infer post-turn HP`
- `Use it only as a cautious hint when priority and speed data are available`

Korean documentation / UX wording:

```text
이 턴 순서 정보는 확정 행동 순서가 아니라 제한적 판단 보조 정보입니다.
스피드 타이, RNG 아이템 발동, 정확한 최종 행동 순서, 아이템 소모, 턴 종료 후 HP를 확정하지 마세요.
```

## Coexistence With `turn_pipeline`

When `turn_pipeline` and `turn_order_context` are both present:

- both are limited contexts
- neither is a full turn simulation
- `turn_order_context` provides cautious priority / Speed / order-hint context only
- `turn_pipeline` provides candidate event list and limited debug summary only
- neither context overrides `damage_estimate`, `ko_context`, or existing item contexts
- if the two contexts appear to conflict or leave ambiguity, the model should state uncertainty instead of resolving it

Recommended combined interpretation:

```text
Use turn_order_context only for cautious priority/Speed order hints.
Use turn_pipeline only for candidate events and known modifiers.
If these limited contexts conflict or are incomplete, say the result is uncertain rather than choosing a final order or resolved event.
```

Forbidden combined interpretation:

- `turn_order_context` resolves the order and `turn_pipeline` confirms the result
- `turn_pipeline` item candidates become consumed items
- a Quick Claw candidate becomes a guaranteed activation
- a tie candidate becomes resolved move order

## Forbidden Phrase Candidates

Future tests may check for forbidden response or prompt-copy patterns such as:

- `will move first`
- `speed tie is resolved`
- `Quick Claw will activate`
- `item will be consumed`
- `post-turn HP will be`
- `full turn simulation shows`
- `final move order is`
- `guaranteed to move before`

The eventual checks should allow case-insensitive and wording-variant matching. v7.5 only documents these candidates; it does not implement phrase checks.

## Prompt Contract Test Plan

Recommended v7.6 tests:

- default-off: when `turn_order_context` is absent, prompt has no `turn_order_context` guard
- explicit-on: when `turn_order_context` is present, prompt includes the safety guard
- guard contains `not a resolved move order`
- guard contains `Do not claim exact final move order`
- guard contains `Do not claim speed ties are resolved`
- guard contains `Do not claim RNG items activate`
- guard contains `Do not infer item consumption`
- guard contains `Do not infer post-turn HP`
- guard contains cautious priority / Speed hint wording
- `turn_pipeline` + `turn_order_context` prompt includes both guards
- default `turn_pipeline` behavior remains unchanged

Avoid brittle full-prompt snapshots. Prefer focused substring / meaning-anchor assertions.

## v7.6 Recommendation

Recommended:

- v7.6 Turn Order Context Prompt Contract Tests

Reason:

- the payload adapter is already implemented
- prompt wording is safety-sensitive
- tests should lock default-off and explicit-on prompt behavior before implementation

Faster alternative:

- v7.6 Turn Order Context Prompt Integration

If this route is chosen, implementation should still include focused prompt guard tests in the same milestone.

Not recommended yet:

- Gemini smoke
- UI / flag integration
- full Turn Engine work

## Safety Statement

- No production code was changed.
- No prompt integration was implemented.
- No UI checkbox auto-connection was implemented.
- No saved setting auto-enable was implemented.
- No actual Gemini call was executed.
- No Vertex AI call was executed.
- No full Turn Engine was implemented.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, or opponent set inference was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
