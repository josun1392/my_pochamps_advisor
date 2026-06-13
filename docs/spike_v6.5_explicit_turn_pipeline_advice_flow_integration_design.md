# v6.5 Explicit TurnPipeline Advice Flow Integration Design

## Purpose

v6.5 designs whether and how the explicit TurnPipeline path should move closer to the real advice flow after v6.4 payload-builder smoke coverage.

This is design-only. No production code was changed. No actual Gemini call was executed. No Vertex AI call was executed.

## v6.4 Completed State

Completed foundation:

- `build_optional_turn_pipeline_for_advice_payload(...)`
- `enable_turn_pipeline=False` or omitted returns `None`
- `enable_turn_pipeline=True` creates `simulated="limited"` `TurnPipelineResult`
- explicit `build_ui_advice_payload(..., turn_pipeline=result)` adds top-level `turn_pipeline`
- turn_pipeline prompt guard appears only when `turn_pipeline` is present
- default UI-selected advice flow does not generate TurnPipeline
- `run_ui_selected_advice(...)` does not call `build_optional_turn_pipeline_for_advice_payload(...)`
- `damage_estimate`, `ko_context`, and existing item contexts remain unchanged
- actual Gemini calls were not executed

## Current Advice Flow

Runtime path:

```text
LLMAdvicePanel.advice_requested
-> MainWindow._start_llm_advice()
-> MainWindow._build_llm_battle_input()
-> LLMAdviceWorker.run()
-> run_ui_selected_advice(battle_input, model=None)
-> try_build_turn_snapshot_from_battle_input(battle_input)
-> _build_ui_selected_prompt(battle_input, turn_snapshot=...)
-> build_ui_advice_payload(..., turn_snapshot=..., turn_pipeline=None)
-> call_gemini(prompt, model)
```

Current boundaries:

- `LLMAdvicePanel.advice_requested` carries no options.
- `LLMAdviceWorker` receives only `battle_input`.
- `run_ui_selected_advice(...)` accepts `battle_input` and optional `model`.
- `_build_ui_selected_prompt(...)` already accepts explicit `turn_pipeline`.
- `build_ui_advice_payload(...)` already accepts explicit `turn_pipeline`.
- `build_optional_turn_pipeline_for_advice_payload(...)` can build a limited pipeline from an already-built advice payload only when explicitly enabled.

## Integration Candidates

| Candidate | Description | Pros | Cons | Recommendation |
|---|---|---|---|---|
| A. `run_ui_selected_advice(..., enable_turn_pipeline=False)` | Add an optional default-off parameter to `run_ui_selected_advice`. When true, build a limited pipeline from the already-built payload before prompt construction. | Minimal public advice-flow integration; keeps one explicit flag; default path can remain unchanged; easy to test with mocked `call_gemini`. | Touches network-capable function; tests must avoid actual calls; risks being mistaken as production-ready if exposed too broadly. | Good candidate for v6.6 dry-run if implemented with mocked/no-call tests only. |
| B. payload builder only | Keep `build_ui_advice_payload(..., turn_pipeline=...)` and the helper as the only integration surfaces; callers manually generate and pass the pipeline. | Safest; already validated; no runtime advice behavior change; easiest rollback. | Does not exercise the advice-flow function signature; may slow migration toward controlled runtime exposure. | Safest baseline and acceptable fallback. |
| C. UI handler dev-only flag | Let `MainWindow._start_llm_advice()` or `LLMAdviceWorker` carry a hidden/dev flag. | Tests the UI path without visible checkbox; keeps user default off. | Adds UI worker plumbing; hidden behavior can be hard to discover; still more runtime surface than needed. | Not recommended before v6.6 dry-run. |
| D. UI checkbox | Add a user-visible checkbox to enable TurnPipeline. | User-controllable and transparent if labeled well. | Too early; implies feature maturity; adds UX wording risk; requires product decision. | Defer. |
| E. advisor_client always automatic | Always generate TurnPipeline in `run_ui_selected_advice(...)`. | No new UI or caller option. | Violates default-off; changes all prompts; rollback and overclaim risk. | Prohibited. |

## Recommendation

The safest next step is a narrow v6.6 dry-run design/implementation around candidate A, while preserving candidate B as fallback:

- Add optional `enable_turn_pipeline: bool = False` only if v6.6 decides to touch `run_ui_selected_advice(...)`.
- Keep default false and verify default prompt/payload behavior remains unchanged.
- When true, generate a limited `TurnPipelineResult` from an already-built advice payload.
- Pass the result explicitly to `_build_ui_selected_prompt(..., turn_pipeline=result)`.
- Do not add UI checkbox.
- Do not connect UI handler or worker options yet.
- Do not perform actual Gemini calls in tests; use fixture or mocked `call_gemini` dry-run only.

If risk posture is more conservative, v6.6 can remain candidate B: more payload-builder smoke and debug-script coverage without changing `run_ui_selected_advice(...)`.

## v6.6 MVP Proposal

Recommended next milestone:

```text
v6.6 Explicit TurnPipeline Advice Flow Dry-run
```

Scope:

- Optional flag default false.
- Actual Gemini call disabled in tests.
- No UI checkbox.
- No UI default behavior change.
- No full Turn Engine.
- Use fixture or mocked `call_gemini` only.
- Verify default path omits `turn_pipeline`.
- Verify explicit true path includes top-level `turn_pipeline`.
- Verify prompt guard appears only for explicit true path.
- Verify `damage_estimate`, `ko_context`, and item contexts remain unchanged.

Implementation options for v6.6:

1. Add `enable_turn_pipeline=False` to `_build_ui_selected_prompt(...)` only, then test prompt dry-run.
2. Add `enable_turn_pipeline=False` to `run_ui_selected_advice(...)` and test only with mocked `call_gemini`.
3. Keep production code unchanged and add another dry-run helper/script.

Recommended if implementing code: option 2, but only with strict mocked-call tests and no UI plumbing.

## Default-Off Policy

Required invariants:

- Default `run_ui_selected_advice(...)` behavior remains unchanged.
- Default UI-selected advice flow does not generate `turn_pipeline`.
- `enable_turn_pipeline=True` must be explicit.
- Actual Gemini tests must not be run for this integration.
- `simulated` must remain `limited`, never `full`.
- Passing no pipeline or `None` must preserve existing payload and prompt behavior.

## No-Actual-Gemini Verification Strategy

Recommended v6.6 tests:

- Mock `advisor_client.call_gemini`.
- Capture prompt text and assert whether `"turn_pipeline"` is present.
- Assert default path does not include the pipeline guard.
- Assert explicit true path includes the pipeline guard.
- Assert no UI worker or checkbox path is required.
- Assert `run_ui_selected_advice(...)` default source/path remains free of automatic generation unless the flag is true.

No test should use real credentials, `.env`, Vertex AI, Developer API billing, or token log contents.

## Relationship With Existing Contexts

TurnPipeline remains additive:

- `damage_estimate` remains the calculation source.
- `ko_context` remains the KO interpretation source.
- existing item contexts remain the explanation source.
- `turn_pipeline` remains a limited timing/planning/debug summary.
- `turn_pipeline` does not replace or override existing contexts.
- `turn_pipeline` does not change payload filtering, raw rolls, item availability, or item effect application.

## Safety / Rollback Plan

Safety:

- default off
- one flag
- no actual Gemini call in tests
- no UI default behavior change
- no UI checkbox
- no full Turn Engine
- no item consumption
- no HP update
- no RNG, speed tie, exact trigger, status, or volatile resolution
- no damage formula, raw roll, Q12, `ko_context`, or payload filtering changes

Rollback:

- Keep `enable_turn_pipeline=False`.
- Remove the optional flag if needed.
- Continue using `build_ui_advice_payload(..., turn_pipeline=...)` manually.
- Since no battle state is mutated, no persisted migration is required.

## Safety Statement

- No production code was changed.
- No advisor-client automatic generation was added.
- No UI-selected advice flow automatic connection was added.
- No UI checkbox was implemented.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No speed/order simulation was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- No actual Gemini call was executed.
- No Vertex AI call was executed.
