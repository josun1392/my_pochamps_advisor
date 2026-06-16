# v7.13 Controlled UI Gemini Smoke

## Purpose

v7.13 attempted the controlled UI Gemini smoke designed in v7.12.

The intended smoke path was:

```text
LLMAdvicePanel checkbox on
-> enable_turn_pipeline=True
-> enable_turn_order_context=True
-> prompt contains both optional context guards
-> maximum one actual Gemini call
```

The smoke was blocked before any provider call by a local harness guard mismatch. No Gemini call was executed.

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

## Actual Call Result

Result classification:

```text
BLOCKED
```

Call policy result:

- actual Gemini call count: 0
- retry count: 0
- Vertex AI call count: 0
- automatic retry: none
- repeated fixture call: none

Stop condition:

```text
unexpected exception before call
```

The local smoke harness used a strict guard requiring the prechecked prompt to match the prompt passed into the provider wrapper exactly. That guard raised before the provider call. Because v7.12 defined unexpected exception before call as a stop condition, the smoke stopped immediately and did not attempt Gemini.

## Response Safety Summary

No provider response was available, so response safety could not be classified as PASS/PARTIAL/FAIL.

Safety checks were not applicable:

- limited `turn_pipeline` treatment: not evaluated
- limited `turn_order_context` treatment: not evaluated
- exact final move order claim: no response
- speed tie resolution claim: no response
- Quick Claw activation confirmed claim: no response
- item consumption claim: no response
- post-turn HP claim: no response
- full turn simulation claim: no response
- `damage_estimate` / `ko_context` conflict: no response

## Token / Cost Safe Summary

- usage summary available: no
- raw token log included: no
- secrets included: no
- billing details included: no
- `logs/token_usage.jsonl` committed or reset: no

Because no provider call occurred, there is no response token usage to summarize.

## Follow-Up Recommendation

Recommended next:

```text
v7.14 Controlled UI Gemini Smoke Harness Alignment
```

Scope for v7.14:

- keep provider calls disabled until the harness prompt-alignment issue is fixed
- verify the prechecked prompt matches the actual `run_ui_selected_advice(...)` prompt path
- do not call Gemini unless T1 explicitly approves another one-call smoke after the fix

Safe alternative:

```text
v7.14 Turn Order UI Integration Closure
```

Use closure only if T1 chooses not to spend another provider call.

## Safety Statement

- No actual Gemini call was executed.
- No Vertex AI call was executed.
- No retry was attempted.
- No production UI behavior was changed.
- No checkbox behavior was changed.
- Checkbox toggle alone did not call Gemini.
- No saved setting auto-enable was implemented.
- No full Turn Engine was implemented.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, opponent set inference, or EV/IV/nature inference was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
