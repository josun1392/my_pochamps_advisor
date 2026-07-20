# v13 dynamic move phase closure

## v13.31 production registry dispatch repair

A repository audit found that prior production construction still used direct
multi-family helper fan-out even though the registry and its self-derived
coverage were complete. v13.31 routes every registered canonical move through
one registry-selected resolver before deterministic context construction.
Ordinary unregistered moves retain metadata power and type. A registered move
without its required trusted context fails closed without metadata power or
type fallback. Only the environment family may override effective type; every
other dynamic family is power-only.

Production-path dispatch tests now spy on actual deterministic context
construction for one representative of every family, and an independent
30-move limited-context matrix verifies the complete canonical inventory.
These additions do not change mechanic formulas or the ten-family/30-move
inventory.

The v13.18–v13.29 sequence closes deterministic dynamic move assessment. The
canonical source is `DYNAMIC_MOVE_ASSESSMENT_REGISTRY`: ten families and 30
moves, with coverage manifest exact-set validation. Environment is the only
type-and-power override family; every other family is power-only. Registered
moves never use metadata fallback when their trusted context is unavailable;
ordinary moves retain metadata behavior, and limited-context OFF emits no
dynamic payload, acknowledgement, or override.

| Family | Moves | Trusted source | Output |
|---|---|---|---|
| current HP | eruption, water-spout, dragon-energy, flail, reversal | exact self HP | power |
| speed | electro-ball, gyro-ball | final speed/stage/Tailwind | power |
| weight | heavy-slam, heat-crash, grass-knot, low-kick | canonical weight | power |
| stat stage | stored-power, power-trip, punishment | trusted stages | power |
| target HP | crush-grip, wring-out | exact opponent HP | power |
| environment | weather-ball, terrain-pulse | weather/terrain/grounded | type + power |
| binary condition | facade, hex, venoshock, brine | condition or exact HP | power |
| turn event | avalanche, revenge, payback, assurance | observed current-turn event | power |
| battle counter | rage-fist, last-respects | confirmed battle counter | power |
| consecutive use | fury-cutter, echoed-voice | confirmed chain stage | power |

All family results use their existing acknowledgement/parser/evaluator
contracts and mocked production coverage. UI/session snapshots are required
for explicit HP, event, counter, and consecutive-use sources; canonical move
metadata only never creates a dynamic result.

Unsupported: Rollout/Ice Ball (Turn Engine), Electro Shot/Meteor Beam
(charge-state history), Trump Card/Return/Frustration (unsupported generation
or state data), Fling/Natural Gift (item integration), and copying or
ability/item transformations (requires item/ability integration).

v14 candidate: battle-advisor integration planning using the completed
deterministic mechanic inventory. No v14 implementation is authorized here.
