# v15.11 Structured Final-Stat Capture Provenance

## Producer inventory

`CurrentFinalStatDialog` and `MainWindow._current_final_stat_confirmations`
already provide explicit exact-stat entries. They are user-confirmed values, not
base stats or derived EV/IV/nature calculations. The legacy session collection
remains unchanged for legacy consumers.

## Structured-only producer

At confirmation time, `MainWindow._capture_structured_final_stat_confirmation`
stores a separate private structured record with side, active slot, Pokemon,
session, source, and trust provenance. The public confirmation entry is not
mutated. `_start_structured_recommendation` deep-copies these records into
`capture_ui_current_state_provenance`, which accepts only already-provenanced
records and writes `final_stat_context.current_final_stats` on the structured
copied input.

## Complete-set policy

The canonical stat names are `hp`, `attack`, `defense`, `special-attack`,
`special-defense`, and `speed`. Each value must pass the existing exact
user-confirmed validator and retain matching side/slot/Pokemon/session
provenance. Partial, invalid, provenance-free, stale-session, and wrong-slot
entries are excluded. They are not filled from species base stats and are not
retagged after a switch.

## Snapshot and Q12 boundary

`TurnSnapshot` freezes the filtered entries. v15.10 then reports final stats
available only when all six entries are present for a side. Q12 formula/API and
legacy payloads remain unchanged; this milestone supplies trusted capture data
but does not invoke Q12 through the new bridge.

## Remaining gaps

Ability provenance, observed damage, full structured-to-Q12 invocation, and
multi-turn state transition remain deferred. Provider/network calls: 0.
