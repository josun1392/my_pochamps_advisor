# v14.6 provider/UI integration readiness audit

## Pure-cycle readiness

`prepare_recommendation_cycle(moves, battle_snapshot, repositories,
battle_snapshot_summary, known_limitations)` composes `evaluate_move_slots`,
`build_evidence_bundle`, and `build_recommendation_request`. Its copied outputs
are provider-neutral and use `ready`, `no_candidates`,
`no_selectable_candidates`, `invalid_snapshot`,
`candidate_evaluation_failed`, and `request_validation_failed`. Non-ready
cycles have no request.

`complete_recommendation_cycle(prepared_cycle, response_payload)` reuses
`parse_recommendation_response`; parser failure returns a sanitized cycle while
retaining copied candidate/evidence/request data. Neither pure entry point
imports provider, network, UI, logging, or repository objects into outputs.

## Existing provider and UI boundaries

`MainWindow._build_llm_battle_input` collects current UI data, including
`_panel_moves_payload` and `_selected_move_payload`. `_start_llm_advice`
creates `LLMAdviceWorker`; its `run` method calls
`advisor_client.run_ui_selected_advice`. That function builds a prompt through
`_build_ui_selected_prompt`, calls `call_gemini`, logs usage via
`_log_advisor_call`, and returns freeform text plus usage/summary.

`LLMAdvicePanel.advice_requested` triggers the worker path. Completion calls
`LLMAdvicePanel.set_advice_text`; failures call `set_error`. The current flow
uses `PokemonPanel.selected_moves` but sends only the index selected by
`PokemonPanel.selected_move_index`. It must remain unchanged until a separately
approved migration.

## Adapter gaps

| Pure input | Current source | Gap / smallest future adapter |
| --- | --- | --- |
| `moves` | `MainWindow._panel_moves_payload` | Convert UI move payloads to ordered identifiers while retaining original slots. |
| `battle_snapshot` | `_build_llm_battle_input` and confirmation contexts | Extract only trusted normalized deterministic contexts expected by candidate evaluation. |
| `repositories` | `MainWindow.move_repo` | Supply as input-only metadata repository; never copy it to cycle output. |
| summary/limitations | `scenario` and `ADVISOR_KNOWN_LIMITATIONS` | Copy approved summary/limitations into the pure boundary. |

The current provider expects selected-move battle input and produces freeform
text, whereas v14 expects an immutable structured recommendation request and
already-decoded structured response payload. A future provider adapter must
serialize only approved request fields, never persist/display raw response, map
provider failures without losing prepared evidence, and respect the existing
token logging boundary without reading protected logs.

The UI currently has no validated recommendation-result model. The smallest
future presentation model should display selected move/slot, structured reasons,
risks, alternatives, and sanitized validation/provider errors while leaving
candidate evidence owned by the pure cycle.

## Migration and ownership

1. **Pure UI snapshot adapter** — `ui/main_window.py` only; tests for trusted
   shape/copies; rollback is no call site. No provider behavior change.
2. **Offline prepare integration** — a non-provider entry point; tests for
   readiness/error display model; rollback removes that entry point.
3. **Provider adapter** — separate client adapter accepting recommendation
   request; tests for serialization/error boundaries; provider behavior changes
   only behind an explicit path.
4. **Offline completion/presentation** — parser result to a presentation model;
   tests for no raw response; UI behavior changes only on that new path.
5. **Coexistence decision** — retain or replace selected-move path only after
   compatibility review and rollback plan.

| Failure | Owner | Evidence survives | Provider allowed | Recommendation display |
| --- | --- | --- | --- | --- |
| Invalid UI snapshot / candidate / request | future snapshot or pure layer | yes when built | no | no |
| No selectable candidates | pure layer | yes | no | sanitized state only |
| Provider failure | future provider adapter | yes | no retry here | sanitized failure only |
| Malformed/semantic response | parser/completion | yes | no | no raw response |
| Worker/UI failure | future worker/presentation | yes | provider unchanged | sanitized UI error |

Security policy: no API key in request/result, no raw response persistence or
UI display, no protected token-log access, and sanitized errors only. Next:
v14.7: offline provider-adapter design and structured request/response boundary
audit. No actual provider call or UI recommendation rendering is authorized.

The ordered `adapt_ui_move_slots`, trusted `adapt_ui_battle_snapshot`, approved
summary/limitations helper, and offline `prepare_ui_recommendation_cycle` now
exist in the pure contract module. They preserve slot positions without using
`selected_move_index` to reduce candidates, copy trusted present values only,
exclude provider/UI fields, keep the repository input-only, and leave the
current selected-move provider/UI flow unchanged. Provider adaptation and
validated UI presentation are still not implemented.

Validation: 15 v14.6 adapter/design tests, 12 v14.5 cycle-regression tests,
89 v14.3/v14.4 contract-regression tests, 28 candidate-regression tests, 52
registry-regression tests, 1282 related-regression tests, and 2541 passed with
2 deselected in the full suite.
