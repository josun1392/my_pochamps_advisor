# v12.76 Known Ability Structured-Context Gemini Stability Smoke

## Final Status

`BLOCKED - ABILITY SMOKE FIXTURE UNAVAILABLE`

## Pre-call Verification

- Required offline contracts passed:
  - `test_known_ability_end_to_end_contract.py`: 25 passed
  - `test_current_ability_ui_contract.py`: 5 passed
  - `test_current_ability_payload_foundation_contract.py`: 20 passed
  - `test_known_ability_source_contract.py`: 50 passed
  - `test_trusted_context_acknowledgement_contract.py`: 14 passed
  - `test_trusted_context_acknowledgement_matrix_contract.py`: 21 passed
  - `test_sanitized_condition_smoke_cli_contract.py`: 7 passed
  - `test_current_condition_response_validation_contract.py`: 20 passed
  - `test_item_event_prompt_fixture.py`: 9 passed
- Full regression: `1888 passed, 2 deselected`.
- The existing CLI only accepts `current-condition-item-event` and builds only
  that condition/item-event fixture. It has no fixed
  `current-condition-ability-item-event` fixture or equivalent ability-bearing
  CLI option.

## Blocking Boundary

The approved smoke requires normalized self `intimidate`, opponent `unknown`
ability entries alongside the fixed condition and Focus Sash event entries.
Passing the existing fixture would omit those ability entries, so it cannot
validate the required structured acknowledgement exact set. Creating an
ability fixture or changing the CLI would violate this smoke task's code-change
policy.

## Actual Calls

- Actual provider attempts: 0.
- Credential availability was not checked because the fixture preflight failed
  first.
- No retry, fallback, second provider, Vertex AI, diagnostic call, response
  recovery, or token-log inspection occurred.

## Next Requirement

A separately authorized offline CLI-fixture contract change is required before
an ability-bearing actual smoke can be approved. It must preserve the existing
single-attempt CLI schema and exit-code contract, then establish the fixed raw
ability confirmations through the production normalization path.
