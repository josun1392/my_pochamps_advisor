# v15.78 known damage-modifier provider grounding

## Fixture pair

`combined-known-damage-modifiers` supplies a known-singles request-start
snapshot with rain, self burn, and opponent Reflect/Light Screen. Its formula
candidates retain only their own applied labels, while a level-based
fixed-damage candidate remains free of ordinary modifier labels.

`mixed-modifier-authority-states` combines relevant unknown weather/self
condition, a known doubles Light Screen, and level-based fixed damage. The
first formula candidate remains insufficient, the screen-affected special
candidate remains unsupported, and the fixed-damage candidate remains known
without ordinary modifiers.

## Provider and presentation boundary

The provider contract is unchanged: it returns only selected candidate ID and
a bounded explanation code. Pre-call fixture checks and post-call completion
checks keep modifier labels server-owned, candidate-local, and absent from
incomplete/unsupported or level-fixed candidates. Presentation checks accept
only bounded Korean labels for the validated selected candidate, never a
multiplier, rounding value, snapshot path, diagnostic, or provider text.

## Actual execution

The pair is allowlisted for the separately approved actual round. It stops at
the first failure, uses no retry/fallback/repair, and reports only sanitized
fixture, status, and bounded diagnostic surfaces.
