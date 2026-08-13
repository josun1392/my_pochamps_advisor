# Practical 1.1: Ice Body first-end-of-turn recovery

Ice Body is supported only for an active Pokémon with an exact observed current
`ice-body` ability, exact observed current `snow` weather, exact HP/max HP,
and a matching confirmed first end-of-turn phase. It recovers
`floor(max_hp / 16)`, capped at maximum HP; full HP is a resolved no-change
outcome.

Current ability and weather are reducer-owned, identity/session-safe facts. A
known non-Snow weather or known non-Ice-Body ability does not activate the
mechanic. Unknown weather, ability, HP, or a material suppression fact remains
incomplete. Exact Cloud Nine, Air Lock, and Neutralizing Gas suppress the
effect under the existing weather/ability rules.

This is not a generic passive-ability engine. Rain Dish is unchanged; Dry Skin,
Solar Power, legacy Hail, weather duration, and broader end-of-turn sequencing
remain outside this bounded support. Where another same-owner residual can
change HP without an authoritative ordering contract, Ice Body remains
incomplete.
