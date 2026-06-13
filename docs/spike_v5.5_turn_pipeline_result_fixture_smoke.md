# v5.5 TurnPipelineResult Fixture Contract Smoke

## Purpose

v5.5 verifies that `TurnEvent` candidates can be bundled into a serializable `TurnPipelineResult` fixture/debug object before any runtime payload exposure.

## Added Helper

- `llm.advisor_turn_events.build_turn_pipeline_result_from_advice_payload(...)`

The helper accepts an advice payload or context fragment plus optional references:

- `selected_move_id`
- `input_snapshot`
- `damage_estimate_ref`
- `ko_context_ref`
- `simulated`

It uses `build_turn_events_from_advice_payload(...)` for events.

## Policy

- Default `simulated` is `limited`.
- The helper does not use `full`.
- `damage_estimate_ref` and `ko_context_ref` are references only.
- Empty payloads produce an empty event tuple and safe result.
- Source payloads are not mutated.

## Limitations

The result limitations state:

- this is not a full turn simulation
- item consumption is not simulated
- HP updates and exact post-turn state are not simulated

Warnings also note that unavailable, blocked, deferred, unknown, or malformed contexts do not create events.

## Boundaries

v5.5 does not:

- connect to `advisor_client.py`
- add `TurnPipelineResult` to the LLM payload
- implement full Turn Engine behavior
- evaluate item triggers
- consume items
- update HP
- simulate speed/order
- change damage formula, raw damage rolls, Q12 multipliers, `ko_context`, or payload filtering
- run actual Gemini or Vertex AI calls

