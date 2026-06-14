# v6.13 Prompt Copy Test Fixtures

## Purpose

v6.13 locks the v6.12 TurnPipeline prompt / UX copy rules with fixture-level tests.

This is a small test and documentation step. It does not implement UI, add a checkbox, connect TurnPipeline to the user-facing advice button, run Gemini, or implement full Turn Engine behavior.

## Fixture Strategy

The fixture tests use plain pytest assertions rather than an external snapshot dependency.

The tests lock:

- no-`turn_pipeline` prompt behavior
- explicit `turn_pipeline` prompt guard behavior
- candidate / limited / not-resolved meaning anchors
- resolved-outcome forbidden wording anchors
- no accidental UI copy / checkbox exposure

The tests avoid brittle full-prompt snapshots. They assert stable substrings that represent the contract meaning.

## No-Turn-Pipeline Path

When `turn_pipeline` is absent:

- the prompt does not contain the top-level `turn_pipeline` payload
- the TurnPipeline prompt guard is not added
- candidate event guard copy is not added
- `not full turn simulation` TurnPipeline warning copy is not added
- UI copy such as `턴 이벤트 후보` / `Candidate Turn Events` is not injected

This preserves the default advice behavior.

## Turn-Pipeline Path

When `turn_pipeline` is present:

- the prompt includes limited planning/debug summary wording
- the prompt says candidate events are not resolved outcomes
- the prompt says TurnPipeline events are candidate or known-modifier context
- the prompt says this is not full turn simulation
- the prompt says not to claim RNG resolution, item consumption, exact post-turn HP, guaranteed move order, exact item trigger result, or speed tie resolution
- the prompt says TurnPipeline does not replace `damage_estimate`, `ko_context`, or existing item contexts

## Copy Rule Anchors

Allowed meaning anchors:

- `limited planning/debug summary`
- `candidate or known-modifier context`
- `candidate events are not resolved outcomes`
- `not full turn simulation`

Forbidden resolved-outcome phrases:

- `will activate`
- `will be consumed`
- `post-turn HP will be`
- `full turn simulation shows`
- `speed tie is resolved`
- `guaranteed activation`

The forbidden phrases are not expected to appear in prompt text as resolved claims.

## UI Exposure Boundary

v6.13 keeps the v6.12 UI labels and help text as design-only copy:

- `턴 이벤트 후보 포함`
- `Candidate Turn Events`

The tests confirm this copy is not wired into `LLMAdvicePanel`, and no TurnPipeline checkbox / worker flag is added.

## Next Step Options

### Option A: v6.14 UI Exposure Design

Design the future UI location, toggle, status text, disabled states, and rollout / rollback plan.

### Option B: v6.14 Offline End-to-End Advice Fixture

Verify payload -> prompt -> mocked advice path end to end without an actual Gemini call.

### Option C: v6.14 UI Dev Flag Implementation

Implement an actual dev flag or checkbox only after explicit T1 approval.

## Recommendation

Recommended next step:

```text
v6.14 UI Exposure Design
```

Safe alternative:

```text
v6.14 Offline End-to-End Advice Fixture
```

Do not proceed directly to UI Dev Flag Implementation without explicit T1 approval.

## Safety Statement

- No actual Gemini call was executed in v6.13.
- No Vertex AI call was executed.
- No UI checkbox was implemented.
- No user-facing advice button automatic connection was added.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No speed/order simulation was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- No external snapshot dependency was added.
- `logs/token_usage.jsonl` was not committed or reset.
- Secrets, API keys, access tokens, ADC credentials, service-account JSON, billing details, and token-log contents were not printed or recorded.
