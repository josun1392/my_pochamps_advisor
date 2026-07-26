# v15.33 Session-Bound Replay Runtime Owner

## Evidence and decision

The current observation path is deliberately split. `MainWindow` creates the
single live `ObservationCollection` at `ui/main_window.py:380`, resets it in
`_begin_new_battle_session()` at lines 778-803, and captures its detached
snapshot at lines 1138-1156 for `StructuredRecommendationWorker`. The worker
deep-copies that mapping, and the request path preserves it only as private
`TurnSnapshot.current_state.canonical_observation_collection`
(`llm/advisor_turn_snapshot.py:960-969`). This request handoff has no store
mutation authority.

In contrast, repository-wide construction search finds `BattleStateStore`,
`ObservationReplayCoordinator`, and `ObservationReplayPersistence` composed
only in v15.31/v15.32 tests. There is no production constructor, caller, UI
connection, worker connection, save/load/restore command, autosave hook, or
startup hook. `ObservationReplayPersistence` is stateless and exposes only
explicit service methods. `ObservationReplayCoordinator` owns its process-local
applied ledger; `BattleStateStore` owns the current detached state and its CAS
lock. This missing composition/lifetime owner must be defined before a command
boundary can safely invoke persistence or before UI can be considered.

The requested v15.30 and v15.31 spike filenames are absent. Their actual
contracts are represented by `docs/PROGRESS.md`,
`docs/advisor_payload_contract.md`,
`docs/handoff_next_session_prompt_v1.9.md`, and the corresponding tests. The
code and tests are authoritative.

## Recommended scope

### Title

`v15.33 Session-Bound Replay Runtime Owner`

### Problem

Store, coordinator, and persistence are individually bounded but have no
production lifetime owner. Consequently no caller can prove that preview,
apply, export, or future explicit persistence commands refer to one matching
session-scoped recovery unit. Connecting any one of them directly to
`MainWindow`, a request worker, or startup would skip that authority boundary.

### In scope

Define and implement one private, runtime-neutral owner (proposed name
`ObservationReplayRuntime`) that is constructed from one valid initial
`battle-state-v1` mapping and owns exactly:

- one `BattleStateStore`;
- one `ObservationReplayCoordinator` bound to that store; and
- one stateless `ObservationReplayPersistence` helper.

It exposes detached, explicit delegation for store read, coordinator preview,
coordinator apply, and persistence envelope export/validate only. It records
the session from the initialized store; callers may not supply a different
session to retag the runtime. The owner does not create an initial reducer state
from UI data and does not execute save/load/restore commands.

### Out of scope

- `MainWindow`, widgets, buttons, or file pickers;
- worker/request/provider payload connections;
- autosave, startup loading, automatic restore, or process-exit persistence;
- persistence `save`, `load`, or `restore` execution through the new owner;
- session rollover/reset, cross-session import, cloud/database storage;
- user-facing undo/redo or observation unapply; and
- provider/network calls.

### Authority and contract

The caller that explicitly constructs the owner supplies a detached valid
initial state. The owner takes a defensive copy; `BattleStateStore` remains the
only state mutation authority, and coordinator apply remains the only normal
observation-commit authority. The coordinator remains the only ledger mutation
authority. Sequence monotonicity and state fingerprints remain store-owned;
canonical observation fingerprints remain persistence-owned.

The proposed constructor rejects invalid initial state with a sanitized
`invalid_initial_state` result or a documented constructor exception boundary
(choose one consistently in implementation; the preferred contract is a
`create(initial_state) -> {status, runtime}` factory to avoid raw exceptions).
All public owner results and returned snapshots/envelopes are detached.

`preview(observation_snapshot)` is read-only and delegates only after exact
same-session validation. `apply(observation_snapshot)` is explicit and returns
the coordinator's deterministic result; it never applies during construction,
read, preview, export, or validation. `export_envelope()` uses the owner's
session rather than a caller-provided retagging value. `validate_envelope()` is
detached/non-mutating and does not imply restore authority.

No new CAS is invented: apply delegates to store fingerprint CAS. A stale
owner snapshot therefore receives the coordinator's `cas_conflict`; lower
sequence stays `sequence_regression` inside normal CAS. v15.32 rollback-only
CAS remains exclusively persistence recovery and is not exposed as owner undo.

### Expected files for implementation

- Production: `llm/advisor_observation_replay_runtime.py` (new); no UI or
  worker production files.
- Tests: `tests/test_v33_session_bound_replay_runtime_owner.py` (new).
- Documentation: this spike plus `docs/PROGRESS.md` and
  `docs/handoff_next_session_prompt_v1.9.md`.

No `advisor_payload_contract.md` change is expected: this owner changes no
provider-visible payload or request schema.

### Completion criteria

One owner has one immutable session identity, detached construction/read/
preview/export/validate boundaries, explicit apply-only mutation, no ledger or
state partial mutation on failures, and inherited CAS/idempotency/session
semantics. Tests must prove no UI, worker, provider, network, save/load/restore,
autosave, or startup invocation exists.

### Deferred follow-up

The next distinct boundary after v15.33 may design an explicit persistence
command owner/caller using this runtime. UI save/load, autosave, startup
recovery, session rollover, cross-session import, and user undo remain separate
decisions.

## Candidate comparison

| Candidate | Current state | Ready dependencies | Missing contract | Risk | v15.33 suitability |
| --- | --- | --- | --- | --- | --- |
| Runtime ownership wiring | No production owner for store/coordinator/persistence | v15.24, v15.31, v15.32 detached APIs | Single session lifetime and delegation authority | Low if runtime-neutral; avoids UI race | **Recommended** |
| Explicit persistence command | Service methods exist, no caller | Validated envelope and recovery rollback | Owner identity and command authority | Could save/restore wrong lifetime | Defer until owner exists |
| Session lifecycle/reset | UI collection resets only | UI session IDs and store start API | Initial-state source and owner rollover policy | Sequence/ledger cross-session leakage | Defer |
| Request-worker handoff integration | Collection snapshot reaches worker | Detached snapshot contract | Store owner and apply authority | Worker/provider response could mutate | Defer |
| UI save/load | No connection | Persistence service | Owner plus user command contract | UI/file/session errors | Defer |
| Startup recovery | No connection | Detached load/validate | Startup session and conflict policy | Implicit mutation | Defer |
| Autosave | No connection | Atomic save primitive | Command policy and lifecycle owner | I/O timing/stale state | Defer |
| Cross-session import | Explicitly unsupported | None | Retag/migration/identity policy | Session integrity loss | Reject/defer |
| User undo/redo | Explicitly unsupported | Rollback-only recovery CAS | Domain-history semantics | Misuse of persistence rollback | Reject/defer |

## Proposed contract test inventory

- `test_runtime_factory_creates_one_detached_same_session_owner`
  - scenario: valid initial state creates the private owner.
  - initial state: valid `battle-state-v1`, session `s`, empty ledger.
  - action: `create(state)` then read/export.
  - expected state/fingerprint/sequence: equal to initial detached state and its store fingerprint/sequence.
  - expected ledger: empty detached map.
  - expected status/error: `ready`.
  - forbidden side effect: no apply, UI, worker, persistence I/O, provider, or network call.

- `test_runtime_preview_requires_explicit_apply_and_is_non_mutating`
  - scenario: eligible same-session observations are previewed.
  - initial state: ready owner with unapplied observation.
  - action: `preview(snapshot)` only.
  - expected state/fingerprint/sequence/ledger: all unchanged.
  - expected status/error: delegated `preview_ready`.
  - forbidden side effect: implicit store CAS or ledger update.

- `test_runtime_apply_commits_once_and_duplicate_is_idempotent`
  - scenario: explicit apply followed by same canonical input.
  - initial state: ready owner with one eligible observation.
  - action: `apply(snapshot)` twice.
  - expected state/fingerprint/sequence: first committed result, then unchanged.
  - expected ledger: one canonical entry, unchanged on second call.
  - expected status/error: `applied`, then `already_applied`.
  - forbidden side effect: duplicate state transition or sequence increment.

- `test_runtime_rejects_cross_session_without_retagging`
  - scenario: foreign observation snapshot reaches owner.
  - initial state: owner session `s`.
  - action: preview/apply snapshot for `other`.
  - expected state/fingerprint/sequence/ledger: unchanged.
  - expected status/error: `session_mismatch`.
  - forbidden side effect: session retagging, store replacement, or ledger namespace creation.

- `test_runtime_apply_preserves_stale_cas_and_concurrent_writer_protection`
  - scenario: preview becomes stale after a direct authorized store writer.
  - initial state: owner session `s`, eligible observation.
  - action: obtain preview, advance store through its normal CAS, then apply stale input.
  - expected state/fingerprint/sequence: concurrent state remains exact.
  - expected ledger: no target entry leaks.
  - expected status/error: `cas_conflict`.
  - forbidden side effect: retry or overwrite of concurrent state.

- `test_runtime_rejects_conflicting_duplicate_without_partial_mutation`
  - scenario: same observation ID has altered canonical content after apply.
  - initial state: owner with the original entry committed.
  - action: apply altered snapshot.
  - expected state/fingerprint/sequence/ledger: all remain at original committed values.
  - expected status/error: `transition_invalid` with conflict evidence.
  - forbidden side effect: replacing original ledger entry or partial store mutation.

- `test_runtime_returns_detached_read_preview_and_envelope_results`
  - scenario: caller mutates returned read, preview, and envelope mappings.
  - initial state: ready owner with canonical ledger entry.
  - action: mutate each returned mapping.
  - expected state/fingerprint/sequence/ledger: owner values remain exact.
  - expected status/error: ready/preview/export results remain detached.
  - forbidden side effect: mutable internal reference exposure.

- `test_runtime_factory_rejects_invalid_initial_shape_safely`
  - scenario: invalid or cross-labeled initial state is supplied.
  - initial state: malformed mapping.
  - action: factory creation.
  - expected state/fingerprint/sequence/ledger: no runtime instance or mutation.
  - expected status/error: `invalid_initial_state`.
  - forbidden side effect: partial component construction or raw traceback.

- `test_runtime_export_and_validate_are_explicit_non_mutating_persistence_seams`
  - scenario: export then validate a valid/tampered envelope.
  - initial state: ready owner with state and ledger.
  - action: explicit export/validate only.
  - expected state/fingerprint/sequence/ledger: unchanged in both paths.
  - expected status/error: `ready` / `load_ready` or sanitized validation status.
  - forbidden side effect: save/load/restore, rollback, or runtime mutation.

- `test_runtime_has_no_ui_worker_or_provider_entry_points`
  - scenario: static ownership surface inspection.
  - initial state: source tree.
  - action: inspect imports/call sites for `ui`, worker, provider, and network modules.
  - expected state/fingerprint/sequence/ledger: not applicable because no runtime is constructed.
  - expected status/error: no prohibited integration symbols.
  - forbidden side effect: any UI, worker, provider, network, autosave, startup, or persistence-command connection.

The lifecycle-race category is represented by stale CAS because the proposed
owner intentionally has no reset/rollover method. A reset race cannot be
specified safely until a separate session-lifecycle boundary defines the source
of the new valid initial state. Persistence recovery interaction is limited to
export/validate because save/load/restore command authority is intentionally
not introduced in this scope.
