# v15.37 Explicit Battle-State Persistence UI Boundary Design

## Existing architecture inventory

| Concern | Existing symbol and behavior |
| --- | --- |
| Save command | `ObservationReplayPersistenceCommands.save(path)` exports one detached runtime envelope and delegates atomic local save. |
| Load command | `ObservationReplayPersistenceCommands.load(path)` performs detached JSON/schema/fingerprint validation and returns `load_ready`; it does not mutate runtime. |
| Restore command | `ObservationReplayPersistenceCommands.restore(candidate, expected_runtime_fingerprint)` validates candidate/session and delegates same-session restore. |
| Atomic file write | `ObservationReplayPersistence.save()` writes a sibling temporary file then uses `os.replace`; I/O failure preserves the existing target. |
| Path validation | Command helpers `_save_target`, `_load_target`, and `_path` accept `str`/`os.PathLike`, reject empty, directories, and missing save parents. |
| Session/CAS | Command restore rejects foreign envelope with `session_mismatch`; expected current fingerprint mismatch is `stale_runtime`. Persistence restore checks again and returns CAS/rollback statuses. |
| Rollback | `ObservationReplayPersistence.restore()` snapshots store, replaces store plus full ledger, and restores store on ledger failure; rollback CAS conflict is `critical_restore_inconsistency`. |
| MainWindow seam | `BattleObservationRuntimeSessionManager.save/load/restore(captured_session_id, ...)` delegates only to its active bounded bundle. `MainWindow` privately owns this manager; it exposes no runtime/store/commands/persistence getter. |

Command results are small status mappings: save uses `save_complete` or a
sanitized failure; load uses `load_ready` plus detached envelope/ledger or
validation/I/O statuses; restore maps success to `restore_complete` and retains
`restore_rolled_back`, `critical_restore_inconsistency`, `session_mismatch`, and
`stale_runtime` failures.

## Recommended UI boundary

Add only explicit `Save Battle State` and `Load Battle State` actions in a later
implementation. No constructor, new-battle rollover, worker callback, timer,
or startup path invokes persistence.

Save requires an active manager session. On explicit action it captures the
current active session ID and calls `manager.save(captured_session_id, path)`.
The command captures its own detached envelope at command start, so save changes
no runtime state, fingerprint, store sequence, allocator, ledger, collection,
or request token. A running worker continues; save result presentation belongs
to a neutral persistence status area/status bar and must not overwrite advice.

Load is also explicit and load-only. It may validate a chosen path with no active
session, but restore is unavailable until an active session exists. `load_ready`
returns a detached candidate; the UI displays only a sanitized summary: candidate
session relation (same/foreign/no active), schema validity, and a short
fingerprint indicator if needed. It never displays raw envelope JSON, state,
secret, or full path. Load never starts rollover, changes selection, retires a
worker, or restores automatically.

## Candidate ownership comparison

| Candidate | Mutation safety | Stale handling | Qt coupling | Testability | Complexity | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| A. MainWindow `_pending_persistence_candidate` | Weak: long-lived raw mutable envelope | Must clear on many paths | High | Moderate | Small initially | Reject |
| B. Detached candidate in load-summary/restore-confirmation closure | Strong: copied candidate has short lifetime | Capture session/fingerprint at load; expire on dialog close/rollover | Moderate | Strong | Small | **Recommended** |
| C. New generic candidate controller | Strong | Strong | Moderate | Moderate | Excessive | Reject |

The confirmation closure owns a defensive copy of the candidate and records:
`loaded_for_active_session_id` and `expected_restore_fingerprint`, both captured
at successful load-summary time. It passes another detached candidate copy only
after explicit user confirmation. There is no MainWindow mutable candidate cache.
Closing/cancelling the dialog, new-battle rollover, restore completion, or a
failed active-session/fingerprint revalidation retires the closure candidate.

## Restore boundary

Restore requires a prior `load_ready` candidate and explicit confirmation.

```text
load-ready detached candidate
→ show same/foreign session and stale-risk summary
→ user confirms restore
→ revalidate active session equals captured active session
→ re-read current fingerprint equals load-time expected fingerprint
→ manager.restore(captured_session_id, detached candidate, expected fingerprint)
→ only restore_complete: retire request authority, refresh persistence-neutral UI
```

Foreign candidates are never imports and are rejected before command invocation.
If the active runtime changed between load and confirmation, the UI reports a
sanitized stale status and does not pass a new fingerprint; this prevents an old
candidate becoming arbitrary historical restore input. `session_mismatch`,
`stale_runtime`, rollback, and critical failures preserve current core and UI;
there is no partial UI reset or retry.

On `restore_complete`, retain session ID: restore is not rollover. Existing
persistence recovery covers store state/fingerprint plus applied ledger only;
the session collection and monotonic allocator are deliberately preserved and
must not be represented as restored data. The UI clears advice/presentation
derived from pre-restore runtime and retires the active request token only after
core success. This makes late pre-restore workers stale even though their session
ID matches. Failed restore leaves their request authority intact. UI selection is
not changed.

## File picker and UI policy

Later implementation may use `QFileDialog` only at explicit actions. Save
offers `.json` as the default extension; load accepts existing `.json` files.
The UI owns cancellation and overwrite confirmation; the command layer remains
the sole path validator and rejects invalid/directory/missing-parent targets.
Cancel maps to a deterministic non-error `cancelled` UI outcome and invokes no
command. Status messages use generic success/failure text, never raw path,
exception, envelope, state, secret, or token log. Actions are disabled when no
active session; load may be enabled independently only if the later UX chooses
validation-without-active-session.

Excluded: autosave, startup recovery, automatic restore, recent files, cloud,
cross-session import, session history, undo/redo, backup rotation, and provider
calls.

## Proposed executable contract tests

- `test_save_action_requires_active_session`,
  `test_save_action_invokes_explicit_command_once`,
  `test_save_is_non_mutating_for_state_sequence_allocator_and_ledger`,
  `test_save_cancel_is_non_error_and_invokes_no_command`,
  `test_save_failure_preserves_current_ui_and_core`, and
  `test_save_does_not_retire_current_worker_request`
  - assert detached command-start snapshot, unchanged active session/state/
    fingerprint/sequence/allocator/ledger/request token, and sanitized status.

- `test_load_action_returns_detached_candidate_without_runtime_mutation`,
  `test_load_cancel_invokes_no_command`,
  `test_invalid_load_candidate_is_sanitized_and_not_retained`,
  `test_foreign_session_candidate_does_not_roll_over_or_restore`,
  `test_load_candidate_does_not_change_battle_selection_or_advice`, and
  `test_load_candidate_is_retired_after_session_rollover`
  - assert no active-core/UI/request mutation and closure-only detached candidate.

- `test_restore_requires_explicit_loaded_candidate_and_confirmation`,
  `test_restore_revalidates_active_session_before_command`,
  `test_restore_rejects_foreign_session_candidate`,
  `test_restore_rejects_expected_fingerprint_mismatch`,
  `test_restore_success_refreshes_ui_after_core_commit`,
  `test_restore_failure_preserves_current_core_and_ui`,
  `test_restore_success_retires_pre_restore_worker_request`,
  `test_restore_success_suppresses_late_pre_restore_worker_result`,
  `test_restore_does_not_change_session_id`, and
  `test_restore_invokes_no_new_battle_rollover`
  - assert core store/ledger recovery result, preserved collection/allocator,
    post-success request retirement, and no partial reset on failure.

- `test_pending_candidate_is_detached`,
  `test_pending_candidate_cannot_be_mutated_into_restore_input`,
  `test_pending_candidate_is_retired_after_restore`,
  `test_pending_candidate_is_retired_after_new_battle`, and
  `test_stale_candidate_cannot_restore_after_runtime_change`
  - assert closure lifetime and load-time fingerprint gate.

- `test_file_dialog_cancel_is_deterministic`,
  `test_ui_does_not_duplicate_persistence_path_validation`,
  `test_status_messages_do_not_expose_raw_state_or_secret_data`,
  `test_persistence_ui_has_no_autosave_startup_import_or_undo_hooks`, and
  `test_save_load_restore_never_call_provider`
  - assert explicit-only UI and sanitized boundaries.

## Expected implementation scope

Expected production modification: `ui/main_window.py` only, using the existing
manager's bounded public `save/load/restore` delegation. No core seam, raw
component getter, or persistence-engine change is currently required. Expected
test file: `tests/test_v37_explicit_persistence_ui_boundary.py`. Documentation:
this file plus `docs/PROGRESS.md` and `docs/handoff_next_session_prompt_v1.9.md`.

Validation of the existing boundary contracts: focused persistence/session/UI
set `120 passed`; full offline suite `2945 passed, 2 deselected`. This is a
documentation-only design step, so compile is intentionally not run.

## Implemented v15.37 boundary

`ui/main_window.py` now adds a minimal `File` menu with explicit `Save Battle
State` and `Load Battle State` actions. Both actions are disabled until the
optional session manager has an active bundle and call only the existing bounded
manager `save/load/restore` methods; no raw runtime, commands, store, or
persistence getter was introduced.

Save opens an explicit `.json` chooser and, when a target already exists, an
explicit overwrite confirmation. A chooser or overwrite cancellation is a
sanitized non-error status and calls no command. A save neither changes runtime
state/fingerprint, collection, store sequence, allocator, ledger, nor active
request authority.

Load opens an explicit `.json` chooser and remains load-only. It captures the
active session ID and runtime fingerprint *before* command load, deep-copies the
validated `load_ready` envelope, rejects a foreign session before confirmation,
and gives the defensive copy only to `_present_loaded_candidate(...)`. The
candidate lives in that confirmation/restore call chain only; MainWindow has no
long-lived raw candidate field. Dialog cancellation, session rollover, stale
runtime detection, and completion retire it by returning from that call chain.

`_restore_loaded_candidate(...)` rechecks the manager identity, active session,
candidate session, and the **load-time** fingerprint before calling bounded
restore. It deliberately never substitutes a newly read fingerprint. Only
`restore_complete` retires existing advice request authority and resets derived
advice presentation; it does not cancel the worker/thread. A late pre-restore
success or error is therefore rejected by the pre-existing token guard while
normal cleanup remains eligible. Restore failure changes neither core state nor
request authority or advice presentation. Restore remains same-session only,
does not roll over, and does not restore collection or allocator state.

All persistence UI messages are generic and do not include raw JSON, state,
fingerprint, path, exception, secret, or token-log content. Autosave, startup
recovery, automatic restore, import, history/recent files, cloud sync, and
undo/redo remain excluded.

Implemented contract coverage is in
`tests/test_v37_explicit_persistence_ui_boundary.py`, including active-session
and cancel gates, command-call count/non-mutation, detached load candidate,
foreign-session rejection, confirmation, load-time CAS, success-only request
retirement, failure preservation, rollover rejection, and source-level excluded
feature checks.
