# v11.0 Controlled Battle State UI Gemini Smoke Design

## Purpose

Design a controlled future Gemini smoke for the UI-selected `battle_state_context`
path without executing the call in v11.0.

The future smoke should verify that, when the existing limited-context checkbox
is on, Gemini treats `battle_state_context` as visible/current species and HP
snapshot context only. It must not infer hidden state or treat the context as a
resolved turn simulation.

This design step does not execute an actual Gemini call, Gemini retry, Vertex AI
call, provider call, or network call.

## Smoke Purpose

The controlled smoke is limited to verifying that Gemini:

- sees `battle_state_context` in the UI-selected prompt when the limited-context checkbox is on
- uses only visible/current species and HP as known battle-state facts
- keeps status, boosts, item, field state, and known conditions unknown when not explicitly provided
- does not reverse-engineer hidden state from `damage_estimate` or `ko_context`
- does not treat `battle_state_context` as a resolved turn simulation

The smoke is not intended to evaluate:

- battle advice quality
- win probability
- full Turn Engine behavior
- damage formula correctness
- item consumption
- Quick Claw activation
- opponent selected move inference

## Prerequisite Checks

Before any future actual call, verify:

- repo is clean except the allowed existing unstaged `config/env.example`
- branch is `master`
- remote tracking is `origin/master`
- latest v10.12 commit is pushed
- no unexpected ahead commits
- targeted and full pytest evidence is green
- `GEMINI_API_KEY` is available without printing its value
- intended Gemini model is available or default model is known without printing secrets
- T1 has approved exactly one actual call for the v11.1 controlled smoke

Do not print API key values, credentials, billing details, or raw token-log lines.

## T1 Approval Requirement

Actual Gemini call execution is allowed only if T1 approves the v11.0 design and
then provides a separate v11.1 controlled smoke execution prompt.

v11.0 must not execute the call.

## Smoke Fixture

Recommended fixture:

Self:

- species: `Garchomp`
- HP percent: `100`
- selected move: `Earthquake` or `Dragon Claw`, following the repo's existing UI-selected fixture style

Opponent:

- species: `Charizard`
- HP percent: `100`
- visible opponent moves: use the existing opponent-move UI fixture style with 1 to 4 visible moves

Checkbox:

```text
limited context checkbox: ON
```

Expected `battle_state_context`:

```text
self_active.species: visible_ui Garchomp
self_active.current_hp_percent: visible_ui 100
self_active.status: unknown
self_active.boosts: unknown
self_active.item: unknown

opponent_active.species: visible_ui Charizard
opponent_active.current_hp_percent: visible_ui 100
opponent_active.status: unknown
opponent_active.boosts: unknown
opponent_active.item: unknown

field.weather: unknown
field.terrain: unknown
field.screens: unknown
field.hazards: unknown
field.room: unknown
known_conditions: []
```

## Exact Call Limit

The future v11.1 smoke is limited to:

- maximum actual Gemini calls: `1`
- retries: `0`
- no retry on failure
- no second call for clarification
- no second call for a better answer
- no automatic rerun
- no Vertex AI call unless a later design explicitly changes the intended provider path

## Retry Policy

Retries are forbidden.

If the first call fails due to auth, quota, billing, routing, timeout, network,
or unexpected provider error, stop and report a sanitized failure class only.

## Abort Criteria

Abort before the actual call if any condition is true:

- repo has unexpected staged files
- repo has unexpected unstaged files other than `config/env.example`
- ahead commits are unexpected
- required tests are not green
- API key is unavailable
- model is unavailable
- prompt payload is missing `battle_state_context`
- `battle_state_context` is missing species/HP `visible_ui` sources
- `battle_state_context` contains hidden item, EV/IV/nature, inferred status, inferred boosts, or inferred field state
- prompt is missing the `battle_state_context` guard
- prompt guard does not forbid hidden inference, reverse inference, and resolved simulation
- provider setup indicates Vertex AI instead of the intended Gemini path, unless explicitly intended
- T1 has not approved the actual call

## Expected Payload Boundary

The pre-call payload must include:

- `battle_state_context`
- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`
- self species and HP percent as `visible_ui`
- opponent species and HP percent as `visible_ui`
- status, boosts, and item as unknown
- field state as unknown
- `known_conditions == []`

The payload must not include:

- hidden item
- EV/IV/nature
- inferred field/status/boosts
- post-turn HP
- item consumption
- RNG resolution
- speed tie resolution
- Quick Claw activation resolution
- full turn outcome

## Expected Prompt Boundary

The pre-call prompt must include:

- serialized `battle_state_context`
- `battle_state_context` prompt guard
- unknown fields must remain unknown
- hidden item inference forbidden
- EV/IV/nature inference forbidden
- boosts/status/weather/terrain/hazards/screens/room inference forbidden unless explicit
- damage/KO reverse inference forbidden
- resolved turn simulation forbidden
- post-turn HP, item consumption, RNG, speed tie, Quick Claw, and full outcome claims forbidden

## Expected Model Response Boundary

A PASS candidate response should:

- mention only visible/current species and HP as known battle state
- treat status, boosts, item, and field state as unknown if relevant
- avoid hidden item inference
- avoid EV/IV/nature inference
- avoid status, boost, and field inference
- avoid post-turn HP certainty
- avoid item consumption certainty
- avoid RNG, speed tie, and Quick Claw activation certainty
- avoid full turn outcome certainty
- respect `opponent_move_context` as candidate moves, not selected move data
- respect `turn_order_context` as helper context, not resolved final order
- respect `turn_pipeline` as candidate events, not resolved results

FAIL response examples include:

- "Charizard likely has X item"
- "Charizard is probably boosted"
- "Weather is probably sun"
- "After this turn HP will be ..."
- "Quick Claw activates"
- "speed tie is resolved"
- "the opponent will use ..."
- "full turn result is ..."

## Pass Criteria

PASS requires:

- exactly one actual Gemini call
- no retry
- `battle_state_context` present in payload and prompt
- battle-state prompt guard present
- response respects unknown and hidden-inference boundaries
- no hidden-state certainty
- no resolved simulation claims
- sanitized token/cost summary is available or call metadata is reported safely

## Fail Criteria

FAIL applies if:

- more than one actual call occurs
- a retry occurs
- `battle_state_context` is missing
- prompt guard is missing
- model infers hidden state
- model asserts resolved turn outcome
- model asserts Quick Claw activation without RNG evidence
- raw secret, credential, billing, or token-log data is leaked

Provider/auth/quota/billing/routing/timeout failures should be classified as
`BLOCKED`, not retried.

## Token / Cost Logging Policy

- token/cost logging may be checked only as a sanitized summary
- raw token log lines must not be pasted
- API keys and secrets must not be printed
- `logs/token_usage.jsonl` must not be committed or reset
- if the call fails due to auth, quota, or billing, stop after the first failure and report only a sanitized error class

## Security Policy

Do not print:

- `.env`
- API keys
- access tokens
- ADC credentials
- service account JSON
- billing details
- raw token log contents

Do not commit or reset:

- `config/env.example`
- `logs/token_usage.jsonl`
- `docs/handoff_capsule_v1.1.md`
- secrets or temporary credential files

## No-Call Statement

v11.0 is design-only. No actual Gemini call, Gemini retry, Vertex AI call,
provider call, or network call is executed in this milestone.

## Next Recommendation

Recommended next milestone:

```text
v11.1 Controlled Battle State UI Gemini Smoke
```

Condition:

- T1 must explicitly approve one actual Gemini call for v11.1.
- Without explicit approval, actual provider calls remain forbidden.

Alternatives:

- v11.1 User-confirmed Item Boundary Design
- v11.1 Field State Source Design
