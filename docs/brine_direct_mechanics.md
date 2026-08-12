# Brine direct mechanics

The native direct-damage evaluator supports Brine when the frozen defender has
exact, defender-owned current and maximum HP. It applies 65 base power above
half HP and 130 base power at or below half HP before the existing Q12 damage,
KO, and danger evaluation.

Missing, malformed, impossible, or fainted defender HP remains incomplete or
unsupported. The evaluator does not infer HP from species data, prior damage,
or move use. Existing Water weather requirements and all other direct-damage
authority checks still apply.

This is limited to Brine; other dynamic-power moves remain unavailable unless
their own trusted prerequisites are explicitly supported.
