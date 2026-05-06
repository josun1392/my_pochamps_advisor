# Product Requirements Document

### Phase 3.3 — Field & Weather: ✅ DONE (Verified)

**Completed:** 2026-05-06  
**PR:** #3.3-A `feat(3.3): close weather parity gaps`  
**Commit:** `42207fb`

**Coverage:**
- Total tests: 397 (+4)
- Parity tests: 143 (+4)
- Status: 396 passed, 1 xfailed

**Verified Scenarios:**
- ✅ `sun_water_nerf` — Water moves halved (2048/4096) under Sun
- ✅ `snow_non_ice_no_boost` — Non-Ice DEF unaffected by Snow
- ✅ `sand_non_rock_no_boost` — Non-Rock SpD unaffected by Sand
- ⚠️ `neutralizing_gas_disables_cloud_nine_in_sun` — xfailed
  - **Status:** Known divergence in `@smogon/calc` bridge
  - **Ground Truth (verified 2026-05-06):**
    - Bulbapedia: Cloud Nine is NOT in NG's exception list
    - Pokémon Showdown (`data/abilities.ts`): `cloudnine.onSwitchIn`
      comment explicitly states *"does not activate ... when
      Neutralizing Gas leaves the field"*
    - Cloud Nine lacks `cantsuppress` flag → NG suppresses it
  - **Verdict:** Our engine resolves NG → Cloud Nine correctly,
    matching Showdown sim behavior. `@smogon/calc` uses a
    simplified ability resolution model.
  - **Tracked:** Upstream issue to be filed against `@smogon/calc`.

**Next:** Phase 3.4 — Move Mechanics (Multi-hit Moves)

### Phase 3.4 — Multi-hit Moves: 🚧 IN PROGRESS

#### PR #3.4-A — Minimum Slice ✅
- **Branch:** `feat/3.4-multihit-minimum-slice`
- **Coverage:** Bullet Seed / Rock Blast / Icicle Spear + Skill Link
- **Tests:** 402 total (+5 parity)
- **Modes:** min / max / skill-link (expected distribution deferred)

#### PR #3.4-B — Item Modifiers (planned)
- Loaded Dice (4-5 hit guarantee)

#### PR #3.4-C — Special Cases (planned)
- Population Bomb (10-hit distribution)
- Triple Axel / Triple Kick (escalating BP, hit-dependent)

#### PR #3.4-D — Distribution Sampling (planned)
- Probabilistic 2-5 hit resolution (35/35/15/15)
- Expected value mode for damage calc UI
