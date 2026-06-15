# v7.9 Turn Order Context UI Flag Integration Design

## Purpose

v7.9 designs how the existing default-off UI developer flag should expose `turn_order_context` in a future implementation.

This is a design milestone only. It does not change UI behavior, connect `enable_turn_order_context`, call Gemini or Vertex AI, or implement a full Turn Engine.

## Current State

The existing UI developer flag is:

- label: `턴 이벤트 후보 포함`
- default state: unchecked
- persisted auto-on: none
- current runtime behavior: enables only `turn_pipeline`
- toggle behavior: toggling alone does not call Gemini
- advice behavior: the existing advice button reads the checkbox only when the user requests advice

`turn_order_context` is ready below the UI layer:

- standalone helper exists
- explicit-only payload adapter exists
- prompt guard integration exists
- offline mocked advice fixture is green
- no UI checkbox connection exists yet

## UI Flag Options

### Option A: One Checkbox Enables Both Contexts

The existing `턴 이벤트 후보 포함` checkbox would enable both:

- `turn_pipeline`
- `turn_order_context`

Pros:

- Keeps the UI simple.
- Matches the user mental model of one limited turn-planning assistance feature.
- Avoids adding another developer flag to the advice panel.
- Fits the current default-off rollout path.

Cons:

- The existing label says event candidates and does not clearly mention turn-order hints.
- Payload may become larger when both source contexts are available.
- Developers cannot test one context through UI while keeping the other disabled.

### Option B: Separate Checkbox

The existing checkbox remains `turn_pipeline`-only, and a new checkbox such as `선후공 판단 보조 포함` controls `turn_order_context`.

Pros:

- Clearer feature boundary.
- Easier per-context UI smoke testing.
- More direct mapping from UI state to payload flags.

Cons:

- Makes the advice panel busier.
- Creates two developer flags for closely related limited planning context.
- May make the feature look more user-facing and complex than intended.

### Option C: One Checkbox, Clarified Scope

Keep one checkbox and use it as the single limited turn-planning developer flag. Internally, the checked state would enable both `turn_pipeline` and `turn_order_context`, while tooltip/status/documentation clarify that the option includes event candidates and turn-order hints.

Pros:

- Best balance between simple UI and accurate scope.
- Keeps rollback to one control.
- Preserves the default-off policy and existing advice-button flow.
- Lets future implementation add `enable_turn_order_context=True` without creating another visible flag.

Cons:

- Tooltip/status copy must work harder to explain the combined scope.
- If future needs require independent toggles, the UI may need to split later.

## Selected Recommendation

Recommend Option C for v7.10:

- Keep one developer checkbox.
- Keep default unchecked.
- Do not persist an enabled state.
- When unchecked, pass both optional context flags as disabled.
- When checked, pass both optional context flags as enabled, but include each optional context only when valid source context exists.
- Do not trigger Gemini on checkbox toggle.
- Apply the flags only when the existing advice button is pressed.

This keeps the feature default-off, explicit, and easy to roll back.

## Copy Decision

### Label

Current label:

- `턴 이벤트 후보 포함`

Alternative:

- `턴 판단 후보 포함`

Recommendation:

- Keep `턴 이벤트 후보 포함` for the first v7.10 implementation to avoid unnecessary UI churn.
- Update tooltip/status wording so the combined scope is clear.
- Revisit `턴 판단 후보 포함` later if manual QA shows the old label hides the new turn-order hint behavior.

### Tooltip

Recommended future tooltip:

```text
확정 턴 시뮬레이션이 아니라, 턴 이벤트 후보와 선후공 판단 보조 정보를 조언에 추가합니다.
RNG, 아이템 소모, 턴 종료 후 HP, 스피드 타이, 정확한 발동 결과나 최종 행동 순서는 확정하지 않습니다.
```

### Status Copy

Recommended future status:

```text
턴 판단 후보 포함됨 | 확정 시뮬레이션 아님
```

The status copy may replace the current enabled status once the checkbox controls both contexts. If copy risk is a concern, v7.10 can keep the current status and document a v7.11 copy polish.

## UI Behavior

Future v7.10 implementation should preserve:

- checkbox default unchecked
- no persisted auto-on
- checkbox toggle does not call Gemini
- existing advice button remains the only user action that starts advice generation
- existing default/off advice behavior remains unchanged

Expected flag mapping:

| Checkbox state | `enable_turn_pipeline` | `enable_turn_order_context` |
| --- | --- | --- |
| unchecked | `False` | `False` |
| checked | `True` | `True` |

## Payload Behavior

When unchecked:

- no top-level `turn_pipeline`
- no top-level `turn_order_context`
- no TurnPipeline prompt guard
- no turn-order prompt guard

When checked:

- include `turn_pipeline` when the limited TurnPipeline source can be generated
- include `turn_order_context` only when valid source context exists
- omit `turn_order_context` if no valid source context exists
- never emit an invalid empty `turn_order_context`
- prompt guards are present only for contexts actually included

`turn_pipeline` and `turn_order_context` remain independent optional top-level fields. Neither should overwrite the other.

## Safety Boundary

This combined flag still does not implement:

- full Turn Engine
- resolved final move order
- speed tie resolution
- RNG item activation resolution
- item consumption
- post-turn HP update
- exact trigger resolution
- opponent set inference

Both optional contexts are limited planning context only.

## Implementation Tests Plan

Required v7.10 tests:

- checkbox defaults unchecked
- checkbox toggle emits no advice request and causes no Gemini call
- unchecked path passes `enable_turn_pipeline=False` and `enable_turn_order_context=False`
- checked path passes `enable_turn_pipeline=True` and `enable_turn_order_context=True`
- no source context path does not create invalid empty `turn_order_context`
- default-off payload omits both `turn_pipeline` and `turn_order_context`
- explicit-on payload includes both contexts when both are available
- prompt includes both guards when both contexts are included
- default-off prompt remains unchanged
- existing TurnPipeline-only tests remain green
- existing turn-order helper/payload/prompt/offline fixture tests remain green

## Next Recommendation

Recommended:

- v7.10 UI Flag Enables Turn Order Context

Safe alternatives:

- v7.10 UI Copy Polish
- v7.10 Controlled Gemini Smoke Design

Do not run an actual Gemini call in v7.10. First connect the flag offline, keep default-off behavior, and verify checkbox toggle no-auto-call behavior.

## Safety Statement

- No production code was changed.
- No UI checkbox behavior was changed.
- No UI checkbox auto-connection was implemented.
- No saved setting auto-enable was implemented.
- No actual Gemini call was executed.
- No Vertex AI call was executed.
- No full Turn Engine was implemented.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, or opponent set inference was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
