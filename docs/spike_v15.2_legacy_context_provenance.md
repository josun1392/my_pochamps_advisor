# v15.2 Legacy Deterministic Context Provenance

Pokémon-scoped legacy contexts (HP, condition, ability, stages, item events,
observed damage, and similar list entries) now require a `provenance` block
with `side`, `slot_index`, `pokemon_id`, `session_id`, `source`, and `trust`.
The capture helper accepts an entry only when it matches the active side/slot,
active Pokémon identity, and current session. A wrong or missing block is
excluded; it is never auto-attached to the current active Pokémon.

Field-scoped `field_state_context` and `battle_format_context` remain valid
without Pokémon slot provenance. Existing normalization is upstream; v15.2
filters only request-start snapshot inclusion. Candidates receive the same
filtered snapshot context that the provider-neutral summary serializes.

Compatibility policy: provenance-free historical inputs are legacy/unknown and
are excluded from current-state capture, not promoted to confirmed current
facts. No provider call, automatic event ingestion, multi-turn transition, or
damage formula change is included. Provider budget: 0.
