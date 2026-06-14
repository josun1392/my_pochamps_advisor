# v6.17 Controlled UI Mock Smoke

## Purpose

v6.17 verifies the future TurnPipeline UI flag flow at mock level without implementing UI.

This is a test and documentation step. It does not add a checkbox, change `LLMAdvicePanel` layout, connect the user-facing advice button to TurnPipeline, run Gemini, call Vertex AI, or implement full Turn Engine behavior.

## Mock Strategy

The smoke test uses a fake UI state object rather than real widgets:

- `turn_pipeline_enabled=None` represents the current default advice path
- `turn_pipeline_enabled=False` represents an unchecked future UI flag
- `turn_pipeline_enabled=True` represents a checked future UI flag

The test monkeypatches:

- `advisor_client.call_gemini`
- `_log_advisor_call`

All captured data stays in memory. No external provider, network, Vertex AI, or token-log write path is used.

## Flag Off Path

The mock flag-off path verifies:

- `run_ui_selected_advice(...)` receives `enable_turn_pipeline=False`
- payload has no top-level `turn_pipeline`
- prompt has no TurnPipeline guard
- fake status text does not include `턴 이벤트 후보 포함됨`
- mocked `call_gemini` receives the default-off prompt shape

The explicit flag-off prompt and payload match the default omitted-flag prompt and payload.

## Flag On Path

The mock flag-on path verifies:

- `run_ui_selected_advice(..., enable_turn_pipeline=True)` is called
- payload has top-level `turn_pipeline`
- `turn_pipeline.simulated == "limited"`
- prompt includes candidate / not-resolved / not-full-simulation guard text
- prompt includes no item consumption / exact post-turn HP resolution meaning
- fake status text can show `턴 이벤트 후보 포함됨 | 확정 시뮬레이션 아님`
- TurnPipeline event order remains Light Ball, Quick Claw, Focus Sash, Chilan Berry

## Default-Off Compatibility

The omitted-flag path remains the compatibility baseline:

- no top-level `turn_pipeline`
- no prompt guard
- no enabled status copy
- existing `damage_estimate`, `ko_context`, and item contexts remain present

## Existing Context Preservation

The test verifies the explicit-on path preserves:

- `damage_estimate`
- `ko_context`
- `species_stat_item_context`
- `speed_order_context`
- `survival_context`
- `chilan_berry_context`

`turn_pipeline` stays additive and does not replace existing payload contexts.

## UI Boundary

v6.17 still does not implement:

- `QCheckBox`
- `LLMAdvicePanel` layout changes
- `MainWindow._start_llm_advice` flag wiring
- user-facing advice button automatic TurnPipeline enablement

The existing UI remains default-off.

## Next Step Options

### Option A: v6.18 UI Dev Flag Implementation

Implement a dev-only checkbox or flag.

Pros:

- v6.17 mock smoke now covers the expected on/off behavior
- can remain default-off
- can reuse v6.12-v6.17 copy and tests

Cons:

- production UI implementation
- requires explicit T1 approval
- requires UI-level regression tests

### Option B: v6.18 UI Copy Snapshot Tests

Lock UI label/help/warning copy.

Pros:

- protects v6.12 wording decisions
- useful before or during implementation

Cons:

- may require partial UI implementation
- does not fully validate flag-to-advice wiring by itself

### Option C: v6.18 Final Pre-UI Integration Review

Document the final checklist before UI implementation.

Pros:

- safest non-code step
- useful if implementation approval is delayed

Cons:

- slower progress toward a usable dev flag

## Recommendation

Recommended next step if T1 approves UI implementation:

```text
v6.18 UI Dev Flag Implementation
```

Safe alternative without UI implementation:

```text
v6.18 Final Pre-UI Integration Review
```

## Safety Statement

- No actual Gemini call was executed in v6.17.
- No Vertex AI call was executed.
- No external network/provider call was executed.
- No UI checkbox was implemented.
- `LLMAdvicePanel` layout was not changed.
- No user-facing advice button automatic connection was added.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No speed/order simulation was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- `logs/token_usage.jsonl` was not committed or reset.
- Secrets, API keys, access tokens, ADC credentials, service-account JSON, billing details, and token-log contents were not printed or recorded.
