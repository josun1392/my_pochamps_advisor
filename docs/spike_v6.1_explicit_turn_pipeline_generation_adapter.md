# v6.1 Explicit TurnPipeline Generation Adapter

## Purpose

v6.1 adds a narrow helper for generating a limited `TurnPipelineResult` from an already-built advisor payload only when a caller explicitly opts in. This is the first integration-adjacent step after the v6.0 design, but it is still default-off and is not connected to the runtime advice flow.

## Added Helper

`llm.advisor_turn_events.build_optional_turn_pipeline_for_advice_payload(...)`

Policy:

- `enable_turn_pipeline=False` returns `None`.
- Omitting `enable_turn_pipeline` returns `None`.
- `enable_turn_pipeline=True` calls `build_turn_pipeline_result_from_advice_payload(...)`.
- The generated result uses `simulated="limited"`.
- The helper does not expose a `simulated` parameter and never creates `simulated="full"`.
- The input payload is not mutated.
- The returned result can be passed manually to `build_ui_advice_payload(..., turn_pipeline=...)`.

## Explicit-Only Adapter Relationship

The helper does not insert anything into the payload by itself. The existing v5.8 optional top-level `turn_pipeline` adapter remains the only insertion path:

```text
pipeline = build_optional_turn_pipeline_for_advice_payload(
    payload,
    enable_turn_pipeline=True,
)
advice_payload = build_ui_advice_payload(payload, turn_pipeline=pipeline)
```

If `pipeline` is `None`, callers should omit `turn_pipeline` or pass `None`, preserving existing payload output.

## Safety Boundaries

v6.1 does not:

- connect to `advisor_client.py`
- connect to the UI-selected advice flow
- call Gemini
- call Vertex AI
- implement a full Turn Engine
- evaluate item triggers
- consume items
- update HP
- simulate speed/order or RNG
- change damage formula, raw damage rolls, Q12 multiplier, `ko_context`, or payload filtering

The helper is a fixture/planning adapter only. Candidate events remain candidate events, not resolved outcomes.

## Verification

Fixture tests cover:

- disabled and omitted flag return `None`
- enabled flag returns `TurnPipelineResult`
- generated result is `simulated="limited"`
- payload mutation does not occur
- event ordering follows the existing mapper order
- limitations state that this is not a full simulation and does not simulate item consumption or HP updates
- empty payload produces a safe limited result
- result can be passed manually to the optional payload adapter
- helper source does not call `advisor_client`, `run_ui_selected_advice`, or Gemini

Actual Gemini calls were not executed. Vertex AI calls were not executed.
