# v5.8 Optional TurnPipeline Payload Adapter

## Purpose

v5.8 adds an explicit-only payload adapter for `TurnPipelineResult`.

The adapter lets tests or future controlled callers pass a prebuilt pipeline result into the advice payload as top-level `turn_pipeline`. It does not generate the pipeline automatically and does not connect the mapper/debug helper to the runtime UI advice flow.

No actual Gemini call was executed. No Vertex AI call was executed.

## Implemented

- `build_ui_advice_payload(..., turn_pipeline=None)` accepts an optional `TurnPipelineResult` or mapping.
- When `turn_pipeline` is absent or `None`, the default advice payload remains unchanged.
- When `turn_pipeline` is explicitly supplied, the payload gains top-level `turn_pipeline`.
- Supplied pipeline values are normalized through `normalize_turn_pipeline_result(...)`.
- `simulated="full"` is rejected for advice payload exposure.
- Pipeline limitations are required.
- Event wording is checked for narrow forbidden resolved-result claims.
- Scenario `known_limitations` gains TurnPipeline guardrails only when `turn_pipeline` is present.
- `_build_ui_selected_prompt(..., turn_pipeline=...)` includes a concise guard only when `turn_pipeline` is present.

## Default-Off Policy

The adapter is explicit-only:

- `run_ui_selected_advice(...)` does not call `build_turn_pipeline_result_from_advice_payload(...)`.
- UI-selected advice does not auto-generate `TurnPipelineResult`.
- The mapper remains a fixture/debug/planning helper.
- Existing payloads without a supplied pipeline remain unchanged.

## Payload Shape

Future controlled callers may provide:

```json
{
  "turn_pipeline": {
    "input_snapshot": null,
    "selected_move_id": "flamethrower",
    "damage_estimate_ref": "moves.my_selected_move.damage_estimate",
    "ko_context_ref": "moves.my_selected_move.ko_context",
    "events": [],
    "warnings": [],
    "limitations": [
      "This result is a limited planning summary, not a full turn simulation."
    ],
    "simulated": "limited"
  }
}
```

This field is additive. It does not replace:

- `damage_estimate`
- `ko_context`
- existing item contexts
- item profile status
- payload filtering

## Limitations

When present, `turn_pipeline` means:

- limited planning/debug summary
- not full turn simulation
- no RNG resolution
- no item consumption
- no post-turn HP
- no guaranteed move order
- no exact trigger result
- no exact status resolution

The prompt guard tells the advisor to use events only as candidate or known-modifier context.

## Not Implemented

- automatic advisor-client generation
- LLM payload insertion by default
- full Turn Engine
- item trigger evaluation
- item consumption
- HP update
- speed/order simulation
- damage formula changes
- raw roll changes
- Q12 multiplier changes
- `ko_context` changes
- payload filtering changes

## Verification

See `docs/PROGRESS.md` for the final v5.8 test record.
