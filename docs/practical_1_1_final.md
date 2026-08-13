# Practical-1.1 Final Release

**Status:** FINAL
**Package version:** `1.1.0`
**Release baseline:** `4ef2720` (`docs: record practical 1.1 release candidate`)
**Offline validation:** 3631 passed, 2 deselected
**Bounded real-environment provider smoke:** PASS (one call, no retry)

Practical-1.1 extends the Practical-1.0 deterministic Move-vs-Switch advisor
by reducing meaningful incomplete outcomes with bounded mechanics and
explicitly trusted, identity-bound runtime authority. It remains a practical
advisor, not a complete Pokemon battle simulator.

## Final bounded scope

Practical-1.1 adds defender type-resist berries, including Chilan Berry;
reducer-owned current type, global weather, and active-ability authority;
Black Sludge; toxic progression; Sandstorm; Rain Dish; Ice Body; Solar Power;
and Dry Skin at the confirmed first end-of-turn phase. It also adds Life Orb
recoil from an explicit qualifying-damage event and Flail/Reversal HP-bracket
power to native direct-Q12 damage.

These mechanics use lifecycle confirmation, replay/reducer state, detached
runtime and frozen snapshots, and existing HP, KO, danger, and recommendation
consumers. Practical-1.0 ranking remains unchanged: only proven deterministic
danger changes cross-action ordering, and a Move remains preferred when actions
share the same danger tier. Unknown, stale, malformed, unsupported, or
identity-mismatched authority remains incomplete or unsupported; it is never
treated as safe, absent, or resolved by implication.

## Release evidence

- `tests/test_v60_practical_1_1_integration_scenarios.py` covers representative
  type-resist berries, current-type lifecycle, end-of-turn effects, toxic
  progression, weather and ability replacement, recoil, Flail/Reversal,
  lethal HP transitions, frozen snapshot detachment, and conservative
  incompleteness.
- The final offline baseline is 3631 passed, 2 deselected.
- One bounded real-environment provider request passed with no retry. Flail
  used exact trusted current/max HP of 4/100, resolving to canonical base power
  200 and native direct-Q12 evidence. The supported orchestration retained and
  consumed the sanitized completion result; semantic validation passed and the
  final presentation consistently selected Flail.

Provider explanations remain subordinate to deterministic evidence. Strict
semantic validation remains active: unsupported mechanics or numeric claims are
rejected, while unknown or incomplete authority remains conservative.

## Post-1.1 boundaries

Practical-1.1 intentionally excludes Sitrus/threshold berries and broader
consumable-trigger lifecycle, Rocky Helmet/Rough Skin contact-event authority,
broader passive item or ability families, a general end-of-turn scheduler,
delayed or scheduled effects, weather duration, broader turn simulation, and
non-damage strategic utility.

Practical-1.1 does not claim exhaustive Pokemon simulator completeness.

## Next phase

Practical-1.1 is complete under this scope. Future work should be planned as
post-1.1 mechanics coverage, product/UX refinement, packaging, or release
operations rather than an implicit expansion of the deterministic core.
