# v6.11 Controlled Gemini Smoke Closure / Next UI Exposure Design

## Purpose

v6.11 closes the v6.10 controlled Gemini smoke result and defines the next safe exposure step for TurnPipeline.

This is a design and documentation step only. It does not run another Gemini call, implement production code, add a UI checkbox, or connect TurnPipeline to a user-facing advice button by default.

## v6.10 Result Summary

The v6.10 smoke used one explicit-on `turn_pipeline` payload fixture.

Result:

- actual Gemini call count: 1
- retry: none
- stop condition: none
- classification: PASS
- Vertex AI calls: none
- UI checkbox implementation: none
- user-facing advice button automatic connection: none

The fixture included a limited `turn_pipeline` with candidate / known-modifier events, existing `damage_estimate`, existing `ko_context`, and existing item contexts. The smoke was intended to check interpretation safety, not to validate a real battle scenario.

## Response Safety Findings

The response did not treat `turn_pipeline` as a full turn simulation or resolved battle truth.

PASS findings:

- candidate wording was maintained
- Quick Claw was treated as possible / "may", not guaranteed activation
- Focus Sash was treated as possible survival, not guaranteed consumption or a guaranteed result
- no full turn simulation claim
- no item consumption claim
- no exact post-turn HP claim
- no RNG, speed tie, or exact trigger resolution claim
- damage estimate was treated as a default-assumption estimate, not final battle damage
- `turn_pipeline` was not treated as stronger than `damage_estimate` or `ko_context`

The fixture also produced an awkward synthetic Light Ball-on-Charizard mention. That did not fail the smoke because the response stated the Light Ball effect was not applied to the Charizard damage estimate and did not use it as a resolved TurnPipeline outcome.

## Current Safety Boundary

Currently possible:

- generate a limited `turn_pipeline` from an explicit flag path
- insert `turn_pipeline` as an optional top-level payload field
- verify prompt guard presence / absence
- run mocked advice-flow dry-runs
- rely on one controlled Gemini smoke PASS as evidence that the current guard is understandable

Still not implemented:

- UI checkbox
- user-facing advice button automatic TurnPipeline enablement
- full Turn Engine
- item consumption
- HP update or post-turn state update
- RNG, speed tie, or exact trigger resolution
- automatic TurnPipeline generation for the default advice path

## Next Step Options

### Option A: v6.12 UI Exposure Design

Design how a UI checkbox, dev flag, or hidden diagnostic toggle would expose TurnPipeline later.

Pros:

- keeps implementation out of scope
- lets the team decide whether exposure is developer-only or user-facing
- can define copy, disabled states, rollback, and future tests before touching UI code

Cons:

- still does not validate user-facing copy
- may be premature if the wording surface is not settled

### Option B: v6.12 Prompt / UX Copy Design

Design the user-facing and prompt-facing copy for describing `turn_pipeline` as a limited planning summary.

Pros:

- safest immediate next step
- clarifies how to explain candidate events without implying resolved outcomes
- prepares future UI exposure without adding UI code

Cons:

- does not add a runtime feature
- UI placement remains a later design decision

### Option C: v6.12 UI Dev Flag Implementation

Implement a dev flag or checkbox that can enable TurnPipeline in the advice flow.

Pros:

- moves toward hands-on UI validation
- can be default-off if carefully scoped

Cons:

- increases user-facing surface area
- still early because copy and exposure policy are not finalized
- raises rollback and support expectations

## Recommendation

The safest next step is:

```text
v6.12 Prompt / UX Copy Design
```

Alternative safe next step:

```text
v6.12 UI Exposure Design
```

The next step should not implement a UI checkbox yet. It should keep actual Gemini calls out of scope unless a later T1 approval explicitly authorizes another controlled one-call smoke.

## Safety Statement

- No actual Gemini call was executed in v6.11.
- No Vertex AI call was executed.
- No production code was implemented.
- No UI checkbox was implemented.
- No user-facing advice button automatic connection was added.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No speed/order simulation was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- `logs/token_usage.jsonl` was not committed or reset.
- Secrets, API keys, access tokens, ADC credentials, service-account JSON, billing details, and token-log contents were not printed or recorded.
