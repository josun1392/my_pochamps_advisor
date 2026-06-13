# v5.9 TurnPipeline Prompt Guard / Contract Documentation

## Purpose

v5.9 strengthens the prompt and contract guardrails for optional `turn_pipeline` exposure.

The goal is to keep `turn_pipeline` useful as a limited planning/debug summary while preventing the LLM from treating events as resolved battle outcomes.

No actual Gemini call was executed. No Vertex AI call was executed.

## Guard Policy

`turn_pipeline` remains:

- optional
- default-off
- explicit-only
- additive context
- not full turn simulation

It must not be interpreted as:

- resolved RNG
- resolved item consumption
- exact post-turn HP
- resolved speed tie
- exact trigger result
- exact status or volatile resolution
- replacement for `damage_estimate`
- replacement for `ko_context`
- replacement for existing item contexts

## Prompt Guard

When `turn_pipeline` is present, the prompt guard now explicitly states:

- `turn_pipeline` is a limited planning/debug summary only
- it is not full turn simulation
- do not claim RNG resolution
- do not claim item consumption
- do not claim exact post-turn HP
- do not claim guaranteed move order
- do not claim exact item trigger result
- do not claim speed tie or exact status resolution
- use events only as candidate or known-modifier context
- candidate events are not resolved outcomes
- do not replace `damage_estimate`, `ko_context`, or existing item contexts

When `turn_pipeline` is absent or `None`, this guard is not added.

## Contract Guard

`TURN_PIPELINE_KNOWN_LIMITATIONS` now records that:

- `turn_pipeline` is limited planning/debug summary only
- it does not resolve RNG, item consumption, post-turn HP, speed ties, exact trigger results, or exact status resolution
- events are candidate or known-modifier context only
- it does not replace `damage_estimate`, `ko_context`, or existing item contexts
- candidate events are not resolved outcomes and must not be described as consumed items, final HP, guaranteed order, or confirmed triggers

## Safety Boundary

v5.9 does not:

- auto-generate `TurnPipelineResult`
- connect `build_turn_pipeline_result_from_advice_payload(...)` to runtime advice flow
- run actual Gemini calls
- run Vertex AI calls
- implement full Turn Engine
- evaluate item triggers
- consume items
- update HP
- simulate speed/order
- change damage formula, raw rolls, Q12 multiplier, `ko_context`, or payload filtering

## Verification

See `docs/PROGRESS.md` for the final v5.9 test record.
