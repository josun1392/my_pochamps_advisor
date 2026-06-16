# v7.11 UI Flag Offline E2E Fixture

## Purpose

v7.11 verifies the existing UI developer checkbox path offline from widget state to mocked advice response.

This milestone does not call Gemini, call Vertex AI, add a checkbox, or implement a full Turn Engine.

## Fixture Scope

The fixture covers:

- `LLMAdvicePanel` checkbox state
- flag mapping from checkbox state
- `run_ui_selected_advice(...)`
- payload optional context generation
- prompt guards
- monkeypatched `call_gemini`
- monkeypatched `_log_advisor_call`
- mocked response safety wording

## Checkbox Off Result

Default/off state:

- checkbox starts unchecked
- `enable_turn_pipeline=False`
- `enable_turn_order_context=False`
- payload has no top-level `turn_pipeline`
- payload has no top-level `turn_order_context`
- prompt has no TurnPipeline guard
- prompt has no turn-order guard
- mocked `call_gemini` path only

## Checkbox On Result

Checked state:

- checkbox checked maps to both optional flags enabled
- source context is available from base Speed and Quick Claw candidate context
- payload includes top-level `turn_pipeline`
- payload includes top-level `turn_order_context`
- prompt includes the TurnPipeline guard
- prompt includes the turn-order guard
- serialized prompt payload includes both optional contexts

## Toggle No-Auto-Call Result

The fixture toggles the checkbox before the second advice request and confirms:

- no `advice_requested` signal is emitted by toggle alone
- no mocked Gemini call is made by toggle alone
- provider-facing work happens only through the explicit advice fixture call

## Mock / No-Call Guarantee

Provider-facing behavior is replaced in memory:

- `call_gemini` is monkeypatched
- `_log_advisor_call` is monkeypatched
- no provider or network call is made
- no Vertex AI call is made
- no token log contents are printed

## Mocked Response Safety

Mocked responses avoid resolved-outcome wording:

- `will move first`
- `speed tie is resolved`
- `Quick Claw will activate`
- `item will be consumed`
- `post-turn HP will be`
- `full turn simulation shows`

The response keeps both contexts as limited planning hints and says exact final order remains uncertain.

## Next Recommendation

Recommended:

- v7.12 Controlled UI Gemini Smoke Design

Safe alternatives:

- v7.12 Turn Order UI Integration Closure
- v7.12 Controlled UI Gemini Smoke, only after explicit T1 approval

Do not run actual Gemini before a one-call smoke design and explicit approval.

## Safety Statement

- No actual Gemini call was executed.
- No Vertex AI call was executed.
- No new checkbox was added.
- No saved setting auto-enable was implemented.
- Checkbox toggle alone does not call Gemini.
- No full Turn Engine was implemented.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, or opponent set inference was implemented.
- No EV/IV/nature inference was added.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
