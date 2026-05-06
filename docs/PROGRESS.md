# Phase 3.1.5d - Item Layer Foundation Progress

## Cumulative State
- Tests: 292 -> 304 -> 316 -> 326 -> 341 -> 357 -> 375 -> 393 -> 381
- Parity: 112 -> 114 -> 118 -> 122 -> 128 -> 134 -> 140 -> 148 -> 139
- Performance: ~0.18ms/calc (must maintain, regression < 5%)

## PR Tracker
- [x] PR #1 Foundation - status_effects.py, move_flags.json, abilities.json seed (296 tests)
- [x] PR #2 Stat Doublers - Huge Power, Pure Power, Hustle (304 tests, parity 114)
- [x] PR #3 Defensive Boosters - Fur Coat, Ice Scales, Multiscale, Shadow Shield (316 tests, parity 118)
- [x] PR #4 SpA Boosters - Solar Power, Plus/Minus (326 tests, parity 122)
- [x] PR #5 BP Modifiers - Technician, Tough Claws, Iron Fist (341 tests, parity 128)
- [x] PR #6 Final Damage Reducers - Filter, Solid Rock, Prism Armor, Punk Rock (357 tests, parity 134)
- [x] PR #7 HP-Conditional Type Boosters - Overgrow, Blaze, Torrent, Swarm, Defeatist (375 tests, parity 140)
- [x] PR #8 Damage Chain Gap Fill - Strong Jaw, Mega Launcher, Reckless, Punk Rock (attacker), Sheer Force, Transistor (393 tests, parity 148)
- [x] PR #9 Item Layer Foundation - Life Orb, Choice Band/Specs, Muscle Band, Wise Glasses, Expert Belt, Flame Plate (417 tests, parity 158)
- [ ] PR #8a Secondary Effect Suppression - Sheer Force secondary-effect suppression

## Verified Q12 Constants (re-audit unnecessary)
- bp_mods 6144 (x1.50): technician
- bp_mods 6144 (x1.50): strong-jaw, mega-launcher
- bp_mods 5325 (x1.30): tough-claws, sheer-force, punk-rock(off)
- bp_mods 4915 (x1.20): iron-fist, reckless
- at_mods 5325 (x1.30): transistor (Gen 9 nerf, previous 6144)
- at_mods 8192 (x2.00): huge-power, pure-power
- at_mods 6144 (x1.50): hustle, guts, overgrow, blaze, torrent, swarm
- at_mods 2048 (x0.50): defeatist
- sa_mods 6144 (x1.50): solar-power, plus, minus, overgrow, blaze, torrent, swarm
- sa_mods 2048 (x0.50): defeatist
- df_mods 2048 (x0.50): fur-coat (physical received)
- sd_mods 2048 (x0.50): ice-scales (special received)
- final_mods 2048 (x0.50): multiscale, shadow-shield (HP full), punk-rock(def, sound)
- final_mods 3072 (x0.75): filter, solid-rock, prism-armor (super-effective received)
- item atk/spa_mods 6144 (x1.50): choice-band, choice-specs
- item atk/spa_mods 4915 (x1.20): flame-plate
- item bp_mods 4505 (x1.10): muscle-band, wise-glasses
- item final_mods 5325 (x1.30): life-orb
- item final_mods 4915 (x1.20): expert-belt

### PR #6-9 + PR #9.1 Squash (3.1.5a-d consolidated)

PRs #6-9 were developed sequentially in working directory and squashed into
one commit. Splitting into 4 reconstructed commits provides no real bisect
value (intermediate states were never tested in isolation).

Restored 4 item tests silently deleted during PR #9:
charcoal, eviolite, light_ball, species_orb (adamant/lustrous/griseous orb).

Deferred:
- [ ] PR #8a Sheer Force secondary-effect suppression
- [ ] PR #9a Life Orb 1/10 HP recoil (turn_engine layer)

### PR #8a + PR #9a — Deferred Debt Closed

- PR #8a: Sheer Force secondary-effect suppression (Path B)
- PR #9a: Life Orb recoil computation (Path B)

Tests: 381 -> 386 -> 393

3.1.5 series fully closed. No deferred items remain in this band.
