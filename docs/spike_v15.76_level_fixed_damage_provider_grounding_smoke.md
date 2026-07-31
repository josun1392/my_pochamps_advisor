# v15.76 level-fixed-damage provider grounding smoke

The approval-gated smoke adds a complete level-fixed versus Q12 fixture and a
mixed immunity, supported level-fixed, and unsupported-special fixture. The
actual provider still returns only a selected slot and bounded explanation
code; damage models, fixed values, percent, KO, and immunity remain entirely
server-owned evidence.

The runner verifies exact trusted-level fixed damage, single-value range,
deterministic KO, and separate Q12/fixed-hit/fixed-damage model identities
before a call. Completion and presentation checks retain only the selected
candidate's evidence and never emit raw provider content or internal paths.

Level and target-HP availability are request-level authority in the current
contract, so their insufficient behavior is covered by offline direct-mechanics
regressions rather than a contradictory mixed per-candidate actual request.
No provider-side stat, base-power, resistance/weakness, expected-damage, or
accuracy-adjusted calculation surface is introduced.
