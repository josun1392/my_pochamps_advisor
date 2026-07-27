# v15.40 Actual Provider Runtime-Grounding Smoke Boundary Design

## Boundary

This is documentation-only. No credential check, provider call, network call,
smoke script, production Python, or test Python is performed. Actual smoke
requires a later explicit T1 approval.

## Current call graph

```text
MainWindow structured request
 -> advisor_candidate_contract.build_provider_recommendation_payload
 -> advisor_client.call_structured_recommendation_provider
 -> advisor_candidate_contract.adapt_provider_recommendation_response
 -> complete_recommendation_cycle
 -> validate_runtime_grounding
```

`call_structured_recommendation_provider` selects the configured model, reads
credential availability only at invocation, sends one JSON-schema request with
a 60-second timeout, and returns decoded response/usage. It has no retry loop.
`structured_fixture_evaluation.py` provides the existing deterministic fake
fixture path; its actual-provider state is suspended. Token logging happens in
`run_structured_ui_recommendation` only after a provider result and must remain
outside a smoke report. Raw provider response is not an approved report field.

## Purpose and fixture allowlist

Smoke verifies only payload acceptance, grounding-v1 structure/semantic
validation, unknown non-promotion, runtime-known precedence over evidence, and
internal-metadata exclusion. It is not recommendation-quality, damage, model
comparison, or broad fixture evaluation.

Approved candidate fixtures are existing sanitized v15.39 mappings only:

| ID | Required | Purpose |
|---|---:|---|
| `runtime-unknown-bootstrap` | yes | unknown is not treated as full/alive/absent |
| `runtime-known-item-stale-ui` | yes | Focus Sash runtime fact beats Choice Scarf evidence |
| `runtime-partial-known-hp` | optional | no percentage/alive/KO inference |

Default maximum is two calls, or three only with exact T1 approval. Retry,
repair, automatic repeat, and multi-model execution are always zero.

## T1 approval and preflight

T1 approval must explicitly specify: actual provider authorization, exact model,
fixture IDs, maximum calls, retry=`0`, and a single-run/cost approval. Without
all fields, the runner is BLOCKED and makes zero credential or network checks.

Preflight must verify master baseline equals origin, no staged changes,
allowlisted fixture IDs/model, budget, retry zero, bounded timeout, and protected
files untouched. Credential status may be reported only as an
available/unavailable boolean after approval; no value or substring is read or
printed. It uses the existing environment boundary, never protected files.

## Execution and redaction contract

For each approved fixture, the path is payload builder -> provider -> response
adapter -> `validate_runtime_grounding`. Stop at first failure. A report may
contain fixture ID, sanitized provider category, schema status, grounding status,
sanitized validation errors, and safe aggregate token/cost metrics if already
available. It must never contain raw prompt, payload, response, local path,
API key, fingerprint, token, session/CAS/ledger metadata, or raw token log.
No artifact is persisted by default.

PASS requires one successful request, grounding-v1, structural and semantic
validation, no forbidden claim, and no internal metadata. FAIL covers provider,
parse, grounding, semantic, timeout, or redaction failure. BLOCKED covers no
approval, baseline/preflight mismatch, unavailable credential, or unsafe runner.

Recommended exit codes: `0` pass, `2` usage, `3` credential unavailable,
`4` provider failure, `5` parse failure, `6` structural grounding failure,
`7` semantic failure, `8` forbidden/internal metadata, `9` blocked preflight.

## Architecture and future offline tests

Prefer extending the existing sanitized smoke runner if it can enforce this
allowlist, first-failure budget, and redaction contract. Otherwise add one
bounded `scripts/run_sanitized_runtime_grounding_smoke.py`; do not use pytest
network markers. Expected offline contract tests cover no-network default,
explicit actual flag, exact fixture/model allowlists, max calls, retry zero,
sanitized output, exact exit codes, first-failure stop, deterministic fake path,
and exclusion from the offline suite.

Actual smoke remains deferred pending explicit T1 approval and a subsequent
exact-stage/commit/push gate.
