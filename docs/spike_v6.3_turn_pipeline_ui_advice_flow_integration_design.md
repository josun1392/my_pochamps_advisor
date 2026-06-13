# v6.3 TurnPipeline UI / Advice Flow Integration Design

## Purpose

v6.3 designs how `TurnPipelineResult` could eventually connect to the UI-selected advice flow without changing runtime behavior yet.

This is design-only. No production code was changed. No actual Gemini call was executed. No Vertex AI call was executed.

## v6.2 Completed State

Completed foundation:

- `build_optional_turn_pipeline_for_advice_payload(...)`
- `enable_turn_pipeline=False` or omitted returns `None`
- `enable_turn_pipeline=True` creates a limited `TurnPipelineResult`
- generated result can be manually passed to `build_ui_advice_payload(..., turn_pipeline=...)`
- top-level `turn_pipeline` appears only when explicitly supplied
- turn_pipeline prompt guard appears only when `turn_pipeline` is present
- `damage_estimate`, `ko_context`, and existing item contexts are preserved
- `advisor_client.py` does not auto-generate `TurnPipelineResult`
- UI-selected advice flow does not auto-generate or auto-insert `turn_pipeline`
- actual Gemini calls were not executed

## Current UI-Selected Advice Flow

Runtime path inspected:

```text
LLMAdvicePanel.advice_requested
-> MainWindow._start_llm_advice()
-> MainWindow._build_llm_battle_input()
-> LLMAdviceWorker.run()
-> run_ui_selected_advice(battle_input)
-> try_build_turn_snapshot_from_battle_input(battle_input)
-> _build_ui_selected_prompt(battle_input, turn_snapshot=...)
-> build_ui_advice_payload(..., turn_snapshot=..., turn_pipeline=None)
-> call_gemini(prompt, model)
```

Current UI controls:

- `LLMAdvicePanel` exposes one request button.
- `LLMAdvicePanel.advice_requested` carries no payload or debug options.
- `LLMAdviceWorker` receives only `battle_input`.
- `run_ui_selected_advice(...)` accepts only `battle_input` and optional `model`.

Current payload boundary:

- `build_ui_advice_payload(...)` already accepts explicit `turn_pipeline`.
- `_build_ui_selected_prompt(...)` already accepts explicit `turn_pipeline`.
- `run_ui_selected_advice(...)` does not pass `turn_pipeline`.

## Integration Candidates

| Candidate | Description | Pros | Cons | Recommendation |
|---|---|---|---|---|
| A. UI checkbox / dev flag | Add a UI or hidden dev flag that eventually controls `enable_turn_pipeline`. | Gives a human-controlled path; keeps default off if unchecked. | Adds UI surface and worker plumbing; may imply user-facing confidence before pipeline is mature; requires design for debug wording. | Not first v6.4 implementation. Consider after fixture smoke. |
| B. payload builder/helper optional parameter only | Keep explicit generation at helper/payload-builder test boundary. | Safest; default path unchanged; validates integration without UI or Gemini; easy rollback. | Not directly user-operable; still requires manual tests/scripts. | Recommended v6.4 MVP. |
| C. debug-only script | Keep using local dry-run scripts and maybe extend them. | Very safe and inspectable; no runtime risk. | Does not exercise prompt/payload builder as much as fixture tests; limited coverage of advice-flow boundaries. | Useful support path, not primary v6.4. |
| D. advisor_client automatic generation | `run_ui_selected_advice(...)` automatically builds and inserts `turn_pipeline`. | No UI work; simplest runtime behavior. | Violates default-off posture; changes prompt payload for all advice calls; harder rollback; risks LLM overreading candidate events. | Not recommended and out of scope. |

## Recommended Integration Path

For v6.4, keep integration at the explicit helper and payload-builder boundary:

```text
v6.4 Explicit TurnPipeline Advice Payload Builder Smoke
```

Recommended policy:

- Default UI-selected advice flow does not generate TurnPipeline.
- `run_ui_selected_advice(...)` remains unchanged.
- UI widgets remain unchanged.
- `enable_turn_pipeline=True` appears only in fixture/dev smoke tests.
- The generated `TurnPipelineResult` is manually supplied to `build_ui_advice_payload(..., turn_pipeline=...)` or `_build_ui_selected_prompt(..., turn_pipeline=...)`.
- Tests verify payload and prompt behavior without calling Gemini.

## Default-Off Policy

Required invariant:

- Default UI-selected advice flow does not create `turn_pipeline`.
- Default `build_optional_turn_pipeline_for_advice_payload(...)` returns `None`.
- Passing `turn_pipeline=None` preserves existing payload/prompt behavior.
- `enable_turn_pipeline=True` must be explicit in a fixture/dev path.
- Any future UI flag must default off and must be labeled as debug/planning, not battle truth.

## v6.4 MVP Proposal

Recommended scope:

- Add fixture smoke around an already-built UI-style payload.
- Use `enable_turn_pipeline=True` explicitly.
- Confirm the resulting payload includes top-level `turn_pipeline`.
- Confirm prompt guard appears only when `turn_pipeline` is present.
- Confirm default path remains unchanged.
- Confirm `run_ui_selected_advice(...)` still does not call `build_optional_turn_pipeline_for_advice_payload(...)`.
- Do not add UI checkbox.
- Do not call Gemini.
- Do not implement full Turn Engine behavior.

Out of scope for v6.4:

- UI checkbox implementation
- `LLMAdviceWorker` option plumbing
- automatic `advisor_client.py` generation
- actual Gemini verification
- item trigger evaluation
- item consumption
- HP update
- speed/order simulation

## Relationship With Existing Contexts

TurnPipeline remains additive.

- `damage_estimate` remains the calculation source for damage numbers.
- `ko_context` remains the KO interpretation source.
- Existing item contexts remain the user-facing explanation source.
- `turn_pipeline` is a limited timing/planning/debug summary.
- `turn_pipeline` does not replace, override, or hide existing contexts.
- `turn_pipeline` does not change item availability, damage item effects, raw rolls, or payload filtering.

Prompt priority should remain:

1. Use `damage_estimate` for damage numbers.
2. Use `ko_context` for limited KO interpretation.
3. Use existing item contexts for item-specific advice.
4. Use `turn_pipeline` only for timing/stage and candidate-vs-known-modifier framing.

## UI / Prompt / Contract Guard

Any future integration must preserve v5.9 guard meaning:

- candidate events are not resolved outcomes
- `turn_pipeline` is not full simulation
- no RNG resolution
- no item consumption resolution
- no post-turn HP resolution
- no speed tie resolution
- no exact trigger result
- no exact status or volatile resolution
- no replacement of `damage_estimate`, `ko_context`, or existing item contexts

For UI wording, if a control is eventually added, it should communicate debug/planning behavior. It must not imply that a full turn simulation will run.

## Safety / Rollback Plan

Safety design:

- default off
- one explicit flag
- no automatic generation
- no actual Gemini call in tests
- no UI hard dependency
- no persisted state changes
- no payload mutation by the generation helper
- easy rollback by not passing `enable_turn_pipeline=True`

Rollback options:

- Keep `enable_turn_pipeline=False`.
- Remove the fixture/dev path without changing runtime advice.
- Keep optional `turn_pipeline` adapter available for manual/debug use.

## Safety Statement

- No production code was changed.
- No advisor-client automatic generation was added.
- No UI-selected advice flow automatic connection was added.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No speed/order simulation was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- No actual Gemini call was executed.
- No Vertex AI call was executed.
