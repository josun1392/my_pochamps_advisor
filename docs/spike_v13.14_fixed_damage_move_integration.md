# v13.14 Fixed-Damage Moves

The limited deterministic adapter supports only explicit move identities:
Seismic Toss and Night Shade (trusted attacker level), Dragon Rage (40), Sonic
Boom (20), and Super Fang, Nature's Madness, and Ruination (floor of confirmed
defender current HP divided by two). Its scope is
`explicit-fixed-damage-rules-only`.

It never uses the ordinary attack/defense formula, STAB, random rolls, burn,
weather, screens, expected damage, or ability/status overrides. Seismic Toss
against Ghost and Night Shade against Normal resolve to zero through the base
type chart. Endeavor, Counter-family, random, and OHKO rules remain unavailable.
