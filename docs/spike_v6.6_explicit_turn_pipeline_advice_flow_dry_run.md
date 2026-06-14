# v6.6 Explicit TurnPipeline Advice Flow Dry-run

## Purpose

v6.6 adds a no-actual-Gemini dry-run path near the UI-selected advice flow for explicit TurnPipeline payload generation.

The goal is to verify prompt and payload differences for the default-off path and the explicit-on path without changing the normal UI button behavior.

## Completed Scope

- `run_ui_selected_advice(..., enable_turn_pipeline=False)` now accepts an explicit default-off flag.
- `_build_ui_selected_prompt(..., enable_turn_pipeline=False)` can build a limited TurnPipeline only when the flag is explicitly true.
- The default path keeps `turn_pipeline` absent.
- The explicit dry-run path builds a `simulated="limited"` `TurnPipelineResult` from the already-built advice payload.
- The generated result is passed through the existing optional top-level payload adapter.
- Prompt guard text appears only when `turn_pipeline` is present.
- Tests mock `call_gemini` and capture the prompt instead of making an actual Gemini call.

## Dry-run Paths

Default path:

```text
run_ui_selected_advice(battle_input)
-> try_build_turn_snapshot_from_battle_input(...)
-> _build_ui_selected_prompt(..., enable_turn_pipeline=False)
-> build_ui_advice_payload(..., turn_pipeline=None)
-> mocked call_gemini in tests
```

Explicit dry-run path:

```text
run_ui_selected_advice(battle_input, enable_turn_pipeline=True)
-> try_build_turn_snapshot_from_battle_input(...)
-> _build_ui_selected_prompt(..., enable_turn_pipeline=True)
-> build_ui_advice_payload(...) as base payload
-> build_optional_turn_pipeline_for_advice_payload(..., enable_turn_pipeline=True)
-> build_ui_advice_payload(..., turn_pipeline=result)
-> mocked call_gemini in tests
```

## Verified Behavior

- Default path does not include top-level `turn_pipeline`.
- Default path does not include the TurnPipeline prompt guard.
- Explicit path includes top-level `turn_pipeline`.
- Explicit path keeps `simulated="limited"`.
- Explicit path includes guard wording that candidate events are not resolved outcomes.
- Explicit path keeps `damage_estimate`, `ko_context`, and existing item contexts present.
- Event ordering remains stable for Light Ball, Quick Claw, Focus Sash, and Chilan Berry fixture contexts.

## Safety Boundaries

No UI checkbox was implemented.

`LLMAdviceWorker` still calls `run_ui_selected_advice(self._battle_input)` without enabling TurnPipeline. The user-facing advice button therefore remains default-off.

This dry-run does not:

- run actual Gemini calls
- run Vertex AI calls
- enable TurnPipeline by default
- add a UI checkbox
- implement a full Turn Engine
- evaluate item triggers
- consume items
- update HP or post-turn state
- resolve RNG, speed ties, exact trigger results, status, or volatile outcomes
- change damage formula, raw rolls, Q12 multipliers, `ko_context`, or payload filtering

## Next Candidate

Recommended next step:

```text
v6.7 TurnPipeline Advice Flow Phase Closure / Runtime Exposure Decision
```

The next step should decide whether to keep TurnPipeline behind dry-run/dev flags, design a UI exposure surface, or close this phase before any user-facing runtime option.
