# v7.7 Turn Order Context Prompt Integration

## Purpose

v7.7 wires the `turn_order_context` prompt guard into `_build_ui_selected_prompt(...)` and verifies the prompt shape offline.

This remains an offline prompt integration milestone. It does not call Gemini, connect UI flags, or implement a full Turn Engine.

## Prompt Connection Point

Connection point:

- `llm.advisor_client._build_ui_selected_prompt(...)`

New keyword-only prompt inputs:

- `turn_order_context: dict[str, Any] | None = None`
- `enable_turn_order_context: bool = False`

The main UI advice flow does not pass these arguments, so existing user-facing behavior remains default-off.

## Guard Placement

Guard order:

1. `turn_snapshot` guard
2. `turn_pipeline` guard
3. `turn_order_context` guard
4. damage / KO / item / Speed context instructions

This follows the v7.5 design: `turn_order_context` sits in the same optional-context guard area as `turn_pipeline`, directly after it when both are present.

## Context Inclusion Style

v7.7 uses the existing prompt payload JSON as the context section.

When explicitly enabled, `build_ui_advice_payload(...)` inserts top-level `turn_order_context`, and `_build_ui_selected_prompt(...)` serializes the full advice payload at the end of the prompt as before.

No separate compact summary is added in v7.7. This keeps the integration small and avoids inventing another representation.

The prompt tests verify that the serialized payload contains:

- top-level `turn_order_context`
- `kind`
- `order_hint`
- unresolved `candidate_modifiers[*].resolved=false`
- unsupported boundaries

## Default-Off Behavior

Default/off prompt behavior is unchanged:

- omitted `turn_order_context` does not change the prompt
- supplied context with `enable_turn_order_context=False` does not change the prompt
- `enable_turn_order_context=True` with no supplied context does not change the prompt
- no `turn_order_context` guard is present by default

## Explicit-On Behavior

When a caller explicitly supplies a valid context and sets `enable_turn_order_context=True`, the prompt includes:

- top-level `turn_order_context` in the serialized payload
- guard wording that it is limited planning context
- guard wording that it is not a resolved move order
- warnings not to claim exact final move order, speed tie resolution, RNG item activation, item consumption, or post-turn HP

## Coexistence With `turn_pipeline`

Prompt tests cover:

- `turn_pipeline` only: TurnPipeline guard present, turn-order guard absent
- `turn_order_context` only: turn-order guard present, TurnPipeline guard absent
- both present: both guards present

Neither context is described as full simulation.

## Forbidden Positive Wording

Prompt tests avoid brittle blanket substring bans because the prompt may contain negative instructions such as `Do not say will move first`.

Instead, tests check that positive resolved-order phrases are absent:

- `You will move first`
- `will move first because`
- `speed tie is resolved`
- `Quick Claw will activate`
- `item will be consumed`
- `post-turn HP will be`
- `full turn simulation shows`

## Next Recommendation

Recommended:

- v7.8 Turn Order Context Offline Advice Fixture

Alternative:

- v7.8 UI / Flag Integration Design

Do not run an actual Gemini call yet. The next step should verify the prompt/context path through a mocked advice fixture.

## Safety Statement

- No actual Gemini call was executed.
- No Vertex AI call was executed.
- No UI checkbox auto-connection was implemented.
- No saved setting auto-enable was implemented.
- No full Turn Engine was implemented.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, or opponent set inference was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
