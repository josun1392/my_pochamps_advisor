# v15.80 attacker-ability provider grounding smoke

## Fixture contract

The approval-gated fixture pair reuses the minimal multi-provider response:
resolved status, deterministic rank-one candidate ID, and the fixture-bound
explanation code only. `supported-attacker-ability-candidates` uses
user-confirmed Iron Fist with a canonical punch, a non-punch formula move, and
a level-based fixed-damage candidate. `unsupported-ability-with-level-fixed-control`
uses known Guts: formula damage stays unsupported while Seismic Toss remains
the deterministic control candidate.

## Authority variants

Unknown, malformed, and unsupported ability identities are provider-free
pre-call variants. They retain insufficient or unsupported mechanics with no
rank-one result; a separate no-usable request remains preparation-blocked.
None of these inputs becomes an absent ability or invokes a provider.

## Evidence and presentation

The smoke checks matching Iron Fist evidence, non-matching absence of the
ability tag, and level-fixed non-application. Completion and presentation keep
only the selected candidate's server-owned evidence. Provider output cannot
add ability identity, condition, multiplier, damage, KO, or evidence paths.

## Validation and actual boundary

Offline coverage includes ability composition with known weather, burn,
Reflect, and fixed-hit mechanics. Actual execution is limited to the approved
two fixtures, two calls per round, no retry/fallback/repair, and sanitized
surface output only. A new T1 approval is required after this smoke budget.
