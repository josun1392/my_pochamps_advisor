# v6.9 TurnPipeline Controlled Gemini Smoke Design

## Purpose

v6.9 designs a controlled actual-Gemini smoke strategy for the explicit TurnPipeline payload path. This milestone does not execute an actual Gemini call and does not use Vertex AI.

The design goal is to decide how a future smoke can verify Gemini interpretation of `turn_pipeline` without letting the model treat it as full simulation or resolved battle truth.

## Smoke Purpose

A future controlled smoke should check whether Gemini:

- treats `turn_pipeline` as a limited planning/debug summary
- avoids treating candidate events as resolved outcomes
- avoids claiming item consumption
- avoids claiming exact post-turn HP
- avoids claiming speed tie, RNG, exact trigger, status, or volatile resolution
- keeps `damage_estimate` as the damage primitive
- keeps `ko_context` as limited damage-roll context
- keeps existing item contexts as additive explanation surfaces
- does not treat `turn_pipeline` as a replacement for existing context

## Fixture Choice

| Fixture | Description | Pros | Cons | Recommendation |
|---|---|---|---|---|
| A. default-off payload | No `turn_pipeline`; current default advice behavior. | Lowest risk; already covered by existing smoke/snapshot tests. | Does not test the TurnPipeline guard. | Not needed for first controlled smoke. |
| B. explicit-on `turn_pipeline` payload | One fixture with limited TurnPipeline and prompt guard. | Directly tests the new risk surface; one call can validate candidate wording. | Higher prompt complexity; must be tightly controlled. | Recommended if actual smoke is approved. |
| C. compare default-off and explicit-on | Two actual calls with side-by-side interpretation. | Best comparison. | More cost/quota/variability; violates one-call goal. | Defer. |

Recommended fixture for a future smoke:

```text
explicit-on turn_pipeline payload fixture only
```

Rationale:

- default-off behavior is already locked by v6.8 payload snapshots
- the remaining model risk is how Gemini interprets explicit `turn_pipeline`
- a single explicit-on fixture keeps cost/quota exposure low

## Call Limit

Future controlled smoke policy:

- maximum actual Gemini calls: 1
- no automatic retry
- no Vertex AI call
- no fallback provider
- no UI button call
- no batch run
- no hidden second call for comparison

The call may proceed only after explicit T1 approval for v6.10 or later.

## Stop Conditions

Stop immediately and report without retry if any of the following occurs:

- HTTP 429
- `RESOURCE_EXHAUSTED`
- quota/prepay/billing blocker
- `API_KEY_INVALID`
- missing API key
- authentication failure
- provider routing uncertainty
- unexpected Vertex AI routing
- unexpected request count above 1
- any prompt fixture mismatch before call

The smoke must not print secrets, API keys, access tokens, ADC credentials, service-account JSON, billing details, or token-log contents.

## Secrets / Cost / Token Log Policy

Required policy:

- do not print `.env`
- do not print API keys or credentials
- do not print billing details
- do not print token-log contents
- do not commit or reset `logs/token_usage.jsonl`
- if a real call writes a local token log, leave it uncommitted
- record only high-level pass/fail and safe token usage fields if already surfaced by test output

## PASS Criteria

The future smoke can pass only if the Gemini response:

- treats `turn_pipeline` as limited planning/debug context
- does not describe candidate events as confirmed outcomes
- does not say Quick Claw will activate
- does not say Focus Sash / Focus Band / Chilan Berry will be consumed
- does not claim exact post-turn HP
- does not claim speed tie, RNG, exact trigger, status, or volatile resolution
- does not say full turn simulation was performed
- does not treat `turn_pipeline` as a stronger source than `damage_estimate` or `ko_context`
- keeps the recommendation grounded in existing damage and KO context limitations

## FAIL Criteria

The future smoke fails if the response says or clearly implies:

- Quick Claw will activate
- Focus Sash / Focus Band / Chilan Berry will be consumed
- after this turn HP will be an exact value
- full turn simulation shows or proves the outcome
- `turn_pipeline` confirms final battle truth
- `turn_pipeline` overrides `damage_estimate` or `ko_context`
- RNG, speed tie, exact trigger, status, or volatile state was resolved
- item consumption or post-turn state was simulated

## v6.10 Candidate

Recommended next milestone:

```text
v6.10 Controlled Gemini Smoke Execution
```

Conditions:

- T1 explicit approval required
- maximum 1 actual Gemini call
- no retry
- explicit-on TurnPipeline fixture only
- stop on 429 / `RESOURCE_EXHAUSTED` / API key / billing / routing errors
- no Vertex AI
- no UI checkbox
- no user-facing advice button automatic connection
- no full Turn Engine

Alternative:

```text
v6.10 Payload / Prompt Offline Eval
```

This alternative keeps actual calls disabled and performs more offline prompt review if quota, cost, or variability risk is not acceptable.

## Safety Statement

- No actual Gemini call was executed in v6.9.
- No Vertex AI call was executed.
- No production code was changed.
- No UI checkbox was implemented.
- No user-facing advice button automatic connection was added.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No speed/order simulation was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
