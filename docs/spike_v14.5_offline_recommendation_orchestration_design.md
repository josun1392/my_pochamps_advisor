# v14.5 offline recommendation orchestration design

## Existing contracts

`evaluate_move_candidate` and `evaluate_move_slots` in
`llm.advisor_candidate_contract` produce isolated deterministic candidate
summaries. `build_evidence_bundle`, `build_recommendation_request`,
`validate_recommendation_selection`, `serialize_recommendation_request`, and
`parse_recommendation_response` provide the pure evidence, request, exact-pair,
serialization, and offline-response boundaries. Candidate evaluation adapts
`build_deterministic_calculation_context` from `llm.advisor_battle_state_context`.

The current production provider path is deliberately separate:
`MainWindow._selected_move_payload` selects one move using
`PokemonPanel.selected_move_index`; `LLMAdviceWorker.run` calls
`advisor_client.run_ui_selected_advice`; `LLMAdvicePanel.set_advice_text` and
`set_error` display that result. `run_ui_selected_advice` owns prompt building,
provider invocation, and token logging, so it is not an offline-cycle adapter.

## Future pure boundaries

`prepare_recommendation_cycle(moves, battle_snapshot, repositories)` should
perform only this sequence: ordered slots → `evaluate_move_slots` →
`build_evidence_bundle` → `build_recommendation_request`. It should return
`ready`, `no_candidates`, `no_selectable_candidates`, `invalid_snapshot`,
`candidate_evaluation_failed`, or `request_validation_failed` with copied
candidates, evidence bundle, request, and sanitized errors. It must not call a
provider, parse provider objects, alter UI state, write logs, rank candidates,
or infer unconfirmed battle facts.

`complete_recommendation_cycle(prepared_cycle, response_payload)` should first
verify a ready prepared cycle, then reuse `parse_recommendation_response` and
return the validated recommendation plus sanitized failures. It must preserve
the prepared deterministic evidence and must not call, retry, or decode a
provider, replace evidence, or modify UI state.

## Integration gaps and migration

`PokemonPanel.selected_moves` exposes all four UI slots, and
`MainWindow._panel_moves_payload` serializes non-empty slots, but no adapter
currently converts those `MoveView` payloads and the normalized UI battle input
into the `moves`, `battle_snapshot`, and repositories shape expected by
`evaluate_move_slots`. The smallest future adapter belongs between
`MainWindow._build_battle_input`/`_panel_moves_payload` and the pure prepare
boundary. It requires neither UI nor provider work by itself.

No current provider insertion point accepts a v14 recommendation request: the
existing `run_ui_selected_advice` accepts a selected-move battle input and emits
freeform text. No current UI presentation model accepts a validated v14 result:
`LLMAdvicePanel` only displays text/error strings. Both provider and UI wiring
therefore require separately approved work. The selected-move path remains the
default while future multi-candidate preparation stays offline.

## Failure ownership

| Failure | Owner | Status | Evidence survives | Provider/UI recommendation |
| --- | --- | --- | --- | --- |
| Invalid slots/snapshot | prepare boundary | `invalid_snapshot` | available inputs only | no/no |
| Metadata or dynamic-context failure | candidate layer | candidate unavailable/partial | yes | no/no |
| All unavailable/request failure/serialization failure | prepare/request layer | non-ready/sanitized failure | yes | no/no |
| Provider failure | future provider boundary | provider failure | yes | no/no |
| Parser or semantic-claim failure | complete/parser layer | `validation_failed` | yes | no/no raw payload |
| UI display failure | future UI boundary | UI failure | yes | provider unchanged/no |

## Immutability ownership

The caller owns the input battle snapshot and slot list. Candidate evaluation
copies each snapshot; the evidence builder owns copied candidates/snapshot;
request construction owns copied summaries, sets, limitations, and guardrails;
the parser owns copied response lists and returns a copied result. A future UI
presentation model must own a final display copy and must never mutate upstream
evidence. No layer may replace deterministic candidate evidence.

The implemented `prepare_recommendation_cycle` and
`complete_recommendation_cycle` now realize these pure boundaries without
provider or UI wiring. Non-ready preparation never returns a request, parser
failure preserves deterministic evidence without retaining raw response data,
and repository objects are input-only. The selected-move path remains
unchanged. Next: v14.6: provider/UI integration readiness audit and migration
design. No actual provider or UI wiring is authorized.

Validation: 12 v14.5 orchestration tests, 89 v14.3/v14.4 contract-regression
tests, 28 candidate-regression tests, 52 registry-regression tests, 1282
related-regression tests, and 2526 passed with 2 deselected in the full suite.
