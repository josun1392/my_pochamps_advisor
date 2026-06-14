# v6.14 TurnPipeline UI Exposure Design

## Purpose

v6.14 designs how TurnPipeline could be exposed in the UI later.

This is a design and documentation step only. It does not implement a checkbox, connect the user-facing advice button to TurnPipeline by default, run Gemini, or change production behavior.

## Current State

Completed:

- optional top-level `turn_pipeline` payload adapter
- explicit/default-off TurnPipeline generation helper
- prompt guard present / absent tests
- default/off/on payload shape lockdown
- prompt / copy fixture anchors
- one controlled Gemini smoke PASS
- user-facing terminology design

Current naming:

- internal / documentation: `TurnPipeline`
- Korean UI label concept: `턴 이벤트 후보`
- Korean explanation: `제한적 턴 판단 보조`
- English UI label concept: `Candidate Turn Events`
- checkbox label candidate: `턴 이벤트 후보 포함`

Still not implemented:

- UI checkbox
- user-facing advice button automatic TurnPipeline enablement
- full Turn Engine
- item trigger evaluation
- item consumption
- HP update
- speed/order simulation

## UI Exposure Options

### Option A: Checkbox inside `LLMAdvicePanel`

Add a visible checkbox near the advice request button.

Pros:

- closest to the advice feature
- easy to discover when requesting advice
- straightforward mental model: users opt in before asking for advice

Cons:

- immediately increases user-facing surface area
- can make an experimental planning feature look production-ready
- requires careful warning/status copy in a compact panel
- risks users assuming the advice button now performs a full turn simulation

Recommendation:

Do not implement this as the first UI step. Revisit only after copy, test plan, and rollback are locked.

### Option B: Settings / developer option dev flag

Expose the feature behind a settings or developer option, still default-off.

Pros:

- makes the experimental nature clear
- avoids surprising normal advice users
- can include longer warning copy
- easier to remove or keep hidden if wording regresses

Cons:

- harder for casual users to find
- requires a settings/dev-option surface if one is not already available
- still needs UI smoke tests and default-off regression tests

Recommendation:

Preferred future implementation path if UI exposure is approved.

### Option C: No UI exposure; config/internal flag only

Keep `enable_turn_pipeline=True` available only for tests, scripts, or internal configuration.

Pros:

- safest option
- no new user-facing behavior
- current mocked/dry-run and payload tests remain sufficient

Cons:

- delays user-facing validation
- makes manual exploration less convenient

Recommendation:

Acceptable if the team wants another offline end-to-end fixture before UI exposure.

## Default-Off Policy

Required policy for any future UI exposure:

- default remains off
- existing advice button behavior remains unchanged
- `enable_turn_pipeline=True` is used only after explicit opt-in
- no saved setting should silently turn it on yet
- disabling the option must produce the same payload and prompt shape as the current default path
- enabling the option must still produce `simulated="limited"` only
- `simulated="full"` remains rejected

## Label / Help / Warning Copy

Korean label:

```text
턴 이벤트 후보 포함
```

Korean tooltip / help:

```text
확정 턴 시뮬레이션이 아니라, 아이템/속도/생존 가능성 같은 제한적 후보 정보를 조언에 추가합니다.
```

Korean warning:

```text
RNG, 아이템 소모, 턴 종료 후 HP, 스피드 타이, 정확한 발동 결과는 확정하지 않습니다.
```

English label:

```text
Include candidate turn events
```

English tooltip / help:

```text
Adds limited planning context, not a full turn simulation.
```

English warning:

```text
Does not resolve RNG, item consumption, post-turn HP, speed ties, or exact triggers.
```

## Status / Feedback Copy

Korean status candidates:

- `턴 이벤트 후보 포함됨`
- `제한적 턴 판단 보조 사용 중`
- `확정 시뮬레이션 아님`

Recommended compact status:

```text
턴 이벤트 후보 포함됨 | 확정 시뮬레이션 아님
```

English status candidates:

- `Candidate turn events included`
- `Limited turn context enabled`
- `Not a full turn simulation`

Recommended compact status:

```text
Candidate turn events included | Not a full turn simulation
```

## Implementation Safety Gates

Before implementing any UI exposure:

- payload snapshot tests are green
- prompt copy fixture tests are green
- no actual Gemini call is required during implementation
- default-off regression test exists
- enabled/disabled UI smoke test exists
- no user-facing advice button automatic enablement occurs without explicit opt-in
- no persisted setting auto-enables the feature
- no full Turn Engine is implemented or implied
- no item consumption, HP update, RNG, speed tie, or exact trigger resolution is implemented or implied
- rollback is one flag / one UI control removal

## Next Step Options

### Option A: v6.15 UI Dev Flag Implementation

Implement a dev-only checkbox or flag.

Pros:

- starts practical UI validation
- can remain default-off
- can use the copy and safety gates from v6.12-v6.14

Cons:

- production code implementation
- requires explicit T1 approval
- increases UI surface and support expectations

### Option B: v6.15 Offline End-to-End Advice Fixture

Verify payload -> prompt -> mocked advice path end to end without UI or actual Gemini.

Pros:

- safest next implementation step
- no actual Gemini call
- no UI exposure
- strengthens rollback confidence before UI code

Cons:

- still does not validate UI placement
- may duplicate some existing mocked advice-flow coverage

### Option C: v6.15 UI Exposure Test Plan

Document the exact tests needed before implementing the dev flag.

Pros:

- safest design-only option
- clarifies acceptance criteria before UI code

Cons:

- slower progress toward a usable UI toggle

## Recommendation

Recommended next step:

```text
v6.15 Offline End-to-End Advice Fixture
```

Safe alternative:

```text
v6.15 UI Exposure Test Plan
```

`v6.15 UI Dev Flag Implementation` should require explicit T1 approval.

## Safety Statement

- No actual Gemini call was executed in v6.14.
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
