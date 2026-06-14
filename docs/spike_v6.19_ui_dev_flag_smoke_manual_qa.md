# v6.19 UI Dev Flag Smoke / Manual QA

## Purpose

v6.19 verifies the v6.18 TurnPipeline dev-only UI flag with smoke / QA checks.

This is a QA and documentation step. It does not change production UI logic, run Gemini, call Vertex AI, add persisted settings, or implement full Turn Engine behavior.

## QA Method

The app UI was checked with PySide offscreen smoke scripts:

- `LLMAdvicePanel` was instantiated directly
- `MainWindow` was instantiated offscreen without entering the interactive event loop
- checkbox state, tooltip text, status text, and toggle behavior were inspected
- no advice request was emitted by checkbox toggle
- no actual Gemini, Vertex AI, or external provider/network call was executed

Existing pytest fixtures verify the off/on advice-flow path with mocked `call_gemini`.

## Checklist Results

| Check | Result |
| --- | --- |
| `LLMAdvicePanel` advice button has `턴 이벤트 후보 포함` checkbox below it | PASS |
| checkbox defaults unchecked | PASS |
| tooltip/help exists | PASS |
| tooltip says this is not full turn simulation | PASS |
| tooltip says RNG / item consumption / post-turn HP / speed tie / exact trigger are not resolved | PASS |
| checkbox toggle alone does not emit `advice_requested` | PASS |
| checkbox toggle alone does not call Gemini | PASS |
| off state preserves default advice path | PASS, covered by existing mocked pytest fixture |
| on state passes `enable_turn_pipeline=True` | PASS, covered by existing mocked pytest fixture |
| enabled status can show `턴 이벤트 후보 포함됨 | 확정 시뮬레이션 아님` | PASS |
| UI copy/layout looks too complex or clipped in smoke inspection | No issue observed in offscreen smoke |

## Actual App Execution

Interactive app QA was not run with a live event loop. Instead, `MainWindow` was instantiated offscreen and inspected as an app-level smoke.

Observed:

- window title: `Master Ball Advisor v0.14`
- embedded `LLMAdvicePanel` contains `턴 이벤트 후보 포함`
- checkbox default is unchecked
- tooltip matches v6.18 help text
- status text matches `턴 이벤트 후보 포함됨 | 확정 시뮬레이션 아님`
- status label is hidden by default

## Off / On Behavior

Default / off behavior:

- checkbox unchecked
- `turn_pipeline_enabled()` returns `False`
- status label stays hidden
- existing default advice path remains no-`turn_pipeline`

On behavior:

- checkbox checked
- `turn_pipeline_enabled()` returns `True`
- status label becomes visible
- advice-flow fixture confirms `enable_turn_pipeline=True` can produce limited top-level `turn_pipeline`

## No-Call Confirmation

The QA scripts and pytest runs did not call the real provider path.

Confirmed:

- checkbox toggle emits no advice request
- QA did not press the advice button against real Gemini
- pytest uses mocked `call_gemini`
- no Vertex AI call
- no external provider/network call
- no token log commit/reset

## Issues / Improvements

No blocking issue was found.

Potential future polish:

- tooltip is intentionally long; if interactive QA finds it visually awkward, move the warning into a compact help label or status detail
- status copy is compact enough in the current smoke check

## Next Step Options

### Option A: v6.20 UI Copy Polish

Polish label, tooltip, and status placement without calling Gemini.

Use if interactive QA finds wording or placement awkward.

### Option B: v6.20 Controlled UI Gemini Smoke

Run one actual Gemini call through the UI with the checkbox enabled.

Requires explicit T1 approval, no retry, no Vertex AI, and stop on provider/auth/billing errors.

### Option C: v6.20 TurnPipeline UI Phase Closure

Close the current UI dev flag phase and move to the next larger feature area.

## Recommendation

Recommended next step:

```text
v6.20 Controlled UI Gemini Smoke
```

Only proceed if T1 explicitly approves one actual UI Gemini call. Safe no-call alternative:

```text
v6.20 TurnPipeline UI Phase Closure
```

## Safety Statement

- No production UI logic was changed in v6.19.
- No actual Gemini call was executed.
- No Vertex AI call was executed.
- No external network/provider call was executed.
- No saved setting or persisted auto-enable was implemented.
- Checkbox toggle alone did not call Gemini.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No speed/order simulation was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- `logs/token_usage.jsonl` was not committed or reset.
- Secrets, API keys, access tokens, ADC credentials, service-account JSON, billing details, and token-log contents were not printed or recorded.
