# v6.7 TurnPipeline Advice Flow Closure / Stability Report

## Purpose

v6.7 closes the current TurnPipeline advice-flow dry-run phase and records the safety boundary before any runtime or UI exposure decision.

This is documentation-only. No production code was changed. No actual Gemini call was executed. No Vertex AI call was executed.

## Phase Summary

Completed TurnPipeline phase work:

- v5.3 Item Context -> TurnEvent mapper:
  - Added `build_turn_events_from_advice_payload(...)`.
  - First-pass mappings cover Light Ball, Quick Claw, Focus Band / Focus Sash, and Chilan Berry.
  - Only `available=true` contexts produce events.
- v5.4 mapper coverage:
  - Expanded fixture coverage for available, unavailable, blocked, deferred, unknown, and malformed contexts.
  - Verified stable event ordering and non-overstated event wording.
- v5.5 TurnPipelineResult fixture:
  - Added `build_turn_pipeline_result_from_advice_payload(...)`.
  - Bundles TurnEvent candidates into a limited `TurnPipelineResult`.
- v5.6 debug report:
  - Added local dry-run/debug report for TurnPipelineResult output.
  - No actual Gemini or Vertex AI calls.
- v5.7 payload exposure design:
  - Designed optional top-level `turn_pipeline` exposure.
  - Recommended default-off / explicit-only payload insertion.
- v5.8 optional top-level payload adapter:
  - Added `build_ui_advice_payload(..., turn_pipeline=None)`.
  - `turn_pipeline=None` preserves existing payload output.
  - `simulated="full"` is rejected.
- v5.9 prompt/contract guard:
  - Added guard wording so candidate events are not treated as resolved outcomes.
  - Preserved `damage_estimate`, `ko_context`, and existing item contexts.
- v6.0 minimal integration design:
  - Recommended explicit/default-off integration before any runtime exposure.
- v6.1 explicit generation adapter:
  - Added `build_optional_turn_pipeline_for_advice_payload(...)`.
  - Returns `None` by default and limited `TurnPipelineResult` only when explicitly enabled.
- v6.2 explicit payload smoke:
  - Verified helper plus optional payload adapter fixture path.
  - Kept advisor-client and UI automatic generation disabled.
- v6.3 UI/advice integration design:
  - Recommended payload-builder/helper smoke before UI runtime integration.
- v6.4 explicit advice payload builder smoke:
  - Verified default/off/on fixture paths, manual payload insertion, prompt guard behavior, and context preservation.
- v6.5 explicit advice flow integration design:
  - Compared `run_ui_selected_advice(...)` flag, payload-builder-only, dev UI flag, UI checkbox, and always-on generation.
  - Recommended v6.6 dry-run before any UI checkbox or automatic generation.
- v6.6 advice flow dry-run:
  - Added `run_ui_selected_advice(..., enable_turn_pipeline=False)`.
  - Default path omits `turn_pipeline` and prompt guard.
  - Explicit true path builds limited TurnPipeline and inserts it through the existing adapter.
  - Tests mock `call_gemini` and capture prompt text.

v6.4 was not skipped. It exists as the explicit payload-builder smoke step between v6.3 design and v6.5 advice-flow design.

## Current Safety Boundary

Currently possible:

- Explicit flag true plus mocked/dry-run path can generate a limited `turn_pipeline`.
- Optional top-level payload insertion works through `build_ui_advice_payload(..., turn_pipeline=...)`.
- Prompt guard present/absent behavior is covered by fixture and mocked-call tests.
- `damage_estimate`, `ko_context`, and existing item contexts remain present and are not replaced.

Still not done:

- actual Gemini call for TurnPipeline advice-flow output
- Vertex AI call
- UI checkbox
- user-facing advice button automatic TurnPipeline enablement
- full Turn Engine
- item trigger evaluation
- item consumption
- HP update or post-turn state mutation
- RNG, speed tie, exact trigger, status, or volatile resolution
- damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering change

## Known Issue: Timing-sensitive Perf

Known intermittent failure:

```text
test_item_damage_calculation_under_point_12ms_average
```

Observed pattern:

- isolated target reruns usually pass
- `tests/test_damage_perf.py -q` usually passes
- full suite and some ordering combinations can intermittently exceed the `0.120000ms` threshold
- observed medians around `0.125000ms` to `0.140625ms`

Actions not taken:

- no threshold change
- no skip or xfail
- no damage formula change
- no raw damage roll change
- no Q12 multiplier change
- no `ko_context` change

This should be treated as a separate perf stability concern. A future dedicated perf stability spike may be useful if this continues to block pushes.

## Next Step Options

| Option | Description | Pros | Cons | Recommendation |
|---|---|---|---|---|
| A. v6.8 Payload Snapshot Lockdown | Add snapshot-style tests for default/off/on payload and prompt shapes. No actual Gemini call. | Safest; locks contract before runtime exposure; no cost/quota risk; easy to review. | Still does not prove LLM wording quality. | Recommended next step. |
| B. v6.8 Controlled Gemini Smoke | Run at most one approved actual Gemini smoke against a pre-approved fixture. | Validates actual model interpretation. | Cost/quota risk; LLM variability; requires explicit approval and careful prompt capture. | Defer until after snapshot lockdown. |
| C. UI checkbox design/implementation | Add or design a user-visible TurnPipeline toggle. | Gives user control eventually. | Too early; increases user-facing surface and wording risk. | Not recommended yet. |

## Recommendation

Proceed with:

```text
v6.8 Payload Snapshot Lockdown
```

Scope should remain:

- actual Gemini call 없음
- default/off/on payload snapshot tests
- prompt guard snapshot tests
- no UI checkbox
- no user-facing advice button automatic enablement
- no full Turn Engine
- no item consumption, HP update, RNG, speed tie, or exact trigger resolution

Controlled Gemini Smoke should wait until the payload and prompt snapshots are locked.

## Safety Statement

- No production code was changed.
- No actual Gemini call was executed.
- No Vertex AI call was executed.
- No UI checkbox was implemented.
- No user-facing advice button automatic connection was added.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No speed/order simulation was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
