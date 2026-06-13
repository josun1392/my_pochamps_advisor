# v6.2 Explicit TurnPipeline Payload Smoke

## Purpose

v6.2 verifies the manual fixture-level path from an already-built advice payload to an optional top-level `turn_pipeline` payload section:

```text
advice payload fixture
-> build_optional_turn_pipeline_for_advice_payload(..., enable_turn_pipeline=True)
-> build_ui_advice_payload(..., turn_pipeline=result)
-> top-level turn_pipeline
```

This is a smoke/preflight check only. It does not connect TurnPipeline generation to `advisor_client.py` or the UI-selected advice flow.

## Verified Behavior

- `enable_turn_pipeline=False` or omitted returns `None`.
- Passing `None` to the optional payload adapter preserves the default payload.
- `enable_turn_pipeline=True` generates a `TurnPipelineResult`.
- The generated result uses `simulated="limited"`.
- The generated events preserve the mapper's stable order:
  - `light-ball`
  - `quick-claw`
  - `focus-sash`
  - `chilan-berry`
- Passing the generated result explicitly to `build_ui_advice_payload(..., turn_pipeline=...)` adds top-level `turn_pipeline`.
- The generated `turn_pipeline` does not replace:
  - `damage_estimate`
  - `ko_context`
  - existing item contexts
- The prompt guard is absent when `turn_pipeline` is absent.
- The prompt guard is present only when `turn_pipeline` is explicitly supplied.

## Safety Boundaries

v6.2 does not:

- auto-generate `TurnPipelineResult` inside `advisor_client.py`
- connect to the UI-selected advice flow
- call Gemini
- call Vertex AI
- implement a full Turn Engine
- evaluate item triggers
- consume items
- update HP
- simulate speed/order
- change damage formula, raw damage rolls, Q12 multiplier, `ko_context`, or payload filtering

## Verification

Fixture-level tests were added to `tests/test_advisor_payload_contract.py`.

Actual Gemini calls were not executed. Vertex AI calls were not executed.
