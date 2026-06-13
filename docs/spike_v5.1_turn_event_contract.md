# v5.1 Turn Event Contract

## Purpose

v5.1 implements the first Minimal Turn Engine contract layer from the v5.0 design.

This milestone adds serializable dataclasses for turn-stage event candidates and planning results. It does not implement turn simulation, trigger evaluation, item consumption, HP updates, speed/order simulation, or LLM payload integration.

No actual Gemini call or Vertex AI call was run.

## Module Choice

The contract lives in:

```text
core/turn_event.py
```

Reason:

- v5.1 defines event/result data contracts only.
- It does not build or execute a turn pipeline.
- Keeping the contract in `core.turn_event` mirrors `core.turn_state` and avoids implying that a working engine exists.
- A later `core.turn_pipeline` module can be added when fixture-level planning or pipeline orchestration is implemented.

## Added Contracts

### TurnEvent

`TurnEvent` represents a turn-stage item/context event. It can describe:

- `candidate`
- `known_modifier`
- `not_simulated`
- `blocked`
- `unavailable`

Allowed stages:

- `pre_turn`
- `pre_move`
- `damage`
- `on_damage_before_ko`
- `on_hit_or_damage_dealt`
- `post_damage`
- `post_turn`

Allowed certainty values:

- `known`
- `likely`
- `possible`
- `unknown`
- `not_simulated`

Allowed side values:

- `player`
- `opponent`
- `field`
- `unknown`
- `None`

### TurnPipelineResult

`TurnPipelineResult` groups event candidates and optional references to existing primitives:

- `input_snapshot`
- `selected_move_id`
- `damage_estimate_ref`
- `ko_context_ref`
- `events`
- `warnings`
- `limitations`
- `simulated`

`simulated` defaults to `none`. The `full` value is schema-reserved for future compatibility only; v5.1 does not produce full simulation.

## Serialization and Normalization

Both contracts provide:

- `to_dict()`
- `from_dict(...)`

Helpers:

- `normalize_turn_event(...)`
- `normalize_turn_pipeline_result(...)`

Lists for limitations, warnings, and events are normalized to tuples inside the dataclasses.

## Explicit Non-goals

v5.1 does not:

- connect to `advisor_client.py`
- insert turn pipeline output into the LLM payload
- evaluate item triggers
- consume items
- mutate HP
- update post-turn state
- simulate speed order
- resolve exact RNG, status, or volatile conditions
- change damage formula, raw damage rolls, Q12 multipliers, `ko_context`, item contexts, or payload filtering

## Next Step

Recommended next milestone:

```text
v5.2 Turn Pipeline Planning Design
```

That should design how fixture-level planning would map existing primitives and item contexts into `TurnEvent` candidates without connecting to advisor payloads or mutating battle state.
