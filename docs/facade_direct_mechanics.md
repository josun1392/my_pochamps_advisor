# Facade direct-damage transition

The native direct-damage evaluator now supports Facade when the attacking
Pokémon has one exact, identity-bound current major-condition record. Burn,
poison, toxic, and paralysis set its base power to 140; none, sleep, and freeze
retain its base power of 70. Burned Facade also correctly omits the ordinary
physical burn Attack reduction.

This consumes existing trusted condition state only and feeds the existing
damage, KO, and danger consumers. Missing, duplicated, malformed, or
untrusted condition authority leaves Facade incomplete. Other dynamic-power
moves, status application, move-hit inference, secondary-effect inference,
and broader turn simulation remain outside this slice.
