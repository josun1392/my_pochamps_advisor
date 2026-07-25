# v15.21 Reducer State-Model and Transition Contract

## Ownership inventory

`MainWindow` state is mutable UI input. `TurnSnapshot.current_state` is frozen
request evidence. Repository species/move data is immutable metadata. Reducer
state is a separate detached future model; no UI or snapshot mapping mutates it.

The `battle-state-v1` base-state schema has `session_id`, `state_version`,
`self_side`, `opponent_side`, `field`, `last_applied_observation_sequence`, and
limitations. Sides hold active slot, slot/identity Pokémon map, and side
conditions. Pokémon candidates hold exact HP only when known, condition, known
item/ability, stages, fainted/availability; absent data remains unknown rather
than zero/false. Field holds weather, terrain, and effects with unknown duration.

## Transition dry-run

`validate_atomic_transition(base_state, replay_plan, expected_session_id)` is a
pure immutable readiness validator. It returns ready, conflict, invalid base or
plan, unsupported version, or no reducer steps. Planned effects map to target
fields only: condition, known item, weather/terrain, side conditions, active
slot, and fainted state. No value is applied.

Session/version mismatch blocks. Unknown state never silently overwrites: exact
HP, remove/end/consume semantic checks remain a required future reducer policy.
Full atomic validation is required before any future mutation; prefix, best
effort, rollback, replay execution, Q12/modifier application, and UI updates are
out of scope. Provider budget is 0.
