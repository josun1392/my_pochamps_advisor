# Practical-1.0 Release Candidate

**Status:** RELEASE-CANDIDATE READY
**Baseline:** `4f3263b` (`test: add explanation integration scenarios`)
**Offline validation:** 3555 passed, 2 deselected

Practical-1.0 is a trustworthy deterministic advisor for choosing between an
available Move and a legal Switch from trusted current battle authority. It is
not an exhaustive Pokémon battle simulator.

## Deterministic scope

The advisor composes supported switch legality and blockers, entry hazards and
entry abilities, direct incoming damage, KO/danger evidence, survival and
damage modifiers, supported action order, and bounded residual or
first-end-of-turn consequences. Trusted observations flow through lifecycle
confirmation, reducer/replay, runtime projection, and detached frozen
snapshots.

Recommendation ranking remains intentionally narrow: only proven deterministic
danger changes cross-action ordering; there is no generic safety, chip, status,
boost, recovery, or switch-native strategic score. A Move remains preferred
when actions share the same danger tier.

Missing, stale, malformed, unsupported, or identity-mismatched authority stays
unknown, incomplete, or unsupported. It is never converted into an absent
hazard, harmless item or ability, safe switch, zero damage, or certain result.

## Validation evidence

The release candidate is covered by three offline integration layers:

- `tests/test_v44_practical_1_0_end_to_end_scenarios.py` validates composed
  Move-vs-Switch outcomes, hazards, survival, action order, events,
  first-end-of-turn state, and conservative incompleteness.
- `tests/test_v45_practical_1_0_multiturn_lifecycle_scenarios.py` validates
  turn expiry, field replacement, switch identity isolation, hazard replacement,
  faint terminality, and detached frozen state.
- `tests/test_v46_practical_1_0_explanation_integration_scenarios.py` validates
  deterministic recommendation-to-presentation consistency and conservative
  UI-facing evidence visibility.

The final release-candidate audit found no current-contract correctness blocker
or outstanding T1 decision. Provider-facing claim schemas keep internal native
mechanics links out of generic explanations; direct-mechanics numeric claims
are linked only by the application to already-trusted deterministic evidence.
Unsupported numeric or mechanics claims remain rejected.

## Post-1.0 boundaries

The following are intentionally outside practical-1.0: broad item and ability
activation families (including berries and Black Sludge), toxic progression,
broad weather residuals, delayed effects, general turn simulation, exhaustive
move/ability coverage, broad non-damage strategic scoring, and richer
provider-generated explanation quality.

## Next phase

Recommended follow-up is a separately authorized bounded real-environment
smoke using this hardened provider-facing contract, then final release
declaration if that smoke is successful. Neither is implied by this
deterministic release-candidate declaration, and no provider call is required
for its offline validation.
