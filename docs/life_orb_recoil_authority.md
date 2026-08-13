# Practical 1.1: observed Life Orb recoil

`qualifying_direct_damage_dealt` is an explicit, trusted, session- and
turn-scoped same-turn observation. It binds the acting Pokémon identity to the
exact damaged target identity; it is never inferred from move choice, damage
estimates, action order, or an HP difference.

For an exact current Life Orb holder, an observed `true` predicate applies one
post-hit recoil of `max(1, floor(max_hp / 10))`, clamped at zero. The reducer
updates authoritative HP, while an explicit faint observation remains required
by the existing faint-terminal lifecycle contract. A trusted `false` predicate
does not recoil. Missing qualifying-hit, item, HP, or relevant suppression
authority stays incomplete rather than being treated as a hit or a miss.

The bounded implementation recognizes exact Magic Guard. Sheer Force remains
incomplete unless the existing state can prove its move-specific applicability;
this unit does not add a generic trigger, contact, or move-result engine.

The event expires outside its matching turn and is identity-safe across
switches and frozen projections. Life Orb's existing direct-damage boost is
unchanged.
