# v12.0 Controlled User-confirmed Item Gemini Smoke Design

## Purpose

Design a controlled actual Gemini smoke for the UI-selected user-confirmed item path without executing it in v12.0. The future smoke should verify that known user-confirmed item context can appear in the actual Gemini prompt while the model still avoids hidden item inference and resolved outcome claims.

The smoke is not for advice quality, broad matchup evaluation, item activation simulation, item consumption, damage formula validation, or full Turn Engine validation.

## Prerequisite Status

Before any future provider call:

- branch must be `master`
- remote tracking must be `origin/master`
- repo must be synced with no unpushed commits
- no unexpected staged files
- `config/env.example` and `logs/token_usage.jsonl` must not be staged
- latest full or targeted + full pytest evidence must be green
- `GEMINI_API_KEY` must be available without printing it
- Gemini model must be known without printing secrets
- provider path must be the intended Gemini path, not accidental Vertex AI
- T1 must explicitly approve exactly one actual Gemini call

Current v12.0 status:

- design-only
- no actual Gemini call
- no network call
- no retry
- no second provider call

## Fixture

Future controlled smoke fixture:

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

UI state:

- limited context checkbox: ON

Existing limited contexts:

- `turn_pipeline` enabled
- `turn_order_context` enabled
- `opponent_move_context` enabled
- `battle_state_context` enabled

## Execution Scope

- v12.0 is design-only.
- No actual Gemini call in v12.0.
- Actual call, if approved later, must be a separate v12.1 task.
- v12.1 requires explicit T1 approval.
- v12.1 must run exactly one actual Gemini call.
- Retry count must be 0.
- Second provider call is forbidden.
- Vertex AI call is forbidden unless separately approved.

## T1 Approval Requirement

Actual Gemini execution is allowed only if T1 explicitly approves a v12.1 controlled smoke with:

- maximum actual Gemini calls: 1
- retry count: 0
- no retry on failure
- no clarification call
- no second call for a better answer
- no automatic rerun

Without that explicit approval, stop before any provider call.

## Call Limit

Future v12.1 maximum:

- actual Gemini calls: exactly 1 if all pre-call checks pass
- retries: 0
- second provider call: forbidden
- automatic rerun: forbidden
- manual rerun in the same task: forbidden

## No Retry Policy

If the single future v12.1 call fails due to auth, quota, billing, routing, timeout, provider exception, malformed response, or local reporting error, do not retry. Report only a sanitized error class.

## Abort Criteria

Abort before provider call if:

- wrong branch
- repo not synced / unpushed commits
- unexpected staged files
- `.env` or secret exposure risk
- `config/env.example` or `logs/token_usage.jsonl` accidentally staged
- tests not green
- API key unavailable
- model unavailable
- provider path unexpected
- limited context checkbox not ON
- `battle_state_context` missing
- known item missing from payload
- item source is not `user_confirmed`
- forbidden item source appears
- field/status/boost hidden inference appears
- prompt guard missing
- existing `turn_pipeline`, `turn_order_context`, or `opponent_move_context` missing unexpectedly

## Payload Boundary Expectations

Expected:

- `battle_state_context` present
- self species/HP `visible_ui`
- opponent species/HP `visible_ui`
- self item `known=True`, `source=user_confirmed`, `value=leftovers`
- opponent item `known=True`, `source=user_confirmed`, `value=choice-scarf`
- field unknown
- `known_conditions` is `[]`
- `turn_pipeline` present
- `turn_order_context` present
- `opponent_move_context` present

Forbidden:

- hidden item source
- inferred item source
- `context_derived` item source
- `visible_ui` item source
- `calculated_from_visible` item source
- item activation field
- item consumption field
- post-turn HP field
- RNG result field
- speed tie result field
- Quick Claw activation field
- full outcome field

## Prompt Boundary Expectations

Expected:

- serialized `battle_state_context` present
- known self item appears as `user_confirmed` context
- known opponent item appears as `user_confirmed` context
- `battle_state_context` guard present
- existing limited context guards remain present where applicable
- prompt does not say known item is activated, consumed, or resolved
- prompt does not infer hidden item
- prompt does not infer EV/IV/nature/status/weather/terrain/boosts/hazards/screens

## Model Response Safety Expectations

Response may:

- mention user-confirmed item as known context
- use known item carefully as one piece of context
- say limitations remain

Response must not:

- claim item activation certainty
- claim item consumption certainty
- claim post-turn HP certainty
- resolve RNG
- resolve speed tie
- claim Quick Claw activation
- claim full turn outcome
- claim selected opponent move certainty
- infer hidden item
- infer EV/IV/nature
- infer weather/terrain/boosts/status/hazards/screens
- reverse-infer item from damage

## Forbidden Response Claims

Fail the future smoke if the model claims or strongly implies:

- `Leftovers` activates or heals with certainty this turn
- `Choice Scarf` resolves final move order with certainty
- item is consumed
- post-turn HP will be a specific value
- RNG is resolved
- speed tie is resolved
- Quick Claw activates
- full turn outcome is known
- opponent selected move is known without explicit source
- hidden item is inferred
- EV/IV/nature, status, boosts, weather, terrain, hazards, screens, or room are inferred

## Token/Cost Logging Policy

- token/cost summary may be reported only in sanitized aggregate form
- token log raw lines must not be printed
- API key/secrets must not be printed
- billing details must not be printed
- `logs/token_usage.jsonl` must not be committed
- `logs/token_usage.jsonl` must not be reset

## Post-call Reporting Policy

After the single future v12.1 provider call:

- report exact call count
- report retry count
- report model id without secrets
- report payload boundary PASS/FAIL
- report prompt boundary PASS/FAIL
- report response safety PASS/FAIL
- report sanitized token/cost summary if available
- do not paste raw prompt, raw token log lines, secrets, credentials, or billing details
- if local post-call reporting fails after a successful provider call, do not make a second provider call

## Pass/Fail Criteria

PASS if:

- exactly one actual Gemini call in later v12.1
- retry count 0
- payload boundary PASS
- prompt boundary PASS
- response safety scan PASS
- no forbidden claims
- sanitized token/cost summary only

FAIL if:

- more than one provider call
- retry occurs
- payload missing known item
- prompt missing guard
- response makes forbidden item/resolved claims
- secrets or token log raw lines are exposed

## No Actual Gemini Call In v12.0

No actual Gemini, Vertex AI, provider, or network call is executed in v12.0. This document only defines a future controlled smoke.

## Next Recommendation

Recommended next:

- v12.1 Controlled User-confirmed Item Gemini Smoke

Conditions:

- T1 must explicitly approve the actual call
- maximum one actual Gemini call
- retry count 0
- no second call

Alternatives:

- v12.1 Field State Source Design
- v12.1 Item Activation/Consumption Boundary Design
