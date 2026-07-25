# v15.30 Trusted Turn-Number Producer

## Purpose

v15.30 adds a private, session-local trusted turn grouping identity. It does not infer turns from requests, sequences, clicks, damage, logs, time, metadata, or provider output.

## Repository revalidation

`MainWindow` already owns battle-session identity, an independent observation sequence, and an independent advice-request token. Its only actual UI-backed canonical producer is observed damage. `LifecycleConfirmationBoundary` exposes used-move, exact-HP-transition, switch, and faint producers only as a contract/fixture seam. Existing battle counters describe move mechanics, not a battle turn. Existing item-event `turn` values are event metadata, not current turn ownership.

## Owner and lifecycle

`MainWindow._current_trusted_turn_number` is the private owner. Initial and new-battle state is `None` (unavailable); no battle-start turn 1 is assumed. `set_current_turn_number()` accepts only `None` or a positive non-bool integer. `advance_turn()` advances only an already explicit value and rejects unavailable state rather than inventing turn 1. Advice requests, snapshot reads, confirmations, duplicate checks, and worker responses never advance it.

## Producer and snapshot handoff

Observed damage reads the current trusted value without mutating it. The contract-only lifecycle producer accepts the same optional value and validates it. `ObservationCollection` accepts only `None` or a positive non-bool integer and preserves that value for duplicate/conflict comparison.

Immediately before structured worker start, MainWindow creates a detached `trusted_turn_context` with the matching session. It is forwarded through the worker and preparation boundary into private `TurnSnapshot.current_state`. Unavailable context remains explicit with `turn_number: None`. It is not a `BattleState.turn_number`, public provider schema, or prompt addition.

## Identity separation

| Identity | Meaning |
| --- | --- |
| Session ID | one battle lifecycle |
| Turn number | explicit grouping within that session |
| Observation sequence | total event order within that session |
| Observation ID | event identity |
| Request token | async advice request/stale-response identity |

Battle counters and consecutive-use counts have no turn-number authority.

## Non-goals and gaps

There is no turn-number UI control yet. Used-move, HP-transition, switch, and faint have no MainWindow call site. No reducer/replay/store execution, UI battle state mutation, persistence, rollback, turn engine, Q12, modifier, provider, or network integration is performed. Provider budget is zero.

## Tests

The v15.30 contract covers initial unavailable state, validation, explicit advance, request/counter separation, observation sequence separation, old observation isolation, new-battle reset, collection validation, lifecycle duplicate/conflict behavior, and detached TurnSnapshot context.
