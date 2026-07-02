# v12.1 Controlled User-confirmed Item Gemini Smoke

## Purpose

Record the controlled actual Gemini smoke for the UI-selected user-confirmed item path. The smoke verifies that known user-confirmed item context can be sent through the existing limited-context UI path while the model avoids hidden item inference and resolved outcome claims.

This smoke is not advice-quality validation, full turn simulation, item activation simulation, item consumption validation, damage formula validation, or field/status/boost inference validation.

## T1 Approval Confirmation

T1 explicitly approved v12.1 with these limits before the provider call:

- exactly one actual Gemini call
- retry count 0
- no second provider call
- no Vertex AI call
- no token log raw line or secret output
- do not commit or reset `logs/token_usage.jsonl`
- do not commit or reset `config/env.example`

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

UI state:

- limited-context checkbox: ON

Expected optional contexts:

- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`
- `battle_state_context`

## Pre-call Checks

Repository precheck:

- branch: `master`
- remote tracking: `origin/master`
- status: synced, no unpushed commits
- expected unstaged files only: `config/env.example`, `logs/token_usage.jsonl`
- no staged files
- `config/env.example` not staged
- `logs/token_usage.jsonl` not staged

Test precheck:

- `tests/test_ui_turn_pipeline_flag_flow.py tests/test_advisor_battle_state_context.py tests/test_advisor_payload_contract.py -q`: `347 passed`
- full pytest: `1305 passed, 2 deselected`

Boundary precheck:

- payload boundary: PASS
- prompt boundary: PASS
- prompt length summary only: `44777` characters
- raw prompt was not printed

## Payload Boundary Result

PASS.

Expected values were present:

- `battle_state_context` present
- self species/HP sourced as `visible_ui`
- opponent species/HP sourced as `visible_ui`
- self item: `{"known": True, "source": "user_confirmed", "value": "leftovers"}`
- opponent item: `{"known": True, "source": "user_confirmed", "value": "choice-scarf"}`
- field state unknown
- `known_conditions=[]`
- `turn_pipeline` present
- `turn_order_context` present
- `opponent_move_context` present

Forbidden values were absent:

- hidden item source
- inferred item source
- `context_derived` item source
- item `visible_ui` source
- item `calculated_from_visible` source
- item activation field
- item consumption field
- post-turn HP field
- RNG result field
- speed tie result field
- Quick Claw activation field
- full outcome field

## Prompt Boundary Result

PASS.

Expected prompt boundaries were present:

- serialized `battle_state_context`
- known self item as `user_confirmed` context
- known opponent item as `user_confirmed` context
- battle-state guard
- turn-pipeline guard
- turn-order-context guard
- opponent-move-context guard

Forbidden prompt implications were absent:

- known item activated
- known item consumed
- post-turn HP resolved
- hidden item inference
- EV/IV/nature inference
- weather/terrain/boosts/status/hazards/screens inference
- damage reverse item inference

## Actual Call Result

Result: PASS.

Sanitized call summary:

- actual Gemini call count: `1`
- retry count: `0`
- second provider call: `NO`
- Vertex AI call: `NO`
- controlled-call-only network/provider behavior: `YES`
- model: `gemini-2.5-flash`

## Response Safety Scan

PASS.

The sanitized scanner found no forbidden response claims for:

- item activation certainty
- item consumption certainty
- post-turn HP certainty
- RNG resolved
- speed tie resolved
- Quick Claw activation certainty
- full turn outcome certainty
- selected opponent move certainty
- hidden item inference
- damage reverse item inference

The response text was not printed.

## Token/Cost Sanitized Summary

Sanitized aggregate only:

- input tokens: `11770`
- output tokens: `213`
- cached tokens: `0`
- estimated cost USD: `0.00000000`
- pricing status: `free_tier_zero_cost`

Raw token log lines, API keys, secrets, credentials, `.env` contents, access tokens, service account JSON, and billing details were not printed.

`logs/token_usage.jsonl` remains uncommitted and unreset.

## Pass/Fail Result

PASS.

Pass criteria satisfied:

- exactly one actual Gemini call
- retry count 0
- payload boundary PASS
- prompt boundary PASS
- response safety scan PASS
- no forbidden response claims
- sanitized token/cost summary only

## No Retry / No Second Call Confirmation

- retry executed: NO
- automatic retry: NO
- second provider call: NO
- Vertex AI call: NO

## Known Limitations

- This is one controlled fixture, not broad model behavior proof.
- It verifies the current user-confirmed item UI path only when the limited-context checkbox is ON.
- It does not add battle log/parser observed item sources.
- It does not implement item activation or consumption.
- It does not implement post-turn HP, RNG, speed tie, Quick Claw, selected opponent move, full outcome, field, status, boost, hazard, screen, or weather resolution.
- Future model changes can still require re-verification.

## Next Recommendation

Recommended next:

- v12.2 User-confirmed Item Actual Smoke Closure

Alternatives:

- v12.2 Field State Source Design
- v12.2 Item Activation/Consumption Boundary Design
