# v15.31 Runtime Reducer/Store Integration Gate

`ObservationReplayCoordinator` is a private, process-local preview/apply seam. It consumes a detached collection snapshot and `BattleStateStore` snapshot, builds `build_replay_plan`, uses detached `execute_atomic_transition`, and calls store CAS only from explicit `apply_confirmed_observations`.

The store supplies `read_snapshot(session_id)` and fingerprint-based `compare_and_replace`; reducer execution is atomic and preserves Q12. Replay currently maps exact HP transition, switch, and faint to candidate effects. Damage-only is evidence-only and never infers HP; used move is unsupported by the current replay policy.

Preview never changes store, collection, UI, or ledger. Apply records accepted `(session_id, observation_id)` content only after successful CAS in a private process-local ledger. Same content is already applied; changed content conflicts. Session mismatch, invalid plans, semantic failures, and stale CAS return sanitized results without retry or partial commit. Turn remains evidence only and is not inferred or committed to `BattleState.turn_number`.

No MainWindow/UI wiring, persistence, rollback, provider call, prompt/schema change, reducer auto-apply, or Q12/modifier integration is included. Provider budget is zero.
