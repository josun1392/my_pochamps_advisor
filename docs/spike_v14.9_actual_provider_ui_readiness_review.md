# v14.9 actual-provider and validated-UI readiness review

## Current audited boundaries

The pure chain is available in `llm.advisor_candidate_contract`:
`prepare_ui_recommendation_cycle(selected_moves, battle_input, move_repository)`
produces copied deterministic evidence; `build_provider_recommendation_payload`
reduces a ready cycle to its approved seven fields;
`adapt_provider_recommendation_response` accepts only decoded structured
mappings; `complete_recommendation_cycle` applies offline semantic validation;
and `build_recommendation_presentation_model` produces a copied UI-neutral
model. `run_offline_recommendation_provider_adapter` and
`run_offline_recommendation_cycle` are in-memory fake-provider compositions.
Neither calls a network provider.

The runtime legacy path is separate. `run_ui_selected_advice(battle_input,
model, flags)` calls `_build_ui_selected_prompt`, then imported
`scripts.spike_advisor.call_gemini`, then `_log_advisor_call`, and returns
freeform text, usage, and a logging summary. `LLMAdviceWorker.run` owns that
call in a `QThread`; its `finished(str, dict)` and `failed(str)` signals are
handled by `MainWindow._on_llm_advice_finished` and `_on_llm_advice_failed`.
`MainWindow._build_llm_battle_input` obtains `PokemonPanel.selected_moves` and
`selected_move_index`; `_panel_moves_payload` omits empty slots for the legacy
payload. `LLMAdvicePanel.set_advice_text` and `set_error` are text APIs only.

## Structured-provider feasibility

The existing `call_gemini(prompt, model)` is not a safe direct reuse. It
accepts a freeform string, constructs a REST `generateContent` request,
extracts `candidates[0].content.parts[0].text`, and exposes HTTP detail text in
its exception. It returns three usage counters, but has no JSON response mode,
schema/config support, finish-reason handling, safety-block mapping, or
malformed-JSON classification. A separate structured-provider function is
therefore required; this is evidence from current contracts, not a provider
capability claim.

The smallest future boundary is
`call_structured_recommendation_provider(provider_payload, model)`. It must
receive the seven-field serialized payload only, make exactly one provider
call, decode into a provider-neutral mapping, return usage separately, and map
provider/decoding failures to sanitized statuses. No provider SDK object,
repository, UI object, raw response, prompt, secret, traceback, retry, or
fallback crosses this boundary. Existing `_log_advisor_call` may record only
approved usage metadata after a completed call; it must not receive payload or
raw response. Provider, decoding, response-adapter, semantic-completion,
worker, and rendering failures remain distinct owners.

## Integration choices for T1

| Decision | Option A | Option B | Provisional recommendation (T1 approval required) |
| --- | --- | --- | --- |
| Provider flow | Coexistence: add a structured entry point; legacy button remains | Replacement: route legacy path through structured cycle | A: smaller rollback boundary; duplicated paths temporarily |
| Worker | Reuse `LLMAdviceWorker` | New structured worker / generic worker | New structured worker: typed result signals and no legacy signal-shape change |
| Presentation | Format validated fields into current text panel | Dedicated structured widget | A: lowest UI change; preserves existing panel accessibility surface |

Coexistence changes `advisor_client`, `ui/main_window.py`, and tests behind a
separate entry point; rollback is removal of that call site, with one actual
call per invocation and a separate usage game/tool identifier. Replacement
also changes existing worker, button, signal, and panel behavior; rollback is
harder and user-visible behavior changes immediately. A dedicated widget adds
widget/layout/accessibility tests but offers more future structure; formatted
text has lower maintenance cost and can later be replaced independently.

## Worker, UI, and safety plan

A new `StructuredRecommendationWorker` is the preferred provisional design:
it owns a copied prepared input and model, receives the move repository only
at preparation time, emits a sanitized presentation model plus usage summary,
and emits separate sanitized provider/validation failures. It must keep the
same thread cleanup/button-disable discipline as the legacy worker without
changing that worker. This is a user-visible-flow decision and requires T1
approval.

The presentation boundary receives only the validated completed cycle/model.
Raw provider response never reaches `MainWindow` or `LLMAdvicePanel`. API keys
remain environment-only; payloads contain no secret; protected token logs are
not read; tracebacks are sanitized; there is no retry/fallback and one actual
call is the maximum.

## Validation plan

1. Fake-transport pure provider-invocation contract.
2. Fake-provider worker/signal contract.
3. Network-free UI presentation contract.
4. Full offline regression.
5. One explicit T1-authorized Gemini smoke: sanitized fixture, one request,
   usage summary only, no secret/raw-response printing, no retry/fallback, and
   declared pass/fail criteria.

## Required T1 decisions before v14.9-B

1. Choose coexistence or replacement.
2. Choose existing worker, new structured worker, or generic worker.
3. Choose formatted text panel or structured widget.
4. Authorize or decline one actual Gemini smoke test after offline validation.

Actual provider invocation and recommendation UI rendering remain unauthorized
until T1 makes these selections.

## T1-approved coexistence implementation

T1 selected coexistence, a new `StructuredRecommendationWorker`, and validated
formatted text in the existing `LLMAdvicePanel`. The new explicit `구조화 추천 받기`
action is separate from the legacy advice action. It runs copied UI input on its
own `QThread` through `run_structured_ui_recommendation`; the legacy
`LLMAdviceWorker` and `run_ui_selected_advice` path remain unchanged.

`call_structured_recommendation_provider` makes one REST request only, requests
JSON output with a response schema, returns decoded provider-neutral mapping
and usage metadata separately, and maps timeout, safety, missing, malformed,
and decode failures to sanitized codes. It has no retry, fallback, correction
prompt, legacy fallback, raw-response retention, or raw-response UI path.
The runtime passes decoded data through response adaptation, completion, and
the pure presentation model before formatting text.

Offline closure results: 23 v14.9 targeted tests, 30 v14.6-v14.8 regression
tests, 1339 related-regression tests, and 2599 passed with 2 deselected in the
full suite. The authorized smoke was not attempted because credential presence
was unavailable; actual call count was 0. No credential, request, response,
secret, or log content was printed. Usage metadata is returned separately. The
sanitized structured logging helper is disabled by default in this closure so
no protected token-log write was performed.

Next: v14.10: structured recommendation stabilization and user-facing
validation based on the v14.9 smoke result. The legacy flow must not be
replaced automatically.
