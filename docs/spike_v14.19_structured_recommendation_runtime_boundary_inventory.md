# v14.19 Structured Recommendation Runtime Boundary Inventory

## Purpose and scope

This is a provider-independent inventory of the structured recommendation
runtime. The v14.17 actual-provider budget remains zero; this review does not
inspect credentials, create a provider client, or call a provider.

## Current production path

1. `MainWindow._start_structured_recommendation` builds UI-shaped battle input
   and selected move slots, disables the structured action, and creates a
   `StructuredRecommendationWorker` on a `QThread`.
2. `StructuredRecommendationWorker.run` copies UI-owned inputs and invokes
   `run_structured_ui_recommendation`; unexpected exceptions become a fixed
   sanitized worker failure message.
3. `run_structured_ui_recommendation` runs
   `prepare_ui_recommendation_cycle`, then `build_provider_recommendation_payload`.
   Non-ready preparation cannot invoke the provider.
4. The structured provider boundary returns only a decoded six-field mapping
   and sanitized usage. `adapt_provider_recommendation_response` checks the
   exact response shape before `complete_recommendation_cycle` performs exact
   candidate/slot and claim semantics.
5. `build_recommendation_presentation_model` accepts only a completed valid
   terminal cycle. The formatter then produces panel text; the panel does not
   receive raw response content.

The legacy `run_ui_selected_advice → call_gemini` flow remains a separate
worker and button path. The structured runtime has no legacy/freeform fallback
after provider, schema, or semantic failure.

## Terminal outcomes and UI boundary

`resolved` may carry a validated exact move/slot pair. `insufficient_context`
and `no_usable_candidate` carry no pair. Preparation, provider, schema, and
semantic failures are mapped to sanitized failure presentation rather than a
resolved pair. The structured panel callback formats only the presentation
model; it does not render request data, raw response text, headers, credentials,
or exception details.

## Ownership and stale-result boundary

The panel tracks an active `legacy` or `structured` owner. Cross-mode results
whose owner is no longer active are ignored; each mode also blocks duplicate
starts while its worker thread exists. However, `_advice_request_sequence` is
incremented but not consumed by result callbacks. A same-owner generation-token
contract is therefore a remaining gap, not a claimed stale-result guarantee.

## Offline guarantees and limits

Offline contracts cover path ordering, exact response validation, non-resolved
pair suppression, worker exception sanitation, panel owner checks, and absence
of structured legacy fallback. They do not prove full UI race behavior, every
real UI session transition, provider availability, latency, costs, retries,
repair, or recovery. The runner remains suspended with no actual-provider
budget.

## Recommended next implementation unit

Before broad runtime expansion, implement and test a monotonic request token
that reaches both worker callbacks and cleanup. It should suppress stale
same-owner results without altering validation, legacy coexistence, or provider
call policy.
