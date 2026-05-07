# Master Ball Advisor — Progress

## Naming Convention (since 3.1 closure)

```
<Major>.<Minor>.<Patch><suffix>
   │       │       │      └─ same-patch split work (a, b, c, ...)
   │       │       └─ patch (single feature unit)
   │       └─ minor (subsystem group)
   └─ major (product stage)
```

- `3.1.5a` = damage engine / 5th patch / split a
- `3.1.5a-Δ` = deferred-debt cleanup of `3.1.5a`
- Internal git PR numbers are **not** referenced in conversation; use milestone codes only.

---

## Current Position

- **Milestone:** `4.0` Stochastic KO Probability Composer — ✅ **COMPLETE**
- **HEAD:** `2f342d8`
- **Tag:** `v0.10.0`
- **Tests:** 560 passing, 0 failures, 0 xfail
- **Performance:** N=4 convolution 0.215 ms (budget < 100 ms)

---

## Phase 4: COMPLETE

- **Completed:** 2026-05-07
- **Tag:** `v0.10.0`
- **Merge commit:** `2f342d8`
- **Tests:** 518 → 560 (+42), 0 failures, 0 xfail
- **Performance:** N=4 convolution avg 0.215 ms (budget 100 ms)
- **Scope:** Fraction-based 1-4 turn KO probability composer, 16-roll Q12 distribution, crit-rate integration, and canonical modifier scenarios.
- **Next:** Phase 5 preview — multi-hit plus chip damage composition.

---

## Phase 5: IN REVIEW

- **Branch:** `feat/phase-5-multihit-chip`
- **Scope:** Multi-hit move probability distributions plus deterministic residual chip integration.
- **Multi-hit:** Tier A 2-5 distribution, Skill Link, Loaded Dice, and Population Bomb Tier C support.
- **Chip:** Burn, poison, toxic, Leech Seed, Curse, sand/hail/snow, and binding residuals.
- **Precision:** `Fraction` probability mass throughout; Q12 damage rolls remain integer-only.
- **Tests:** 560 -> 602 (+42) locally.
- **Performance:** N=4 multi-hit + chip worst measured 17.886 ms with crit-mixed Bullet Seed; Population Bomb + Loaded Dice measured 3.500 ms. Both remain under the 100 ms hard ceiling.
- **Next:** Phase 5 review should decide whether the 5 ms soft target requires a follow-up optimization PR before merge.

---
## Major Roadmap

| Major | Codename | Status |
|---|---|---|
| 1.x | Foundation | ✅ Complete |
| 2.x | Stat Engine | ✅ Complete |
| **3.x** | **Damage Engine** | 🔧 ~30% (3.1 done) |
| 4.x | Turn Engine | ❌ Not started |
| 5.x | Battle AI | ❌ Not started |
| 6.x | UI / CLI / API | ❌ Not started |

---

## 3.x — Damage Engine

### 3.1 — Core Damage Formula ✅ CLOSED

| Code | Item | Status | Tests |
|---|---|---|---|
| 3.1.1 | Status modifiers (burn/paralysis) | ✅ | 296 |
| 3.1.2 | Stat Doublers (Huge Power, Pure Power, Hustle) | ✅ | 304 |
| 3.1.3 | Defensive Boosters (Fur Coat, Ice Scales, Multiscale, Shadow Shield) | ✅ | 316 |
| 3.1.4a | SpA Boosters (Solar Power, Plus, Minus) | ✅ | 326 |
| 3.1.4b | Two-Pass BP Hook (Technician, Tough Claws, Iron Fist) | ✅ | 341 |
| 3.1.5a | Damage Reducers (Filter, Solid Rock, Prism Armor, Punk Rock-D) | ✅ | 357 |
| 3.1.5b | HP-Conditional Type Boosters (Overgrow, Blaze, Torrent, Swarm, Defeatist) | ✅ | 375 |
| 3.1.5c | Damage Chain Gap Fill (Strong Jaw, Mega Launcher, Reckless, Punk Rock-O, Sheer Force BP, Transistor) | ✅ | 393 |
| 3.1.5d | Item Layer 1 (Life Orb, Choice Band/Specs, Muscle Band, Wise Glasses, Expert Belt, Flame Plate) | ✅ | 381* |
| 3.1.5a-Δ | Sheer Force secondary-effect suppression (Path B predicate) | ✅ | 386 |
| 3.1.5d-Δ | Life Orb 1/10 max HP recoil (Path B pure function) | ✅ | 393 |

\* 3.1.5d temporarily showed 417 before squash reconciliation; final consolidated count = 381 after restoring 4 silently-deleted item tests (charcoal, eviolite, light_ball, species_orb).

### 3.2 — Item Wiring (next candidate)

| Code | Item | Status |
|---|---|---|
| 3.2.1 | Choice Scarf (defer to 4.x — speed only) | ⏭️ deferred |
| 3.2.2 | Assault Vest, Eviolite (partial in 3.1.5d) | 🟡 partial |
| 3.2.3 | Type-resist Berries (Occa, Passho, etc.) | ❌ |
| 3.2.4 | Pinch Berries (Salac, Liechi — damage only) | ❌ |
| 3.2.5 | Sitrus / Lum / Leftovers | ⏭️ defer to 4.x |
| 3.2.6 | Air Balloon, Iron Ball, Ring Target | ❌ |
| 3.2.7 | Weakness Policy, Throat Spray | ⏭️ defer to 4.x |
| 3.2.8 | Z-Crystals (Gen 7) | ⏭️ low priority |
| 3.2.9 | Mega Stones (stat + type/ability swap) | ❌ |

### 3.3 — Field & Weather

| Code | Item | Status |
|---|---|---|
| 3.3.1 | Weather (Sun/Rain/Sand/Snow) damage modifiers | ❌ |
| 3.3.2 | Terrain (Electric/Grassy/Misty/Psychic) | ❌ |
| 3.3.3 | Weather/Terrain-setting abilities (Drought, Surge) | ❌ |
| 3.3.4 | Aura abilities (Fairy/Dark Aura, Aura Break) | ❌ |
| 3.3.5 | Room effects (Wonder Room, Magic Room) | ❌ |

### 3.4 — Move-Specific Mechanics

| Code | Item | Status |
|---|---|---|
| 3.4.1 | Multi-hit moves (Bullet Seed, Rock Blast) | ❌ |
| 3.4.2 | Fixed damage (Seismic Toss, Night Shade, Endeavor) | ❌ |
| 3.4.3 | Variable BP (Gyro Ball, Electro Ball, Low Kick) | ❌ |
| 3.4.4 | Counter / Mirror Coat / Metal Burst | ❌ |
| 3.4.5 | OHKO moves | ❌ |
| 3.4.6 | Spread moves (0.75x doubles) | ❌ |
| 3.4.7 | Critical hit mechanics | 🟡 partial |

### 3.5 — Parity Hardening

| Code | Item | Status |
|---|---|---|
| 3.5.1 | `@smogon/calc` 1000-case randomized comparison | ❌ |
| 3.5.2 | Per-generation branching (Gen 1–9) | 🟡 Gen 9 only |
| 3.5.3 | Edge case regression suite (Wonder Guard, Levitate) | 🟡 partial |
| 3.5.4 | Performance benchmark (10k calc / sec) | ❌ |

---

## Test Count Trajectory

```
292 → 296 → 304 → 316 → 326 → 341 → 357 → 375 → 393 → 381 → 386 → 393
 (init)  PR#1  PR#2  PR#3  PR#4  PR#5  PR#6  PR#7  PR#8  squash  Δ-a   Δ-d
```

Parity tests: `112 → 114 → 118 → 122 → 128 → 134 → 140 → 148 → 139`

The dip from 393 → 381 reflects the squash + silent-deletion restoration of 4 item tests, not a regression.

---

## Verified Q12 Constants (audit-stable)

### BP Modifiers
| Constant | Multiplier | Sources |
|---|---|---|
| 6144 | ×1.50 | technician, strong-jaw, mega-launcher |
| 5325 | ×1.30 | tough-claws, sheer-force, punk-rock (offensive) |
| 4915 | ×1.20 | iron-fist, reckless |
| 4505 | ×1.10 | muscle-band, wise-glasses |

### Attack / Special Attack Modifiers
| Constant | Multiplier | Sources |
|---|---|---|
| 8192 | ×2.00 | huge-power, pure-power |
| 6144 | ×1.50 | hustle, guts, overgrow, blaze, torrent, swarm (Atk); solar-power, plus, minus, overgrow, blaze, torrent, swarm (SpA); choice-band, choice-specs (item) |
| 5325 | ×1.30 | transistor (Gen 9 nerf, was 6144) |
| 4915 | ×1.20 | flame-plate (item) |
| 2048 | ×0.50 | defeatist (Atk + SpA) |

### Defense / Special Defense Modifiers
| Constant | Multiplier | Sources |
|---|---|---|
| 2048 | ×0.50 | fur-coat (physical received), ice-scales (special received) |

### Final Modifiers
| Constant | Multiplier | Sources |
|---|---|---|
| 5325 | ×1.30 | life-orb |
| 4915 | ×1.20 | expert-belt |
| 3072 | ×0.75 | filter, solid-rock, prism-armor (super-effective received) |
| 2048 | ×0.50 | multiscale, shadow-shield (full HP), punk-rock (def, sound) |

---

## History Log (chronological commits)

### `3.1.5a-d` Consolidated Squash → `e8a0893`
Sequential PRs #6–9 + PR #9.1 hotfix were developed in working directory and squashed into one commit. Splitting into 4 reconstructed commits provided no real bisect value (intermediate states were never tested in isolation).

Restored 4 item tests silently deleted during PR #9:
- charcoal, eviolite, light_ball, species_orb (adamant / lustrous / griseous orb)

### `3.1.5a-Δ` (Sheer Force suppression) → `587d29f`
- Path B chosen: no secondary-effect resolver exists yet
- Added pure predicate in `advisor/damage/move_categories.py`
- Tests: 381 → 386
- Note: commit subject reads `3.1.6a / PR #8a` (pre-rename); milestone code is `3.1.5a-Δ`

### `3.1.5d-Δ` (Life Orb recoil) → `d3469ca`
- Path B chosen: no turn engine exists yet
- Added pure recoil computation in `advisor/damage/recoil.py`
- Spec: Bulbapedia — 10% max HP, rounded down, min 1 HP; suppressed by Magic Guard and Sheer Force-boosted moves
- Tests: 386 → 393
- Note: commit subject reads `3.1.6b / PR #9a` (pre-rename); milestone code is `3.1.5d-Δ`

### Docs commit → `4a833a4`
- 3.1.5 deferred debt closed
- 3.1 milestone fully terminated

---

## Legacy ↔ Current Code Mapping

| Old reference (in commits / earlier docs) | Current milestone code |
|---|---|
| PR #1 | 3.1.1 |
| PR #2 | 3.1.2 |
| PR #3 | 3.1.3 |
| PR #4 | 3.1.4a |
| PR #5 / 3.1.5c-pr5 | 3.1.4b |
| PR #6 | 3.1.5a |
| PR #7 | 3.1.5b |
| PR #8 | 3.1.5c |
| PR #9 / PR #9.1 | 3.1.5d |
| PR #8a / "3.1.6a" | 3.1.5a-Δ |
| PR #9a / "3.1.6b" | 3.1.5d-Δ |

Future commits use milestone codes directly. PR numbers are git-internal only.

---

## Next Decision Point

`3.1` is closed. Choose next branch before opening any new patch:

- **Option A — `3.2` Item Wiring**: horizontal expansion, fastest path to single-hit Smogon parity 100%
- **Option B — `4.1` Turn Engine**: vertical expansion, unlocks deferred items naturally
- **Option C — `3.3` Field/Weather**: high battle-impact gap-fill

Decision pending. Baseline `4a833a4` / 393 tests is safe to pause on.
