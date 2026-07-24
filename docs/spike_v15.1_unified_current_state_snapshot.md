# v15.1 Unified Current-State Snapshot

## Purpose and v15.0 baseline

v15.0 froze active Pokémon identity and selectable moves. v15.1 extends the
same `TurnSnapshot` with a deeply frozen `current_state` mapping so structured
preparation and deterministic candidate evaluation use one request-start source.
No provider adapter, turn transition, or damage formula changed. Provider
budget remains 0.

## Inventory and schema

| Context | Source/trust | Ownership | Snapshot use |
| --- | --- | --- | --- |
| HP, conditions, abilities, stat stages | normalized current confirmations | side; optional slot/session | current_state; deterministic candidate input |
| weather, terrain, field effects | normalized field confirmation | global or side | current_state; deterministic candidate input |
| item events | explicit observed/user-confirmed event | side; optional slot/session | current_state; structured summary |
| final stats, battle format, observed damage, counters | existing deterministic context | existing source contract | current_state where present |
| item/ability/EV/IV/nature not confirmed | unknown | no inferred owner | absent/unknown only |

`TurnSnapshot.current_state` recursively freezes mappings and lists. Its
serialization thaws only into a detached provider-neutral dictionary. The
snapshot excludes request tokens, fingerprints, widgets, repositories,
provider objects, and raw provider data.

## Validation and alignment

`build_request_start_recommendation_snapshot` validates active identity and
selectable move ownership, then captures rich contexts. Explicit context side
must be `self` or `opponent`; if an entry gives `slot_index`, it must match the
active slot for that side. If session metadata is supplied, it must match
`current_state_session_id`; absent session metadata remains unknown, not an
inferred match. A mismatch produces sanitized `invalid_snapshot` before
candidate evaluation or provider payload creation.

`prepare_ui_recommendation_cycle` obtains deterministic candidate context from
the captured snapshot, while its provider summary serializes the same snapshot.
Existing context normalization still happens before this boundary in UI/input
builders; no mutable widget or session object is re-read during preparation.

## Gaps and non-goals

There is no multi-turn transition, automatic event ingestion, identity check
for legacy contexts without slot metadata, provider cancellation, inferred
opponent state, or complete unification of every damage input. Session identity
is checked only when supplied by an upstream session model.

## Verification

Offline contracts cover nested mutation isolation, round-trip serialization,
side/slot/session mismatch blocking, unknown preservation, same snapshot for
candidates and provider summary, and no token/fingerprint serialization.
Provider/network calls: 0.
