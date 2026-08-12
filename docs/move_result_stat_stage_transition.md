# Observed move-result stat-stage transition

The lifecycle accepts explicit user-confirmed `stat_stage_observed` records for
one identity-matched active Pokémon. A record carries the absolute observed
stage, not a predicted delta: supported stats are Attack, Defense, Special
Attack, Special Defense, Speed, Accuracy, and Evasion, each clamped by input
validation to the canonical -6 through +6 range.

The observation collection and replay policy send the fact to the canonical
`set_current_stat_stage` reducer effect. It replaces only that exact owner's
stored absolute stage, preserving other stages and never borrowing an active
slot's state after identity changes. The authoritative state can be projected
to downstream stat-stage consumers where the request path carries the current
stage context.

No move effect, hit, boost/drop delta, secondary chance, immunity, ability,
item interaction, or unobserved stage is inferred. Stat resets, switching
reset behavior, and automatic parsing of move effects remain outside this
bounded transition.
