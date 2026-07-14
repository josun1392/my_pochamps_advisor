# v12.61 Current Condition Gemini Stability Smoke

## Final Status

**BLOCKED - PRECALL CONTRACT FAILURE**

## Pre-call Verification

The required offline suites passed:

- `test_current_condition_payload_prompt_contract.py`: 12 passed
- `test_current_condition_response_validation_contract.py`: 9 passed
- `test_current_condition_ui_contract.py`: 7 passed
- `test_status_condition_source_contract.py`: 39 passed
- `test_item_event_prompt_fixture.py`: 9 passed

The fixed current-condition candidate preflight was valid: self burn and
opponent unknown normalize into `condition_context.current_conditions` with
the expected known/current semantics.

## Blocker

The approved fixed raw item-event fixture included `confidence=observed`.
Current production raw confirmation validation accepts source/status/side/item/
event type (plus optional turn/note), then adds `confidence=observed` only to
the normalized `item_event_context.observed_events` payload. Therefore the
provided raw candidate was omitted before prompt construction and the required
`item_event_context` was absent.

Because the pre-call contract required both the condition and observed-item
event contexts, no actual Gemini call was made. This task did not alter the
fixture, production validator, prompt, payload, or code to work around that
failure.

## Actual Calls

- Model: `gemini-2.5-flash`
- Attempts: 0 of 3
- Retry/fallback/second provider/Vertex AI: 0
- Token usage/cost: not applicable
- Credential availability: not evaluated after pre-call failure

## Safe Follow-up

A future approved smoke must reconcile the fixed fixture representation with
the raw-confirmation versus normalized-payload boundary before any provider
call. It must repeat the complete offline and prompt preflight with no code or
fixture changes during its own approved smoke attempts.

## Safety

No provider/network call, credential validation, secret output, raw response,
or token-log output occurred. `config/env.example` and
`logs/token_usage.jsonl` were not staged, committed, reset, or restored.
