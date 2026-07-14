# v12.68 CLI-Captured Attribution Gemini Re-smoke

## Final status

`FAIL - SEMANTIC STABILITY`

## Pre-call verification

- Attribution response, payload/prompt, item-event prompt, sanitized CLI,
  capture, item-event mapping, and advisor payload contracts passed.
- Production prompt preflight confirmed the payload-driven `Trusted context
  attribution` block for self burn, opponent unknown, and opponent Focus Sash
  activation. Disabled and conditional paths remain covered offline.
- Forbidden condition/item resolved, exact, post-turn, RNG, and order fields
  were absent. Credential availability was confirmed without reading a value.

## Actual CLI attempts

All attempts used the same approved single-attempt CLI command, fixed fixture,
model, prompt, payload, and evaluator.

| Attempt | Exit | Provider | Response | Semantic | Sanitized usage | Sanitized result |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 0 | success | available | fail | input 5529, output 83, cached 0, estimated cost 0.0 USD | Current-condition or observed-item-event attribution was missing, mixed, or overstated. |
| 2 | 0 | success | available | fail | input 5529, output 84, cached 0, estimated cost 0.0 USD | Current-condition or observed-item-event attribution was missing, mixed, or overstated. |
| 3 | 0 | success | available | fail | input 5529, output 102, cached 0, estimated cost 0.0 USD | Current-condition or observed-item-event attribution was missing, mixed, or overstated. |

Each stdout result was a parseable one-line sanitized JSON payload and each
stderr stream was empty. No raw response, prompt, provider object, or error
body was stored or output.

## Assessment

- Semantic PASS: 0.
- Semantic FAIL: 3.
- Response unavailable: 0.
- Evaluator failure: 0.
- Provider failure: 0.
- CLI/precall failure: 0.
- CLI result contract mismatch: 0.

v12.67 increased the prompt input from 5429 to 5529 tokens and its attribution
block passed offline fixtures, but it did not change the observed semantic
stability result for this fixed actual fixture. Capture transport and provider
availability remain healthy; the repeated failures do not authorize a fourth
call or an immediate prompt change.

## Safety and regression

- Actual provider calls: exactly 3; no retry, fallback, second provider, or
  Vertex AI call.
- No production/test/script/dependency file was changed during execution.
- No credential value, raw response, past-response recovery, or token-log
  content was read, stored, or output.
- `config/env.example` remains untouched. `logs/token_usage.jsonl` remains
  unstaged after normal call logging.
- Post-call offline contracts and full pytest passed.
