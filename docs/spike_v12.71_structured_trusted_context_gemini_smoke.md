# v12.71 Structured Trusted-Context Gemini Stability Smoke

## Scope

This smoke used the v12.70 single-attempt sanitized CLI with the fixed
`current-condition-item-event` fixture and model `gemini-2.5-flash`.
The fixture's normalized trusted entries were:

- Current condition: `self | burn`
- Current condition: `opponent | unknown`
- Observed item event: `opponent | focus-sash | item_activation_observed`

The parser requires the `[Trusted Context]` entries to match this normalized
expected set exactly, then applies the existing advice-presence and forbidden
claim checks. Raw provider responses, prompts, credentials, and token-log
contents were not read, stored, or recorded.

## Pre-call validation

All required offline contracts passed before the approved calls:

- trusted-context acknowledgement: 12 passed
- response validation: 20 passed
- condition payload/prompt: 14 passed
- sanitized smoke CLI: 7 passed
- smoke response capture: 6 passed
- item-event prompt: 9 passed
- item-event payload mapping: 27 passed
- advisor payload: 500 passed

The production preflight confirmed the structured prompt requirement,
payload-derived expected entries, parser/exact-set validation,
condition-only/item-only/absent paths, and absence of forbidden fields.
Credential availability was confirmed without reading its value.

## Actual calls

Exactly three approved independent CLI invocations were initiated with the
same fixture and model. No retry, fallback, second provider, Vertex AI call,
fixture change, or between-attempt code/prompt/payload/parser/evaluator change
occurred.

### Attempt 1

- Execution was initiated as the approved single CLI attempt.
- The outer execution channel did not preserve the sanitized result for this
  record, so its exit code, usage, provider status, response status, and
  semantic status are unavailable.
- No raw response was recovered or re-requested, and no replacement call was
  made.

### Attempt 2

- Model: `gemini-2.5-flash`
- Exit code: 0
- Provider status: success
- Response status: available
- Semantic status: pass
- Sanitized usage: 5,613 input tokens, 114 output tokens, 5,100 cached tokens;
  estimated cost USD 0.00.
- Sanitized summary: trusted-context acknowledgement matched; no forbidden
  condition or item-event outcome claim was found.

### Attempt 3

- Model: `gemini-2.5-flash`
- Exit code: 0
- Provider status: success
- Response status: available
- Semantic status: pass
- Sanitized usage: 5,613 input tokens, 101 output tokens, 0 cached tokens;
  estimated cost USD 0.00.
- Sanitized summary: trusted-context acknowledgement matched; no forbidden
  condition or item-event outcome claim was found.

## Result

**PASS - LIMITED SAMPLE**

- Semantic PASS: 2
- Semantic FAIL: 0
- Response unavailable: 1 (outer capture result unavailable)
- Evaluator failure: 0
- Provider failure: 0 observed
- CLI/pre-call failure: 0

The two semantically evaluable responses both passed the exact structured
acknowledgement set, retained the current-condition versus observed-item-event
categories, and passed advice-presence plus forbidden-claim checks. The first
attempt is excluded from semantic-rate calculation because its sanitized outer
result was unavailable. Under the two-evaluable-response policy, 2/2 semantic
PASS is `PASS - LIMITED SAMPLE`.

## Post-call verification

- structured acknowledgement: 12 passed
- sanitized smoke CLI: 7 passed
- smoke response capture: 6 passed
- response validation: 20 passed
- condition payload/prompt: 14 passed
- full suite: 1,764 passed, 2 deselected
- `git diff --check`: passed
- `git diff --cached --check`: passed

## Safety

- Total actual provider calls: 3.
- No retry, fallback, second provider, or Vertex AI call occurred.
- No raw response, secret, credential value, or token-log content was output
  or persisted.
- `config/env.example` and `logs/token_usage.jsonl` remain unstaged and were
  not staged, committed, reset, or restored.
- No production, test, script, dependency, payload-schema, or UI file changed
  in this smoke task.
