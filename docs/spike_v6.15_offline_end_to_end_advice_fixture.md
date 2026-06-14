# v6.15 Offline End-to-End Advice Fixture

## Purpose

v6.15 verifies the TurnPipeline advice path offline from payload to prompt to mocked recommendation.

This is a test and documentation step. It does not execute Gemini, call Vertex AI, implement UI, add a checkbox, connect the user-facing advice button to TurnPipeline by default, or implement full Turn Engine behavior.

## Fixture Strategy

The fixture uses `run_ui_selected_advice(...)` with monkeypatched dependencies:

- `advisor_client.call_gemini` is replaced with a local fake function
- `_log_advisor_call` is replaced with a local fake function
- no provider/network call is made
- no token log write is required

The same payload fixture is run twice:

1. default path with `enable_turn_pipeline` omitted
2. explicit path with `enable_turn_pipeline=True`

The test captures both prompts and parses the embedded JSON payload from each prompt.

## Default-Off Path

The default path verifies:

- one mocked advice call is made
- no top-level `turn_pipeline` appears in the payload
- no `turn_pipeline` prompt guard appears
- existing `damage_estimate`, `ko_context`, and item contexts remain present
- default advice behavior remains unchanged

## Explicit-On Path

The explicit path verifies:

- one mocked advice call is made
- top-level `turn_pipeline` appears in the prompt payload
- `turn_pipeline.simulated == "limited"`
- event order remains Light Ball, Quick Claw, Focus Sash, Chilan Berry
- prompt guard includes candidate / not-resolved / not-full-simulation wording
- prompt guard includes no RNG, item consumption, exact post-turn HP, and exact trigger resolution meaning
- existing `damage_estimate`, `ko_context`, and item contexts remain unchanged

## Mock / No-Call Guarantee

The fixture checks the fake `call_gemini` call count and captured prompts. It never invokes the real Gemini client, Vertex AI, or any external provider path.

The fake token logging helper records only in-memory test data and does not write token logs.

## Existing Context Preservation

The default and explicit prompt payloads are compared for the selected move contexts:

- `damage_estimate`
- `ko_context`
- `species_stat_item_context`
- `speed_order_context`
- `survival_context`
- `chilan_berry_context`

`turn_pipeline` remains additive and does not replace these surfaces.

## Next Step Options

### Option A: v6.16 UI Exposure Test Plan

Document UI test cases before implementing any dev flag or checkbox.

### Option B: v6.16 Controlled UI Mock Smoke

Exercise UI-level on/off behavior with mocks and no actual Gemini call.

### Option C: v6.16 UI Dev Flag Implementation

Implement a dev-only flag or checkbox only after explicit T1 approval.

## Recommendation

Recommended next step:

```text
v6.16 UI Exposure Test Plan
```

Safe alternative:

```text
v6.16 Controlled UI Mock Smoke
```

`v6.16 UI Dev Flag Implementation` should require explicit T1 approval.

## Safety Statement

- No actual Gemini call was executed in v6.15.
- No Vertex AI call was executed.
- No external network/provider call was executed.
- No UI checkbox was implemented.
- No user-facing advice button automatic connection was added.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No speed/order simulation was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- `logs/token_usage.jsonl` was not committed or reset.
- Secrets, API keys, access tokens, ADC credentials, service-account JSON, billing details, and token-log contents were not printed or recorded.
