# v14.10 structured recommendation stabilization

The structured coexistence path now hardens fake-transport decoding before the
offline response adapter: missing candidates/content, missing text, invalid or
array JSON, fenced JSON, unknown response fields, safety blocks, HTTP failure,
timeout, and network failure return sanitized codes only. A valid six-field
decoded mapping remains the only input to completion.

Usage metadata is independent of recommendation data and is normalized to
input/output/cached tokens, model, tool, success, and failure code. Missing,
partial, negative, or non-numeric counters become sanitized zero values with a
usage-unavailable code. Structured logging remains disabled by default and
logging failure cannot alter recommendation status.

The separate structured worker blocks duplicate starts, copies UI input, cleans
up thread/worker references, restores its button on success/failure, and emits
no raw provider content. The legacy selected-move button, worker, freeform
client path, and text behavior remain separate. Formatted presentation renders
only validated fields and user-friendly Korean failure messages.

Security policy: one call maximum, no retry/fallback/repair/legacy fallback,
and no request, raw response, secret, traceback, repository, or provider object
crosses structured runtime, signals, formatter, or logging metadata.

Validation: 39 structured tests, 30 v14.6-v14.8 regressions, 1355 related
tests, and 2615 passed with 2 deselected in the full suite. Credential
availability was unavailable at the smoke gate; actual call count was 0 and
smoke status was blocked by environment. No raw request/response/secret or
protected token-log content was printed.

Next: v14.11: user-facing structured recommendation validation and coexistence
UX review. Legacy replacement remains unauthorized.
