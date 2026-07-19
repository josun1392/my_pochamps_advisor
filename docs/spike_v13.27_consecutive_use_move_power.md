# v13.27 deterministic consecutive-use move power

The current-use stage is a user-confirmed current-battle snapshot: stage 1 is
the first use being evaluated. Chain resets, misses, failures, switches, and
ally activity are never reconstructed.

- Fury Cutter: `min(160, 40 * 2 ** (stage - 1))`.
- Echoed Voice: `min(200, 40 * stage)`.

Only a confirmed single-user chain is supported. Missing or unconfirmed input
is unavailable, with no metadata-power fallback. The effective power replaces
the move power once; it is not a second damage multiplier.
