# v15.23 Atomic Reducer Execution Contract

## Purpose

`execute_atomic_transition` is a pure optimistic-concurrency baseline on top
of v15.22 `project_atomic_transition`. It re-runs semantic projection at
execution time and returns a detached committed state only after the complete
batch validates. It does not replace runtime/UI state or persist anything.

## Existing execution inventory

| Source/helper | Ownership | Mutable / side effects | Atomic / reusable | Gap |
|---|---|---|---|---|
| `ui.main_window` capture paths | UI | UI-owned copied input | not reducer-atomic / no | never called here |
| `advisor_turn_snapshot.build_turn_snapshot_from_battle_input` | snapshot | detached capture | immutable snapshot / contextual only | no committed reducer state |
| `advisor_replay_policy.build_replay_plan` | policy | pure deepcopy | planning only / yes | no semantic application |
| `validate_atomic_transition` | state model | pure | schema-only / yes | no projection |
| `project_atomic_transition` | state model | pure temporary copy | full semantic dry run / yes | no commit receipt |

No persistence, save/load, transaction abstraction, or runtime reducer commit
path is reused.

## Contract

Input is base state, replay plan, expected session/version, and optional base
fingerprint. `state_fingerprint` uses sorted canonical JSON plus SHA-256 and
excludes executor receipt metadata; dict insertion order and object identity do
not affect it. `replay_batch_fingerprint` deterministically covers session,
replay-policy version, and ordered planned steps. Neither digest is public or
provider-visible; SHA-256 collision resistance is practical, not proof.

The executor validates session/version, calculates and checks the base digest,
rejects sequence overlap, then reruns v15.22 projection. Success returns
`committed_state`, both state fingerprints, batch fingerprint, applied IDs, and
minimal internal provenance. A supplied stale digest returns `stale_base_state`
before projection. A batch wholly at or below `last_applied_observation_sequence`
is `already_applied` only when its stored batch digest matches; partial overlap
is blocked and never silently skipped.

| Status | Committed state | Base mutation | Behavior |
|---|---|---|---|
| `committed` | present | none | detached atomic result |
| `stale_base_state` | none | none | caller must re-project/retry |
| `already_applied` | none | none | no double application |
| semantic/plan/session/version/no-step failure | none | none | no partial execution |

Committed metadata is private: last batch digest, source replay-policy version,
and a compact commit provenance summary. Every result is deep-copied. Session
retagging/migration are forbidden; version mismatch is unsupported.

## Boundaries and gaps

The executor applies no Q12, modifier, candidate ranking, provider payload,
legacy prompt, public confirmation payload, UI state, global state, persistence,
rollback, Turn Engine, or network call. Tests cover successful parity, canonical
fingerprints, stale state, already-applied and overlap behavior, session/version,
conflict/no-step handling, alias isolation, and Q12/ranking non-application.
Provider budget: 0.

Remaining gaps are runtime state integration, persistence, rollback execution,
trusted lifecycle producers, Turn Engine, and modifier integration.
