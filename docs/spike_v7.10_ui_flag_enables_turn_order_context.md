# v7.10 UI Flag Enables Turn Order Context

## Purpose

v7.10 connects the existing default-off `턴 이벤트 후보 포함` developer checkbox so the checked state enables both limited TurnPipeline context and limited deterministic turn-order context.

This is not a new checkbox, not a Gemini smoke, and not a full Turn Engine milestone.

## Implementation Scope

Changed behavior:

- the existing checkbox remains the single developer control
- unchecked maps to `enable_turn_pipeline=False` and `enable_turn_order_context=False`
- checked maps to `enable_turn_pipeline=True` and `enable_turn_order_context=True`
- `run_ui_selected_advice(...)` accepts `enable_turn_order_context: bool = False`
- `LLMAdviceWorker` stores and forwards `enable_turn_order_context`
- `_build_ui_selected_prompt(...)` builds optional turn-order context only when explicitly enabled

Unchanged behavior:

- checkbox default remains unchecked
- no persisted auto-enable setting exists
- checkbox toggle alone does not call Gemini
- the existing advice button remains the only UI action that starts advice generation
- no new checkbox was added

## Copy Decision

The visible checkbox label remains:

```text
턴 이벤트 후보 포함
```

The tooltip now clarifies the broader scope:

```text
확정 턴 시뮬레이션이 아니라, 턴 이벤트 후보와 선후공 판단 보조 정보를 조언에 추가합니다.
RNG, 아이템 소모, 턴 종료 후 HP, 스피드 타이, 정확한 발동 결과나 최종 행동 순서는 확정하지 않습니다.
```

The enabled status text is:

```text
턴 판단 후보 포함됨 | 확정 시뮬레이션 아님
```

## Source Context Behavior

The runtime source extraction is intentionally narrow:

- own/opponent base Speed can feed `turn_order_context`
- own/opponent user-confirmed final Speed can feed `turn_order_context`
- visible Quick Claw `speed_order_context` can feed an unresolved candidate modifier
- move priority remains unknown because current move metadata does not provide priority
- opponent move priority is not inferred
- EV/IV/nature are not inferred

If no Speed source or candidate modifier source exists, `enable_turn_order_context=True` still omits `turn_order_context`; it does not create an invalid empty context.

## Prompt Guard Behavior

When both source contexts are available and the checkbox is checked:

- prompt includes the TurnPipeline guard
- prompt includes the turn-order guard
- serialized payload includes top-level `turn_pipeline`
- serialized payload includes top-level `turn_order_context`

When unchecked:

- prompt remains default/off
- no `turn_pipeline` guard
- no `turn_order_context` guard

## No-Call Guarantee

Tests use mocked Gemini paths where advice generation is exercised.

No actual Gemini call, Vertex AI call, or provider/network call is made by v7.10.

## Tests

Coverage added or updated:

- checkbox default remains unchecked
- checkbox toggle does not emit `advice_requested`
- UI flag off maps to both optional flags disabled
- UI flag on maps to both optional flags enabled
- source-less enabled path omits invalid empty `turn_order_context`
- enabled path with base Speed / Quick Claw context includes valid `turn_order_context`
- prompt includes both guards when both contexts are present
- default-off prompt remains unchanged

## Next Recommendation

Recommended:

- v7.11 UI Flag Offline E2E Fixture

Safe alternatives:

- v7.11 Turn Order Source Extraction Design
- v7.11 Controlled Gemini Smoke Design

Do not run actual Gemini yet. Verify the UI checkbox through a mocked advice path first.

## Safety Statement

- No actual Gemini call was executed.
- No Vertex AI call was executed.
- No new checkbox was added.
- No saved setting auto-enable was implemented.
- Checkbox toggle alone does not call Gemini.
- No full Turn Engine was implemented.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, or opponent set inference was implemented.
- No EV/IV/nature inference was added.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
