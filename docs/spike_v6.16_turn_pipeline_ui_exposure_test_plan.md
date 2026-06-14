# v6.16 TurnPipeline UI Exposure Test Plan

## Purpose

v6.16 defines the tests required before exposing TurnPipeline in the UI.

This is a test-plan and documentation step only. It does not implement UI, add a checkbox, connect the user-facing advice button to TurnPipeline, run Gemini, call Vertex AI, or implement full Turn Engine behavior.

## Scope

In scope:

- test plan for a future dev-only TurnPipeline UI flag
- default-off regression requirements
- UI flag on/off smoke requirements
- mocked advice-path and no-call guarantees
- copy visibility and rollback requirements
- implementation entry criteria

Out of scope:

- production code implementation
- UI checkbox implementation
- user-facing advice button auto-connection
- actual Gemini call
- Vertex AI call
- full Turn Engine
- item trigger evaluation
- item consumption
- HP update
- speed/order simulation

## UI Exposure Candidate Under Test

The safest candidate to test is a developer-only flag or developer option, not a general visible user checkbox.

Required properties:

- default-off
- no persisted auto-enable
- no change to existing advice button behavior when off
- explicit opt-in is required before `enable_turn_pipeline=True`
- one flag/control can disable or remove the feature
- copy must make the feature experimental and limited

Candidate Korean label:

```text
턴 이벤트 후보 포함
```

Candidate Korean help:

```text
확정 턴 시뮬레이션이 아니라, 아이템/속도/생존 가능성 같은 제한적 후보 정보를 조언에 추가합니다.
```

Candidate Korean warning:

```text
RNG, 아이템 소모, 턴 종료 후 HP, 스피드 타이, 정확한 발동 결과는 확정하지 않습니다.
```

Candidate enabled status:

```text
턴 이벤트 후보 포함됨 | 확정 시뮬레이션 아님
```

## Required Tests Before Implementation

### A. Default-Off Regression

Verify the existing advice path stays unchanged:

- existing advice button behavior is unchanged
- `enable_turn_pipeline` is omitted or `False`
- payload has no top-level `turn_pipeline`
- prompt has no TurnPipeline guard
- no user-facing TurnPipeline warning is shown by default
- existing payload snapshot tests remain green
- existing prompt copy fixture tests remain green
- existing offline end-to-end advice fixture remains green

### B. UI Flag Off Smoke

When the future checkbox/dev flag is unchecked:

- `run_ui_selected_advice(...)` is called with `enable_turn_pipeline=False` or with the flag omitted
- payload has no top-level `turn_pipeline`
- prompt guard is absent
- status copy does not show `턴 이벤트 후보 포함됨`
- warning copy is not shown as an enabled-state message
- fake `call_gemini` receives only the default-off prompt shape

### C. UI Flag On Smoke

When the future checkbox/dev flag is checked:

- `run_ui_selected_advice(...)` is called with `enable_turn_pipeline=True`
- payload has top-level `turn_pipeline`
- `turn_pipeline.simulated == "limited"`
- prompt guard is present
- prompt guard says candidate events are not resolved outcomes
- prompt guard says this is not full turn simulation
- prompt guard says not to resolve RNG, item consumption, post-turn HP, speed ties, or exact triggers
- status copy shows `턴 이벤트 후보 포함됨 | 확정 시뮬레이션 아님`
- existing `damage_estimate`, `ko_context`, and item contexts remain present

### D. No-Call Guarantee

UI smoke tests must avoid provider calls:

- mock `call_gemini`
- mock token logging or keep it in memory
- no actual Gemini call
- no external provider/network call
- no Vertex AI call
- no token log commit
- no secrets, API keys, access tokens, ADC credentials, service-account JSON, billing details, or token-log contents printed

### E. Copy Visibility

Copy tests should verify:

- label/help/warning copy matches v6.12 decisions
- warning is visible only when the feature is enabled or when help/tooltip text is opened
- default UI does not imply TurnPipeline is active
- enabled UI does not imply a full simulation
- status copy stays compact enough for the advice panel

The copy must not claim:

- guaranteed activation
- item consumption
- final post-turn HP
- full turn simulation result
- speed tie resolution
- exact trigger resolution

### F. Rollback / Safety Switch

Rollback must be straightforward:

- one flag/control can disable the feature
- default-off remains safe
- removing the checkbox/dev flag does not affect the current advice path
- no persisted user setting silently re-enables the feature
- disabling the flag restores the current payload and prompt shape

## Implementation Entry Criteria

Do not start UI implementation until:

- v6.15 offline end-to-end advice fixture is green
- v6.13 prompt copy fixtures are green
- v6.8 payload snapshot tests are green
- T1 explicitly approves UI implementation
- no unresolved Gemini provider issue blocks the planned workflow
- the implementation plan preserves default-off behavior
- the implementation plan includes UI flag on/off smoke tests
- the implementation plan includes no-call guarantees

Credit/provider policy:

- do not assume a credit blocker before Gemini reports `429`, billing, prepay, auth, or provider routing errors
- do not use automatic retries
- do not run unnecessary repeated actual calls
- UI implementation tests should remain offline/mocked

## Next Step Options

### Option A: v6.17 Controlled UI Mock Smoke

Exercise UI-level on/off behavior with mocks and no actual Gemini call.

Pros:

- safest next step
- validates future UI wiring assumptions without shipping a checkbox
- keeps provider/network calls disabled

Cons:

- still does not expose the feature to users
- may require light UI harness work

### Option B: v6.17 UI Dev Flag Implementation

Implement a dev-only checkbox or flag.

Pros:

- starts practical UI validation
- can remain default-off
- can reuse v6.12-v6.16 copy and safety gates

Cons:

- production code implementation
- requires explicit T1 approval
- increases UI surface area and rollback responsibility

### Option C: v6.17 UI Copy Snapshot Tests

Lock label/help/warning copy at UI level.

Pros:

- makes copy regressions visible
- useful before or alongside a dev flag

Cons:

- may require partial UI implementation
- does not by itself validate advice-flow wiring

## Recommendation

Recommended next step:

```text
v6.17 Controlled UI Mock Smoke
```

Acceptable alternative with explicit T1 approval:

```text
v6.17 UI Dev Flag Implementation
```

`v6.17 UI Copy Snapshot Tests` can be folded into either path if UI code becomes necessary.

## Safety Statement

- No production code was implemented in v6.16.
- No UI checkbox was implemented.
- No user-facing advice button automatic connection was added.
- No actual Gemini call was executed.
- No Vertex AI call was executed.
- No external network/provider call was executed.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No speed/order simulation was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- `logs/token_usage.jsonl` was not committed or reset.
- Secrets, API keys, access tokens, ADC credentials, service-account JSON, billing details, and token-log contents were not printed or recorded.
