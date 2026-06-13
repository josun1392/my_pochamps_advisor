# v6.4 Explicit TurnPipeline Advice Payload Builder Smoke

## Purpose

v6.4 strengthens fixture-level smoke coverage for the explicit TurnPipeline helper plus the advice payload builder path.

This does not connect TurnPipeline to `advisor_client.py` or the UI-selected advice flow. It does not call Gemini or Vertex AI.

## Smoke Path

Verified fixture path:

```text
already-built advice payload
-> build_optional_turn_pipeline_for_advice_payload(..., enable_turn_pipeline=False)
-> None
-> build_ui_advice_payload(..., turn_pipeline=None)
-> unchanged payload
```

and:

```text
already-built advice payload
-> build_optional_turn_pipeline_for_advice_payload(..., enable_turn_pipeline=True)
-> limited TurnPipelineResult
-> build_ui_advice_payload(..., turn_pipeline=result)
-> top-level turn_pipeline
```

## Verified Behavior

- omitted/default flag returns `None`
- explicit `enable_turn_pipeline=False` returns `None`
- default/disabled payload output remains unchanged
- explicit `enable_turn_pipeline=True` produces `simulated="limited"`
- generated events preserve stable mapper order
- manual adapter insertion adds top-level `turn_pipeline`
- prompt guard is absent when `turn_pipeline` is absent
- prompt guard is present when `turn_pipeline` is supplied
- prompt guard says candidate events are not resolved outcomes
- prompt guard includes no RNG, item consumption, and post-turn HP resolution wording
- `damage_estimate` remains present and unchanged
- `ko_context` remains present and unchanged
- existing item contexts remain present and unchanged
- `run_ui_selected_advice(...)` does not call `build_optional_turn_pipeline_for_advice_payload(...)`

## Safety Boundaries

v6.4 does not:

- auto-generate `TurnPipelineResult` inside `advisor_client.py`
- connect TurnPipeline generation to the UI-selected advice flow
- call Gemini
- call Vertex AI
- implement a full Turn Engine
- evaluate item triggers
- consume items
- update HP
- simulate speed/order
- change damage formula, raw damage rolls, Q12 multiplier, `ko_context`, or payload filtering

Actual Gemini calls were not executed. Vertex AI calls were not executed.
