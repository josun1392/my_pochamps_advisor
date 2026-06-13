# v6.0 Minimal TurnPipeline Integration Design

## Purpose

v6.0 designs the smallest safe path for integrating `TurnPipelineResult` into the advice flow after the v5.x foundation work.

This is design-only. No production code was changed. No actual Gemini call was executed. No Vertex AI call was executed.

## v5.x Completed State

Implemented foundation:

- v5.3: `build_turn_events_from_advice_payload(...)` maps selected item contexts to `TurnEvent` candidates.
- v5.4: mapper fixture coverage verifies positive cases, negative cases, stable ordering, and safe wording.
- v5.5: `build_turn_pipeline_result_from_advice_payload(...)` bundles events into `TurnPipelineResult`.
- v5.6: `scripts/spike_turn_pipeline_debug.py` and `docs/debug_turn_pipeline_sample_v5.6.md` provide local dry-run inspection.
- v5.7: payload exposure design recommends optional top-level `turn_pipeline`.
- v5.8: optional top-level `turn_pipeline` adapter is implemented.
- v5.9: prompt/contract guards state that candidate events are not resolved outcomes.

Current behavior:

- `turn_pipeline` is default-off and explicit-only.
- `build_ui_advice_payload(..., turn_pipeline=None)` preserves existing payload behavior.
- `simulated="full"` is rejected for advice payload exposure.
- `run_ui_selected_advice(...)` does not auto-generate `TurnPipelineResult`.
- UI-selected advice flow does not automatically include `turn_pipeline`.
- Full Turn Engine, item trigger evaluation, item consumption, HP update, speed/order simulation, RNG resolution, and exact trigger resolution are not implemented.

## Current UI-Selected Advice Flow

Current runtime path:

```text
LLMAdvicePanel.advice_requested
-> MainWindow._start_llm_advice()
-> MainWindow._build_llm_battle_input()
-> attach_selected_move_damage_estimate(...)
-> attach_opponent_known_move_damage_estimates(...)
-> LLMAdviceWorker.run()
-> run_ui_selected_advice(battle_input)
-> try_build_turn_snapshot_from_battle_input(battle_input)
-> _build_ui_selected_prompt(battle_input, turn_snapshot=...)
-> build_ui_advice_payload(..., turn_snapshot=..., turn_pipeline=None)
-> call_gemini(prompt, model)
```

Existing integration point:

- `build_ui_advice_payload(...)` can already accept explicit `turn_pipeline`.

Not integrated:

- `run_ui_selected_advice(...)` does not call `build_turn_pipeline_result_from_advice_payload(...)`.
- `MainWindow` does not pass a pipeline flag.
- `LLMAdvicePanel` does not expose a debug/pipeline toggle.

## Integration Candidates

| Candidate | Description | Pros | Cons | Recommendation |
|---|---|---|---|---|
| A. advisor_client automatic generation | `run_ui_selected_advice(...)` automatically builds a pipeline and includes it. | Simple for users; no UI changes. | Too easy for LLM to over-trust pipeline; changes default advice payload; harder rollback; conflates debug planning with runtime advice. | Not recommended for v6.1. |
| B. explicit flag at payload builder/advice boundary | Add a helper or optional flag such as `enable_turn_pipeline=False`; generate only when true. | Preserves default behavior; easy rollback; allows tests and controlled local dry-runs; aligns with v5.8 default-off adapter. | Requires explicit call path and tests; still needs careful prompt guard. | Recommended v6.1 MVP. |
| C. debug script / dry-run only | Keep v5.6 style local report as the only integration. | Safest; no runtime payload risk. | Does not validate controlled prompt/payload integration; delays migration. | Safe fallback, but less useful after v5.8. |
| D. tests/fixture only until later | Keep helper tests only and defer all runtime-adjacent integration. | Very low risk. | Duplicates v5.5-v5.6 status; no new integration learning. | Too conservative for v6.1 unless risk posture changes. |

## Recommended v6.1 MVP

Recommended next step:

```text
v6.1 Explicit TurnPipeline Generation Adapter
```

Proposed helper:

```text
build_optional_turn_pipeline_for_advice_payload(
    advice_payload: Mapping[str, Any],
    *,
    enable_turn_pipeline: bool = False,
    selected_move_id: str | None = None,
    input_snapshot: Mapping[str, Any] | None = None,
    damage_estimate_ref: str | None = None,
    ko_context_ref: str | None = None,
) -> TurnPipelineResult | None
```

Policy:

- Default is `enable_turn_pipeline=False`.
- When false, return `None`.
- When true, build a limited `TurnPipelineResult` from the already-built advice payload.
- Generated result must use `simulated="limited"`.
- `simulated="full"` remains rejected by the payload adapter.
- The helper returns a pipeline result; it does not mutate the payload.
- The caller may pass the result to `build_ui_advice_payload(..., turn_pipeline=...)`.

Suggested v6.1 test shape:

- helper returns `None` by default
- helper returns `TurnPipelineResult` only when explicitly enabled
- result events match existing mapper output
- result is `simulated="limited"`
- result limitations preserve not-full-simulation wording
- `build_ui_advice_payload(..., turn_pipeline=result)` adds top-level `turn_pipeline`
- omitted/disabled helper path preserves existing payload
- no actual Gemini call
- no UI button or runtime advice default behavior change

Out of scope for v6.1:

- automatic `run_ui_selected_advice(...)` generation
- UI toggle
- actual Gemini call
- full Turn Engine
- item consumption
- HP update
- speed tie resolution
- RNG resolution
- exact trigger resolution
- damage formula, raw roll, Q12, `ko_context`, or payload filtering changes

## Relationship With Existing Contexts

`turn_pipeline` is additive.

Rules:

- `damage_estimate` remains the primitive calculation source for damage ranges, item-effect application, and raw rolls.
- `ko_context` remains the primitive KO interpretation source for limited damage-roll context.
- Existing item contexts remain the current user-facing item explanation surfaces.
- `turn_pipeline` is a timing/planning/debug summary over existing context.
- `turn_pipeline` must not override item context availability.
- `turn_pipeline` must not change payload filtering.
- `turn_pipeline` must not transform candidate events into confirmed outcomes.

Recommended prompt priority remains:

1. Use `damage_estimate` for numeric damage statements.
2. Use `ko_context` for limited KO interpretation.
3. Use existing item contexts for current item explanation.
4. Use `turn_pipeline` only to organize timing/stage and candidate-vs-known-modifier framing.

## Prompt / Contract Guard

v5.9 guardrails must remain active for any v6.1 integration.

Required meaning:

- candidate events are not resolved outcomes
- `turn_pipeline` is not full simulation
- no RNG resolution
- no item consumption resolution
- no post-turn HP resolution
- no speed tie resolution
- no exact trigger resolution
- no exact status or volatile resolution
- no replacement of `damage_estimate`, `ko_context`, or existing item contexts

Any v6.1 helper should rely on the v5.8/v5.9 adapter and prompt guard rather than adding a second, conflicting prompt surface.

## Rollback / Safety Plan

Design for easy rollback:

- Keep default off.
- Add one small helper.
- Do not mutate payloads in the helper.
- Do not change `run_ui_selected_advice(...)` default behavior.
- Do not add a UI hard dependency.
- Use fixture-level tests.
- Keep actual Gemini calls disabled.
- Keep `simulated="limited"` only.
- Preserve v5.8 behavior: passing `turn_pipeline=None` produces unchanged payload.

Rollback path:

- Stop passing `enable_turn_pipeline=True`.
- Or remove the v6.1 helper without changing existing payload builder behavior.
- Since no state mutation is performed, no persisted battle-state migration is required.

## Safety Statement

- No production code was changed.
- No advisor-client automatic generation was added.
- No UI-selected advice flow automatic connection was added.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No speed/order simulation was implemented.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- No actual Gemini call was executed.
- No Vertex AI call was executed.
