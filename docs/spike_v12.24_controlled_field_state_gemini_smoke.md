# v12.24 Controlled Field State Gemini Smoke

## Purpose

Execute the v12.20 controlled field-state actual Gemini smoke once after T1/T2
approval and verify that user-confirmed field state reaches the actual provider
prompt safely.

This smoke verifies response safety only. It is not advice-quality validation,
field duration tracking, field expiration tracking, post-turn state resolution,
exact damage validation, full turn simulation, damage-engine validation, or
hidden state inference validation.

## Fixture Summary

Self:

- species: `Garchomp`
- HP percent: `100`
- item: `leftovers`
- item metadata: `status=user_confirmed`, `source=user_input`

Opponent:

- species: `Charizard`
- HP percent: `87`
- item: `choice-scarf`
- item metadata: `status=user_confirmed`, `source=user_input`

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

UI state:

- limited-context checkbox path: ON
- enabled optional contexts:
  - `turn_pipeline`
  - `turn_order_context`
  - `opponent_move_context`
  - `battle_state_context`

Fixture boundaries:

- no hidden item or hidden field inference
- no species/common/meta-based field generation
- no damage-reverse field inference
- known field means user-confirmed current context only

## Preflight Repo State

Preflight repo state passed:

- branch: `master`
- remote tracking: `origin/master`
- pushed baseline: `9ca45d1 docs(spike): record environment setup execution`
- unpushed commits before smoke: none
- allowed existing unstaged files only:
  - `config/env.example`
  - `logs/token_usage.jsonl`
- no staged files
- no `.env`, API key, access token, ADC credential, service account JSON, or
  secret file staged
- `docs/handoff_capsule_v1.1.md` was not staged

## Preflight Test Results

Targeted tests passed:

- `uv run pytest tests/test_field_profile_button_integration_contract.py -q`
  - `8 passed`
- `uv run pytest tests/test_field_profile_dialog.py -q`
  - `7 passed`
- `uv run pytest tests/test_ui_turn_pipeline_flag_flow.py -q`
  - `19 passed`
- `uv run pytest tests/test_advisor_battle_state_context.py -q`
  - `39 passed`
- `uv run pytest tests/test_advisor_payload_contract.py -q`
  - `366 passed`

Full pytest passed:

- `uv run pytest -q`
  - `1397 passed, 2 deselected`

## Payload / Prompt Safety Result

Result: `PASS`.

Pre-call payload/prompt audit passed before the provider call:

- limited-context path enabled
- `battle_state_context` present
- `battle_state_context.field.weather` known `rain`
- `battle_state_context.field.terrain` known `electric_terrain`
- `battle_state_context.field.room` known `trick_room`
- side-specific screens preserved
- side-specific hazards preserved
- user-confirmed item context coexists
- `turn_pipeline`, `turn_order_context`, and `opponent_move_context` coexist
- top-level `field_profiles` does not leak into the prompt payload
- known field values serialize only through gated `battle_state_context.field`
- existing battle-state prompt guard is present
- prompt guard wording was not changed

Forbidden payload/prompt fields were absent:

- `duration_turns`
- `expiration`
- `post_turn`
- `damage_precision`
- `resolved_outcome`
- `full_turn_result`

## Actual Provider Call Count

Actual call result:

- actual Gemini call count: `1`
- retry count: `0`
- second provider call count: `0`
- Vertex AI call count: `0`
- model: `gemini-2.5-flash`

The harness wrapped `call_gemini(...)` and would have failed immediately if a
second provider call was attempted. No retry was made.

## Response Safety Result

Result: `PASS`.

Sanitized response scan:

- response character count: `723`
- field/current-context anchor present: `yes`
- forbidden response categories matched: `none`

The response text was not pasted into this document.

The response did not claim:

- rain duration certainty
- terrain expiration certainty
- room expiration certainty
- screen expiration certainty
- exact hazard chip calculation
- post-turn field state certainty
- exact damage certainty
- full turn outcome certainty
- field inferred from damage
- hidden field exists
- hidden item exists

## Sanitized Token / Cost Summary

Sanitized token/cost summary:

- model: `gemini-2.5-flash`
- provider call count: `1`
- retry count: `0`
- input tokens: `11879`
- output tokens: `172`
- cached tokens: `0`
- pricing status: `free_tier_zero_cost`
- estimated cost USD: `0.0`

Raw `logs/token_usage.jsonl` contents were not printed.

## logs/token_usage.jsonl Handling

- `logs/token_usage.jsonl` was modified by normal token logging.
- `logs/token_usage.jsonl` remains unstaged.
- `logs/token_usage.jsonl` was not committed.
- `logs/token_usage.jsonl` was not reset.

## Pass / Fail Result

Result: `PASS`.

PASS basis:

- targeted tests passed
- full pytest passed
- exactly one actual Gemini call
- retry count 0
- no second provider call
- no Vertex AI call
- payload contained gated `battle_state_context.field`
- no top-level `field_profiles` leakage
- response acknowledged field/current-context anchors
- response avoided duration, expiration, post-turn state, exact damage, full
  outcome, damage-inferred field, hidden field, and hidden item claims
- token/cost summary stayed sanitized
- raw token log contents were not printed
- no secrets were printed or committed

## Non-Goals

This smoke did not:

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
- implement full Turn Engine behavior
- resolve turn order
- calculate post-turn HP
- implement item activation or consumption
- resolve RNG, speed ties, or Quick Claw activation
- infer hidden item or field state
- infer EV/IV/nature
- infer weather, terrain, boosts, status, hazards, screens, or room
- reverse-infer from damage
- change damage formula, raw damage rolls, Q12 multiplier, `ko_context`,
  `damage_estimate`, or payload filtering

## Next Recommendation

Recommended next:

- v12.25 Field State Actual Smoke Closure

Reason:

- the controlled actual smoke passed
- the one-call/no-retry audit trail is complete
- field-state actual validation should be closed before starting a new feature
  boundary
