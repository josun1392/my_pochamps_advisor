# v7.8 Turn Order Context Offline Advice Fixture

## Purpose

v7.8 verifies the `turn_order_context` path offline from payload to prompt to mocked LLM response.

This is a test fixture milestone. It does not call Gemini, call Vertex AI, connect UI flags, or implement a full Turn Engine.

## Fixture Scope

The fixture uses:

- `_build_ui_selected_prompt(...)`
- monkeypatched `advisor_client.call_gemini`
- monkeypatched `advisor_client._log_advisor_call`

`run_ui_selected_advice(...)` is not used for the explicit turn-order path because the runtime UI advice flow does not yet expose `turn_order_context` inputs. This keeps v7.8 explicit-only and avoids UI auto-connection.

## Mock / No-Call Guarantee

The fixture replaces provider-facing behavior in memory:

- `call_gemini` is a local fake function
- `_log_advisor_call` is a local fake function
- captured prompts are inspected in memory
- no provider or network call is made
- no token log write is required
- no token log contents are printed

## Default-Off Result

Default path:

- no `turn_order_context` prompt payload section
- no turn-order prompt guard
- mocked `call_gemini` path only
- existing default prompt behavior remains unchanged

## Explicit-On Result

Explicit turn-order path:

- supplied valid `turn_order_context`
- `enable_turn_order_context=True`
- prompt contains top-level `turn_order_context`
- prompt contains the turn-order safety guard
- serialized payload preserves `order_hint`
- `candidate_modifiers[*].resolved` remains `false`
- unsupported boundaries include speed tie resolution, RNG item activation, exact final order, item consumption, and post-turn HP update

## TurnPipeline Coexistence Result

Coexistence path:

- supplied limited `turn_pipeline`
- supplied valid `turn_order_context`
- prompt contains both top-level sections
- prompt contains both guards
- both contexts remain limited and non-resolved

## Mocked Response Safety

The mocked response uses cautious wording:

- exact final order remains uncertain
- Quick Claw may alter move order
- activation is not resolved
- no item consumption or post-turn HP is inferred

The fixture checks that mocked responses do not include resolved-outcome phrases:

- `will move first`
- `speed tie is resolved`
- `Quick Claw will activate`
- `item will be consumed`
- `post-turn HP will be`
- `full turn simulation shows`

## Next Recommendation

Recommended:

- v7.9 UI / Flag Integration Design

Safe alternative:

- v7.9 Controlled Turn Order Gemini Smoke Design

Do not run an actual Gemini call yet. UI / flag behavior should be designed before any controlled Gemini smoke.

## Safety Statement

- No actual Gemini call was executed.
- No Vertex AI call was executed.
- No UI checkbox auto-connection was implemented.
- No saved setting auto-enable was implemented.
- No full Turn Engine was implemented.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, or opponent set inference was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
