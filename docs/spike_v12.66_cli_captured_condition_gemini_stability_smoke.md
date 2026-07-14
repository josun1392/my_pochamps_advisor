# v12.66 CLI-Captured Current Condition Gemini Stability Smoke

## Final status

`FAIL - SEMANTIC STABILITY`

## Pre-call verification

- Required offline suites passed: sanitized CLI contract (7), capture contract
  (6), response validation (9), condition payload/prompt (12), condition UI
  (7), condition source (39), item-event prompt (9), and item-event payload
  mapping (27).
- The fake-provider subprocess contract confirmed a single parseable sanitized
  JSON line on stdout, no raw sentinel in stdout/stderr, and no forbidden raw
  response, prompt, request, credential, environment, traceback, or provider
  body keys.
- Production normalization confirmed self burn and opponent unknown current
  conditions with `confidence=known`, plus the opponent Focus Sash activation
  observed event with `confidence=observed`. Required condition and item-event
  prompt guards were present and forbidden fields were absent.
- Credential availability was confirmed without reading or printing a value.

## Actual CLI attempts

Each independent attempt used exactly:

```text
uv run python scripts/run_sanitized_condition_smoke.py \
  --fixture current-condition-item-event \
  --model gemini-2.5-flash
```

| Attempt | Exit | Provider | Response | Semantic | Sanitized usage | Sanitized result |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 0 | success | available | fail | input 5429, output 43, cached 0, estimated cost 0.0 USD | Current-condition or observed-item-event attribution was missing, mixed, or overstated. |
| 2 | 0 | success | available | fail | input 5429, output 71, cached 0, estimated cost 0.0 USD | Current-condition or observed-item-event attribution was missing, mixed, or overstated. |
| 3 | 0 | success | available | fail | input 5429, output 44, cached 0, estimated cost 0.0 USD | Current-condition or observed-item-event attribution was missing, mixed, or overstated. |

All three stdout JSON payloads matched the exit-code contract. `stderr` was
empty for each attempt. No raw response, prompt, provider object, or error body
was output or persisted.

## Assessment

- Semantic PASS: 0.
- Semantic FAIL: 3.
- Response unavailable: 0.
- Evaluator failure: 0.
- Provider failure: 0.
- CLI/precall failure: 0.
- CLI result contract mismatch: 0.

The CLI transport boundary is working: each provider result was captured as a
sanitized JSON line and classified consistently. The three semantic failures
therefore identify a stability failure of the current fixture evaluator
criteria, not a response-capture loss. This document does not retain response
text and does not diagnose a prompt correction. No fourth call, retry,
fallback, second provider, or Vertex AI call was made.

## Safety and regression

- Actual provider calls: exactly 3, all through the approved CLI command.
- No code, test, script, dependency, prompt, or payload modification was made
  during smoke execution.
- No secret, credential value, raw response, past-response recovery, or token
  log content was read, stored, or output.
- `config/env.example` remained untouched. `logs/token_usage.jsonl` changed
  only through normal call logging and remains unstaged.
- Post-call offline contract suites and full pytest passed.
