# v15.34 Explicit Persistence Command Boundary

## Current surface and authority gap

`ObservationReplayRuntime` (`llm/advisor_observation_replay_runtime.py`) is
created only by `ObservationReplayRuntime.create(initial_state)`. It owns one
private `BattleStateStore`, `ObservationReplayCoordinator`, and
`ObservationReplayPersistence`, fixes `session_id` for its lifetime, and
publicly exposes only `read_state`, `read_applied_ledger`, `preview`, `apply`,
`export_envelope`, and `validate_envelope`. It exposes no raw helper and no
save/load/restore command.

`ObservationReplayPersistence` (`llm/advisor_observation_replay_persistence.py`)
already supplies the primitive operations:

- `export_envelope(store, coordinator, session_id)`: detached deterministic
  store state/fingerprint plus sorted canonical ledger;
- `validate(value)`: detached schema, store fingerprint, ledger identity, and
  canonical fingerprint validation;
- `save(path, envelope)`: validate, sibling `.tmp` write, `os.replace`, and
  best-effort temp cleanup; returns `saved`, `invalid_envelope`, or `io_error`;
- `load(path)`: JSON read plus validation; returns `file_not_found`,
  `invalid_json`, `io_error`, or validator status; and
- `restore(store, coordinator, candidate, expected_current_fingerprint)`:
  same-session normal CAS followed by full-map ledger replacement, with
  `restored`, `restore_rolled_back`, or `critical_restore_inconsistency`.

The v15.32 recovery unit is store state/fingerprint, applied ledger,
session ID, and canonical observation ID/fingerprint. Restore captures a
pre-target store rollback snapshot; its rollback CAS expects the applied target
fingerprint and never overwrites a concurrent writer. The coordinator's ledger
replacement fails before its full-map assignment, so old ledger content remains
exact on that injected failure path.

No production search result constructs the persistence service outside runtime
or calls save/load/restore. There is consequently no authority for path I/O,
load-only ownership, explicit restore approval, stale-runtime gating, or
sanitized command-level results. UI, workers, startup, and autosave are also
not callers.

## Candidate comparison

| Candidate | Ownership | Session safety | I/O isolation | Encapsulation | Testability | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| A. Add runtime methods | One owner, but runtime core becomes I/O surface | Good | Poor | Expands every runtime's public API | Good | Defer |
| B. Runtime-bound command service | One service bound to one runtime identity/session | Strong | Good | Raw components remain private | Strong | **Recommended** |
| C. Stateless free functions | Caller combines context | Weak | Good | Enables wrong component combinations | Moderate | Reject |

## Recommended v15.34 contract

### Implemented command owner

`v15.34 Runtime-Bound Explicit Persistence Commands`

`ObservationReplayPersistenceCommands` is implemented in
`llm/advisor_observation_replay_persistence_commands.py`. Its factory accepts
exactly one `ObservationReplayRuntime`, records that runtime object identity and
immutable session ID, and may not be rebound to another runtime. It accepts no
raw store, coordinator, or persistence helper. A minimal runtime-private
`_persistence_command_context()` seam lets this service invoke its matching helper
without making raw components public. The command service must not outlive its
runtime in a usable state: every command verifies the captured runtime identity
and session before acting and returns sanitized `stale_runtime` if that binding
cannot be verified.

### Save

`save(path)` accepts only `str` or `os.PathLike` target paths. At command start
it obtains one detached runtime envelope, then passes that exact envelope to the
existing atomic persistence save primitive. The command does not lock, pause,
or retry runtime apply. Therefore an apply that completes after export may
change the runtime but not the file: save has explicit snapshot-at-command-start
semantics.

The command maps primitive `saved` success to `save_complete` and preserves a sanitized
primitive failure (`invalid_envelope` or `io_error`) without raw OS text or raw
path. It rejects empty/non-path input, directory targets, and missing parent
directories as `invalid_path` before save. It never creates parents, rotates
backups, selects default locations, or exposes an absolute path in results.
The primitive retains sibling temporary output, existing-target preservation,
atomic `os.replace`, and best-effort cleanup. Existing local symlink semantics
are left to the OS; symlink hardening is not introduced in this boundary.

### Load-only

`load(path)` is explicit and never restores. It performs path validation, then
delegates to the primitive load/validate path and returns a detached candidate.
It has runtime mutation count zero for every outcome. A valid foreign-session
envelope is intentionally allowed to become a detached `load_ready` candidate:
session admission belongs exclusively to explicit restore. Missing files map to
`not_found`; permission/other OS failures remain sanitized `io_error` unless
the primitive is minimally extended to distinguish `permission_denied` without
leaking platform text. Corruption retains existing exact validator statuses.

### Explicit restore

`restore(candidate, expected_runtime_fingerprint)` is the only command mutation
operation. It requires a prior detached `load_ready` candidate, an exact
nonempty expected current runtime fingerprint, and candidate session equal to
the command-bound runtime session. Before invoking v15.32 restore it reads the
current runtime fingerprint and compares it to the caller-provided expected
fingerprint. Mismatch returns `stale_runtime` with no store or ledger mutation
and without invoking the persistence restore primitive.

After that gate, the service delegates to v15.32 restore using the same expected
fingerprint. It maps `restored` to `restore_complete`, preserves
`restore_rolled_back` and `critical_restore_inconsistency`, and passes through
sanitized session/validation conflicts. It never retries, retags, exposes
rollback APIs, or treats a partial state as success. This is recovery-unit
restore, not undo or arbitrary historical replacement. The explicit fingerprint
gate distinguishes a caller-approved recovery point from a stale loaded
envelope; same session alone is insufficient.

### Explicit invocation and excluded integration

Command construction does no I/O or restore. Runtime construction, read,
preview, apply, export, and validation do not invoke commands. There is no UI,
file picker, worker, provider, network, timer, autosave, startup hook, session
rollover, cross-session import, or user undo/redo connection.

### Actual implementation inventory

- New production: `llm/advisor_observation_replay_persistence_commands.py`.
- New tests: `tests/test_v34_explicit_persistence_command_boundary.py` (30
  focused cases including parameterized path and corruption matrices).
- Existing runtime change: private `_persistence_command_context()` only; no
  public raw-component accessor.
- Persistence change: none. Permission and other OS failures retain existing
  sanitized `io_error`; no separate permission status was added.
- Documentation: this spike, `docs/PROGRESS.md`, and
  `docs/handoff_next_session_prompt_v1.9.md`.

## Proposed executable contract tests

This inventory is implemented by the focused v15.34 suite. It also proves
constructor I/O/restore count zero, detached/sanitized results, and exclusion of
UI, workers, provider clients, autosave, startup, rollback, history, undo,
reset, and rollover surface.

- `test_explicit_save_writes_deterministic_snapshot_without_runtime_mutation`
  - initial runtime: same-session state and ledger.
  - filesystem setup: writable explicit target.
  - command: `save(path)`.
  - expected runtime state/fingerprint/sequence/ledger: exact before values.
  - expected file/envelope: deterministic command-start envelope bytes.
  - expected status/error: `save_complete`.
  - forbidden side effect: apply, UI, provider, or network.

- `test_save_uses_command_start_snapshot_when_runtime_changes_concurrently`
  - initial runtime: unapplied observation.
  - filesystem setup: injected pause after export before write.
  - command: concurrent apply during save.
  - expected runtime: post-apply state; file retains pre-apply envelope.
  - expected status/error: `save_complete` without retry/re-export.
  - forbidden side effect: runtime lock or lost apply.

- `test_save_failure_preserves_existing_target` and
  `test_save_replace_failure_cleans_temp_and_preserves_target`
  - initial runtime: stable state/ledger.
  - filesystem setup: existing bytes, temporary-write or replace failure.
  - command: save.
  - expected runtime/fingerprint/sequence/ledger: unchanged.
  - expected file/envelope: old bytes exact; temp absent after replace failure.
  - expected status/error: sanitized `io_error`.
  - forbidden side effect: target truncation or raw path/exception output.

- `test_save_rejects_invalid_path_without_runtime_mutation` and
  `test_save_is_never_invoked_implicitly_by_runtime_creation_preview_or_apply`
  - initial runtime: ready.
  - filesystem setup: empty, directory, missing-parent, and invalid path cases.
  - command: explicit save or non-command runtime operations.
  - expected runtime/fingerprint/sequence/ledger: unchanged.
  - expected file/envelope: no output or write call.
  - expected status/error: `invalid_path` for explicit invalid paths.
  - forbidden side effect: parent creation or implicit I/O.

- `test_load_returns_detached_validated_envelope_without_runtime_mutation`,
  `test_load_corruption_matrix_is_non_mutating`, and
  `test_load_missing_or_unreadable_file_returns_sanitized_status`
  - initial runtime: ready state/ledger.
  - filesystem setup: valid, corrupt, missing, and injected unreadable files.
  - command: load only.
  - expected runtime/fingerprint/sequence/ledger: exact before values.
  - expected file/envelope: detached valid candidate or unchanged source bytes.
  - expected status/error: `load_ready`, existing corruption status, `not_found`,
    or sanitized `io_error`.
  - forbidden side effect: restore, retag, raw OS error/path.

- `test_load_foreign_session_envelope_is_detached_and_does_not_restore` and
  `test_mutating_loaded_envelope_does_not_alias_runtime_or_file_state`
  - initial runtime: session `s`.
  - filesystem setup: valid foreign envelope and source bytes.
  - command: load then mutate returned candidate.
  - expected runtime/fingerprint/sequence/ledger: unchanged, session remains `s`.
  - expected file/envelope: source bytes unchanged; candidate detached.
  - expected status/error: `load_ready`.
  - forbidden side effect: automatic restore or retagging.

- `test_explicit_restore_applies_same_session_recovery_unit`
  - initial runtime: same session but distinct current state/ledger.
  - filesystem setup: validated target candidate.
  - command: restore with current fingerprint.
  - expected runtime/fingerprint/sequence/ledger: target envelope exact full-map values.
  - expected status/error: `restore_complete`.
  - forbidden side effect: partial ledger replacement.

- `test_restore_rejects_cross_session_without_retagging` and
  `test_restore_rejects_stale_expected_runtime_fingerprint`
  - initial runtime: session `s` and captured before values.
  - filesystem setup: foreign candidate or valid same-session candidate plus stale fingerprint.
  - command: explicit restore.
  - expected runtime/fingerprint/sequence/ledger: exact before values.
  - expected status/error: `session_mismatch` or `stale_runtime`.
  - forbidden side effect: primitive restore call, retagging, or mutation.

- `test_restore_ledger_failure_rolls_store_back`,
  `test_restore_concurrent_writer_conflict_preserves_writer`, and
  `test_restore_critical_inconsistency_is_not_reported_as_success`
  - initial runtime: old state/ledger with target candidate.
  - filesystem setup: no further I/O after candidate load.
  - command: injected ledger failure, optionally concurrent normal CAS.
  - expected runtime/fingerprint/sequence/ledger: old recovery-unit restoration
    or exact concurrent-writer preservation.
  - expected status/error: `restore_rolled_back` or
    `critical_restore_inconsistency`, never `restore_complete`.
  - forbidden side effect: retry or success masking.

- `test_restore_duplicate_ledger_semantics_survive_command_boundary` and
  `test_restore_is_not_available_as_undo_or_arbitrary_history_api`
  - initial runtime: restored target with canonical ledger.
  - filesystem setup: validated candidate.
  - command: apply same/altered observation; inspect public command API.
  - expected runtime/fingerprint/sequence/ledger: duplicate is idempotent,
    altered duplicate conflicts; no history/unapply surface.
  - expected status/error: coordinator's `already_applied` / conflict status.
  - forbidden side effect: rollback API or arbitrary historical selection.

- `test_command_owner_does_not_expose_raw_runtime_components`,
  `test_command_boundary_has_no_ui_worker_provider_autosave_or_startup_hooks`,
  `test_command_constructor_performs_no_io_or_restore`, and
  `test_command_results_are_detached_and_sanitized`
  - initial runtime: ready.
  - filesystem setup: monkeypatched primitive seams.
  - command: construct/read command results and inspect API/import surface.
  - expected runtime/fingerprint/sequence/ledger: unchanged unless explicit restore.
  - expected file/envelope: no constructor I/O; detached results.
  - expected status/error: sanitized deterministic values.
  - forbidden side effect: raw components, UI/worker/provider import, timer,
    startup hook, raw error/path/envelope output.
