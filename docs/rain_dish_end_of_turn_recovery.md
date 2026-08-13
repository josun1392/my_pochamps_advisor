# Practical 1.1: Rain Dish first-end-of-turn recovery

Rain Dish is supported only for an active Pokémon with an exact observed current
`rain-dish` ability, exact observed current `rain` weather, exact HP/max HP,
and a matching confirmed first end-of-turn phase. It recovers
`floor(max_hp / 16)`, capped at maximum HP; full HP is a resolved no-change
outcome.

Current ability and weather are reducer-owned, identity/session-safe facts. A
known non-Rain weather or known non-Rain-Dish ability does not activate the
mechanic. Unknown weather, ability, HP, or a material suppression fact remains
incomplete. Exact Cloud Nine, Air Lock, and Neutralizing Gas suppress the
effect under the existing weather/ability rules.

This is not a generic passive-ability engine. Ice Body, Dry Skin, Solar Power,
weather duration, and broader end-of-turn sequencing remain outside this
bounded support. Where another same-owner residual can change HP without an
authoritative ordering contract, Rain Dish remains incomplete.
