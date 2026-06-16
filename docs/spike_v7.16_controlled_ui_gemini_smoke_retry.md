# v7.16 Controlled UI Gemini Smoke Retry

## Purpose

v7.16 retries the controlled UI Gemini smoke after the v7.15 harness alignment.

This smoke uses the actual UI checkbox-on path with both optional contexts enabled:

- `turn_pipeline`
- `turn_order_context`

The smoke allows at most one actual Gemini call, uses no retry, and does not implement a full Turn Engine.

## Pre-Check Result

Pre-check passed:

- checkbox default unchecked: passed
- checkbox toggle no-auto-call: passed
- checkbox on state used for explicit advice request: passed
- `enable_turn_pipeline=True`: passed
- `enable_turn_order_context=True`: passed
- prompt has TurnPipeline guard: passed
- prompt has turn-order context guard: passed
- prompt/payload has `turn_pipeline`: passed
- prompt/payload has `turn_order_context`: passed
- no full Turn Engine implementation: passed
- no resolved order implementation: passed
- no item consumption or post-turn HP implementation: passed

## Focused Smoke Guard Result

Focused smoke guard passed:

- `turn_pipeline` guard present
- `turn_order_context` guard present
- limited candidate/debug context anchor present
- limited planning context anchor present
- not-a-resolved-move-order anchor present
- exact final move order prohibition present
- speed tie resolution prohibition present
- RNG item activation prohibition present
- item consumption prohibition present
- post-turn HP prohibition present
- Quick Claw context remains candidate / possible / unresolved wording
- positive Quick Claw activation certainty wording absent

## Structural Summary

Provider-path prompt structure:

- payload has `turn_snapshot`: true
- payload has `turn_pipeline`: true
- payload has `turn_order_context`: true
- prompt has TurnPipeline guard: true
- prompt has turn-order context guard: true

The auto-built `turn_snapshot` presence is expected and harmless for this smoke.

## Actual Call Result

Result classification:

```text
PASS
```

Call policy result:

- actual Gemini call count: 1
- retry count: 0
- Vertex AI call count: 0
- stop condition: none
- repeated fixture call: none

## Response Safety Summary

Gemini treated the optional contexts as limited planning information.

Safety checks:

- limited `turn_pipeline` treatment: passed
- limited `turn_order_context` treatment: passed
- exact final move order claim: none found
- speed tie resolution claim: none found
- Quick Claw activation confirmed claim: none found
- item consumption claim: none found
- post-turn HP claim: none found
- full turn simulation claim: none found
- `damage_estimate` / `ko_context` conflict: none found

Quick Claw wording:

- safe: described as something that may occasionally affect move order
- unsafe certainty absent: no `Quick Claw will activate`, no `Quick Claw activates`, no `Quick Claw lets/makes it move first`, no `Quick Claw activation is confirmed`

Short safe excerpt:

> Garchomp appears faster based on raw Speed, but Charizard's user-confirmed Quick Claw may occasionally affect move order.

The response did not present this as resolved final turn order.

## Token / Cost Safe Summary

- usage summary available: yes
- input token field present: yes
- output token field present: yes
- cached token field present: yes
- raw token log included: no
- secrets included: no
- billing details included: no
- `logs/token_usage.jsonl` committed or reset: no

Raw token log contents were not printed or copied into this document.

## Follow-Up Recommendation

Recommended next:

```text
v7.17 Turn Order UI Integration Closure
```

Reason:

- controlled UI Gemini smoke retry passed
- exactly one Gemini call was made
- no retry was made
- no stop condition occurred
- response avoided resolved order / full simulation claims
- Quick Claw activation certainty remained absent

Safe alternatives:

```text
v7.17 Prompt Wording Polish
v8.0 Battle State / Opponent Move Context Expansion Design
```

Use wording polish only if T1/T2 wants to make the "appears faster based on raw Speed" phrasing even more cautious.

## Safety Statement

- Actual Gemini call count was exactly 1.
- No retry was executed.
- No repeated provider call was executed.
- No Vertex AI call was executed.
- No UI checkbox behavior was changed.
- Checkbox toggle alone did not call Gemini.
- No saved setting auto-enable was implemented.
- No full Turn Engine was implemented.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, opponent set inference, or EV/IV/nature inference was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- Quick Claw activation certainty remains forbidden.
