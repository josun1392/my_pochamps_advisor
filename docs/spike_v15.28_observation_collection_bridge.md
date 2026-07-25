# v15.28 Structured Observation Collection Bridge

`ObservationCollection` is a private, single-session evidence buffer. It accepts
only `confirmed` canonical observations with valid identity, positive producer
sequence, supported kind, and matching session. It never stores raw confirmation
results, allocates/reorders sequences, or applies reducer/store/UI state.

Same ID and content is a duplicate no-op; same ID with different content is a
conflict; different IDs are distinct occurrences. Snapshots are deep-copied and
ordered by `(observation_sequence, observation_id)`; repeated reads do not mutate
the collection. Explicit `start_new_session` clears the current namespace without
retagging prior data, and frozen snapshots remain detached.

Current inventory: confirmation boundary produces canonical damage, used-move,
HP-transition, switch, and faint evidence. This bridge stores all five. The
production TurnSnapshot/UI call-site handoff is deliberately not connected: no
existing owner currently injects the new collection without widening UI state
scope. That remains a gap. Provider/public/legacy schemas, Q12, store, reducer,
and UI state are unchanged. Provider budget: 0.
