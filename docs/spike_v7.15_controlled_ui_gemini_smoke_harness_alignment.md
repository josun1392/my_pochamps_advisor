# v7.15 Controlled UI Gemini Smoke Harness Alignment

## Purpose

v7.15 aligns the controlled UI Gemini smoke harness after the v7.13 `BLOCKED` result.

This milestone does not call Gemini, retry Gemini, call Vertex AI, change UI behavior, or implement a full Turn Engine.

## v7.13 / v7.14 Recap

v7.13 stopped before provider call:

- pre-check passed
- actual Gemini call count: 0
- retry count: 0
- result: `BLOCKED`
- stop condition: unexpected exception before call

v7.14 triage found:

- cause classification: dynamic field difference
- direct pre-check prompt omitted the auto-built `turn_snapshot`
- `run_ui_selected_advice(...)` provider path included `turn_snapshot`
- `turn_pipeline` and `turn_order_context` guards were still present
- safety anchors were still present

## Alignment Change

The smoke harness alignment is test-only.

Offline prompt regression checks remain exact where they already exist. The provider-call pre-check now has a focused smoke guard fixture that:

- captures the prompt through the actual `run_ui_selected_advice(...)` path
- keeps `call_gemini` monkeypatched, so no provider call is made
- accepts harmless `turn_snapshot` presence
- requires structural optional context presence
- requires focused safety anchors
- avoids byte-for-byte equality against a separately built direct prompt

## Offline Exact Check Status

Existing offline checks remain in place:

- default-off prompt unchanged checks
- explicit-on prompt guard checks
- `turn_pipeline` + `turn_order_context` coexistence checks
- offline mocked advice fixtures

v7.15 does not weaken those exact / focused regression tests.

## Focused Smoke Guard Anchors

The provider-path smoke guard now requires:

- payload has `turn_pipeline`
- payload has `turn_order_context`
- TurnPipeline guard is present
- turn-order context guard is present
- `limited planning/debug summary only, not full turn simulation`
- `limited planning context, not a resolved move order`
- `Do not claim exact final move order`
- `Do not claim speed ties are resolved`
- `Do not claim RNG items activate`
- `Do not infer item consumption`
- `Do not infer post-turn HP`

The guard accepts `turn_snapshot` as optional provider-path context.

## Quick Claw Wording Guard

Quick Claw remains an unresolved order modifier candidate.

The smoke guard checks that Quick Claw context remains compatible with cautious wording such as:

- may alter move order
- unresolved
- possible
- candidate

The prompt guard does not treat negative safety wording such as `Do not claim Quick Claw will activate` as a positive resolved claim.

Positive resolved wording remains forbidden:

- `Quick Claw activates`
- `Quick Claw makes it move first`
- `Quick Claw lets it move first`
- `Quick Claw activation is confirmed`

## Test Coverage Added

v7.15 adds test-only harness coverage for:

- accepting provider-path prompt with auto-built `turn_snapshot`
- rejecting missing TurnPipeline guard
- rejecting missing turn-order context guard
- rejecting missing exact final order prohibition
- rejecting missing RNG / Quick Claw activation prohibition
- accepting harmless `turn_snapshot` presence
- not misclassifying negative Quick Claw safety wording as a positive claim

## Next Recommendation

Recommended next:

```text
v7.16 Controlled UI Gemini Smoke Retry
```

Requirements for v7.16:

- explicit T1 approval
- maximum 1 actual Gemini call
- no retry
- no Vertex AI call
- focused smoke guard must pass before provider call
- Quick Claw activation certainty remains FAIL

Safe alternatives:

```text
v7.16 Smoke Harness Closure
v7.16 Turn Order UI Integration Closure
```

## Safety Statement

- No actual Gemini call was executed.
- No Gemini retry was executed.
- No Vertex AI call was executed.
- No production behavior was changed.
- No UI checkbox behavior was changed.
- Checkbox toggle alone was not changed to call Gemini.
- No saved setting auto-enable was implemented.
- No full Turn Engine was implemented.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, opponent set inference, or EV/IV/nature inference was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- Raw full prompt was not recorded.
- Quick Claw activation certainty remains forbidden.
