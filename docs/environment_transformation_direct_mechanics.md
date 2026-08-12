# Field transformation direct mechanics

The native direct-damage evaluator supports Weather Ball and Terrain Pulse from
trusted frozen current field authority. Weather Ball changes from 50 base power
and Normal type to 100 power and the weather's Fire, Water, Rock, or Ice type.
Terrain Pulse changes from 50 power and Normal type to 100 power and the active
terrain's type only when the attacker has exact self-owned groundedness.

The resulting power and type enter the existing Q12 modifier, damage, KO, and
danger path. Missing, malformed, or untrusted field state remains incomplete or
unsupported; Terrain Pulse also remains incomplete when groundedness is
unknown. No field duration, turn simulation, or inferred field state is added.
