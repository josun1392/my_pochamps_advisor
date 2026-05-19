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

- **Milestone:** `5.0` Multi-hit Moves & Chip Damage Integration - **COMPLETE**
- **HEAD:** `fa8501d`
- **Tag:** `v0.11.0`
- **Tests:** 602 passing, 0 failures, 0 xfail
- **Performance:** N=4 multi-hit + chip hard ceiling met; worst measured 17.886 ms

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

## Phase 5: COMPLETE

- **Completed:** 2026-05-07
- **Tag:** `v0.11.0`
- **Merge commit:** `fa8501d`
- **Tests:** 560 -> 602 (+42), 0 failures, 0 xfail
- **Scope:** Multi-hit move probability distributions plus deterministic residual chip integration.
- **Multi-hit:** Tier A 2-5 distribution, Skill Link, Loaded Dice, and Population Bomb Tier C support.
- **Chip:** Burn, poison, toxic, Leech Seed, Curse, sand/hail/snow, and binding residuals.
- **Precision:** `Fraction` probability mass throughout; Q12 damage rolls remain integer-only.
- **Performance:** N=4 multi-hit + chip worst measured 17.886 ms with crit-mixed Bullet Seed; Population Bomb + Loaded Dice measured 3.500 ms. Both remain under the 100 ms hard ceiling.

### Phase 5.1: Performance Optimization Accepted

- **Branch:** `feat/phase-5.1-bullet-seed-perf`
- **Diagnosis:** H2/H4 - missing survivor bucket merge plus convolution loop overhead.
- **Fix:** Composer survivor state uses dense integer buckets below KO threshold; `Fraction` construction is deferred to the final by-turn probability boundary.
- **Tests:** 602 default -> 604 with slow (+2), 0 failures, 0 xfail.

| Case | Before | After |
|---|---:|---:|
| bullet_seed_default_burn_no_crit | 13.608 ms | 6.137 ms |
| bullet_seed_default_burn_with_crit | 17.886 ms | 8.861 ms |
| bullet_seed_loaded_dice_toxic_with_crit | 2.207 ms | 1.161 ms |
| population_bomb_loaded_dice_poison_with_crit | 3.500 ms | 2.388 ms |

#### Perf Test Strategy

Perf regression tests use the `slow` pytest marker and are excluded from the default test run. This isolation prevents resource contention with 600+ functional tests that otherwise inflate measurements 2.1~2.6x in shared-environment runs.

**Usage:**
- Default development: `pytest` (602 tests, perf tests excluded)
- Perf verification: `pytest -m slow` (2 perf tests, clean env)
- Full coverage: `pytest -m ""` (604 tests, perf may be flaky)

**Threshold:** 15ms median (warmup + 3-run) on the bullet_seed worst case. T3 standalone baseline 8.861ms; threshold provides ~70% headroom for per-machine variance while still catching algorithmic regressions.

**Phase 6 note:** New perf tests (Parental Bond, Accuracy-Turn) should inherit the `slow` marker via module-level `pytestmark`.

Soft target 5ms partially recovered. The with_crit case at 8.86ms is accepted; hard ceiling 100ms maintained with >90% headroom. Deferred deeper optimization (FFT-style convolution) is out of scope until Phase 6 baseline is established.

T1 to record local measurement post-merge for cross-validation.

### Phase 6 Outlook

- Parental Bond interaction modeling.
- Accuracy and turn-engine interactions for move continuation and chip timing.
- Broader battle-state integration on top of the Phase 4/5 probability core.

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

---

## v0.5.2 LLM Advice Panel Success Verification

Completed: 2026-05-08

- Verified `scripts/spike_advisor.py` with a valid Gemini API key.
- LLM recommendation returned successfully for the Mega Kangaskhan vs Garchomp spike.
- Recommendation selected `Return`, identified no OHKO, and flagged Garchomp `Outrage` as the main threat.
- Token usage: 1960 input / 148 output / 0 cached.
- Estimated cost: `$0.000958`.
- UI success path confirmed by screenshot:
  - `LLMAdvicePanel` displays the recommendation.
  - Status bar shows `Done | input 1960 / output 148 | $0.0009580`.
  - Fallback cost label also shows the token/cost summary.
- Existing validation remains: `613 passed, 2 deselected`.

Status: v0.5.2 success path verified. Ready for the next UI integration slice.

---

## v0.8.1 — Manual move payload verification attempt

Completed: 2026-05-14

Purpose:
- Attempt to verify the v0.8 manual move selection path from UI-selected Pokemon state to the LLM payload and Gemini response.
- Record the verified payload behavior separately from the blocked Gemini success path.
- Preserve the existing pytest baseline.

Partial verification succeeded:
- Manual move selection path exercised with Charizard vs Garchomp and slot 1 set to Flamethrower.
- Confirmed the selected move button text updates to `화염방사`.
- Confirmed `moves.my_available_moves` includes only the user-selected Flamethrower move.
- Confirmed empty move slots are omitted from `moves.my_available_moves`.
- Confirmed `moves.my_selected_move` matches `moves.my_selected_move_index == 0`.
- Confirmed `moves.move_data_status` is `user_selected_partial_v0.8`.
- Confirmed cache learnsets are not included in the LLM payload.
- Confirmed `moves.opponent_available_moves` remains empty in v0.8.
- Confirmed the UI running state sets the request button disabled, recommendation text to `분석 중...`, and status bar to `Analyzing...`.
- Confirmed the UI recovers after a failed Gemini call by re-enabling the request button and showing the fallback error label.

Blocked / not verified:
- `GEMINI_API_KEY` was present in the Codex environment; `GOOGLE_API_KEY` was not present.
- The Gemini endpoint returned HTTP 400 `INVALID_ARGUMENT` in this environment.
- Gemini success response was not verified.
- LLM response quality was not evaluated.
- The success status bar path `Done | input N / output N | $...` was not verified in this run.
- No API key value was printed, saved, or committed.

Tests:
- `uv run pytest -q`
- Result: 613 passed, 2 deselected.

Remaining limitations:
- A valid T1 local Gemini run is still needed to verify the v0.8.1 success response path.
- Opponent moves are not connected yet.
- Damage/OHKO/2HKO/KO chance are not connected yet.
- EV/IV/nature/item/final stats are not connected yet.
- LLM response quality for the v0.8 selected-move payload remains unjudged because the Gemini call did not succeed.

---

## v0.8.3 — Advisor Payload Contract

Purpose:
- Freeze the current UI-to-LLM payload contract before selected-move damage estimates are added.
- Keep the Gemini recommendation layer from treating incomplete UI metadata as confirmed battle math.

Added:
- `docs/advisor_payload_contract.md`
- `llm/advisor_payload_contract.py`
- `tests/test_advisor_payload_contract.py`

Contract summary:
- Current payload mode remains `ui-selected-pokemon-v0.8`.
- Payload includes selected Pokemon identity, type, base stats, abilities, HP percent, selected move index, and user-confirmed move metadata.
- Payload explicitly does not include final stats, EV/IV/nature, held items, weather, terrain, boosts, exact HP, opponent moves, damage rolls, OHKO/2HKO/KO chance, turn order, or Turn Engine state.
- Guardrails prohibit the LLM from inferring exact damage, KO odds, speed order, survival, unprovided stats/items/field state, or Terastallization.

Next milestones:
- `v0.9 — Selected Move Damage Estimate`
- `v0.10 — Four-Move Damage Comparison`

---

## v0.9 — Selected Move Damage Estimate

Purpose:
- Add a default-assumption damage estimate for the currently selected user-confirmed move.
- Keep the estimate scoped to `moves.my_selected_move.damage_estimate`.
- Preserve the v0.8.3 guardrails so the LLM does not treat the estimate as final battle damage.

Implemented:
- `llm/advisor_damage_estimate.py`
- Default assumptions: level 50, IV 31 all, EV 0 all, neutral nature, no item, no boosts, no weather, no terrain, no screens, no crit, no ability effects, non-spread single-target estimate.
- `MainWindow._build_llm_battle_input()` now attaches the selected move estimate through the helper instead of doing damage math in UI code.
- `docs/advisor_payload_contract.md` and `llm/advisor_payload_contract.py` now describe the v0.9 estimate and limitations.

Out of scope maintained:
- No OHKO/2HKO/KO chance.
- No four-move comparison.
- No opponent moves.
- No EV/IV/nature/item/final stat UI.
- No Turn Engine.
- No `advisor/damage/` or `advisor/probability/` engine changes.
