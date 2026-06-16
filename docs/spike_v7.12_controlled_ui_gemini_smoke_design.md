# v7.12 Controlled UI Gemini Smoke Design

## Purpose

v7.12 designs a future one-call controlled Gemini smoke for the UI checkbox path that now enables both `turn_pipeline` and `turn_order_context`.

This milestone does not execute Gemini, call Vertex AI, change UI behavior, or implement a full Turn Engine.

The future smoke should verify that, from the actual UI checkbox-on flow, Gemini treats both optional contexts as limited planning information:

- `turn_pipeline` as limited candidate/debug context
- `turn_order_context` as limited turn-order planning context
- no full simulation claim
- no resolved final move order claim
- no Quick Claw activation, speed tie, item consumption, or post-turn HP certainty

## Pre-Call Checklist

Before any actual provider call in a later milestone, the runner must verify:

- checkbox defaults unchecked
- checkbox toggle alone emits no `advice_requested`
- checkbox toggle alone makes no Gemini/provider call
- checkbox is explicitly set checked before the advice request
- the advice request maps to `enable_turn_pipeline=True`
- the advice request maps to `enable_turn_order_context=True`
- prompt includes the TurnPipeline guard
- prompt includes the turn-order context guard
- serialized payload includes `turn_pipeline` when its source context is available
- serialized payload includes `turn_order_context` when its source context is available
- no full Turn Engine, resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, or opponent set inference is present

If any pre-check fails, do not call Gemini. Record the result as `BLOCKED`.

## Call Count And Retry Policy

The controlled smoke must use a strict one-call policy:

- actual Gemini call count: maximum 1
- automatic retry: forbidden
- manual retry in the same milestone: forbidden
- repeated calls with the same fixture: forbidden
- if the call fails or times out, stop and record `BLOCKED` or `FAIL`

The call path should use a local counter or equivalent guard so a second provider call fails the smoke immediately.

## Stop Conditions

Stop immediately and do not attempt another call if any of these occur:

- HTTP 429
- `RESOURCE_EXHAUSTED`
- `API_KEY_INVALID`
- authentication or credential error
- billing, prepay, or credit related error
- provider routing error
- timeout after the single attempt
- unexpected exception before or after the call

Provider availability or billing failures should not be worked around with retries.

## Result Classification

Use one of these classifications:

- `PASS`: Gemini response satisfies the safety criteria.
- `PARTIAL`: response is mostly safe but wording polish or guard refinement is needed.
- `FAIL`: response includes resolved-order or full-simulation claims.
- `BLOCKED`: no usable response due to provider/auth/billing/quota/routing/timeout/pre-check failure.

## PASS Criteria

The response can be classified as `PASS` only if it:

- treats `turn_pipeline` as limited candidate/debug context
- treats `turn_order_context` as limited planning context
- does not claim exact final move order
- does not claim speed ties are resolved
- does not claim Quick Claw or other RNG items activate
- does not claim item consumption
- does not claim post-turn HP
- does not claim a full turn simulation
- does not override or conflict with `damage_estimate` / `ko_context`
- uses uncertainty when optional contexts are incomplete or in tension

## PARTIAL Criteria

Use `PARTIAL` when the response avoids hard resolved claims but has wording that could be clearer, such as:

- overconfident phrasing without a direct false claim
- weak distinction between likely order and resolved order
- missing one of the intended limitation reminders
- unclear relationship between `turn_pipeline` and `turn_order_context`

Do not run another call to clarify a `PARTIAL`; record the issue and recommend prompt polish.

## FAIL Criteria

Use `FAIL` if the response asserts or implies any of the following as a resolved result:

- `will move first` in a final-order sense
- `speed tie is resolved`
- `Quick Claw will activate`
- `item will be consumed`
- `post-turn HP will be`
- `full turn simulation shows`
- `turn_order_context` is a resolved source of final order
- `turn_pipeline` is a full simulation result

When checking these phrases, inspect the response body. Do not count prompt guard text such as "Do not claim X" as a response failure.

## Response Safety Checks

The smoke record should include a short safety summary for:

- final move order wording
- speed tie wording
- RNG item wording, especially Quick Claw
- item consumption wording
- post-turn HP wording
- full simulation wording
- interaction with `damage_estimate` and `ko_context`

Use short excerpts only when needed for classification. Prefer paraphrase for the rest.

## Recording Policy

Record:

- UI flag state
- pre-check result
- actual call count
- retry count
- stop condition, if any
- result classification
- short response safety summary
- PASS/PARTIAL/FAIL/BLOCKED rationale

Do not record:

- raw response in full
- API keys
- access tokens
- ADC credentials
- service account JSON
- billing details
- token log raw contents

`logs/token_usage.jsonl` may remain locally modified through existing logging behavior, but it must not be printed, committed, or reset as part of the smoke.

## Next Recommendation

Recommended next milestone:

```text
v7.13 Controlled UI Gemini Smoke
```

Requirements for v7.13:

- T1 explicit approval before the actual call
- maximum 1 Gemini call
- no retry
- no Vertex AI call
- stop immediately on provider/auth/billing/quota/routing/timeout errors
- no full Turn Engine or resolved turn order implementation

Safe alternative:

```text
v7.13 Turn Order UI Integration Closure
```

Use the closure alternative if T1 does not want to spend a provider call yet.

## Safety Statement

- No actual Gemini call was executed in v7.12.
- No Vertex AI call was executed.
- No production code was changed.
- No UI checkbox behavior was changed.
- No saved setting auto-enable was implemented.
- Checkbox toggle alone was not changed to call Gemini.
- No full Turn Engine was implemented.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, opponent set inference, or EV/IV/nature inference was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
