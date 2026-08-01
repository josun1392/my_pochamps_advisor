# v15.79 known attacker-ability damage modifiers

## Authority and narrow allowlist

Only a request-start, user-confirmed self ability identity may enter formula
damage. The implemented static base-power allowlist is `iron-fist`,
`strong-jaw`, `mega-launcher`, and `technician`. Iron Fist, Strong Jaw, and
Mega Launcher require a canonical move-flag record; Technician uses only the
canonical base power. A known ability outside this allowlist is unsupported,
while explicit unknown ability input remains insufficient context. Legacy
`known_absent` continues to be a distinct no-ability authority.

## Native mechanics boundary

The existing Q12 formula receives the resolved `AbilityEffect` and retains its
existing base-power ordering and integer rounding. Fixed-hit formula moves use
the resulting per-hit rolls before the existing exact convolution. Level-based
fixed damage never enters this ability modifier path. No ability/item/status,
opponent, HP-threshold, terrain, weather-dependent, or dynamic ability rule is
added.

## Evidence and presentation

Only an actually applied modifier adds one allowlisted candidate-local tag:
`ability_iron_fist_boost`, `ability_strong_jaw_boost`,
`ability_mega_launcher_boost`, or `ability_technician_boost`. The completed
result and presentation use only the selected candidate's Korean label; they
expose no multiplier, raw metadata, or unapplied ability.

## Validation

Offline coverage verifies matching/non-matching conditions, missing flag
metadata, unknown and unsupported ability behavior, fixed-hit composition,
level-fixed non-application, request-start candidate isolation, and
presentation redaction. No credential, provider, or network activity occurs.
