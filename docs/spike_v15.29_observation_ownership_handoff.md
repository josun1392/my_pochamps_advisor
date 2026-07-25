# v15.29 Observation Ownership and TurnSnapshot Handoff

`MainWindow` privately owns the single live `ObservationCollection` for its
current battle session. The observed-damage confirmation path is its only
v15.29 producer: after the existing amount-only confirmation is bound to the
current active owners, the canonical confirmation result is added to that
collection. This does not apply evidence to store/reducer/UI current state.

`build_turn_snapshot_from_battle_input(..., observation_snapshot=...)` accepts
one detached collection snapshot. Only a `ready` snapshot whose session matches
`current_state_session_id` is copied to the private
`current_state.canonical_observation_collection` field. Absent or mismatched
input is omitted without retagging or partial evidence. The builder never reads
the live collection, allocates sequences, or mutates input.

Immediately before a structured request is started, `MainWindow` captures a
detached collection snapshot using the existing battle session ID and passes
that frozen mapping to `StructuredRecommendationWorker`. The worker never
receives the live collection; it forwards the detached mapping through the
structured client and candidate preparation to
`build_request_start_recommendation_snapshot(...)`.

`_begin_new_battle_session()` resets the collection with the newly allocated
session ID. Request tokens remain request/stale-response identifiers, not
session or observation identity. Store/reducer/UI state/Q12/provider schemas
are unchanged; this work performs no provider call.
