# v15.36 MainWindow Session Lifecycle and Stale Worker Completion Wiring Design

## Current call graph (code evidence)

`ui/main_window.py` `MainWindow.__init__` directly creates
`_battle_session_sequence = 0`, `_current_battle_session_id =
_current_state_session_id = "ui-session-0"`, `_observation_sequence = 0`, and
`ObservationCollection("ui-session-0")`. It also owns legacy/structured thread
and worker refs plus `_advice_request_sequence`, `_active_advice_owner`,
`_active_advice_request_token`, and `_active_advice_terminal_token`. It creates
neither a `BattleObservationRuntimeSessionManager` nor a `battle-state-v1`
initial state.

`begin_new_battle()` calls `_begin_new_battle_session()`. That method increments
the `ui-session-N` counter, resets the existing collection, clears UI
confirmation/turn/observed-evidence fields, and sets `_observation_sequence` to
0. It does not invalidate request token state, create/roll over the core
manager, or have a failure path. Consequently a running worker may finish after
new battle begins.

`_capture_structured_observed_damage_confirmation()` increments MainWindow's
mutable sequence before constructing the observation. `_open_current_observed_damage_dialog()`
then calls the raw collection's `add_confirmation_result()`. Production does not
call replay `apply`: collection evidence and runtime transition are still split.

Structured path:

```text
structured_advice_requested
→ MainWindow._start_structured_recommendation
→ _build_llm_battle_input
→ capture_ui_current_state_provenance(current state session ID)
→ _observation_collection.snapshot(current battle session ID)
→ _trusted_turn_context_snapshot
→ _begin_advice_request("structured")
→ StructuredRecommendationWorker
→ run_structured_ui_recommendation
→ finished/failed signal
→ _on_structured_recommendation_finished/_failed(request token, payload)
→ _claim_current_advice_terminal
→ advice panel/status bar
```

`StructuredRecommendationWorker` is also in `ui/main_window.py`. It deep-copies
battle input, observation snapshot, and trusted turn context. Session identity
exists only in those nested values: its signals carry result or message only and
the signal lambdas capture request token only. Current token guard protects
same-owner request ordering. It does not protect a prior battle session because
new battle does not invalidate the token. Current callbacks affect presentation,
not collection/runtime/store/ledger. `_cleanup_structured_worker()` deletes the
thread before its token/current-worker checks; cleanup must remain independent
of future presentation session suppression. `closeEvent()` invalidates tokens
and requests interruption, unlike new battle.

Relevant existing evidence is in `tests/test_v14_same_owner_request_token_lifecycle_contract.py`,
`tests/test_v14_adversarial_advice_lifecycle_contract.py`,
`tests/test_v14_advice_window_teardown_lifecycle_contract.py`,
`tests/test_v15_battle_session_lifecycle_contract.py`,
`tests/test_v29_observation_ownership_ui_bridge_contract.py`, and
`tests/test_v30_trusted_turn_number_producer_contract.py`.

## Initial-state source conclusion before T1 decision

**A bounded initial-state factory is required.** There is no production builder
for exact `battle-state-v1`; search finds validators and test fixtures only.
`_build_llm_battle_input()` explicitly produces advisory payload data with no
full battle state. Selected slots identify Pokémon/slot but do not authoritatively
provide all initial reducer records: current/max HP, fainted, condition, known
item, field state, and side conditions. `capture_ui_current_state_provenance()`
is request provenance, not a store initializer.

Before the T1 decision, this was the unresolved question: **which explicit trusted
source is authorized to populate the initial self/opponent Pokémon records,
including HP/max HP, fainted, condition, known item, active slots, field, and
side conditions?** The factory must reject missing data; it must not infer from
selection, damage estimates, default assumptions, or provider output.

## T1 bootstrap decision and schema decision

T1 now defines the normative bootstrap rule: explicitly UI-selected Pokemon
identity is trusted input. Unconfirmed current/max HP, fainted, condition,
item, field, and side-condition facts begin as explicit **unknown**. Unknown is
not full HP, alive, no item, no condition, no field, or an empty side-condition
collection. Provider/LLM output, damage estimates, and species metadata never
authoritatively populate bootstrap battle facts; later trusted observations or
user confirmations resolve only the facts they establish.

**Decision B: v15.36A Unknown Bootstrap State Contract must precede MainWindow
wiring.** Current validators (`BattleStateStore._valid_state()` and
`ObservationReplayRuntime._valid_initial_state()`) validate top-level version,
session, maps, and sequence, but do not provide exact canonical unknown
semantics. In `advisor_reducer_state_model`, HP accepts absent/`None`/`"unknown"`
values, `fainted` only has a true-fainted interpretation, and condition/item
and field clear operations write `None` although set operations treat `None` and
`"unknown"` alike. Side conditions must be a list, making `[]` a concrete empty
collection rather than unknown. Thus unknown and known absent are not
deterministically distinguishable across all required facts.

The selected identity can be mapped into the existing side/roster shape, but
each active selected identity must be explicit; missing self or opponent
identity is rejected rather than guessed. The initial
`last_applied_observation_sequence` remains the existing neutral `None`,
separate from unknown combat facts.

v15.36A defines serialization- and fingerprint-stable unknown markers,
known-absent distinction, exact validation, reducer/store compatibility, and
backward compatibility for concrete state. It also introduces the bounded
`llm/advisor_initial_battle_state.py` factory: plain detached session and
selected identities in, exact detached state out; no UI widgets, runtime/
manager creation, provider/filesystem/network calls, species-meta inference,
or `100`/`False`/`None`/`[]`/`{}` substitutes. Missing identity, malformed
identity, session mismatch, or unsupported partial-team shape returns a
sanitized invalid-initial-state result with no partial state. Equivalent input
must produce stable state/fingerprint and no aliasing.

MainWindow manager ownership, rollover, collection/allocator migration, and
worker session gates remain deferred until v15.36A passes.

## Candidate comparison

| Candidate | Single authority | MainWindow changes | Stale protection | Qt coupling | Testability | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| A. MainWindow directly owns one manager | Yes after migration | Smallest | Direct callback gate | UI adapter only | Strong harness tests | **Recommended** |
| B. New lifecycle controller | Yes | Adds layer | Good | Higher | Good | Defer; no demonstrated need |
| C. Keep legacy fields plus manager | No | Superficially small | Divergence risk | High | Poor | Reject |

## Recommended v15.36 contract (deferred behind v15.36A)

MainWindow owns one `_observation_runtime_session_manager`. Active session ID,
observation sequence, and collection become manager-derived reads/delegation;
remove `_current_battle_session_id`, `_current_state_session_id`,
`_observation_sequence`, and `_observation_collection` as independent mutable
authorities. Raw bundle/runtime/commands are never exposed.

Initial creation waits for a detached valid factory result and performs no
provider/filesystem I/O. New battle ordering is:

```text
new session ID → trusted initial-state factory → manager.rollover
→ on session_replaced only: reset UI confirmation/presentation state
→ retire active request presentation authority
```

Rollover/factory failure preserves old manager and all UI state. Same-ID
`session_unchanged` resets neither. No persistence command runs.

Observed confirmation uses manager allocation followed by bounded admission with
the captured active ID. Admission failure may leave a gap but never changes store
or ledger; a stale callback cannot allocate from the new bundle. Worker launch
captures explicit `captured_session_id` alongside request token in callback
closure; it does not infer the ID from nested payload.

Success/error ordering is `token guard → session gate → terminal claim →
presentation`. Token guards same-session prior requests; session gates pre-
rollover requests. Both remain. Stale success/error changes no panel, status,
token/cost display, collection, runtime, fingerprint, store sequence, allocator,
or ledger, and never retries or retags. Thread cleanup always runs independently.

No UI save/load, picker, autosave, startup restore, import, undo, cancellation,
or raw component API is in scope.

## Proposed executable tests

### v15.36A unknown bootstrap and reducer/store contract

- `test_initial_state_factory_uses_only_explicit_selected_identity` and
  `test_initial_state_factory_rejects_missing_required_identity_without_guessing`
  - expected: selected identity/slot mapping only, or sanitized invalid input;
    no provider, metadata, damage, or UI-object inference.

- `test_initial_state_factory_marks_unconfirmed_battle_facts_unknown`,
  `test_unknown_bootstrap_does_not_encode_full_hp_alive_or_no_item_as_fact`, and
  `test_unknown_and_known_absent_are_distinct`
  - expected: canonical distinct unknown HP/max HP, fainted, condition, item,
    field, and side conditions; no concrete defaults.

- `test_initial_state_factory_is_deterministic_and_detached`,
  `test_unknown_bootstrap_passes_exact_battle_state_validation`, and
  `test_unknown_bootstrap_fingerprint_is_stable`
  - expected: valid output is exact, detached, and fingerprint-stable.

- `test_runtime_accepts_unknown_bootstrap_state`,
  `test_unknown_bootstrap_preview_is_non_mutating`,
  `test_trusted_observation_can_resolve_unknown_field`,
  `test_unrelated_unknown_fields_remain_unknown_after_partial_observation`, and
  `test_unknown_bootstrap_does_not_create_false_transition_conflicts`
  - expected: preview preserves state/fingerprint/sequence/ledger; trusted
    application resolves only observed facts and leaves unrelated unknowns.

### v15.36 MainWindow wiring (after v15.36A)

- `test_main_window_uses_session_manager_as_single_session_authority`,
  `test_main_window_has_no_independent_mutable_observation_sequence_authority`,
  `test_main_window_does_not_own_a_second_mutable_observation_collection`, and
  `test_main_window_session_reads_are_derived_from_active_bundle`
  - expected: one active ID/allocator/collection; detached state/fingerprint/
    store sequence/ledger; no raw getter or legacy mirror.

- `test_initial_state_factory_produces_exact_matching_battle_state`,
  `test_initial_state_factory_rejects_missing_domain_input_without_guessing`,
  `test_main_window_creates_initial_runtime_session_without_provider_or_filesystem_io`,
  and `test_invalid_initial_session_creation_does_not_publish_partial_ui_or_core_state`
  - expected: matching state/session with allocator 0 and empty ledger, or exact
    old/no state preservation; no inferred battle facts or I/O.

- `test_begin_new_battle_rolls_over_core_session_before_resetting_ui`,
  `test_successful_rollover_resets_ui_after_new_bundle_publication`,
  `test_failed_rollover_preserves_old_core_session_and_ui_state`,
  `test_begin_new_battle_performs_no_save_load_or_restore`, and
  `test_new_battle_invalidates_old_request_without_retagging_result`
  - expected: success publishes B then resets UI; failure preserves exact A UI,
    collection/state/fingerprint/store sequence/allocator/ledger; no persistence.

- `test_confirmation_capture_allocates_sequence_from_active_bundle`,
  `test_confirmation_capture_uses_matching_captured_session_id`,
  `test_stale_confirmation_does_not_advance_new_session_allocator`,
  `test_confirmation_admission_uses_bundle_without_raw_collection_access`,
  `test_collection_snapshot_for_worker_is_detached_from_active_bundle`, and
  `test_admission_failure_may_leave_sequence_gap_without_store_mutation`
  - expected: allocation/admission scoped to active bundle; duplicate/conflict
    preserved; collection capture alone leaves runtime fingerprint/store sequence/
    ledger unchanged.

- `test_current_worker_success_updates_presentation_after_token_and_session_guards`,
  `test_old_session_worker_success_is_suppressed_after_rollover`,
  `test_same_session_old_request_token_is_suppressed`,
  `test_stale_success_does_not_mutate_collection_runtime_or_ledger`,
  `test_stale_success_does_not_overwrite_advice_or_status_bar`, and
  `test_stale_success_still_performs_thread_cleanup`
  - expected: only current token/session updates presentation; stale core values
    remain exact and old thread still cleans up.

- `test_current_worker_error_updates_current_session_presentation`,
  `test_old_session_worker_error_is_suppressed_after_rollover`,
  `test_stale_error_does_not_overwrite_new_session_status`,
  `test_stale_error_still_performs_thread_cleanup`, and
  `test_session_gate_does_not_delete_or_rewrite_token_logs`
  - expected: identical guard separation for failure; cleanup remains safe.

- `test_request_token_guard_and_session_guard_reject_distinct_stale_cases`,
  `test_matching_request_token_with_old_session_is_still_rejected`,
  `test_matching_session_with_old_request_token_is_still_rejected`, and
  `test_worker_result_session_is_never_inferred_or_retagged_from_current_ui`
  - expected: the two guards independently reject their stale condition.

- `test_main_window_lifecycle_wiring_has_no_autosave_startup_file_picker_or_import_hooks`,
  `test_rollover_wiring_does_not_call_provider`,
  `test_persistence_commands_remain_explicit_and_inactive_during_ui_lifecycle`, and
  `test_ui_wiring_does_not_expose_raw_runtime_store_or_commands`
  - expected: no forbidden integration or implicit persistence.

After T1 approval, expected production files are `ui/main_window.py`, a bounded
`llm/advisor_initial_battle_state.py`, and possibly no worker file because a
callback closure can carry captured session metadata. Expected tests:
`tests/test_v36_main_window_session_lifecycle_wiring.py` and, if needed,
`tests/test_v36_initial_battle_state_factory.py`. Payload contract remains
unchanged.
