# Practical-1.0 Final Release

**Status:** FINAL
**Package version:** `1.0.0`
**Release baseline:** `4c3f253` (`fix: constrain provider claims to evidence`)
**Offline validation:** 3558 passed, 2 deselected
**Bounded real-environment provider smoke:** PASS (one call, no retry)

Practical-1.0 is a trustworthy deterministic advisor for choosing between an
available Move and a legal Switch from trusted current battle authority. It is
not an exhaustive Pokémon battle simulator.

## Final deterministic scope

The advisor composes supported switch legality and blockers, entry hazards and
entry abilities, direct incoming damage, KO/danger evidence, survival and
damage modifiers, supported action order, and bounded residual or
first-end-of-turn consequences. Trusted observations flow through lifecycle
confirmation, reducer/replay, runtime projection, and detached frozen
snapshots.

Ranking remains intentionally narrow: only proven deterministic danger changes
cross-action ordering; there is no generic safety, chip, status, boost,
recovery, or switch-native strategic score. A Move remains preferred when
actions share the same danger tier.

Missing, stale, malformed, unsupported, or identity-mismatched authority stays
unknown, incomplete, or unsupported. It is never converted into an absent
hazard, harmless item or ability, safe switch, zero damage, or certain result.

## Release evidence

- `tests/test_v44_practical_1_0_end_to_end_scenarios.py` covers composed final
  Move-vs-Switch outcomes, hazards, survival, action order, same-turn events,
  first-end-of-turn state, and conservative incompleteness.
- `tests/test_v45_practical_1_0_multiturn_lifecycle_scenarios.py` covers turn
  expiry, field replacement, switch identity isolation, hazard replacement,
  faint terminality, and detached frozen state.
- `tests/test_v46_practical_1_0_explanation_integration_scenarios.py` covers
  deterministic recommendation-to-presentation consistency and conservative
  UI-facing evidence visibility.
- The final offline baseline is 3558 passed, 2 deselected.
- One bounded real-environment provider request passed with no retry. Its
  deterministic recommendation and user-facing presentation agreed; strict
  semantic validation passed, and unknown or incomplete authority remained
  conservative.

Provider explanations remain subordinate to deterministic evidence. Internal
mechanics links are not exposed to generic claims, generic claim kinds are
limited to available candidate evidence, and unsupported numeric or mechanics
claims remain rejected.

## Post-1.0 boundaries

Practical-1.0 intentionally excludes broad item and ability activation
families, berries and Black Sludge, toxic progression, broad weather residuals,
delayed effects, general turn simulation, exhaustive move and ability coverage,
broad non-damage strategic utility scoring, and richer provider-generated prose
or UX refinement.

## Next phase

Practical-1.0 is complete under this scope. Any future work should be planned
as post-1.0 coverage, UX refinement, packaging, or release operations rather
than an implicit expansion of the deterministic core.
