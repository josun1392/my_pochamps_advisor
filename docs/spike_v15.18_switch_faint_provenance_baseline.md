# v15.18 Switch/Faint Observation Provenance

UI slot selection is analysis state, not a battle switch. HP zero and Q12 KO are evidence only, not faint confirmation. The new structured-only contract accepts explicit `pokemon_switch_observed` and `pokemon_faint_observed` records with session, ID, sequence, optional trusted turn, owner identity, and user-confirmed source/trust. Switch-in must match the current captured active owner; faint must match its captured owner. No active slot, HP, selectable state, or reducer state changes.

Records are ordered by sequence/ID, stale and invalid records are excluded, and same-ID duplicates collapse per event kind. No actual switch/faint UI or log producer exists yet; this is a private producer/fixture boundary. Reducer readiness still requires condition, item, ability, field, switch/faint conflict, and replay contracts. Provider budget is 0.
