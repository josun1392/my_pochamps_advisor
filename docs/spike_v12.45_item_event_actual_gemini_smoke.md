# v12.45 Item Event Actual Gemini Smoke

## Result

`FAIL - SEMANTIC BOUNDARY`

## Approved Execution Audit

- Model: `gemini-2.5-flash`
- Actual Gemini call attempts: 1
- Retry attempts: 0
- Fallback, second provider, and Vertex AI calls: 0
- Provider result: success
- TokenLogger metadata recording: completed
- Sanitized usage: input `9899`, output `140`, cached `0`

No additional provider or diagnostic call was made after this result.

## Pre-call Verification

The offline contracts passed before the actual call:

- `tests/test_item_event_prompt_fixture.py`: 9 passed
- `tests/test_item_event_payload_mapping_contract.py`: 27 passed
- `tests/test_advisor_payload_contract.py`: 500 passed

The local pre-call production prompt check passed:

- limited context gate enabled
- self known current `leftovers` present as user-confirmed current context
- opponent `focus-sash` activation normalized into
  `item_event_context.observed_events`
- event source/status/confidence were
  `explicit_user_event_confirmation` / `user_confirmed` / `observed`
- forbidden fields absent
- observed-only item-event prompt guard present
- required credential available; its value was not read or printed

## Fixed Fixture

- Known current item: self `leftovers`, user-confirmed current context only.
- Explicit observed event: opponent `focus-sash`,
  `item_activation_observed`, `user_confirmed`,
  `explicit_user_event_confirmation`, turn 5, and the fixed v12.44 note.
- `confidence=observed` was added by the existing mapper in the normalized
  payload, as required by the production source contract.

## Semantic Review

The response did not promote Focus Sash into exact HP=1, a resolved item effect,
post-turn state, RNG result, or final speed order. It did use uncertainty for a
candidate order modifier.

However, it did not clearly recognize or distinguish the explicit opponent Focus
Sash observation from the self known Leftovers context. Instead, it foregrounded
other available current-item and move/damage information and included a specific
HP damage range. That does not satisfy the v12.44 PASS requirement that the
observed event be treated explicitly as limited user-confirmed context and kept
separate from known-item context without exact numeric overclaiming.

The complete provider response is intentionally not stored here.

## No Immediate Fix

This smoke does not change production code, prompt wording, fixture data, or
tests. It does not retry the call. The result requires analysis before any
follow-up implementation or future provider execution.

## Recommended Next Step

`v12.46 Item Event Smoke Failure Analysis Design`

Analyze the response-salience and context-separation failure without another
provider call. Any prompt or payload change requires a separate design and
contract decision.

## Security and Protected Files

- No API key, credential, `.env`, authorization header, or environment dump was
  printed.
- No raw `logs/token_usage.jsonl` content was read or printed.
- `config/env.example` was not staged, committed, reset, or restored.
- `logs/token_usage.jsonl` was not staged, committed, reset, or restored.
