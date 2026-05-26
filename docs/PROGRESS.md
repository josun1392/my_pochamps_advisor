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

## v0.9.2b - MoveSearchBox Champions Fixture Integration

Purpose:
- Route move search candidates through the sample Champions movepool fixtures instead of PokeAPI historical Pokemon learnsets.
- Keep PokeAPI move data as metadata only.

Implemented:
- MoveSearchBox now receives candidate move ids from `ChampionsMovePoolRepository`.
- Fixture-backed Pokemon use their sample Champions move ids.
- Pokemon without a Champions movepool fixture show an unavailable search state instead of silently falling back to PokeAPI learnsets.
- Added regression tests for Charizard, Froslass, Vanilluxe, Starmie, missing fixtures, and metadata lookup.

Out of scope maintained:
- No full Serebii/RotomLabs scraping.
- No full roster Champions movepool cache.
- No damage engine changes.
- No four-move comparison.

---

## v0.9.2c - Serebii Champions Full Movepool Cache

Purpose:
- Replace narrow sample movepools with Serebii-derived Champions movepool fixtures for the full local Champions roster.
- Keep PokeAPI pokemon learnsets out of move legality decisions.

Implemented:
- Added `scripts/build_serebii_champions_movepools.py` to parse Serebii Champions Pokédex Standard Moves tables.
- Added `scripts/verify_champions_movepools.py`.
- Generated movepool fixtures for all 276 unique local Champions battle entities.
- Preserved global denial of `tera-blast` and verified `hidden-power` is absent.
- Marked `pawmot` as `unavailable_source_error` because Serebii Champions currently returns 404 for its page.

Verification:
- `uv run python scripts/verify_champions_movepools.py`
- Result: 276 entities, 17,115 listed move entries, unavailable source fixtures: `pawmot`.

Out of scope maintained:
- No RotomLabs scraping.
- No automatic scheduled scraping.
- No damage engine changes.
- No four-move damage comparison.

---

## v0.9.2d - Champions Move Korean Name Coverage

Purpose:
- Ensure every move in the Serebii-derived Champions movepool cache has a Korean display/search name.
- Keep move selection working even when PokeAPI move metadata is not locally cached.

Implemented:
- Added `scripts/update_champions_move_ko_mapping.py`.
- Updated `data/ko_mapping.json` for all 490 Champions move ids.
- Added manual Korean-name overrides for recent moves that PokeAPI does not localize yet.
- Added Champions movepool metadata fallback in `MoveRepository`.
- Verified `expanding-force` maps to `와이드포스` and can be searched for Starmie.

Verification:
- `uv run pytest -q`
- Result: 648 passed, 2 deselected.

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

---

## v0.10 - Four-Move Damage Comparison

Purpose:
- Add default-assumption damage estimates for each user-confirmed move slot.
- Let the LLM compare the Q/W/E/R moves already selected in the UI without adding KO odds or full battle state.

Implemented:
- `moves.my_available_moves[*].damage_estimate` now uses the same default-assumption schema as the selected move.
- `moves.my_selected_move.damage_estimate` remains available for backward-compatible selected-move advice.
- Status moves and incomplete move payloads return unavailable schemas instead of inferred damage.
- Payload mode updated to `ui-selected-pokemon-v0.10`.

Out of scope maintained:
- No OHKO/2HKO/KO chance.
- No opponent moves.
- No EV/IV/nature/item/final stat UI.
- No weather/terrain/boost/screen UI.
- No Turn Engine.
- No `advisor/damage/` or `advisor/probability/` engine changes.

---

## v0.10.1 - Four-Move Damage Comparison verification

Purpose:
- Verify the v0.10 four-move damage payload path before moving to the next feature milestone.

Verified:
- Repository started clean and synced with `my_pochamps/master`.
- Offscreen payload check confirmed `moves.my_available_moves[*].damage_estimate` is attached for four user-confirmed move slots.
- Selected move consistency confirmed: `moves.my_selected_move.damage_estimate.selected_move_id` matched the selected slot's move id.
- Damaging moves returned default-assumption `damage_range`, `percent_range`, and 16 rolls.
- Status move handling confirmed with `will-o-wisp` returning `unavailable_status_move`.
- KO chance, OHKO chance, and 2HKO chance fields were absent from available-move estimates.
- Offscreen UI launch succeeded with `Master Ball Advisor v0.10`.
- LLM advice button state transition was verified: enabled -> disabled while running -> enabled after completion state.

Gemini:
- Actual Gemini call was verified with `GEMINI_MODEL=gemini-2.5-flash`.
- Gemini returned a recommendation successfully for Charizard vs Gardevoir with four user-confirmed moves.
- The response selected `Overheat` and compared it using the provided damage estimate: 49.0-58.7% of Gardevoir's default max HP.
- The response preserved the main limitation: estimates use default assumptions and are not final battle damage.
- The response did not claim OHKO, 2HKO, KO chance, survival, Tera, EVs, items, or final stats.
- No API key or secret value was printed or committed.
- The UI success path displayed usage (`input 4031 / output 52`) and re-enabled after completion.
- Cost display showed `$0.0000000`, indicating pricing metadata for `gemini-2.5-flash` still needs a TokenLogger update.

Verification:
- `uv run pytest -q`
- Result: 650 passed, 2 deselected.

Remaining limitations:
- Damage estimates remain default-assumption references, not final battle damage.
- EV/IV/nature/item/final stats, field state, exact HP, opponent moves, OHKO/2HKO/KO chance, and Turn Engine remain unconnected.

---

## v0.10.2 - Gemini Cost Logging Semantics

Purpose:
- Clarify what the UI cost number means after `gemini-2.5-flash` showed `$0.0000000`.
- Distinguish Free Tier zero-cost estimates from unknown model pricing.

Implemented:
- Added explicit pricing statuses to `TokenLogger`:
  - `free_tier_zero_cost`
  - `paid_tier_estimated_cost`
  - `unknown_model_or_unknown_pricing`
- Treated `gemini-2.5-flash` as a Free Tier zero-cost estimate in the local logger.
- Preserved paid-tier estimated cost behavior for existing priced models.
- Preserved warnings for unknown model pricing.
- Added `pricing_status` and `pricing_status_counts` to JSONL records and session summaries.
- Updated the UI cost label to show:
  - `Free tier | input N / output N | $0.0000000`
  - `Paid estimate | input N / output N | $...`
  - `Pricing unknown | input N / output N`

Notes:
- The official Gemini API pricing page distinguishes Free Tier from Paid Tier pricing.
- This logger reports local estimated cost semantics only; actual billing depends on the user's Google account, project, tier, limits, and current Gemini pricing.
- Prices and Free Tier availability can change and should be reviewed against the official Gemini API pricing page before budget-sensitive use.

Verification:
- `uv run pytest tests/test_token_logger.py tests/test_advisor_payload_contract.py -q`
- Result: 20 passed.

---

## v0.11 - Opponent Move Payload

Purpose:
- Add opponent move context to the LLM payload without treating possible moves as confirmed.
- Keep v0.10 my-side four-move damage comparison intact.

Implemented:
- Added top-level `opponent_moves` to the advisor payload.
- Added `known_moves` from user-confirmed opponent Q/W/E/R slots.
- Added `candidate_moves` from the Serebii-derived Champions movepool cache.
- Capped `candidate_moves` at 24 entries.
- Added `confidence: "possible_not_confirmed"` to all candidate moves.
- Removed known move ids from candidate moves to avoid duplicate semantics.
- Kept legacy `moves.opponent_available_moves` as an empty compatibility field.
- Updated payload contract guardrails so Gemini must not treat candidate moves as confirmed.

Out of scope maintained:
- No opponent damage estimate.
- No OHKO/2HKO/KO chance.
- No speed or turn order.
- No Turn Engine.
- No EV/IV/nature/item/final stats UI.
- No `advisor/damage/` or `advisor/probability/` engine changes.

Verification:
- Manual payload check confirmed Garchomp `Earthquake` appears in `opponent_moves.known_moves`.
- Confirmed `opponent_moves.candidate_moves` is capped at 24 and labeled `possible_not_confirmed`.
- Confirmed known move ids are removed from candidate moves.
- Confirmed `moves.opponent_available_moves` remains `[]`.
- Confirmed opponent moves do not include `damage_estimate`.
- Confirmed v0.10 my-side `damage_estimate` still appears.
- `uv run pytest -q`
- Result: 657 passed, 2 deselected.

---

## v0.11.1 - Opponent move payload Gemini verification

Purpose:
- Verify that the v0.11 opponent move payload separates known opponent moves from possible candidate moves.
- Attempt a Gemini quality check for known/candidate move semantics.

Payload verification:
- Confirmed `opponent_moves.known_moves` includes user-confirmed Garchomp `Earthquake`.
- Confirmed known moves use `source: "user_confirmed"`.
- Confirmed `opponent_moves.candidate_moves` is generated from the Champions movepool cache.
- Confirmed every candidate move uses `confidence: "possible_not_confirmed"`.
- Confirmed candidate moves are capped at 24.
- Confirmed known move ids are removed from candidate moves.
- Confirmed `moves.opponent_available_moves` remains the legacy empty list.
- Confirmed opponent moves do not include `damage_estimate`.
- Confirmed my-side four-move `damage_estimate` remains present.

Gemini:
- Actual Gemini call was attempted with `GEMINI_MODEL=gemini-2.5-flash`.
- The Codex tool environment returned `API_KEY_INVALID`, so Gemini response quality could not be verified in this run.
- No API key or secret value was printed or committed.

T1 local app verification:
- Gemini call succeeded from the local PySide app.
- Status bar showed Free Tier cost semantics: `Free tier | input 6473 / output 75 | $0.0000000`.
- In a Charizard vs Garchomp scenario, Gemini recommended `Earthquake` based on the four-move damage comparison.
- The response mentioned the default-assumption limitation.
- The response did not claim KO, OHKO, or 2HKO.
- The response did not assert EVs, IVs, nature, items, boosts, speed order, or final stats.
- No candidate-move overclaim was observed.
- Opponent known/candidate move usage was not strongly visible in the response and needs more observation.

Verification:
- `uv run pytest -q`
- Result: 657 passed, 2 deselected.

Remaining limitations:
- More local Gemini runs are needed to judge whether the model consistently uses `known_moves` as confirmed and `candidate_moves` as possible only.
- Opponent damage estimate remains out of scope until v0.12.

---

## v0.11.2 - Opponent Move Awareness Prompt/Guardrail Polish

Purpose:
- Make Gemini's interpretation of `opponent_moves` more explicit without changing the payload schema.
- Encourage use of known opponent moves and cautious discussion of candidate moves.

Implemented:
- Added a concise prompt guardrail that:
  - treats `opponent_moves.known_moves` as user-confirmed opponent moves
  - treats `opponent_moves.candidate_moves` as possible, not confirmed, moves
  - allows candidate moves to be mentioned as possible threats only when labeled unconfirmed
  - states opponent move damage is not calculated
  - tells the model to use `my_available_moves` damage estimates for comparing the user's own move options
- Strengthened `ADVISOR_KNOWN_LIMITATIONS` with the same opponent-move semantics.
- Updated the advisor payload contract docs.

Manual verification checklist for T1:
- Confirm a known opponent move is reflected in the response when relevant.
- Confirm candidate moves are not described as confirmed moves.
- Confirm candidate moves, if mentioned, are labeled as possible/unconfirmed threats.
- Confirm opponent damage is not described as calculated.
- Confirm my four-move damage comparison remains part of the recommendation.

Out of scope maintained:
- No payload schema change.
- No opponent damage estimate.
- No candidate sorting polish.
- No UI changes.
- No `advisor/damage/` or `advisor/probability/` engine changes.

---

## v0.12 - Opponent Known Move Damage Estimate

Purpose:
- Add default-assumption damage estimates for user-confirmed opponent known moves.
- Let the advisor reason about how threatening a confirmed opponent move is against `my_active`.

Implemented:
- Generalized the LLM damage estimate helper so the attacker and defender payload keys can be selected.
- Added an opponent known move wrapper that calculates `opponent_moves.known_moves[*].damage_estimate`.
- Set opponent known move damage `scope` to `opponent_known_move_only`.
- Set opponent known move damage `target` to `my_active`.
- Kept the same default assumptions as v0.9/v0.10:
  - level 50
  - IV 31 all
  - EV 0 all
  - neutral nature
  - no item, boosts, weather, terrain, screens, critical hit, doubles, or unselected ability effects
- Updated advisor payload contract guardrails for v0.12.

Maintained boundaries:
- Candidate moves do not receive `damage_estimate`.
- OHKO/2HKO/KO chance is not included.
- Speed order, Turn Engine, final stats, EV/IV/nature/item UI, switch recommendation, and lead recommendation remain out of scope.
- No `advisor/damage/` or `advisor/probability/` engine changes.

Verification:
- Confirmed opponent known move estimates are attached under `opponent_moves.known_moves[*].damage_estimate`.
- Confirmed opponent known move estimates use `target: "my_active"`.
- Confirmed candidate moves do not receive `damage_estimate`.
- Confirmed status known moves return `unavailable_status_move`.
- Confirmed v0.10 my-side damage estimate regression remains covered.
- `uv run pytest -q`
- Result: 661 passed, 2 deselected.

---

## v0.12.1 - Opponent known move damage Gemini verification

Purpose:
- Verify the v0.12 opponent known move damage payload shape.
- Attempt a Gemini quality check for opponent known move damage awareness.

Payload verification:
- Offscreen payload check used Charizard vs Garchomp with opponent known move `Earthquake`.
- Confirmed `opponent_moves.known_moves[0].move_id` is `earthquake`.
- Confirmed `opponent_moves.known_moves[0].source` is `user_confirmed`.
- Confirmed `opponent_moves.known_moves[0].damage_estimate.status` is `available_with_default_assumptions`.
- Confirmed `opponent_moves.known_moves[0].damage_estimate.target` is `my_active`.
- Confirmed `is_final_battle_damage` is `false`.
- Confirmed Charizard's Ground immunity is represented as `damage_range: 0-0` and `percent_range: 0.0-0.0`.
- Confirmed candidate moves do not include `damage_estimate`.
- Confirmed `moves.my_available_moves[*].damage_estimate` remains present for four user-confirmed moves.
- Confirmed `moves.opponent_available_moves` remains the legacy empty list.
- Confirmed KO/OHKO/2HKO fields are not present.

Gemini:
- Actual Gemini call was attempted with `gemini-2.5-flash`.
- The Codex execution environment returned `API_KEY_INVALID`, even though the environment variable was present.
- This is recorded as an environment/key validation issue, not a v0.12 payload regression.

T1 local app verification:
- Gemini call succeeded from the local valid-key PySide app.
- Status bar showed Free Tier cost semantics: `Free tier | input 7478 / output 101 | $0.0000000`.
- In a Charizard vs Garchomp scenario, Gemini recommended `Heat Wave` from the user's four move options.
- The response used the four-move damage comparison and cited `Heat Wave` at 18.0-21.3% estimated damage to Garchomp.
- The response recognized the opponent known move `Earthquake`.
- The response interpreted Charizard's Flying typing correctly and stated that Earthquake is ineffective/immune against Charizard.
- Candidate Dragon-type moves were described only as unconfirmed possible threats.
- No candidate move overclaim was observed.
- No opponent damage overclaim was observed.
- The response did not claim KO, OHKO, or 2HKO.
- The response preserved the default-assumption limitation and did not assert EVs, IVs, nature, items, final stats, speed order, or turn outcome.

Verification:
- `uv run pytest -q`
- Result: 661 passed, 2 deselected.

Remaining limitations:
- Codex tool environment Gemini response quality remains unverified because that environment returned `API_KEY_INVALID`.
- The damage estimate remains a default-assumption reference, not final battle damage.
- Candidate move damage, KO odds, speed order, final stats, EV/IV/nature/item, and Turn Engine state remain out of scope.

---

## v0.13 - Stats Assumption Profile

Purpose:
- Make the stat model behind every damage estimate explicit.
- Clarify that current damage estimates are still default-assumption rough references.

Implemented:
- Added `ADVISOR_DEFAULT_ASSUMPTION_PROFILE` with id `default_level50_ivs31_evs0_neutral_no_item`.
- Added `assumption_profile` to available damage estimates.
- Added `assumption_profile` to unavailable damage estimate schemas.
- Kept the existing `assumptions` field for compatibility.
- Updated advisor payload mode and contract guardrails for v0.13.
- Updated advisor payload contract documentation.

Maintained boundaries:
- No UI changes.
- No final stats input.
- No EV/IV/nature/item input.
- No top-level `stat_profiles`.
- No item selection.
- No KO/OHKO/2HKO, speed order, or Turn Engine.
- No `advisor/damage/` or `advisor/probability/` engine changes.

Verification:
- Confirmed `moves.my_available_moves[*].damage_estimate.assumption_profile` is present.
- Confirmed `moves.my_selected_move.damage_estimate.assumption_profile` is present.
- Confirmed `opponent_moves.known_moves[*].damage_estimate.assumption_profile` is present.
- Confirmed the default profile id is `default_level50_ivs31_evs0_neutral_no_item`.
- Confirmed `source: "system_default"`, `confidence: "rough_reference"`, and `is_user_confirmed: false`.
- Confirmed the existing `assumptions` field remains present.
- Confirmed `is_final_battle_damage` remains `false`.
- `uv run pytest -q`
- Result: 662 passed, 2 deselected.

---

## v0.14 - Final Stats Input

Purpose:
- Allow user-confirmed final stats for the selected my/opponent active Pokemon.
- Use those final stats in existing my-side and opponent-known-move damage estimates without changing the damage engine.

Implemented:
- Added top-level `stat_profiles.my_active` and `stat_profiles.opponent_active`.
- Added `StatProfileDialog` for HP / Atk / Def / SpA / SpD / Spe entry.
- Added a compact `Stats` button to Pokemon panels that opens the dialog for the selected slot.
- Stored final stats on the selected Pokemon panel.
- Added validation that accepts only complete six-stat positive integer profiles.
- Kept partial final stats as default assumptions instead of silently mixing values.
- Updated damage helper stat resolution:
  - my move damage can use `my_active` attacker final stats and `opponent_active` defender final stats
  - opponent known move damage can use `opponent_active` attacker final stats and `my_active` defender final stats
- Updated `damage_estimate.assumption_profile` to `user_confirmed_final_stats_level50` when user-confirmed final stats are used.
- Kept `is_final_battle_damage` as `false`.
- Updated advisor payload contract guardrails for v0.14.

Maintained boundaries:
- No bench Pokemon final stats editing.
- No EV/IV/nature/item input.
- No item, ability, boost, weather, terrain, or screen UI.
- No KO/OHKO/2HKO.
- No speed order.
- No Turn Engine.
- No `advisor/damage/` or `advisor/probability/` engine changes.

Verification:
- Confirmed default stat profiles are emitted for both active Pokemon when final stats are absent.
- Confirmed user-confirmed final stats are emitted for `my_active` and `opponent_active` when all six stats are present.
- Confirmed partial final stats remain default assumptions.
- Confirmed my move damage uses user-confirmed attacker/defender final stats.
- Confirmed opponent known move damage uses user-confirmed attacker/defender final stats.
- Confirmed `damage_estimate.assumption_profile` changes to `user_confirmed_final_stats_level50`.
- Confirmed `is_final_battle_damage` remains `false`.
- Confirmed KO/OHKO/2HKO fields remain absent.

---

## v0.16.1 - Type Effectiveness Metadata

Purpose:
- Prevent LLM type matchup explanation overclaims.
- Add calculated type effectiveness metadata to each available damage estimate.
- Give Gemini an explicit source for immune / resisted / neutral / super-effective wording.

Context:
- T1 local Gemini testing correctly reflected damage comparison and Ground immunity, but incorrectly described Dragon damage against Corviknight as super effective.
- Corviknight is Flying/Steel, so Dragon is resisted by Steel and should be labeled `not_very_effective`.

Implemented:
- Added `damage_estimate.type_effectiveness`.
- Added `multiplier` and `label` fields.
- Label mapping:
  - `0.0` -> `immune`
  - greater than `0.0` and less than `1.0` -> `not_very_effective`
  - `1.0` -> `neutral`
  - greater than `1.0` -> `super_effective`
- Updated prompt guardrails so type matchup wording must use `damage_estimate.type_effectiveness` when present.
- Updated advisor payload contract documentation and guardrails.

Maintained boundaries:
- No type chart changes.
- No new damage formula.
- No item UI.
- No speed order.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No candidate move damage.
- No `advisor/damage/` or `advisor/probability/` engine changes.

Verification:
- Confirmed Dragon Claw/Outrage-style Dragon damage into Corviknight is labeled `not_very_effective`.
- Confirmed Earthquake into Corviknight is labeled `immune` and has 0 damage.
- Confirmed prompt and contract mention `damage_estimate.type_effectiveness`.
- Offscreen UI smoke confirmed `Master Ball Advisor v0.14` launches and Pokemon panels expose Stats buttons.
- `uv run pytest -q`
- Result: 670 passed, 2 deselected.

---

## v0.16 - Minimal Damage Item Assumption

Purpose:
- Add item profile payload structure without adding item UI.
- Apply a small attacker-side damage item subset to existing my move and opponent known move damage estimates.
- Make applied and unapplied item effects explicit for the LLM.

Implemented:
- Added top-level `item_profiles.my_active` and `item_profiles.opponent_active`.
- Default UI payload emits `system_default_none` for both active Pokemon.
- Added support for user-confirmed attacker-side damage items in helper/test payloads.
- Applied the v0.16 subset through the existing damage engine item path:
  - `choice-band` for physical damage.
  - `choice-specs` for special damage.
  - `life-orb` for damage, with recoil marked as unapplied.
  - `muscle-band` for physical damage.
  - `wise-glasses` for special damage.
- Added `damage_estimate.item_effects` to available damage estimates.
- Updated `assumption_profile` ids when a supported damage item modifier is applied.
- Kept `is_final_battle_damage` as `false`.
- Updated advisor payload contract and prompt guardrails for item semantics.

Maintained boundaries:
- No item UI.
- No legal item scraping or cache generation.
- No Expert Belt or Assault Vest.
- No Choice Scarf speed.
- No Focus Sash survival.
- No Leftovers/Sitrus recovery.
- No Choice lock.
- No Life Orb recoil.
- No candidate move damage.
- No KO/OHKO/2HKO.
- No speed order or Turn Engine.
- No `advisor/damage/` or `advisor/probability/` engine changes.

Verification:
- Confirmed default item profiles are emitted as `system_default_none`.
- Confirmed `choice-band` modifies physical move damage and not special move damage.
- Confirmed `choice-specs` modifies special move damage and not physical move damage.
- Confirmed `life-orb` modifies damage and records recoil in `unapplied_effects`.
- Confirmed `muscle-band` and `wise-glasses` apply only to their matching move categories.
- Confirmed unsupported items do not modify damage and are marked `unsupported_item`.
- Confirmed opponent known move damage uses `item_profiles.opponent_active` as attacker item.
- Confirmed candidate moves still do not receive `damage_estimate`.
- Confirmed KO/OHKO/2HKO fields remain absent.

---

## v0.14.1 - Final Stats Input local verification

Purpose:
- Verify the v0.14 final stats input flow without adding new functionality.
- Confirm that UI state, payload `stat_profiles`, and damage estimate assumption profiles remain aligned.

Verification:
- Confirmed the app launches offscreen as `Master Ball Advisor v0.14`.
- Confirmed Pokemon panels expose compact `Stats` buttons.
- Confirmed `StatProfileDialog` can save all six final stats.
- Confirmed the dialog `Clear` path returns to default assumptions.
- Confirmed partial final stats are not accepted as `user_confirmed_final_stats`.
- Confirmed `stat_profiles.my_active` and `stat_profiles.opponent_active` are emitted.
- Confirmed complete final stats produce `status: "user_confirmed_final_stats"` and `source: "user_input"`.
- Confirmed missing/partial final stats keep `status: "default_assumption"`.
- Confirmed my available move damage estimates use `assumption_profile.id: "user_confirmed_final_stats_level50"` when final stats are present.
- Confirmed opponent known move damage estimates use `assumption_profile.id: "user_confirmed_final_stats_level50"` when final stats are present.
- Confirmed sample final stats changed damage ranges compared with default-reference calculations.
- Confirmed `is_final_battle_damage` remains `false`.
- Confirmed KO/OHKO/2HKO fields remain absent.
- Confirmed opponent candidate moves still do not include `damage_estimate`.

Gemini verification:
- Attempted one Codex-environment Gemini call with `gemini-2.5-flash`.
- Result: not verified in Codex because the configured key returned `API_KEY_INVALID`.
- T1 local valid-key app verification is still required to confirm Gemini response quality.
- Expected checks for T1 local verification:
  - Gemini distinguishes user-confirmed final stats from default assumptions.
  - Gemini does not describe the damage as final battle damage.
  - Gemini keeps item/ability/boost/weather/terrain limitations.
  - Gemini does not assert KO/OHKO/2HKO or speed order.

Maintained boundaries:
- No payload schema changes.
- No UI changes.
- No EV/IV/nature/item input.
- No KO/OHKO/2HKO.
- No speed order or Turn Engine.
- No `advisor/damage/` or `advisor/probability/` engine changes.

Test:
- `uv run pytest -q`
- Result: 670 passed, 2 deselected.

---

## v0.16.2 - Type Effectiveness Metadata local Gemini verification

Purpose:
- Verify the v0.16.1 `damage_estimate.type_effectiveness` metadata with a local valid-key Gemini call.
- Confirm Gemini uses the structured type-effectiveness metadata instead of inventing type matchup wording.

Scenario:
- My active Pokemon: Garchomp.
- Opponent active Pokemon: Corviknight.
- My available moves included `Outrage`, `Earthquake`, and `Rock Slide`.
- Opponent known moves were not required for this check.

Payload verification:
- Confirmed `Outrage` includes `damage_estimate.type_effectiveness.label: "not_very_effective"`.
- Confirmed `Outrage` damage range was `41-48`.
- Confirmed `Earthquake` includes `damage_estimate.type_effectiveness.label: "immune"`.
- Confirmed `Earthquake` damage range was `0-0`.
- Confirmed `Rock Slide` includes `damage_estimate.type_effectiveness.label: "neutral"`.
- Confirmed KO/OHKO/2HKO fields remain absent.
- Confirmed candidate moves remain outside damage estimate generation.

Gemini verification:
- Local valid-key Gemini call succeeded with `gemini-2.5-flash`.
- Gemini recommended `Outrage` based on the available move damage estimates.
- Gemini described `Outrage` as dealing more than `Rock Slide` despite being not very effective.
- Gemini described `Earthquake` as doing 0 damage because Corviknight is immune.
- Gemini did not call Dragon damage against Corviknight super effective.
- Gemini did not contradict `damage_estimate.type_effectiveness`.
- Gemini kept the limitation that estimates are reference values based on default assumptions, not final battle damage.

Maintained boundaries:
- No code changes.
- No prompt changes.
- No payload schema changes.
- No item UI.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No `advisor/damage/` or `advisor/probability` engine changes.

Test:
- `uv run pytest -q`
- Result: 686 passed, 2 deselected.

---

## v0.18 - Minimal Supported Item Selector

Purpose:
- Add a minimal app UI path for selecting supported held items.
- Connect selected item state to top-level `item_profiles` so existing v0.16 item damage helpers can apply supported attacker-side item modifiers.

Implemented:
- Added `ItemProfileDialog` with v0.18 options:
  - Unknown item
  - No item
  - Choice Band
  - Choice Specs
  - Life Orb
  - Muscle Band
  - Wise Glasses
- Added compact `Item` button state to Pokemon panels.
- Added item profile state to Pokemon panels.
- Reset item profile state when a panel's Pokemon changes or is cleared.
- `my_active` defaults to `system_default_none`.
- `opponent_active` defaults to `unknown`.
- User-confirmed supported items are emitted in `item_profiles`.
- Existing damage helpers now receive UI-selected item profiles through `MainWindow._build_llm_battle_input()`.
- Updated advisor payload mode to `ui-selected-pokemon-v0.18`.
- Updated advisor payload contract for the minimal item selector and opponent unknown-item default.

Verification:
- Confirmed `ItemProfileDialog` exposes the full v0.18 option set.
- Confirmed Unknown, No item, and supported item selections produce distinct payload profiles.
- Confirmed default `my_active` item profile is `system_default_none`.
- Confirmed default `opponent_active` item profile is `unknown`.
- Confirmed user-selected `Choice Band` is reflected in `item_profiles.my_active`.
- Confirmed user-selected `Life Orb` is reflected in `item_profiles.opponent_active`.
- Confirmed selected supported items flow into damage estimates through `item_effects`.
- Confirmed Life Orb recoil remains listed as an unapplied effect.
- Confirmed panel item profile resets on Pokemon change/clear.
- Confirmed offscreen `MainWindow` smoke creates both team columns with Item buttons.

Maintained boundaries:
- No legal item cache.
- No scraping.
- No unsupported legal item selector.
- No Expert Belt or Assault Vest.
- No Choice Scarf, Focus Sash, Leftovers, or Sitrus Berry.
- No Choice lock.
- No Life Orb recoil.
- No speed order or Turn Engine.
- No KO/OHKO/2HKO.
- No `advisor/damage/` or `advisor/probability/` engine changes.

Test:
- `uv run pytest -q`
- Result: 693 passed, 2 deselected.

---

## v0.18.1 - Minimal item selector verification and Korean UI polish

Purpose:
- Polish the minimal item selector UI text for Korean users.
- Verify that supported item selections continue to flow through `item_profiles` and `damage_estimate.item_effects`.

Implemented:
- Localized the `ItemProfileDialog` guidance text to Korean.
- Kept the v0.18 item selector scope unchanged.

Verification:
- Confirmed `ItemProfileDialog` guidance is Korean:
  - "현재는 데미지 보정 아이템 일부만 지원합니다."
  - "구애 고정, 반동, 스피드, 회복, 생존 효과, KO 확률은 미지원입니다."
- Confirmed `Life Orb` is emitted as a user-confirmed item profile.
- Confirmed `Life Orb` item effects mark `damage_modifier` as applied.
- Confirmed `Life Orb` recoil remains an unapplied effect.
- Confirmed `Choice Band` applies only to physical move damage.
- Confirmed `Choice Specs` applies only to special move damage.
- Confirmed `Unknown` item does not modify damage.
- Confirmed `No item` does not modify damage.
- Confirmed `opponent_active` default item state remains `unknown`.
- Confirmed KO/OHKO/2HKO fields remain absent.

Gemini verification:
- Not run in this Codex verification pass.
- T1 local valid-key app verification is still recommended for confirming natural-language wording around item modifiers.

Maintained boundaries:
- No legal item cache.
- No scraping.
- No unsupported item UI.
- No Expert Belt or Assault Vest.
- No Choice Scarf speed.
- No Focus Sash survival.
- No Leftovers/Sitrus recovery.
- No Choice lock.
- No Life Orb recoil.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No `advisor/damage/` or `advisor/probability` engine changes.

Test:
- `uv run pytest tests/test_item_profile_dialog.py tests/test_advisor_damage_estimate.py tests/test_advisor_payload_contract.py -q`
- Result: 45 passed.
- `uv run pytest -q`
- Result: 695 passed, 2 deselected.

---

## v0.18.2 - Item modifier Gemini response guardrail

Purpose:
- Make Gemini's natural-language response reflect supported item damage modifiers when they are already applied in `damage_estimate.item_effects`.
- Avoid confusing wording where an item-applied estimate is described as only default assumptions.

Context:
- T1 local Gemini checks showed correct move recommendations and type-effectiveness handling.
- However, when `Life Orb` or `Choice Band` was selected, Gemini often omitted the applied item modifier and only said "default assumptions."

Implemented:
- Strengthened the UI-selected advisor prompt:
  - if `damage_estimate.item_effects.attacker_item.status` is `applied`, mention the supported item damage modifier.
  - describe item-applied numbers as default assumptions plus the supported item modifier, not only default assumptions.
  - keep Choice lock, Life Orb recoil, speed, survival, recovery, and KO odds unmodeled.
- Added the same guardrail to `ADVISOR_KNOWN_LIMITATIONS`.
- Updated the advisor payload contract with explicit allowed/disallowed item explanation semantics.

Verification:
- Confirmed prompt text includes the applied-item explanation guardrail.
- Confirmed contract limitations include the same guardrail.
- Confirmed existing item-effect, type-effectiveness, and opponent-move guardrails remain present.

Gemini verification:
- Not run in this Codex verification pass.
- T1 local valid-key app verification is recommended to confirm Gemini now mentions Life Orb / Choice Band / Choice Specs damage modifiers when applied.

Maintained boundaries:
- No payload schema change.
- No item UI change.
- No legal item cache.
- No scraping.
- No unsupported item UI.
- No recoil, Choice lock, speed, survival, recovery, or KO/OHKO/2HKO implementation.
- No Turn Engine.
- No `advisor/damage/` or `advisor/probability` engine changes.

Test:
- `uv run pytest tests/test_advisor_payload_contract.py -q`
- Result: 17 passed.

- `uv run pytest -q`
- Result: 696 passed, 2 deselected.
- `uv run pytest -q`
- Result: 696 passed, 2 deselected.

T1 local valid-key verification:
- Confirmed Gemini now mentions supported item damage modifiers when applied.
- Choice Band case:
  - Gemini recommended `Iron Head`.
  - Gemini stated that the Choice Band damage modifier is applied to the physical move damage estimates.
  - Gemini did not claim Choice lock is modeled.
  - Gemini did not claim KO/OHKO/2HKO.
- Life Orb case:
  - Gemini recommended `Iron Head`.
  - Gemini described the estimate as `default assumptions plus the supported Life Orb damage modifier`.
  - Gemini mentioned the opponent item is unknown.
  - Gemini did not describe the estimate as final battle damage.
- Remaining response polish:
  - Gemini may surface the raw type-effectiveness label `super_effective` instead of natural wording like `super effective`.
  - Life Orb recoil is not always explicitly mentioned as unmodeled, even though it remains excluded in the payload/contract.

---

## v0.18.3 - Response wording polish for type labels and item effects

Purpose:
- Reduce awkward or misleading wording in Gemini responses without changing payload schema or damage calculation.
- Ensure raw type-effectiveness labels are converted to natural language.
- Make non-damage item limitations more consistently visible when supported item modifiers are applied.

Implemented:
- Strengthened prompt guidance:
  - do not print raw `type_effectiveness` labels such as `super_effective` or `not_very_effective`.
  - convert labels to natural wording such as `super effective`, `not very effective`, `immune/no effect`, or `neutral`.
  - if Life Orb is applied, say recoil is not modeled.
  - if Choice Band or Choice Specs is applied, say choice lock is not modeled.
  - avoid describing item-applied estimates as only default assumptions.
- Added the same wording guardrails to `ADVISOR_KNOWN_LIMITATIONS`.
- Updated `docs/advisor_payload_contract.md` with explicit type label and item-effect wording rules.

Verification:
- Confirmed prompt includes raw-label avoidance guidance.
- Confirmed prompt includes `super_effective` -> natural wording guidance.
- Confirmed prompt includes `not_very_effective` -> natural wording guidance.
- Confirmed prompt includes `immune/no effect` guidance.
- Confirmed prompt includes Life Orb recoil-not-modeled guidance.
- Confirmed prompt includes Choice Band/Specs choice-lock-not-modeled guidance.
- Confirmed contract limitations include the same guardrails.

Maintained boundaries:
- No payload schema change.
- No damage calculation change.
- No item calculation change.
- No item UI change.
- No legal item cache.
- No scraping.
- No recoil, Choice lock, speed, survival, recovery, or KO/OHKO/2HKO implementation.
- No Turn Engine.
- No `advisor/damage/` or `advisor/probability` engine changes.

Test:
- `uv run pytest tests/test_advisor_payload_contract.py -q`
- Result: 17 passed.

---

## v0.20 - Champions legal item fixture and repository

Purpose:
- Start separating Pokemon Champions Regulation M-A item legality from current damage-engine item support.
- Prevent the v0.18 minimal item selector from being mistaken for a Champions legal item selector.

Implemented:
- Added `data/static/champions_legal_items.json` as a manually curated sentinel fixture.
- Added `core/champions_item_repository.py`.
- Added repository helpers for:
  - fixture loading and schema validation.
  - item lookup and normalization.
  - legal item listing.
  - damage-supported-but-not-legal item listing.
  - item classification.
- Added tests for source refs, Regulation M-A metadata, legal sentinels, damage-supported mismatch sentinels, unknown items, list helpers, and fixture validation.

Fixture scope:
- This is not the full 117-item Regulation M-A list.
- Included legal sentinel items:
  - `choice-scarf`
  - `focus-sash`
  - `leftovers`
  - `sitrus-berry`
  - `metal-coat`
  - `charcoal`
- Included damage-supported-but-not-normal-legal-selector sentinels:
  - `choice-band`
  - `choice-specs`
  - `life-orb`
  - `muscle-band`
  - `wise-glasses`

Source policy:
- Primary legal snapshot: MetaVGC.
- Cross-check candidates: RotomPicks and Serebii.
- Contextual held-item guide: ChampDex.
- Existing `data/static/items.json` and `data/static/items_damage.json` remain metadata/effect-support references, not Champions legality sources.
- PokeAPI remains metadata fallback only, not a Champions legality source.

Important classification result:
- `Choice Band`, `Choice Specs`, and `Life Orb` remain damage-supported by the current helper, but are not treated as normal Champions legal selector items.
- `Muscle Band` and `Wise Glasses` are kept as unconfirmed damage-supported mismatch sentinels until legality is confirmed.
- Legal-but-not-modeled items such as `Choice Scarf`, `Focus Sash`, `Leftovers`, and `Sitrus Berry` are recognized without applying speed, survival, recovery, or turn effects.

Maintained boundaries:
- No UI changes.
- No legal item selector integration.
- No scraping or build script.
- No `data/cache` generation.
- No item damage effect additions.
- No Expert Belt or Assault Vest additions.
- No Choice Scarf speed, Focus Sash survival, Leftovers/Sitrus recovery, Choice lock, Life Orb recoil, speed order, KO/OHKO/2HKO, or Turn Engine implementation.
- No `advisor/damage/` or `advisor/probability` engine changes.

Test:
- `uv run pytest tests/test_champions_item_repository.py -q`
- Result: 16 passed.
- `uv run pytest tests/test_items.py tests/test_item_modifiers.py tests/test_item_profile_dialog.py tests/test_advisor_damage_estimate.py -q`
- Result: 47 passed.
- `uv run pytest -q`
- Result: 712 passed, 2 deselected.

---

## v0.20.1 - Item selector label clarification

Purpose:
- Clarify that the current ItemProfileDialog is not a full Pokemon Champions legal item selector.
- Reduce the risk that damage-supported test items are mistaken for confirmed Regulation M-A legal items.

Implemented:
- Updated ItemProfileDialog guidance text in Korean.
- The guidance now states:
  - the current list is not the full Pokemon Champions legal item list.
  - only some items connected to damage calculation are shown.
  - some items may be unconfirmed or differ from the actual Reg M-A legal list.
  - Choice lock, recoil, speed, recovery, survival effects, and KO odds are unsupported.
- Added test coverage for the clarified guidance text.

Maintained boundaries:
- No legal item selector implementation.
- No repository/UI integration.
- No legal item fixture changes.
- No scraping or build script.
- No `data/cache` generation.
- No item effect additions.
- No `advisor/damage/` or `advisor/probability` engine changes.

Test:
- `uv run pytest tests/test_item_profile_dialog.py -q`
- Result: 6 passed.

---

## v0.20.2 - Local item selector and Gemini verification

T1 local valid-key verification:
- Life Orb selected state produced a successful Gemini response.
- Gemini recommended `Iron Head`.
- Gemini reflected the expected damage range: `140-166`.
- Gemini explicitly mentioned that the Life Orb damage modifier was applied.
- Gemini explicitly mentioned that Life Orb recoil is not modeled.
- Gemini mentioned that `Outrage` has no effect.
- Gemini mentioned that the opponent held item is unknown.
- Gemini used natural wording (`super effective`) instead of the raw `super_effective` label.
- Gemini did not overclaim final battle damage.
- Gemini did not claim KO/OHKO/2HKO certainty.
- Item selector behavior was confirmed locally.

Remaining follow-up:
- ItemProfileDialog guidance length/truncation can receive one more visual check in the running app.

Maintained boundaries:
- Documentation-only update.
- No code changes.
- No UI changes.
- No legal item selector implementation.
- No repository/UI integration.
- No item effect additions.
- No `advisor/damage/` or `advisor/probability` engine changes.

---

## v0.22a - Full legal item fixture expansion plan

Purpose:
- Plan the next data step before any legal item selector UI integration.
- Define how to expand the current sentinel `champions_legal_items.json` fixture toward a full Regulation M-A legal item fixture.
- Keep Champions legality separate from local damage-effect support.

Documented:
- Current v0.20/v0.21 state: legal item repository exists, but the fixture is sentinel-only.
- Source strategy:
  - MetaVGC as the primary legal snapshot.
  - RotomPicks and Serebii as cross-check sources.
  - ChampDex as contextual guide for cut/missing held items.
  - PokeAPI and existing static files as metadata/effect fallback only, not legality sources.
- Fixture expansion options:
  - manual
  - semi-manual static JSON expansion
  - scraper/build script
- Recommended v0.22b direction: semi-manual static JSON expansion before legal selector UI work.
- Fixture schema plan, item ID normalization rules, category rules, source conflict policy, repository impact, tests plan, and v0.22b candidate scope.
- Damage-supported but non-legal item policy for `Choice Band`, `Choice Specs`, `Life Orb`, `Muscle Band`, and `Wise Glasses`.

Maintained boundaries:
- Design/documentation only.
- No code implementation.
- No `data/static/champions_legal_items.json` changes.
- No fixture expansion implementation.
- No UI changes.
- No legal item selector implementation.
- No scraping or build script.
- No `data/cache` generation.
- No item effect additions.
- No `advisor/damage/` or `advisor/probability` engine changes.

Test:
- Not run; documentation-only planning update.
