# Observed Tailwind action-order authority

An explicit user-confirmed `tailwind_side_condition_observed` record may set
the reducer-owned Tailwind status for exactly one side to `active` or
`inactive`. This is a side condition, not a Pokémon identity property. The
record is admitted only through lifecycle confirmation with the dedicated
Tailwind observation source, then flows through collection, replay, and the
canonical reducer.

The detached runtime projection exposes this narrow authority only when its
current reducer provenance is the user-confirmed Tailwind observation. Frozen
turn-state construction converts it to the existing `field_state_context`
Tailwind contract, which the existing action-order evaluator consumes. A
separately unobserved side remains unknown; it is never made inactive merely
because the other side was observed.

This bridge does not infer Tailwind from move selection or use, a species, or
generic side-condition state. It does not project Trick Room or any other
field/side condition: existing `field_state_context` entries are preserved,
and Trick Room remains unknown unless supplied by its established authority.
No score or strategic reward is added; the only consequence is the existing
action-order evidence when all of its independent prerequisites are trusted.
