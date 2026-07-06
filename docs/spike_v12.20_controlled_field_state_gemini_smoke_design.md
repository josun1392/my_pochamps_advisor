# v12.20 Controlled Field State Gemini Smoke Design

## Purpose

Design a future controlled actual Gemini smoke for the user-confirmed field
state UI path without executing it.

The future smoke should verify that user-confirmed field state reaches the
actual Gemini prompt safely, remains current context only, and does not cause
the response to overclaim duration, expiration, post-turn state, exact damage,
or a full turn outcome.

This milestone is design-only. It does not call Gemini, does not call any
provider, and does not change production code, prompt guard wording,
FieldProfileDialog behavior, field mapping behavior, checkbox defaults, payload
builder flow, damage, KO, or turn-resolution behavior.

## Fixture

Controlled future fixture:

- self active:
  - species: Garchomp
  - HP percent: 100
  - item: `leftovers`
  - item source: user-confirmed
- opponent active:
  - species: Charizard
  - HP percent: 87
  - item: `choice-scarf`
  - item source: user-confirmed
- field profiles:
  - weather: `rain`
  - terrain: `electric_terrain`
  - room: `trick_room`
  - screens:
    - self: `["reflect"]`
    - opponent: `["light_screen"]`
  - hazards:
    - self: `[]`
    - opponent: `["stealth_rock"]`

Fixture boundaries:

- It is a controlled PoChamps/project test input.
- It does not infer hidden item or hidden field state.
- It does not create field state from species, common sets, or meta data.
- It does not reverse-infer field state from damage results.
- It does not imply field duration, expiration, post-turn state, exact damage,
  or full turn resolution.

## Preflight Checks

Required repo preflight before any future actual smoke:

```bash
git status --short
git branch --show-current
git status -sb
git log --oneline origin/master..master
```

Required repo state:

- branch is `master`
- remote tracking is `origin/master`
- no unpushed commit exists
- only allowed unstaged files are:
  - `config/env.example`
  - `logs/token_usage.jsonl`
- no staged `.env`, API key, access token, ADC credential, service account JSON,
  or secret file
- `docs/handoff_capsule_v1.1.md` is not staged

Recommended tests immediately before any future actual smoke:

```bash
python -m pytest tests/test_ui_turn_pipeline_flag_flow.py -q
python -m pytest tests/test_advisor_payload_contract.py -q
python -m pytest tests/test_advisor_battle_state_context.py -q
```

If PySide6, pytest, uv, or the local project environment is unavailable:

- report the test environment failure before the actual smoke
- do not run an actual Gemini call without explicit T1/T2 approval
- prefer a repair/preflight milestone before provider execution

## Provider Call Policy

Future execution policy:

- actual Gemini call allowed count: exactly 1
- retry count: 0
- second provider call: 0
- Vertex AI call: 0
- network/provider call before final T1/T2 approval: 0
- actual call execution must be a separate v12.21-or-later task with explicit
  T1/T2 approval

Any condition requiring another provider call, retry, fallback provider, or
Vertex AI call aborts the smoke.

## Payload / Prompt Expectations

The future smoke should run with the limited-context checkbox on.

Expected payload and prompt conditions:

- `battle_state_context` is present
- `battle_state_context.field.weather` is known `rain`
- `battle_state_context.field.terrain` is known `electric_terrain`
- `battle_state_context.field.room` is known `trick_room`
- screens side-specific values are preserved
- hazards side-specific values are preserved
- user-confirmed item context coexists
- `turn_pipeline`, `turn_order_context`, and `opponent_move_context` coexist if
  enabled by the same limited-context path and source data
- top-level `field_profiles` does not leak
- known field values serialize only under `battle_state_context.field`
- the existing `battle_state_context` prompt guard wording is unchanged

The pre-call prompt audit should fail if field values appear as top-level
`field_profiles` metadata or outside the gated battle-state context.

## Response Safety Expectations

The response must not claim:

- rain duration certainty
- terrain expiration certainty
- room expiration certainty
- screen expiration certainty
- hazard chip exact calculation unless explicitly computed by an approved engine
- post-turn field state certainty
- exact damage certainty
- full turn outcome certainty
- field inferred from damage
- hidden field exists
- hidden item exists

The response may say:

- user-confirmed rain, electric terrain, Trick Room, screens, and hazards are
  current context
- field state may affect strategic considerations
- exact duration, expiration, and outcome are not resolved
- advice should avoid overclaiming missing mechanics

## Token / Cost Logging Policy

Token log raw contents must not be printed.

Allowed sanitized summary:

- input tokens
- output tokens
- cached tokens
- estimated cost
- model name
- retry count
- provider call count

Forbidden reporting:

- raw `logs/token_usage.jsonl` contents
- API key or credential output
- ADC credential output
- service account JSON output
- billing details beyond sanitized estimate

`logs/token_usage.jsonl` must remain unstaged and uncommitted after the future
smoke.

## Pass Criteria

Future actual smoke passes only if all are true:

- exactly 1 actual Gemini call
- retry count 0
- no second provider call
- no Vertex AI call
- payload contains gated `battle_state_context.field`
- no top-level `field_profiles` leakage
- response acknowledges field state as current/user-confirmed context
- response avoids duration, expiration, post-turn, exact damage, and full
  outcome certainty
- response avoids damage-inferred field and hidden field/item claims
- token/cost summary is sanitized
- `logs/token_usage.jsonl` remains unstaged
- no secrets are printed or committed

## Fail / Abort Criteria

Abort before provider execution if:

- repo state is dirty beyond allowed files
- unexpected unpushed commit exists
- API key or provider setup is missing/invalid
- test environment is unresolved and T2 has not approved proceeding
- pre-call payload/prompt audit fails
- more than 1 provider call would be needed
- retry would be triggered
- second provider or Vertex AI fallback would be used
- token log raw output would be exposed
- secrets or credentials are at risk

Fail after the single allowed response if:

- response implies exact field duration
- response implies field expiration certainty
- response implies post-turn field state certainty
- response implies exact damage certainty
- response implies full turn outcome certainty
- response says field was inferred from damage
- response claims hidden field or hidden item existence
- top-level `field_profiles` leakage is found

## Non-Goals

v12.20 does not implement or execute:

- actual Gemini call
- Gemini retry
- second provider call
- Vertex AI call
- production code changes
- FieldProfileDialog behavior changes
- field mapping behavior changes
- prompt guard wording changes
- checkbox default changes
- payload builder call-flow changes
- full Turn Engine behavior
- field duration/expiration tracking
- post-turn field updates
- damage engine consumption of known field
- `damage_estimate` or `ko_context` changes

## No Actual Gemini Call

No actual Gemini call, network/provider call, retry, second provider call,
Vertex AI call, or token-log output is part of v12.20.

## Next Recommendation

Recommended next milestone depends on preflight environment status:

- v12.21 Controlled Field State Gemini Smoke, if repo and test environment
  preflight are clean and T1/T2 explicitly approve exactly one actual Gemini
  call
- v12.21 Field State Actual Smoke Preflight Repair, if PySide6, pytest, uv, or
  local environment issues block the required preflight tests

Safe alternative:

- v12.21 Item Activation/Consumption Boundary Design
