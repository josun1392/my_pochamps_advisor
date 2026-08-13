# Practical 1.1 Release Candidate

**Status:** RELEASE-CANDIDATE READY
**Package version:** `1.1.0`
**Release baseline:** `9102380` (`test: add practical 1.1 integration scenarios`)
**Offline validation:** 3631 passed, 2 deselected

Practical 1.1 extends the Practical 1.0 deterministic Move-vs-Switch advisor
by reducing meaningful incomplete outcomes through explicitly trusted,
identity-bound runtime authority and bounded mechanics. It remains a practical
advisor, not a complete Pokemon battle simulator.

## Added bounded scope

- defender type-resist berries, including Chilan Berry;
- reducer-owned current type, global weather, and active-ability authority;
- Black Sludge, toxic progression, Sandstorm, Rain Dish, Ice Body, Solar
  Power, and Dry Skin at the confirmed first end-of-turn phase;
- Life Orb recoil from an explicit qualifying-damage event; and
- Flail and Reversal HP-bracket power in native direct-Q12 damage.

These mechanics follow lifecycle confirmation, replay/reducer state, detached
runtime/frozen snapshots, and existing HP, KO, danger, and recommendation
consumers. The Practical 1.1 integration scenarios cover representative
cross-turn identity isolation, authority replacement, residual/recovery,
suppression, recoil, berries, and direct-Q12 paths.

## Preserved contracts and evidence

- Practical 1.0 danger-only cross-action ranking and same-tier Move preference
  remain unchanged.
- Unknown, stale, malformed, unsupported, or identity-mismatched authority
  remains incomplete or unsupported; it is never treated as safe, absent, or
  resolved by implication.
- The full offline suite passes: 3631 passed, 2 deselected.

## Post-1.1 boundaries

Practical 1.1 intentionally excludes Sitrus/threshold berries and broader
consumable triggers, contact retaliation such as Rocky Helmet and Rough Skin,
broader passive item or ability families, a general end-of-turn scheduler,
delayed or scheduled effects, weather duration, general turn simulation, and
non-damage strategic utility scoring.

Practical 1.1 does not claim exhaustive Pokemon simulator completeness.
