# v14.8 offline provider-cycle completion design

## Audited existing boundaries

`prepare_ui_recommendation_cycle(selected_moves, battle_input, move_repository)`
adapts trusted UI-shaped input and returns the pure prepared-cycle contract.
`run_offline_recommendation_provider_adapter(prepared_cycle, fake_provider)`
builds the seven-field outbound payload, calls an injected in-memory callable,
and returns only a copied structured response payload.  It never retains the
fake provider or its raw return value.  `complete_recommendation_cycle` takes
a ready prepared cycle plus that decoded payload and delegates semantic and
exact-pair checking to `parse_recommendation_response`.

The legacy selected-move path remains separate:
`run_ui_selected_advice` builds a freeform selected-move prompt, calls
`call_gemini`, and records approved usage metadata through `_log_advisor_call`.
`LLMAdviceWorker.run` invokes that legacy client path; `LLMAdvicePanel` exposes
`set_advice_text` and `set_error`.  None of those runtime symbols call the
v14 offline boundaries.

## Proposed future composition

The future pure, offline entry point is
`run_offline_recommendation_cycle(selected_moves, battle_input,
move_repository, fake_provider)`.  It must compose these existing boundaries
in this fixed order:

1. `prepare_ui_recommendation_cycle`.
2. `run_offline_recommendation_provider_adapter`, only if preparation is
   `ready`.
3. `complete_recommendation_cycle`, only when the provider-adapter status is
   `provider_response_ready`.

It returns the completed canonical cycle with deterministic candidates,
evidence bundle, recommendation request where available, validated result when
available, and sanitized errors.  It must not call a network provider, decode
provider SDK objects, retain raw response data, render UI, rank candidates, or
expand into Turn Engine behavior.

## Failure ownership

| Boundary | Sanitized outcome | Deterministic evidence | Provider stage |
| --- | --- | --- | --- |
| preparation not ready | prepared-cycle status | retained where built | blocked |
| fake provider unavailable/malformed | provider-adapter status | retained | completed without response |
| structured response validation failure | `response_validation_failed` | retained with request | no recommendation display |
| validated response | response status | retained unchanged | completion allowed |

Provider-stage failures never expose or store the raw return value.  A
non-ready cycle never reaches the injected provider.  The legacy selected-move
flow remains unchanged.

## Proposed presentation boundary

`build_recommendation_presentation_model(completed_cycle)` is a later,
UI-neutral mapper.  It may accept only a completed cycle with a validated
recommendation result and produce:

```python
{
    "status": "resolved",
    "recommended_move": "flamethrower",
    "recommended_slot_index": 0,
    "primary_reasons": [],
    "risks": [],
    "alternatives": [],
    "candidate_summaries": [],
    "errors": [],
}
```

It must copy its inputs and exclude provider objects, repositories, UI objects,
secrets, raw response/prompt data, network configuration, tracebacks, and
token-log data.  Invalid or failed completion states receive only a sanitized
non-recommendation presentation; raw payload never crosses this boundary.

## Implemented offline closure

`run_offline_recommendation_cycle` now implements the documented composition:
it prepares first, skips the provider stage for non-ready preparation, invokes
only the injected fake-provider adapter for a ready cycle, and completes only
after a `provider_response_ready` result. Provider-stage failure retains the
independent prepared deterministic evidence. Response semantic failure retains
the prepared evidence and the sanitized completed failure without raw response.

`build_recommendation_presentation_model` accepts completed-cycle mappings
only. It emits copied validated recommendation fields and ordered candidate
summaries for `resolved`, `insufficient_context`, and `no_usable_candidate`.
Any failed or malformed completion maps to a sanitized `validation_failed`
model with no recommended move or slot. Provider-stage internals, repositories,
UI/provider objects, raw responses, secrets, tracebacks, and network/token-log
data are absent from its output.

The legacy selected-move provider/UI flow remains unchanged. No actual Gemini,
provider, network, or recommendation UI rendering integration exists.

Validation at closure: 17 v14.8 tests, 27 v14.6/v14.7 regression tests, 53
v14.3/v14.4/v14.5 regression tests, 28 candidate-regression tests, 52
registry-regression tests, 1283 related-regression tests, and 2576 passed with
2 deselected in the full suite.

Next: v14.9: actual-provider and validated-UI integration readiness review
with explicit T1 decision gate. No actual provider or UI wiring is authorized
automatically.
