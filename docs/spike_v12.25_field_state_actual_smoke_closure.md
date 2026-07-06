# v12.25 Field State Actual Smoke Closure

## Purpose

Close the field-state actual smoke phase after the v12.24 controlled actual
Gemini smoke passed.

This closure records the design, environment repair, setup execution, one-call
actual provider smoke, payload/prompt boundary, response safety boundary, and
remaining limitations for user-confirmed field state.

No additional actual Gemini call was made for this closure.

## Phase Scope

Closed phase:

```text
v12.20 Controlled Field State Gemini Smoke Design
-> v12.21 Field State Actual Smoke Preflight Repair
-> v12.22 Python Environment Setup Guide
-> v12.23 Environment Setup Execution
-> v12.24 Controlled Field State Gemini Smoke
-> v12.25 Field State Actual Smoke Closure
```

Scope:

- verify the user-confirmed field-state UI path against an actual Gemini
  response once
- preserve the existing limited-context checkbox gate
- confirm no top-level `field_profiles` leakage
- confirm known field values remain current context only
- confirm response avoids duration, expiration, post-turn, exact damage, full
  outcome, hidden-field, and damage-inferred-field claims
- keep logs and secrets out of committed artifacts

## Completed Milestones

v12.20 Controlled Field State Gemini Smoke Design:

- designed a future controlled smoke without executing a provider call
- selected the Garchomp/Charizard fixture with user-confirmed items and field
  profiles
- set the provider policy: exactly 1 actual Gemini call, retry 0, second
  provider 0, Vertex AI 0
- defined payload/prompt expectations, response safety checks, token/cost
  logging policy, pass criteria, and fail/abort criteria

v12.21 Field State Actual Smoke Preflight Repair:

- diagnosed the environment mismatch
- found bare `python` was Anaconda Python 3.13.5
- found `uv` missing from PATH
- found PySide6 missing outside the uv-managed environment
- confirmed repo dependencies were already declared/locked
- documented that current shell was not actual-smoke ready

v12.22 Python Environment Setup Guide:

- documented Windows setup for `uv`, `uv sync --dev`, targeted tests, and full
  pytest
- documented troubleshooting for missing `uv`, PySide6, pytest, wrong Python,
  Anaconda PATH priority, missing/broken `.venv`, and PATH refresh issues
- did not install dependencies or call providers

v12.23 Environment Setup Execution:

- installed/restored `uv 0.11.26`
- ran `uv sync --dev`
- restored repo-local `.venv`
- verified Python 3.11.9, pytest 9.0.3, and PySide6 6.11.0
- passed the targeted field-state preflight suite
- passed full pytest: `1397 passed, 2 deselected`
- left production code and dependency files unchanged

v12.24 Controlled Field State Gemini Smoke:

- ran the approved controlled actual smoke
- executed exactly one actual Gemini call
- passed payload/prompt safety
- passed response safety
- reported only sanitized token/cost summary
- left `logs/token_usage.jsonl` unstaged and uncommitted

## Environment Readiness Summary

Final environment status:

- runner: `uv run pytest`
- Python: 3.11.9 in repo-local `.venv`
- pytest: 9.0.3
- PySide6: 6.11.0
- targeted preflight tests: PASS
- full pytest: `1397 passed, 2 deselected`
- dependency files changed: no
- production code changed: no

## Controlled Smoke Fixture

Self:

- species: `Garchomp`
- HP percent: `100`
- item: `leftovers`
- item source: user-confirmed

Opponent:

- species: `Charizard`
- HP percent: `87`
- item: `choice-scarf`
- item source: user-confirmed

Field profiles:

- weather: `rain`
- terrain: `electric_terrain`
- room: `trick_room`
- screens:
  - self: `["reflect"]`
  - opponent: `["light_screen"]`
- hazards:
  - self: `[]`
  - opponent: `["stealth_rock"]`

Fixture boundary:

- no hidden item/field inference
- no species/common/meta field generation
- no damage reverse inference
- known field remains user-confirmed current context only

## Provider Call Policy Result

Result: `PASS`.

- actual Gemini call count: `1`
- retry count: `0`
- second provider call count: `0`
- Vertex AI call count: `0`
- model: `gemini-2.5-flash`

The v12.24 harness wrapped `call_gemini(...)` and would have failed if a second
provider call was attempted.

## Payload / Prompt Safety Result

Result: `PASS`.

Payload/prompt closure:

- limited-context checkbox path was on
- `battle_state_context` was present
- `battle_state_context.field.weather` contained known `rain`
- `battle_state_context.field.terrain` contained known `electric_terrain`
- `battle_state_context.field.room` contained known `trick_room`
- screens side-specific values were preserved
- hazards side-specific values were preserved
- user-confirmed item context coexisted
- `turn_pipeline`, `turn_order_context`, and `opponent_move_context` coexisted
- top-level `field_profiles` leakage was absent
- known field values serialized only under gated `battle_state_context.field`
- prompt guard wording was unchanged

Forbidden payload/prompt fields remained absent:

- `duration_turns`
- `expiration`
- `post_turn`
- `damage_precision`
- `resolved_outcome`
- `full_turn_result`

## Response Safety Result

Result: `PASS`.

Forbidden categories matched: none.

The sanitized response scan found no:

- rain duration certainty
- terrain expiration certainty
- room expiration certainty
- screen expiration certainty
- hazard chip exact calculation
- post-turn field state certainty
- exact damage certainty
- full turn outcome certainty
- field inferred from damage
- hidden field exists claim
- hidden item exists claim

Allowed response range:

- user-confirmed field state may be treated as current context
- field state may affect strategic considerations
- duration, expiration, and outcome remain unresolved

The raw response text was not committed or pasted into the closure.

## Sanitized Token / Cost Summary

Sanitized v12.24 summary:

- model: `gemini-2.5-flash`
- input tokens: `11879`
- output tokens: `172`
- cached tokens: `0`
- estimated cost: `$0.0`
- pricing status: `free_tier_zero_cost`
- provider call count: `1`
- retry count: `0`

Raw token log contents were not printed.

## logs/token_usage.jsonl Handling

- `logs/token_usage.jsonl` was modified by the v12.24 actual smoke logging.
- `logs/token_usage.jsonl` remains unstaged.
- `logs/token_usage.jsonl` was not committed.
- `logs/token_usage.jsonl` was not reset.

## Safety Boundary

Closed safety boundary:

- known field is user-confirmed current context only
- known field does not imply duration
- known field does not imply expiration
- known field does not imply post-turn outcome
- known field does not imply damage precision
- known field does not imply full turn outcome
- unknown remains unknown
- `none` means user-confirmed absence only
- no field source from damage reverse inference
- no field source from species/common/meta
- no field source from item inferred effects
- no field source from LLM/model guess
- no hidden field guessing
- no hidden item guessing
- no full Turn Engine
- no `damage_estimate` behavior change
- no `ko_context` behavior change

## Remaining Limitations

Known remaining limitations:

- no field duration tracking
- no field expiration tracking
- no post-turn field state update
- no battle log/parser field source
- no imported replay field source
- no damage engine consumption of known field
- no exact hazard chip damage implementation
- no full turn simulation
- no item activation/consumption implementation
- no status/condition source design yet
- no opponent hidden set/moveset inference

## Non-Goals

This closure did not:

- run another actual Gemini call
- call a provider or network service
- retry Gemini
- call a second provider
- call Vertex AI
- change production code
- change dependency files
- change `pyproject.toml`
- change `uv.lock`
- change requirements files
- change FieldProfileDialog behavior
- change field mapping behavior
- change prompt guard wording
- add a limited-context checkbox
- change UI checkbox defaults
- change payload builder call flow
- implement a full Turn Engine
- calculate post-turn HP
- implement item activation/consumption
- implement RNG, speed tie, or Quick Claw resolution
- infer hidden item/field, EV/IV/nature, weather, terrain, boosts, status,
  hazards, screens, room, opponent set, hidden moveset, or selected opponent
  move
- change damage formula, raw damage rolls, Q12 multiplier, `ko_context`,
  `damage_estimate`, or payload filtering

## Final Phase Status

Field State Actual Smoke phase status: `CLOSED - PASS`.

The field-state UI path is now:

- designed
- contract-tested
- helper-normalized
- UI-integrated
- checkbox-gated
- copy-updated
- offline-smoke verified
- environment-preflight repaired
- actual Gemini-smoke verified
- closed as PASS

## Next Recommendation

Recommended next:

- v12.26 Item Activation/Consumption Boundary Design

Reason:

- field state actual validation is closed as PASS
- the next likely ambiguity is whether known user-confirmed items should imply
  activation, consumption, post-turn behavior, or resolved outcomes
- that boundary should be designed before implementation
