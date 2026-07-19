# v13.16 Observed Damage Counter Moves

`Previous Damage` is a current-context panel action. Apply stores one defensive
session copy of `{damage, damage_category, damage_kind, source_side,
target_side}`; Cancel does not mutate it and Clear sets it to `None`.

The snapshot is accepted only for positive integer direct move damage from
opponent to self with physical or special category. It is attached only while
limited context is enabled; disabled advice omits it without clearing session
state. The normalized payload has user-confirmed/known provenance.

Counter returns twice observed physical damage, Mirror Coat twice observed
special damage, and Metal Burst `floor(3 * observed / 2)`. Returned damage is
capped by confirmed opponent HP when present, with resulting HP and guaranteed
KO/no-KO. Missing opponent HP leaves a resolved returned-damage-only result;
a fainted target is not applicable. Counter respects Ghost immunity and Mirror
Coat respects Dark immunity. Counter mechanics never fall back to ordinary,
fixed, or HP-special damage estimates.

The trusted acknowledgement is `Previous direct damage`; deterministic output
uses `Reactive damage`, optional actual/resulting HP, and KO lines. Parsing is
exact-set: mutation, missing, duplicate, extra, or gate-off lines fail. The
semantic boundary rejects inferred damage/category, priority or same-turn
success, Bide/Shell Trap/Focus Punch, Substitute/Focus Sash/Sturdy, indirect
damage, and ability-immunity overrides. Unsupported mechanics remain outside
scope.
