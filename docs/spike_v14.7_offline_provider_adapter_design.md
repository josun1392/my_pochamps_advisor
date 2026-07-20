# v14.7 offline provider adapter design

## Audited boundaries

`prepare_ui_recommendation_cycle` returns a copied ready cycle with an immutable
`recommendation_request`; `serialize_recommendation_request` enforces JSON-safe
data and secret-like-key rejection; `complete_recommendation_cycle` accepts an
already-decoded mapping and reuses the offline parser.

The legacy path remains `run_ui_selected_advice(battle_input, model, flags)` →
`_build_ui_selected_prompt` → `call_gemini(prompt, selected_model)` →
`_log_advisor_call(model, usage, game_id)`. It returns `(text, usage, summary)`;
the caller maps timeout/runtime/format failures in `LLMAdviceWorker`. It is a
freeform selected-move path and must not be replaced in v14.7.

## Future pure adapter contracts

`build_provider_recommendation_payload(prepared_cycle)` must accept only a
ready cycle, extract its recommendation request, and serialize exactly these
keys: `request_version`, `battle_snapshot_summary`, `candidate_exact_set`,
`selectable_candidate_exact_set`, `candidate_comparisons`, `known_limitations`,
and `guardrails`. It rejects forbidden keys recursively and never includes a
repository, UI object, secret, model override, network setting, raw prompt,
raw response, token usage, traceback, or internal exception.

`adapt_provider_recommendation_response(provider_response)` must accept only an
already-decoded plain structured mapping with `resolved`,
`insufficient_context`, or `no_usable_candidate`; `validation_failed` remains
local-only. It rejects provider objects, raw-text fallback, and persistence of
raw response. Its copied result is the only response payload admitted to
`complete_recommendation_cycle`.

## Failure, logging, and UI handoff

Non-ready cycles block provider use. Serialization failure is a pure adapter
failure. Provider unavailable/timeout/malformed/freeform response are future
provider-adapter statuses that retain the prepared deterministic cycle and emit
sanitized errors only. Semantic failure remains owned by
`complete_recommendation_cycle`. Raw provider data is neither stored nor shown.

`_log_advisor_call` is the current usage-metadata boundary; a future structured
adapter may report approved token counts through that boundary but must never
read protected logs or log requests, credentials, headers, raw responses, or
secret-bearing tracebacks. A later UI adapter receives only prepared evidence,
validated recommendation result, sanitized provider status, and sanitized
errors.

## Migration

1. Pure provider payload builder in `llm/advisor_candidate_contract.py`; unit
   tests; rollback is no call site; no provider/UI behavior change.
2. Offline fake-provider response adapter tests; no provider/UI behavior change.
3. Structured invocation behind a separate client entry point; provider behavior
   changes only there.
4. Complete-cycle integration; parser boundary tests; no legacy replacement.
5. Validated UI presentation adapter; UI behavior changes only on its new path.
6. T1 coexistence/replacement decision for the legacy selected-move flow.

Next: v14.7-B: implement pure provider payload and response adapters with
fake-provider offline tests. Actual provider invocation and UI rendering remain
unauthorized.

The pure `build_provider_recommendation_payload`,
`adapt_provider_recommendation_response`, and
`run_offline_recommendation_provider_adapter` boundaries now implement this
offline contract. The outbound request is restricted to the seven approved
fields, response input is decoded structured data only, and injected fake
provider failures retain deterministic prepared evidence without raw response,
retry, or fallback. The legacy selected-move provider/UI flow is unchanged; no
actual Gemini, provider, or network integration exists. Next: v14.8: offline
provider-cycle completion integration design and contract audit. Actual provider
invocation and recommendation UI rendering remain unauthorized.

Validation: 18 v14.7 adapter tests, 27 v14.5/v14.6 regression tests, 89
v14.3/v14.4 regression tests, 28 candidate-regression tests, 52
registry-regression tests, 1286 related-regression tests, and 2559 passed with
2 deselected in the full suite.
