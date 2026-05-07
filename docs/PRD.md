# PRD 2.0 — Master Ball Advisor (PoChamps Format)

**Project Codename:** `josun1392/my_pochamps_advisor`
**Version:** 2.0 (v0.8)
**Last Updated:** 2026-05-06
**Data Cutoff:** 2026-06-16
**Document Status:** 🟢 LIVING DOCUMENT
**Author:** Lead Systems Architect (T1)
**Format:** PoChamps Tournament (Custom Gen 9 derivative)
**Repository:** [github.com/josun1392/my_pochamps_advisor](https://github.com/josun1392/my_pochamps_advisor)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Scope](#2-product-scope)
3. [The Constitution (Architectural Laws)](#3-the-constitution-architectural-laws)
4. [Current Implementation Status](#4-current-implementation-status)
5. [System Architecture](#5-system-architecture)
6. [Roadmap](#6-roadmap)
7. [Phase 3.3 Specification — Field & Weather (DONE)](#7-phase-33-specification--field--weather-done)
8. [Phase 3.4 Specification — Multi-hit Moves (DONE)](#8-phase-34-specification--multi-hit-moves-done)
9. [Phase 3.5 Specification — Damage Roll & Field Audit (DONE)](#9-phase-35-specification--damage-roll--field-audit-done)
10. [Phase 3.6 Specification — Critical Hit Sampling (DONE)](#10-phase-36-specification--critical-hit-sampling-done)
11. [Phase 4.0 Specification — PoChamps Localization Layer](#11-phase-40-specification--pochamps-localization-layer)
12. [Quality Gates / Definition of Done](#12-quality-gates--definition-of-done)
13. [Re-Entry Protocol — Common Misconceptions](#13-re-entry-protocol--common-misconceptions)
14. [3-Tier AI Orchestration Model](#14-3-tier-ai-orchestration-model)
15. [Risks & Open Questions](#15-risks--open-questions)
16. [Glossary](#16-glossary)
17. [Appendix A — Q12 Lookup Reference](#17-appendix-a--q12-lookup-reference)
18. [Version History](#18-version-history)
19. [Document Control](#19-document-control)

---

## 1. Executive Summary

The **Master Ball Advisor** is a desktop battle copilot for the **PoChamps** tournament format — a custom competitive Pokémon ruleset derived from Generation 9 mechanics with explicit gimmick bans and status RNG nerfs. The product is a **PySide6** desktop application backed by a pure-Python damage and turn engine, designed for **bit-perfect parity** with `@smogon/calc` (Showdown Standard) at the engine layer, with PoChamps-specific overrides isolated in a dedicated localization layer.

| Field | Status |
|---|---|
| **Current Phase** | 3.6 DONE -> 4.0 NEXT |
| **Tests Passing** | **485** (485 collected, 0 xfailed) |
| **Engine Math** | Q12 fixed-point (Base 4096), no float |
| **Parity Reference** | `@smogon/calc` v0.11.0 (`gen789.ts`) |
| **Architecture** | Path A (stateful) / Path B (pure functional) |

### Core Tenets

1. **Bit-Perfect Parity** — Damage engine is a 1:1 mirror of `@smogon/calc` v0.11.0 `gen789.ts`.
2. **Q12 Fixed-Point Math** — All multipliers use Base 4096 integer arithmetic. No floats.
3. **Test-Driven Development (TDD)** — No code without a failing test first.
4. **Single Source of Truth (SSoT)** — Each rule lives in exactly one place.
5. **Dual-Path Architecture** — Path A (stateful turn engine) and Path B (pure functional damage predicates).

---

## 2. Product Scope

### 2.1 Goals

1. Real-time damage calculation for PoChamps battles with **<50ms** response time.
2. Move recommendation engine (Phase 5.x Minimax AI) for tournament play.
3. Korean-localized UI with full Pokémon name mapping (Phase 2.2 — DONE).
4. Format-aware: support Showdown standard and PoChamps profiles via switch.

### 2.2 Non-Goals

- ❌ Online multiplayer / battle simulator (use Showdown for that).
- ❌ Team-builder / damage calc replacement for casual ladder play.
- ❌ Mobile or web ports (desktop-first, Windows primary).
- ❌ Coverage of other formats (VGC, Smogon OU/UU). Future work only.

### 2.3 Target User

The user is a **Master Ball-tier PoChamps competitor** who demands:

- Engine accuracy verifiable against `@smogon/calc` test vectors.
- Sub-second decision support during live tournament play.
- Transparent reasoning ("why did the AI suggest Move X?").

### 2.4 Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| **UI** | PySide6 (Qt 6) | Native desktop, mature widget toolkit |
| **Engine** | Python 3.11+ | Pure-Python for testability |
| **Math** | Q12 fixed-point (int) | Bit-perfect parity, no float drift |
| **Tests** | pytest | TDD foundation |
| **Data** | PokeAPI (cached) + manual overrides | Source of truth for species/moves |
| **Parity** | `@smogon/calc` v0.11.0 bridge | Ground truth for engine assertions |
| **AI (future)** | Minimax + Alpha-Beta | Phase 5.x |

### 2.5 PoChamps Format Specification ★ CRITICAL

> ✅ **Decision:** Documentation-only in Phase 3.x. Implementation deferred to Phase 4.0.
> **Authority:** Final arbiter is the Lead Architect. When PoChamps rules conflict with Showdown defaults, **PoChamps wins — but ONLY in the format layer, never in the engine.**

#### 2.5.1 Allowed Mechanics

| Mechanic | Status | Notes |
|---|---|---|
| Mega Evolution | ✅ Allowed | The **ONLY** gimmick permitted |
| Z-Moves | ❌ Banned | No Z-crystal interactions |
| Dynamax / Gigantamax | ❌ Banned | No Max moves, no HP doubling |
| Terastallization | ❌ Banned | Includes Stellar type |
| Standard items / abilities | ✅ Allowed | Per Gen 9 rules unless overridden |

#### 2.5.2 Status RNG Overrides (Format Nerfs)

| Status | Showdown Standard | PoChamps Override | Layer |
|---|---|---|---|
| Paralysis (full para) | 25% skip turn | **12.5% skip turn** | Turn Engine (4.x) |
| Sleep (wake-up) | 1–3 turns RNG | **3 turns fixed** | Turn Engine (4.x) |
| Freeze (thaw rate) | 20%/turn, no cap | **25%/turn, cap 3 turns** | Turn Engine (4.x) |

#### 2.5.3 Status Stat Modifiers (UNCHANGED — already implemented)

| Status | Modifier | Exception | Status |
|---|---|---|---|
| Burn | ATK × 0.5 | Guts ability | ✅ Same |
| Frostbite | SpA × 0.5 | — | ✅ Same |
| Paralysis | SPE × 0.5 | Quick Feet | ✅ Same |

→ No code change required. Already in `advisor/damage/status_effects.py`.

#### 2.5.4 PP Cap Table

| Base PP | PoChamps Cap |
|---|---|
| 5 | 8 |
| 10 | 12 |
| 15 | 16 |
| 20 | 20 (cap) |
| 25+ | 20 (cap) |

→ Stored as static metadata at `data/pochamps_pp_table.py` (Phase 4.0.3).
→ Used by Turn Engine (Struggle detection) and Battle AI (stall-war depth).

#### 2.5.5 Battle Format

Singles, 6v6, **Bring 6 / Pick 4** (assumed; pending confirmation).

---

## 3. The Constitution (Architectural Laws)

> ✅ **Decision:** Inviolable principles. Amendments require explicit decision logged in § 16.

### 3.1 Accuracy > Performance

When in conflict, **correctness wins**. Optimization is permitted only after parity tests pass.

### 3.2 Bit-Perfect Parity Law (AMENDED 2026-05-06)

- **Definition:** "Bit-Perfect" means a 1:1 mirror of `@smogon/calc` v0.11.0 `gen789.ts`.
- **Boundary:**
    - Damage Engine (`advisor/damage/`) MUST be a pure Showdown Standard mirror.
    - PoChamps rules are classified as **Format Overrides**, NOT Engine Behavior.
    - Format Overrides MUST live outside `advisor/damage/` — exclusively in `advisor/format/`.
- **Enforcement:** Any PR that introduces PoChamps-specific code into `advisor/damage/` MUST be rejected.
- **Upstream Divergence:** Where our engine matches Showdown sim but `@smogon/calc` bridge diverges, we patch the local bridge only after ground-truth review (Showdown source, Bulbapedia). The Phase 3.3 divergence is resolved in § 9.

### 3.3 Q12 Fixed-Point Discipline

- Base = **4096**.
- All multipliers represented as integers in Q12 space (e.g., ×1.5 = `6144`, ×0.5 = `2048`).
- All chained multiplications use the `chainMods` pattern (Smogon-canonical).
- Final division uses integer floor division (`//`), never float.
- **No float types in `advisor/damage/`.** Linter enforced.

### 3.4 TDD Mandate

- No production code without a failing test first.
- Every PR description states test count delta (e.g., "397 → 402").
- Parity tests against Showdown vectors are tracked separately (currently **143**).

### 3.5 Single Source of Truth (SSoT)

- Each rule lives in exactly **ONE** module.
- The damage formula entry is `advisor/damage/formula.py` (NOT `damage.py`).
- Q12 lookup tables documented in `docs/Q12_LOOKUP.md` and verified against `gen789.ts`.

### 3.6 Modularity & Path A/B Decoupling

- **Path A:** Stateful turn engine (mutates battle state).
- **Path B:** Pure functional damage predicates (no side effects).
- New features default to **Path B** unless state mutation is fundamentally required.

### 3.7 Pipeline Order (Canonical)

```
(Base + IV + EV) → Nature → Item → Ability → Boost → Status
→ Type chart → STAB → Weather/Field (final mods) → Roll
```

### 3.8 Two-Pass BP Hook

Base Power modifiers are resolved in **two passes** to handle conditional triggers
(e.g., Technician runs in Pass 2 after other BP boosts settle).

---

## 4. Current Implementation Status

### 4.1 Phase 3.1 — Core Damage Engine ✅ COMPLETE

- **Tests passing:** 393 (initial)
- **Parity assertions:** 139

**Implemented:**

- Q12 fixed-point primitives (`q12.py`)
- Stat calculation (Base + IV + EV + Nature)
- Damage formula entry point (`formula.py`)
- **Item modifiers:** Life Orb, Choice Band/Specs, Muscle Band, Wise Glasses, Expert Belt, Flame Plate, Charcoal, Eviolite, Light Ball, species orbs
- **Ability modifiers:**
    - Damage reducers: Filter, Solid Rock, Prism Armor, Punk Rock(def)
    - HP-conditional boosters: Overgrow, Blaze, Torrent, Swarm, Defeatist
    - Damage chain: Strong Jaw, Mega Launcher, Reckless, Punk Rock(atk), Sheer Force(BP), Transistor (Gen9 5325)
    - SpA conditionals: Solar Power, Plus, Minus
    - Type immunity, Mold Breaker
- Status stat modifiers (Burn, Frostbite, Paralysis)
- Screens (Reflect, Light Screen, Aurora Veil)
- Type chart, STAB, type immunity
- Damage rolls (16-roll spread)
- Move categories (contact, sound, bite, pulse, punch, etc.)
- Sheer Force secondary-effect suppression (predicate)
- Life Orb recoil computation (1/10 max HP, with suppression)
- Grounded check (for Earthquake, Terrain interactions)

### 4.2 Phase 3.3 — Field & Weather ✅ DONE (Verified)

- **Completed:** 2026-05-06
- **PR:** #3.3-A `feat(3.3): close weather parity gaps`
- **Commit:** `42207fb` (feat) + `ae71966` (docs)
- **Branch:** `master` (synced to `my_pochamps/master`)

**Coverage:** 397 tests total (+4), 143 parity tests (+4). The historical bridge divergence is resolved in Phase 3.5; current suite has **0 xfailed**.

See § 7 for full specification.

### 4.3 Phase 3.4 — Multi-hit Moves ✅ DONE

- **PR #3.4-A:** Minimum Slice (Bullet Seed / Rock Blast / Icicle Spear + Skill Link) — DONE.
- **PR #3.4-B:** Loaded Dice integration — DONE.
- **PR #3.4-C:** Triple Axel / Triple Kick BP escalation — DONE.
- **PR #3.4-C2:** Population Bomb deterministic Tier C multiaccuracy — DONE.
- **PR #3.4-C3:** Skill Link + Loaded Dice Tier C regression fix — DONE.
- **PR #3.4-D:** Probabilistic multihit sampling — DONE.
- **Current test count:** 441 collected, 440 passed, 1 xfailed at Phase 3.4 close. The remaining xfail is resolved in Phase 3.5.

See § 8 for full specification.

### 4.4 Status Effects Code Audit (`status_effects.py`)

- ✅ Confirmed: Only stat modifiers are implemented.
- ✅ Confirmed: No RNG/probability logic exists.
- ✅ Confirmed: This is correct — RNG belongs to Turn Engine (4.x).
- `Status` Literal contains 8 states; sleep/freeze/poison/toxic are declared but have no damage-side modifier (correct).

### 4.5 Parity Bridge

`advisor/parity/` contains parity assertions against `@smogon/calc`. **143 parity tests** passed at Phase 3.3 close; the Neutralizing Gas / Cloud Nine bridge limitation is now patched locally.

---

## 5. System Architecture

### 5.1 Repository Layout

```
my_pochamps_advisor/
├── advisor/
│   ├── damage/                # Engine layer — Showdown mirror only
│   │   ├── formula.py         # ★ ENGINE ENTRY (not damage.py)
│   │   ├── modifiers.py
│   │   ├── status_effects.py
│   │   ├── q12.py
│   │   ├── multihit.py        # ★ NEW (Phase 3.4)
│   │   └── ...
│   ├── parity/                # Parity bridge to @smogon/calc
│   └── format/                # ★ NEW (Phase 4.0) — PoChamps overrides
│       └── pochamps.py
├── core/                      # PokeAPI fetcher, KO name mapping, search
├── data/                      # Static lookup tables
│   ├── moves.py
│   ├── abilities.py
│   └── pochamps_pp_table.py   # (Phase 4.0.3)
├── docs/                      # PRD, Q12_LOOKUP, parity audit notes
│   ├── PRD.md
│   └── Q12_LOOKUP.md
└── tests/                     # pytest suite (397 passing)
    ├── test_damage_parity_abilities_weather.py
    └── test_damage_parity_multihit.py     # ★ NEW (Phase 3.4)
```

### 5.2 Layer Boundaries

| Layer | Responsibility | Forbidden |
|---|---|---|
| `advisor/damage/` | Showdown mirror, pure functions | RNG, PoChamps logic, state mutation |
| `advisor/format/` | PoChamps overrides | Damage formula |
| `advisor/parity/` | Bridge assertions | Engine logic |
| Turn Engine (4.1+) | State mutation, RNG resolution | Damage math (delegates to engine) |

---

## 6. Roadmap

| Phase | Name | Status | Tests |
|---|---|---|---|
| 1.x | Foundation / PokeAPI | ✅ DONE | — |
| 2.x | Localization (KO names) | ✅ DONE | — |
| 3.1 | Core Damage Engine | ✅ DONE | 393 |
| 3.3 | Field & Weather | ✅ DONE (Verified) | **397** (xfail resolved in 3.5) |
| **3.4** | **Multi-hit Moves** | ✅ DONE | **441** |
| 3.5 | Damage Roll & Field Audit | DONE | **453** |
| 3.6 | Critical Hit Sampling | DONE | **485** |
| 4.0 | PoChamps Localization Layer | ⏳ Planned | — |
| 4.1 | Turn Engine | ⏳ Planned | — |
| 5.x | Battle AI (Minimax) | ⏳ Planned | — |
| 6.x | UI Integration (PySide6) | ⏳ Planned | — |

---

## 7. Phase 3.3 Specification — Field & Weather (DONE)

**Completed:** 2026-05-06
**PR:** #3.3-A `feat(3.3): close weather parity gaps`
**Commit:** `42207fb`
**Docs Commit:** `ae71966 docs(3.3): mark Phase 3.3 DONE + enrich xfail reason`
**Branch:** `master`

### 7.1 Coverage

- **Total tests:** 397 (+4)
- **Parity tests:** 143 (+4)
- **Status:** Phase 3.3 originally closed with 396 passed, 1 xfailed; Phase 3.5 resolves the bridge divergence and the test now passes.

### 7.2 Verified Scenarios

| Test | Description | Status |
|---|---|---|
| `sun_water_nerf` | Water moves halved (`2048/4096`) under Sun | ✅ |
| `snow_non_ice_no_boost` | Non-Ice DEF unaffected by Snow | ✅ |
| `sand_non_rock_no_boost` | Non-Rock SpD unaffected by Sand | ✅ |
| `neutralizing_gas_disables_cloud_nine_in_sun` | NG suppresses Cloud Nine -> Sun boost applies | PASS in Phase 3.5 |

### 7.3 Bridge Resolution

Phase 3.5 patches the local `@smogon/calc` bridge to mirror Showdown's active-field ability suppression model:

1. `sim/pokemon.ts` `ignoringAbility()` suppresses Cloud Nine / Air Lock while Neutralizing Gas is active.
2. `effectiveWeather()` keeps the weather condition active; only weather effects are ignored by Cloud Nine / Air Lock.
3. The bridge now removes Cloud Nine / Air Lock from the calc-side Pokemon only when Neutralizing Gas is active, so Sun/Rain/Sand/Snow remain present and resolve correctly.

**Result:** the former strict xfail is now a passing parity regression test.
---

## 8. Phase 3.4 Specification — Multi-hit Moves (DONE)

### 8.0 Hit Count Resolution Model

`resolve_hit_count()` operates under the post-connect assumption: the move is presumed to have passed the initial accuracy check. The minimum return value is 1 for default Tier C moves, not 0. Initial accuracy is handled at a higher layer or supplied directly by advisor flows.

### 8.1 Sub-PR Plan

| PR | Scope | Status |
|---|---|---|
| #3.4-A | Minimum Slice — Bullet Seed / Rock Blast / Icicle Spear + Skill Link | ✅ DONE |
| #3.4-B | Item Modifiers — Loaded Dice (4-5 hit guarantee) | ✅ DONE |
| #3.4-C | Triple Axel/Kick — escalating BP fixed-3 moves | ✅ DONE |
| #3.4-C2 | Population Bomb — deterministic Tier C multiaccuracy | ✅ DONE |
| #3.4-D | Distribution Sampling — probabilistic 2-5 and 1-10 hit resolution | ✅ DONE |

### 8.2 PR #3.4-A — Minimum Slice (Current)

**Branch:** `feat/3.4-multihit-minimum-slice`
**Base:** `master @ ae71966`
**Target:** 397 → 402 tests

#### 8.2.1 Scope (IN)

**Moves (3):**

| Move | Type | Cat | BP | Hits |
|---|---|---|---|---|
| Bullet Seed | Grass | Physical | 25 | 2-5 |
| Rock Blast | Rock | Physical | 25 | 2-5 |
| Icicle Spear | Ice | Physical | 25 | 2-5 |

**Abilities (1):**

- **Skill Link** — forces multihit moves to always roll **5 hits**.

**Hit-count distribution (Smogon/Showdown standard, reference only):**

| Hits | Probability |
|---|---|
| 2 | 35% |
| 3 | 35% |
| 4 | 15% |
| 5 | 15% |
| **Expected** | **~3.166** |

> ⚠️ This PR tests **min(2)**, **max(5)**, and **Skill Link(5 fixed)** only. Probability sampling deferred to PR #3.4-D.

#### 8.2.2 Scope (OUT)

- ❌ Loaded Dice (PR #3.4-B)
- ❌ Population Bomb (PR #3.4-C)
- ❌ Triple Axel / Triple Kick — escalating BP (PR #3.4-C)
- ❌ Hit-miss interruption (PR #3.4-C)
- ❌ Multiscale / Multi-hit ability interactions (separate)
- ❌ Probability distribution sampling (PR #3.4-D)

#### 8.2.3 Engine Design

**Critical rule:** Each hit MUST be calculated as an **independent Q12 damage roll** and then summed. **NEVER** as `single_hit_damage * hit_count`.

```python
def calculate_multihit_damage(
    attacker, defender, move, field, *,
    hit_count: int,
    roll_index: int = 0,  # 0..15
) -> Q12:
    """Each hit is an independent Q12 roll. Sum at the end."""
    total = Q12.zero()
    for hit_idx in range(hit_count):
        hit_dmg = calculate_single_hit_damage(
            attacker, defender, move, field,
            roll_index=roll_index,
            hit_index=hit_idx,  # reserved for escalating-BP moves
        )
        total = total + hit_dmg  # Q12 add
    return total
```

#### 8.2.4 Hit-Count Resolver

```python
def resolve_hit_count(
    move, attacker, *, mode: Literal["min", "max", "expected"] = "min"
) -> int:
    if not is_multihit(move):
        return 1
    if attacker.ability == "skilllink" and move.multihit_is_range:
        return move.multihit_max
    if mode == "min":
        return move.multihit_min
    if mode == "max":
        return move.multihit_max
    raise NotImplementedError("expected mode reserved for PR #3.4-D")
```

#### 8.2.5 Test Plan (5 new tests)

| ID | Test | Hit Count |
|---|---|---|
| T1 | `test_bulletseed_min_hits_2` | 2 |
| T2 | `test_bulletseed_max_hits_5` | 5 |
| T3 | `test_rockblast_min_hits_2` | 2 |
| T4 | `test_iciclespear_max_hits_5` | 5 |
| T5 | `test_skill_link_forces_5_hits` | 5 (Cinccino) |

All tests assert bit-perfect parity with `@smogon/calc(..., {hits: <count>})`.

### 8.3 PR #3.4-B — Loaded Dice ✅ DONE

**Branch:** `feat/3.4-loaded-dice`  
**Tests:** 406 collected, 405 passed, 1 xfailed (+4 parity)

#### Priority Rule (Locked)

```text
Multihit hit-count resolution priority:
1. Skill Link (ability)     -> max hits (range multihit only)
2. Loaded Dice (item)       -> 4 (min) / 5 (max)
3. Default                  -> move's multihit_min / multihit_max
```

#### Verified Scenarios

- Loaded Dice + Bullet Seed (min 4) -> verified.
- Loaded Dice + Rock Blast (max 5) -> verified.
- Loaded Dice + Icicle Spear (min 4) -> verified.
- Skill Link beats Loaded Dice (5 fixed) -> verified.

#### Out of Scope (Tracked)

- Triple Kick/Axel hit-miss interruption -> future PR.
- Population Bomb distribution -> PR #3.4-C2.
- Loaded Dice 4-vs-5 probability -> PR #3.4-D.

### 8.4 PR #3.4-C — Triple Axel / Triple Kick ✅ DONE

**Branch:** `feat/3.4-triple-axel-kick`  
**Commit:** `7fbb84b`  
**Tests:** 410 collected, 409 passed, 1 xfailed (+4 parity)

#### BP Escalation Rule

```text
effective_bp = base_bp * (hit_index + 1)
```

Each hit uses its own escalated BP before the full BP modifier pipeline. The final multihit result is the sum of independent Q12 damage rolls, never `single_hit_damage * hit_count`.

#### Verified Scenarios

- Triple Kick 3 hits escalating BP (10 / 20 / 30) -> verified.
- Triple Axel 3 hits escalating BP (20 / 40 / 60) -> verified.
- Triple Kick + Technician: all hits boosted (`bp <= 60`) -> verified.
- Triple Axel + Technician: all hits boosted (`bp <= 60`) -> verified.

#### Out of Scope (Tracked)

- Hit-miss interruption -> future PR.
- Population Bomb -> PR #3.4-C2.
- Probabilistic hit count -> PR #3.4-D.

### 8.5 PR #3.4-C2 — Population Bomb ✅ DONE

**Branch:** `feat/3.4-population-bomb`  
**Commit:** `8972888`  
**Tests:** 419 collected, 417 passed, 2 xfailed (+8 passing, +1 xfail)

#### Three-Tier Classification

```text
Tier A: range multihit      -> tuple[int, int], e.g. Bullet Seed (2-5)
Tier B: fixed multihit      -> int, e.g. Triple Axel / Triple Kick (3)
Tier C: multiaccuracy fixed -> int + multiaccuracy, e.g. Population Bomb (10)
```

#### Tier C Deterministic Resolution

```text
Default:
  min -> 1
  max -> 10

Skill Link:
  removes multiaccuracy -> 10 guaranteed

Loaded Dice:
  removes multiaccuracy
  min -> 4
  max -> 10
  probabilistic distribution -> PR #3.4-D
```

#### Verified Scenarios

- Population Bomb default min 1 hit -> verified.
- Population Bomb default max 10 hits -> verified.
- Skill Link forces Population Bomb to 10 hits -> verified.
- Loaded Dice deterministic min/max for Population Bomb -> verified.
- Skill Link beats Loaded Dice on Population Bomb -> verified.
- Population Bomb per-hit BP remains fixed at 20 -> verified.
- Technician applies to Population Bomb per hit (`bp <= 60`) -> verified.

#### Out of Scope (Tracked)

- Probabilistic multiaccuracy sampling -> PR #3.4-D.
- Accuracy stat application / hit-miss interruption -> future turn-engine PR.

### 8.6 PR #3.4-C3 — Skill Link x Loaded Dice Tier C Fix ✅ DONE

**Branch:** `feat/3.4-c3-tier-c-loaded-dice-fix`  
**Tests:** 423 collected, 421 passed, 2 xfailed (+4 passing)

#### Interaction Matrix

| Tier | Skill Link only | Loaded Dice only | Both |
|---|---|---|---|
| A | max | 4 or 5 | max (Skill Link wins) |
| B | fixed | fixed | fixed |
| C | 10 | 4..10 uniform | 4..10 uniform (Loaded Dice still applies) |

#### Rationale

Showdown's onModifyMove phase converts Tier A multihit arrays to their max int, which causes Loaded Dice's `targetHits < 4` branch to fail. However, Tier C's Loaded Dice branch checks `targetHits === 10` directly, which Skill Link does not modify. The two effects are independent on Tier C.

PR #3.4-C2 incorrectly assumed Skill Link beats Loaded Dice on Tier C. Fixed in PR #3.4-C3.

### 8.7 PR #3.4-D — Probabilistic Sampling Mode ✅ DONE

**Branch:** `feat/3.4-d-multihit-probabilistic`  
**Tests:** 441 collected, 440 passed, 1 xfailed (+18 passing tests)

#### RNG Layer

`advisor/damage/rng.py` provides a seedable `RNG` wrapper with Showdown-shaped `random(n)` and weighted-choice APIs. It uses Python's Mersenne Twister, not Showdown's `sim/prng.ts`; bit-level PRNG parity is out of scope.

#### Probabilistic Distributions

| Tier | Scenario | Distribution |
|---|---|---|
| A | Default 2-5 range | 2:35%, 3:35%, 4:15%, 5:15% |
| A | Loaded Dice | 4 or 5, uniform |
| A | Skill Link + Loaded Dice | 5 fixed |
| B | Fixed multihit | fixed |
| C | Population Bomb default | post-connect 1 hit guaranteed, hits 2-10 roll 90% and stop on miss |
| C | Loaded Dice | 10 - random(7), uniform 4-10 |
| C | Skill Link | 10 fixed |
| C | Skill Link + Loaded Dice | uniform 4-10; Loaded Dice still applies |

#### Source References

- Tier A weighted 35/35/15/15: Showdown `sim/battle-actions.ts` lines 864-865.
- Tier A Loaded Dice 4/5: Showdown `sim/battle-actions.ts` lines 866-867.
- Tier C Loaded Dice 4-10: Showdown `sim/battle-actions.ts` line 876.
- Tier C multiaccuracy loop: Showdown `sim/battle-actions.ts` lines 907-933.

#### Phase 3.4 Closure

Phase 3.4 deterministic and probabilistic multihit mechanics are complete. Remaining accuracy-modifier interactions such as Compound Eyes and Hustle are intentionally outside this phase.

---

## 9. Phase 3.5 Specification — Damage Roll & Field Audit (DONE)

**Completed:** 2026-05-06  
**Branch:** `feat/3.5-damage-roll-and-field-audit`  
**Version:** v0.7.0  
**Tests:** 453 collected, 453 passed, 0 xfailed, 0 skipped

### 9.1 Track A — Field Bridge Resolution

The Phase 3.3 Neutralizing Gas / Cloud Nine parity case is no longer xfailed. The local bridge now mirrors Showdown's `sim/pokemon.ts` `ignoringAbility()` and `effectiveWeather()` behavior: Neutralizing Gas suppresses weather-related abilities, but the weather condition itself remains active.

Verified controls:

| Scenario | Expected |
|---|---|
| Neutralizing Gas + defender Cloud Nine + Sun | Sun remains active; Fire damage is boosted |
| Air Lock + Sun | Weather damage modifier is suppressed |
| Cloud Nine + Sun | Weather state persists; only effects are suppressed |

### 9.2 Track B — Damage Roll Layer

`advisor/damage/roll.py` adds the 16-value damage roll projection used by Pokemon Showdown.

**Showdown source:** `pokemon-showdown/sim/battle.ts` `randomizer()`, lines 2404-2406.

```python
damage = floor(base_damage * (100 - random(16)) / 100)
```

This is equivalent to uniform integer percentages 85, 86, ..., 100.

| Mode | Return | Behavior |
|---|---|---|
| `min` | `int` | `floor(base * 85 / 100)` |
| `max` | `int` | `base` |
| `deterministic` | `tuple[int, int]` | `(min, max)` |
| `probabilistic` | `int` | Seedable sampled roll via `advisor.damage.rng.RNG` |
| `distribution` | `dict[int, int]` | All 16 roll outcomes, preserving duplicate damage values |

### 9.3 Calculator Compatibility

`advisor/damage/calculator.py` provides an opt-in roll projection wrapper around `formula.calc_damage_rolls()`.

| Call | Return |
|---|---|
| `calculate(ctx)` | max-roll `int` (backward compatible default) |
| `calculate(ctx, roll_mode="deterministic")` | `(min, max)` |
| `calculate(ctx, roll_mode="distribution")` | 16-roll distribution map |

Default `roll_mode="max"` preserves existing single-value callers. Tuple and distribution returns are opt-in.

### 9.4 Phase 3.5 Closure

- Final Phase 3.5 count: **453 collected, 453 passed**.
- xfailed: **0**.
- skipped: **0**.
- Phase 3.3 field divergence is closed.
- Phase 3.5 damage roll distribution layer is complete.

---

## 10. Phase 3.6 Specification — Critical Hit Sampling (DONE)

**Completed:** 2026-05-07  
**Branch:** `feat/3.6-critical-hit-sampling`  
**Version:** v0.8.0  
**Tests:** 485 collected, 485 passed, 0 xfailed, 0 skipped

### 10.1 Critical Hit Probability Table

`advisor/damage/crit.py` models the Gen 9 critical-hit stage table exactly:

| Stage | Probability |
|---|---|
| 0 | 1/24 |
| 1 | 1/8 |
| 2 | 1/2 |
| 3+ | 1/1 |

Showdown source: `sim/battle-actions.ts` lines 1627-1645 (`ModifyCritRatio`, Gen 9 `critMult = [0, 24, 8, 2, 1]`, and `randomChance(1, critMult[critRatio])`).

### 10.2 Modifier Sources

| Source | Effect |
|---|---|
| High-crit moves (`critRatio: 2`) | +1 stage |
| Always-crit moves (`willCrit: true`) | Guaranteed crit |
| Super Luck | +1 stage |
| Merciless vs poisoned target | Guaranteed crit |
| Razor Claw / Scope Lens | +1 stage |
| Stick on Farfetch'd / Lucky Punch on Chansey | +2 stages |
| Focus Energy / Lansat Berry effect | +2 stages |
| Dragon Cheer | +1 stage, +2 for Dragon-type users |
| Battle Armor / Shell Armor / Lucky Chant | Blocks crit |

Showdown source citations:

- `data/moves.ts`: `critRatio: 2` entries and `willCrit: true` entries, e.g. lines 190, 5890, 6267, 18146, 18554, 20792.
- `data/abilities.ts`: Battle Armor lines 345-346, Merciless lines 2527-2528, Shell Armor lines 4177-4178, Super Luck lines 4658-4659.
- `data/items.ts`: Lansat Berry line 3323, Lucky Punch line 3522, Razor Claw line 5090, Scope Lens line 5555, Stick line 6097.
- `sim/battle-actions.ts`: CriticalHit blocker event lines 1649-1650.

### 10.3 Five-Mode Contract

| Mode | Return | Behavior |
|---|---|---|
| `min` | `bool` | `False` (no crit) |
| `max` | `bool` | `True` unless blocked |
| `deterministic` | `tuple[bool, bool]` | `(False, True)` unless blocked |
| `probabilistic` | `bool` | Seedable sampled crit outcome via `advisor.damage.rng.RNG` |
| `distribution` | `dict[bool, int]` | Exact numerator counts, e.g. `{True: 1, False: 23}` |

### 10.4 Damage Modifier and Composition Order

Gen 9 critical hits use `floor(base_damage * 1.5)`.

Showdown source: `sim/battle-actions.ts` lines 1752-1755 (`crit - not a modifier`, `baseDamage = tr(baseDamage * ... 1.5)`), followed by the randomizer at line 1759.

```
Base damage
  -> weather/base field modifiers
  -> critical hit 1.5x
  -> 16-roll
  -> STAB / type effectiveness / final modifiers
```

`advisor/damage/calculator.py` integrates crit with `crit_mode="min"` by default. This is intentionally asymmetric with `roll_mode="max"` because both defaults preserve v0.7.0 output: historical calls were non-crit max-roll single integers.

### 10.5 Phase 3.6 Closure

- Final Phase 3.6 count: **485 collected, 485 passed**.
- xfailed: **0**.
- skipped: **0**.
- All stochastic damage inputs are now present: multihit count, damage roll, critical hit.
- Phase 4 KO probability composition can begin.

---

## 11. Phase 4.0 Specification — PoChamps Localization Layer

### 11.1 `advisor/format/pochamps.py`

```python
def get_paralysis_full_para_rate() -> float: return 0.125
def get_sleep_wake_turns()           -> int:   return 3
def get_freeze_thaw_rate()           -> float: return 0.25
def get_freeze_max_turns()           -> int:   return 3
```

### 11.2 FormatProfile System

```python
class FormatProfile(Enum):
    SHOWDOWN  = "showdown"
    POCHAMPS  = "pochamps"
```

Turn Engine reads the profile at init. **Default = SHOWDOWN** for engine purity (UI can override to POCHAMPS).

### 11.3 `data/pochamps_pp_table.py`

PP cap lookup, used by Turn Engine and Battle AI.

### 11.4 Format Isolation Tests

- Assert PoChamps overrides differ from Showdown defaults.
- Assert Damage Engine output is **identical** regardless of profile.

### 11.5 Implementation Layer Map

| Override | Engine Layer | Phase |
|---|---|---|
| Status RNG | Turn Engine | 4.0 / 4.1 |
| PP Caps | Turn Engine + AI | 4.0.3 / 5.x |
| Mega-only gimmick | UI + Turn Engine | 4.x |

---

## 12. Quality Gates / Definition of Done

### 12.1 PR-Level DoD

- [ ] All new tests pass
- [ ] No regressions in existing test suite
- [ ] Q12 invariant preserved (no float leakage)
- [ ] Code added in correct architectural layer
- [ ] Commit message follows convention: `feat(<phase>): <summary> (PR #<id>)`
- [ ] PR description states test count delta (e.g., "397 → 402")
- [ ] `xfail` cases (if any) include detailed `reason` with ground-truth references and `strict=True`

### 12.2 Phase-Level DoD

- [ ] All sub-milestones complete
- [ ] PRD updated to reflect new state
- [ ] Q12_LOOKUP audited if new modifiers added
- [ ] Parity bridge run; no regressions
- [ ] Commit boundary clean (no squashed cross-PR pollution)
- [ ] Phase status flipped from 🚧 IN PROGRESS to ✅ DONE in § 6 Roadmap

---

## 13. Re-Entry Protocol — Common Misconceptions

> 📖 **Read this section first when resuming after a break.**

### 13.1 DO NOT assume:

| Misconception | Reality |
|---|---|
| "Terastal exists in this project." | ❌ BANNED. Only Mega Evolution is allowed. |
| "Z-Moves or Dynamax exist." | ❌ Both BANNED. |
| "Paralysis full-para is 25%." | In PoChamps it is **12.5%**. |
| "Sleep is 1-3 turn RNG." | In PoChamps it is **3 turns fixed**. |
| "Freeze thaw is 20%." | In PoChamps it is **25%, capped at 3 turns**. |
| "PP equals Bulbapedia values." | PoChamps caps: 5→8, 10→12, 15→16, 20+→20. |
| "PoChamps overrides go in `status_effects.py`." | ❌ NO. They go in `advisor/format/pochamps.py` (Phase 4.0). |
| "`damage.py` is the engine entry." | ❌ NO. `formula.py` is the entry point. |
| "Multihit damage = single_hit × count." | ❌ NO. Each hit is an **independent Q12 roll**, then summed. |
| "If `@smogon/calc` differs, our engine is wrong." | Not always. Verify against Showdown sim source first (see § 7.3). |

### 13.2 Architectural Boundaries (Quick Reference)

```
Damage Engine (3.x)         = Showdown standard mirror
advisor/format/pochamps.py  = All PoChamps overrides (4.0)
Turn Engine (4.1+)          = Imports both, applies profile
```

### 13.3 Sanity Checks Before Coding

| Question | Layer |
|---|---|
| Is this rule in Showdown standard? | Damage Engine OK |
| Is this rule PoChamps-specific? | `format/` layer only |
| Is this RNG/probability? | Turn Engine only |
| Does this need state mutation? | Path A (Turn Engine) |
| Pure function over inputs? | Path B (Damage Engine) |

---

## 14. 3-Tier AI Orchestration Model

### 14.1 Roles

| Tier | Role | Responsibility |
|---|---|---|
| **T1** | Architect / Product Owner (Human) | Defines vision, priorities, acts as **Quality Gate** for Bit-Perfect Parity Law |
| **T2** | Prompt Engineer / QA Lead (Claude) | Translates T1 requirements into precision prompts for T3, gap analysis, audits architectural integrity |
| **T3** | Implementer / Code Author (GPT-5.5) | Generates Python code, diffs, unit tests based on Q12 fixed-point standard |

### 14.2 Operating Principles

1. **T1 has final authority** on scope and architectural boundaries.
2. **T2 owns "Verify, Don't Trust"** — every parity discrepancy triggers ground-truth investigation before code changes.
3. **T3 produces "Diff-Ready Output"** — exact code/markdown/test strings for zero-context-loss handoff.
4. **"Plan B" (Safety/Investigation) > Quick Merge** when parity divergence appears.

### 14.3 Workflow Pattern

```
T1 (Decision) → T2 (Prompt + Audit) → T3 (Diff-Ready Code) → T1 (Quality Gate)
                                              ↓
                                     T2 (Re-audit on report)
```

---

## 15. Risks & Open Questions

### 15.1 Pipeline Ordering for Weather (RESOLVED)

✅ Verified during Phase 3.3 implementation. Weather modifier insertion point in `formula.py` `chainMods` sequence is correct.

### 15.2 PoChamps Spec Source (OPEN)

Status RNG overrides (12.5% para, 3-turn sleep, 25%/3-turn freeze) and PP caps need a citable source to lock spec before data cutoff (2026-06-16).

### 15.3 Mega Evolution Implementation (DEFERRED)

Mega forms exist in PokeAPI but trigger logic (one-per-team, activation timing) requires Turn Engine state. **Deferred to 4.1.**

### 15.4 Format Profile Default (DECIDED)

✅ Default profile = **SHOWDOWN** (engine purity). UI provides override to POCHAMPS.

### 15.5 Multi-hit Probability Distribution (RESOLVED)

Probabilistic 2-5 and Population Bomb hit resolution are implemented in PR #3.4-D with seedable `advisor.damage.rng.RNG` tests.

### 15.6 `@smogon/calc` Bridge Divergence (RESOLVED)

Cloud Nine / Neutralizing Gas bridge divergence is resolved in Phase 3.5 by suppressing Cloud Nine / Air Lock only in the local calc bridge when Neutralizing Gas is active.

---

## 16. Glossary

| Term | Definition |
|---|---|
| **Q12** | Fixed-point representation with Base 4096 (1.0 = 4096) |
| **chainMods** | Smogon-canonical sequential modifier accumulation pattern |
| **Bit-Perfect Parity** | 1:1 numerical match with `@smogon/calc` v0.11.0 `gen789.ts` |
| **Path A** | Stateful turn engine layer (mutates battle state) |
| **Path B** | Pure functional damage predicates (no side effects) |
| **SSoT** | Single Source of Truth — each rule in exactly one module |
| **PoChamps** | Pokémon Champions tournament format (custom Gen 9 derivative) |
| **xfail** | pytest expected-failure marker (with `strict=True` to flag unexpected passes) |
| **Bridge** | `advisor/parity/` adapter to `@smogon/calc` for parity assertions |
| **Skill Link** | Ability forcing range-multihit moves to always roll max hits (5) |
| **Critical Hit Stage** | Gen 9 crit-ratio stage resolved from move, ability, item, and volatile modifiers |
| **Crit Blocker** | Defender-side effect such as Battle Armor, Shell Armor, or Lucky Chant that prevents critical hits |

---

## 17. Appendix A — Q12 Lookup Reference

| Multiplier | Q12 Value | Common Use |
|---|---|---|
| ×0.25 | `1024` | Quad-resist |
| ×0.5 | `2048` | Resist, Sun-vs-Water nerf, screens (singles) |
| ×1.0 | `4096` | Identity |
| ×1.3 | `5325` | Transistor (Gen 9), Expert Belt |
| ×1.5 | `6144` | STAB, Sun-vs-Fire boost, Sand SpD (Rock) |
| ×2.0 | `8192` | Super-effective |
| ×4.0 | `16384` | Quad-effective |

Full table: `docs/Q12_LOOKUP.md`.

---

## 18. Version History

### v0.8.0 (current, 2026-05-07)

- PR #3.6 merged: critical hit sampling and modifier resolution.
- Test count: 485 collected, 485 passed, 0 xfailed, 0 skipped.
- Added `advisor/damage/crit.py` with crit stage, probability, blocker, five-mode roll, and Gen 6+ 1.5x modifier helpers.
- Integrated `crit_mode` into `advisor/damage/calculator.py`; default `crit_mode="min"` preserves v0.7.0 non-crit behavior.
- All stochastic damage inputs needed for Phase 4 KO probability composition are now present.

### v0.7.0 (2026-05-06)

- PR #3.5 merged: damage roll distribution + field divergence audit.
- Test count: 453 collected, 453 passed, 0 xfailed, 0 skipped.
- Resolved the Phase 3.3 Neutralizing Gas / Cloud Nine bridge xfail.
- Added `advisor/damage/roll.py` and `advisor/damage/calculator.py` roll-mode integration.
- Default calculator behavior remains max-roll `int`; ranges and distributions are opt-in.

### v0.6 (2026-05-06)

- PR #3.4-D merged: probabilistic multihit sampling mode.
- Test count: 441 collected, 440 passed, 1 xfailed.
- Multihit Phase 3.4 marked DONE.
- Remaining xfail at v0.6 was the Phase 3.3 Neutralizing Gas / Cloud Nine bridge divergence; it is resolved in v0.7.0.

### v0.5.1 (2026-05-06)

- PR #3.4-C3 fixed Skill Link + Loaded Dice interaction on Tier C.
- Test count: 423 collected, 421 passed, 2 xfailed.
- Post-connect hit-count model documented for `resolve_hit_count()`.

### v0.5 (2026-05-06)

- PR #3.4-C2 merged: Population Bomb deterministic Tier C multiaccuracy.
- Test count: 419 collected, 417 passed, 2 xfailed.
- Loaded Dice and Skill Link now cover Tier A range moves and Tier C multiaccuracy moves.
- Probabilistic Population Bomb distribution remains xfailed for PR #3.4-D.

### v0.4 (2026-05-06)

- PR #3.4-C merged: Triple Axel / Triple Kick BP escalation.
- Test count: 410 collected, 409 passed, 1 xfailed.
- Technician threshold verified for all Triple Axel/Kick hits (`bp <= 60`).

### v0.3.2 (2026-05-06)

- PR #3.4-B merged: Loaded Dice + ability/item priority lock.
- Test count: 406 collected, 405 passed, 1 xfailed.
- Re-Entry Protocol updated with Loaded Dice misconceptions.

### v0.3 (2026-05-06)

- ✅ **Phase 3.3 marked DONE** (Verified). 397 tests, 143 parity, 1 xfail (NG/Cloud Nine bridge limitation).
- ✅ Added § 7 Phase 3.3 specification with ground-truth divergence record.
- ✅ Added § 8 Phase 3.4 specification (Multi-hit Moves) with 4-PR sub-plan.
- ✅ Added § 12 (3-Tier AI Orchestration Model).
- ✅ Updated Re-Entry Protocol (§ 11) with multihit-related misconception.
- ✅ Marked § 13.1 (Weather pipeline ordering) as RESOLVED.
- ✅ Marked § 13.4 (Format profile default = SHOWDOWN) as DECIDED.
- ✅ Added § 13.5 (Multi-hit probability deferral).
- ✅ Added § 13.6 (Upstream bridge issue tracking).

### v0.2 (2026-05-06)

- Added § 2.5 (PoChamps Format Spec).
- Removed proposed "Type Edge Cases" milestone (was based on hallucinated Tera/Stellar mechanics).
- Added Phase 4.0 (PoChamps Localization Layer).
- Added Re-Entry Protocol section.

### v0.1 (initial)

- Phases 1-3.1 scope. Type Edge Cases proposed as 3.6 (later removed).

---

## 19. Document Control

| Field | Value |
|---|---|
| **Owner** | Lead Systems Architect (T1) |
| **Document Status** | 🟢 LIVING DOCUMENT |
| **Last Reviewed** | 2026-05-06 |
| **Next Review Trigger** | Phase 4 KO probability composer entry |
| **Storage** | `docs/PRD.md` in `josun1392/my_pochamps_advisor` |
| **Amendment Process** | All Constitution changes (§ 3) require explicit T1 decision logged in § 16 |

---

*End of PRD 2.0 (v0.8) — Master Ball Advisor*
