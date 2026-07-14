# v12.65 Sanitized Smoke CLI Output Contract

## Purpose

Provide a single-attempt CLI that explicitly writes a sanitized smoke result to
stdout. This removes the v12.62/v12.64 dependency on an external execution
channel preserving a Python return value.

## Output-loss inventory

The existing production path remains:

```text
run_ui_selected_advice
-> _build_ui_selected_prompt
-> call_gemini
-> response text extraction
-> run_ui_selected_advice_with_sanitized_smoke_capture
-> Python return value
```

The v12.62 and v12.64 one-shot runner invoked the capture function but did
not surface its returned sanitized result through its execution channel. The
normal advisor return path and worker signal had already passed sentinel
contracts. TokenLogger metadata was observable because logging occurs in the
normal production call path, but it does not carry semantic-evaluator output.
No past raw response or token-log content was inspected for this conclusion.

## CLI contract

New entry point:

```text
uv run python scripts/run_sanitized_condition_smoke.py \
  --fixture current-condition-item-event \
  --model gemini-2.5-flash
```

- One process execution maps to exactly one provider attempt.
- The CLI has no loop, retry, fallback, or provider selection logic.
- The only accepted fixture is `current-condition-item-event`: self current
  burn, opponent current unknown, and opponent Focus Sash activation observed.
- Raw confirmations omit `confidence`; existing production normalization adds
  `known` for conditions and `observed` for item events.
- The CLI reuses `run_ui_selected_advice_with_sanitized_smoke_capture(...)`.
  It does not alter normal UI advice flow, payload construction, or prompt
  wording.

## Sanitized stdout schema

stdout contains exactly one compact JSON line with only these top-level keys:

```text
schema_version, provider_status, semantic_status, response_status,
summary, model, usage, error_category
```

`schema_version` is `1`. `usage` contains only input/output/cached token
counts and estimated cost. Forbidden raw-response, prompt, request, header,
credential, environment, stack-trace, and provider-body keys are rejected
before output.

State mapping and exit codes:

| Result | JSON state | Exit |
| --- | --- | --- |
| Semantic pass or fail | `success` + `pass`/`fail` + `available` | 0 |
| Invalid CLI input or malformed capture output | `not_called` + `not_evaluated` + `unavailable` | 2 |
| Provider failure | `failure` + `not_evaluated` + `unavailable` | 4 |
| Provider success, response unavailable | `success` + `unavailable` + `unavailable` | 5 |
| Provider success, evaluator failure | `success` + `unavailable` + `available` | 6 |

The capture seam now explicitly distinguishes an absent response text from an
evaluator exception. Both remain separate from provider failure. The CLI does
not print exception details, provider raw bodies, or a raw response in any
state.

## Offline subprocess contract

Seven subprocess tests exercise the real CLI `main` boundary with an injected
fake provider and the existing production capture path. They lock:

- One parseable JSON line and the expected exit code.
- Semantic pass and semantic fail with exit code 0.
- Response-unavailable, evaluator-failure, provider-failure, invalid-input,
  and malformed-capture classifications.
- No fake raw-response sentinel in stdout or stderr.
- No non-JSON stdout noise, raw-response keys, Python repr, traceback, or
  provider exception detail.

## Readiness

**READY FOR CLI-CAPTURED ACTUAL STABILITY SMOKE**

This is offline readiness only. A future actual stability smoke requires a
separate explicit approval and must invoke this CLI once per approved attempt.
It must not reuse the v12.64 return-value-only one-shot path.

## Safety

- No actual Gemini/provider/network call or credential check was made.
- No raw response, token-log content, past response recovery, or secret output
  occurred.
- `config/env.example` and `logs/token_usage.jsonl` remain protected and
  unstaged.
