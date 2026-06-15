# v7.6 Turn Order Context Prompt Contract Tests

## Purpose

v7.6 locks the `turn_order_context` prompt guard contract before full prompt integration.

This milestone adds focused guard/copy tests and a minimal guard helper. It does not wire `turn_order_context` into `_build_ui_selected_prompt(...)`, does not call Gemini, and does not implement a full Turn Engine.

## Implementation Scope

Added helper:

```python
_build_turn_order_context_prompt_guard(payload)
```

The helper is conditional:

- returns an empty string when top-level `turn_order_context` is absent
- returns guard text when top-level `turn_order_context` is present

The helper is not yet inserted into the main prompt builder. Runtime prompt integration remains a v7.7 candidate.

## Default-Off Guard Absent

Tests verify:

- default payload has no top-level `turn_order_context`
- `_build_turn_order_context_prompt_guard(default_payload) == ""`
- default `_build_ui_selected_prompt(...)` does not include `turn_order_context`
- default prompt does not include the new `not a resolved move order` guard wording

## Explicit-On Guard Present

Tests verify that an explicit `turn_order_context` payload produces guard text containing:

- `limited planning context`
- `not a resolved move order`
- cautious priority / Speed hint wording
- `Do not claim exact final move order`
- `Do not claim speed ties are resolved`
- `Do not claim RNG items activate`
- `Do not infer item consumption`
- `Do not infer post-turn HP`

## Coexistence With `turn_pipeline`

Tests verify:

- `turn_pipeline` only: TurnPipeline guard present, turn-order guard absent
- `turn_order_context` only: turn-order guard present, TurnPipeline guard absent
- both present: both guards are independently available
- the combined guard text does not claim full turn simulation

## Forbidden Phrase Anchors

The guard must not positively instruct resolved outcomes with phrases such as:

- `will move first`
- `speed tie is resolved`
- `Quick Claw will activate`
- `item will be consumed`
- `post-turn HP will be`
- `full turn simulation shows`

These remain prompt/response safety anchors for future prompt integration and Gemini smoke work.

## Next Recommendation

Recommended:

- v7.7 Turn Order Context Prompt Integration

Alternative:

- v7.7 Turn Order Context Offline Advice Fixture

Do not run an actual Gemini smoke yet. Prompt integration should be wired and verified offline first.

## Safety Statement

- No actual Gemini call was executed.
- No Vertex AI call was executed.
- No UI checkbox auto-connection was implemented.
- No saved setting auto-enable was implemented.
- No full Turn Engine was implemented.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, or opponent set inference was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
