# v15.32 Persistence and Rollback Boundary

v15.32 introduces only a private, offline durability boundary for one recovery
unit: the detached `BattleStateStore` snapshot plus the coordinator's applied
canonical-observation ledger. It does not connect MainWindow, widgets,
autosave, startup restore, providers, networks, reducers, or replay policy.

## CAS boundary

Normal `BattleStateStore.compare_and_replace()` is unchanged in meaning. It
requires the expected session and base fingerprint, rejects stale writers, and
continues to reject a lower `last_applied_observation_sequence` with
`sequence_regression`. Durable restore uses that normal CAS, so it preserves
runtime monotonicity; it is not an arbitrary historical restore API.

`capture_rollback_snapshot()` and `compare_and_restore_snapshot()` are private
rollback-only APIs. A snapshot is process-local provenance captured immediately
before the target store CAS. Restore rollback supplies the fingerprint of the
just-applied target as `expected_current_fingerprint`; the API revalidates the
captured state/fingerprint and allows sequence regression only at that point.
It also requires one session. If another writer changed the target, it returns
`rollback_cas_conflict` without retrying or overwriting that writer. A foreign
session snapshot returns a sanitized rollback session-mismatch result, and a
tampered or malformed snapshot returns `invalid_rollback_snapshot`.

This rollback is persistence recovery after a failed ledger replacement. It is
not user-facing undo/redo, observation unapply, or arbitrary history replay.

## Envelope and validation

`ObservationReplayPersistence` exports a private schema-versioned envelope:

- session ID;
- detached store state and deterministic state fingerprint;
- sorted applied-observation entries with canonical copies and deterministic
  canonical fingerprints; and
- fixed private metadata.

There are no wall-clock timestamps, request tokens, or provider values in the
fingerprints. Export, validate, and load return detached copies and do not
mutate runtime state. Validation rejects unsupported schemas (no migration),
unexpected or missing top-level fields, bad nested shapes, state fingerprint
mismatch, canonical ledger fingerprint mismatch, and duplicate observation IDs
(both identical and conflicting duplicates). It also requires a store state
valid under the store contract, canonical observation identity/sequence/session
shape, and agreement between the envelope entry ID and canonical observation
ID. JSON load restores the state model's numeric slot-map key types before
fingerprint validation, so a loaded store state remains value-equal to the
runtime state that was saved.

Save serializes validated data to a sibling `.tmp` file and publishes with
`os.replace()`. Serialization, temporary-write, and replace failures return a
sanitized I/O status, preserve the old target bytes, and make best-effort temp
cleanup. Load/validation has no runtime mutation.

## Explicit restore and ledger atomicity

Restore accepts only a prior successful validation result and an explicit
current-store fingerprint. It is same-session only: a different-session
envelope returns `session_mismatch`; it never retags state or ledger entries.
After target store CAS, it replaces the ledger with one detached full-map swap.
No entry-by-entry repair is used.

The coordinator full-map replacement validates and deep-copies before its
single assignment. Thus injected replacement failure occurs before mutation:
the old ledger remains exact and old-ledger restoration cannot independently
fail. This is the documented test substitute for an old-ledger restoration
failure simulation. On such a failure after target store CAS, the persistence
service calls rollback-only CAS with the target envelope fingerprint. A success
returns `restore_rolled_back`; the target ledger has no leaked entries. If a
concurrent writer changed the store before rollback, it returns sanitized
`critical_restore_inconsistency`, preserves the concurrent state and old ledger,
and performs no retry or further mutation.

## Test coverage and remaining gaps

The v15.32 dedicated contract suite covers normal CAS monotonicity,
rollback-only success/conflict/session/tampering, full-map ledger failure,
same-session success and duplicate idempotency, deterministic/detached
envelopes, the validation corruption matrix, atomic-save failures, load-only
non-mutation, alias isolation, and cross-session restore rejection. Load-only
tests mutate loaded store/ledger copies and prove runtime state, fingerprint,
sequence, and full ledger map remain unchanged. Restore duplicate tests cover
both same-ID/same-canonical idempotency and same-ID/different-canonical conflict.

Remaining intentional gaps are UI save/load, autosave, startup restore,
cross-session import, database/cloud storage, user undo/redo, observation
unapply, arbitrary historical restore, and provider integration. Provider and
network call budget for this boundary is zero.
