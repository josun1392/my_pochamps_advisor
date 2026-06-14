# v6.18 UI Dev Flag Implementation

## Purpose

v6.18 adds a default-off developer UI flag for including limited TurnPipeline candidate events in advice.

This is a minimal UI implementation. It does not make TurnPipeline an always-on user-facing feature, does not persist settings, does not call Gemini on toggle, and does not implement full Turn Engine behavior.

## UI Location

The flag lives inside `LLMAdvicePanel`, near the advice request button.

Label:

```text
턴 이벤트 후보 포함
```

Tooltip:

```text
확정 턴 시뮬레이션이 아니라, 아이템/속도/생존 가능성 같은 제한적 후보 정보를 조언에 추가합니다.
RNG, 아이템 소모, 턴 종료 후 HP, 스피드 타이, 정확한 발동 결과는 확정하지 않습니다.
```

Enabled status copy:

```text
턴 이벤트 후보 포함됨 | 확정 시뮬레이션 아님
```

## Default-Off Behavior

The checkbox defaults to unchecked.

There is no saved setting, no `QSettings` auto-enable, and no startup state that turns the feature on. If the user never checks the box, the existing advice button behavior stays the same default-off path.

## Flag Off Path

When the checkbox is unchecked:

- `panel.turn_pipeline_enabled()` returns `False`
- `LLMAdviceWorker` receives `enable_turn_pipeline=False`
- `run_ui_selected_advice(..., enable_turn_pipeline=False)` uses the default-off path
- payload has no top-level `turn_pipeline`
- prompt guard is absent

## Flag On Path

When the checkbox is checked and the advice button is pressed:

- `panel.turn_pipeline_enabled()` returns `True`
- `LLMAdviceWorker` receives `enable_turn_pipeline=True`
- `run_ui_selected_advice(..., enable_turn_pipeline=True)` builds a limited TurnPipeline result
- payload may include top-level `turn_pipeline`
- `turn_pipeline.simulated == "limited"`
- prompt guard is present

## No Auto Call Behavior

Toggling the checkbox does not emit `advice_requested`, does not call `call_gemini`, and does not call any provider.

The checkbox changes only local UI state and the small status label. A Gemini call can still happen only through the existing advice request flow.

## Status / Feedback

The status label is hidden by default. It becomes visible when the checkbox is checked and uses:

```text
턴 이벤트 후보 포함됨 | 확정 시뮬레이션 아님
```

This is intentionally compact and avoids implying a full turn simulation.

## Tests

v6.18 adds / updates fixture coverage for:

- checkbox default unchecked
- tooltip copy
- enabled status copy
- checkbox toggle does not emit advice requests
- no persisted auto-enable source
- `MainWindow._start_llm_advice` passes the checkbox state into `LLMAdviceWorker`
- `LLMAdviceWorker` defaults `enable_turn_pipeline=False`
- mocked default/off/on advice paths still avoid real Gemini calls

## Next Step Options

### Option A: v6.19 UI Dev Flag Smoke / Manual QA

Run the app and manually confirm the checkbox is default-off, toggles status copy, and passes the flag only when advice is requested.

Actual Gemini calls should remain disabled unless T1 approves at most one controlled call.

### Option B: v6.19 UI Copy Polish

Refine the label, tooltip, and status placement without running Gemini.

### Option C: v6.19 Controlled UI Gemini Smoke

Use the UI flag with one actual Gemini call only after explicit T1 approval.

## Recommendation

Recommended next step:

```text
v6.19 UI Dev Flag Smoke / Manual QA
```

Actual Gemini call remains opt-in and requires explicit approval.

## Safety Statement

- No actual Gemini call was executed in v6.18.
- No Vertex AI call was executed.
- No external network/provider call was executed.
- Checkbox toggle alone does not call Gemini.
- No saved setting or persisted auto-enable was implemented.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No speed/order simulation was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- `logs/token_usage.jsonl` was not committed or reset.
- Secrets, API keys, access tokens, ADC credentials, service-account JSON, billing details, and token-log contents were not printed or recorded.
