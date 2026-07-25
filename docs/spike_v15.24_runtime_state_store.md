# v15.24 Runtime State Ownership and Atomic Replacement

## Purpose and ownership inventory

`BattleStateStore` is the sole process-local owner of the current committed
`battle-state-v1` namespace. It follows v15.23's detached executor; it is not
connected to `MainWindow`, persistence, or a global singleton.

| State/source | Current owner | Mutable/thread access | Desired owner | Gap |
|---|---|---|---|---|
| `MainWindow` copied battle input | UI | UI/worker capture boundary | UI remains owner | no reducer connection |
| TurnSnapshot | snapshot builder | detached immutable copy | snapshot builder | not committed runtime state |
| executor committed state | caller | detached result | `BattleStateStore` | caller must CAS it |
| provider worker/request token | worker lifecycle | worker-specific | unchanged | token is not session ID |

## API and CAS

`read_snapshot(session_id=None)` returns a detached state, session, and
fingerprint, or sanitized `uninitialized`/`session_mismatch`. The constructor
accepts only a valid explicit state; it never invents Pokémon, HP, conditions,
or a session.

`compare_and_replace(committed_state, expected_session_id,
expected_base_fingerprint)` computes the current fingerprint and replaces only
if session and digest match. Results are `replaced`, `stale_state`,
`already_current`, `session_mismatch`, `unsupported_state_version`,
`invalid_committed_state`, `sequence_regression`, or `uninitialized`.

| Status | Store mutation | Snapshot | Caller action |
|---|---|---|---|
| `replaced` | new detached state | returned | continue |
| `already_current` | none | current copy | no-op |
| `stale_state` | none | none | read/replan/re-execute |
| session/version/shape/sequence failure | none | none | repair input |

Sequences must advance. Equal sequence with a different state and any backwards
sequence are rejected; missing sequence is never generated. The caller performs
planning/execution outside the lock, so executor success alone never overrides a
state replaced in the meantime.

## Session and threading

`start_new_session(initial_state, new_session_id)` is explicit and replaces the
single current namespace with a deep copy. No history is persisted; callers may
retain previously returned detached snapshots. Session IDs are never derived
from request tokens.

An internal standard-library `RLock` covers only read/CAS/new-session copying,
fingerprinting, and assignment. It provides thread-safe store operations, not a
UI-thread, provider, callback, or persistence transaction guarantee. No UI or
provider call is made while locked.

## Boundaries

The intended flow is `read → plan/project/execute externally → CAS replace`.
Store replacement does not recalculate Q12, rerank candidates, apply modifiers,
emit UI signals, write files, persist state, undo/rollback, or change provider,
legacy, or public-confirmation schemas. Provider budget: 0.

Tests cover initialization, detached aliases, CAS/stale writers, session/version
and sequence boundaries, explicit new sessions, executor parity, and Q12/ranking
non-application. Remaining work is explicit MainWindow ownership integration,
persistence, rollback/undo, lifecycle producers, Turn Engine, and modifiers.
