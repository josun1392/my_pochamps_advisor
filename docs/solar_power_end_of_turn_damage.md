# Practical 1.1: Solar Power first-end-of-turn self-damage

Solar Power is supported only for an active Pokémon with an exact observed
current `solar-power` ability, exact observed current `sun` weather, exact
HP/max HP, and a matching confirmed first end-of-turn phase. It takes
`floor(max_hp / 8)` damage, clamped at zero. A resulting zero HP is recorded as
deterministic lethal evidence; existing faint-terminal observation semantics
remain unchanged.

Current ability and weather are reducer-owned, identity/session-safe facts. A
known non-Sun weather or known non-Solar-Power ability does not activate the
mechanic. Unknown weather, ability, HP, or a material suppression fact remains
incomplete. Exact Cloud Nine, Air Lock, and Neutralizing Gas suppress the
effect under the existing weather/ability rules.

This adds only Solar Power's named first-end-of-turn self-damage. Its existing
Sun-dependent offensive damage modifier is unchanged. Dry Skin, weather
duration, automatic weather creation, and broader end-of-turn sequencing remain
outside this bounded support.
