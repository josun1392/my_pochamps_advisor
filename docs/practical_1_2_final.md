# Practical-1.2 Final Release

**Status:** FINAL
**Package version:** `1.2.0`
**Release baseline:** `78682b3` (`docs: record practical 1.2 release candidate`)
**Final offline validation:** 3655 passed, 2 deselected
**Bounded in-process release smoke:** PASS (provider/network calls: 0;
desktop/global automation: none)

Practical-1.2 improves trusted-state capture and recommendation readiness for
the existing deterministic Move-vs-Switch advisor. It makes already-supported
explicit authority easier to provide without inferring battle state, changing
recommendation ranking, or expanding Pokemon mechanics. It remains a practical
advisor, not a complete Pokemon battle simulator.

## Final bounded scope

Practical-1.2 adds a read-only structured readiness projection from canonical
deterministic incomplete and unsupported results; grouped presentation of
confirmable, unavailable, and unsupported gaps; readiness-linked held-item
capture through the existing item-profile flow; and paired exact current/max HP
capture for active self and opponent Pokemon.

All capture remains explicitly confirmed. Opening or cancelling a route, or
leaving a side unticked, does not mutate authority. Session, slot, and Pokemon
identity checks reject stale readiness routes and HP records. Successful
confirmation refreshes the frozen readiness evaluation; resolving one gap does
not hide other material gaps.

## Release evidence

- `tests/test_v62_practical_1_2_ui_integration_scenarios.py` covers multi-gap
  presentation, explicit confirmation routes, paired and partial HP capture,
  held-item identity checks, stale/cancel protection, detached readiness
  projection, and conservative unavailable/unsupported handling.
- The final offline baseline is 3655 passed, 2 deselected.
- The bounded in-process release smoke reused production-backed Pikachu versus
  Arcanine with cached Thunderbolt. Trusted cached priority was exactly 0;
  native direct-Q12 resolved; unknown attacker item produced `Held item
  unknown` and the existing `current_item` route. Paired HP valid apply and
  stale-owner rejection passed. Item open/cancel caused no mutation, and
  explicit Choice Specs confirmation refreshed readiness and removed the item
  gap while unrelated unresolved authority remained visible.
- The smoke made zero provider or network calls and used no desktop/global
  automation.

Practical-1.1 deterministic mechanics, danger-only cross-action ranking,
same-tier Move preference, and conservative unknown/incomplete semantics
remain unchanged. Readiness creates no second authority model and does not
infer, autofill, use species fallback, guess state through a provider, or
automatically capture battle state.

## Bounded RC integration corrections

RC validation corrected only application-boundary integration defects: invalid
candidate preparation no longer renders as ready; active selectable moves use
canonical `slot_index`; confirmed current-state context reaches preparation;
and the supported application path requests native direct mechanics. Checked-in
canonical move metadata now preserves explicit priority where available. These
changes preserve strict ownership and unknown-authority behavior.

## Post-1.2 boundaries

Practical-1.2 intentionally excludes same-turn event capture UX,
provenance-aware toxic-progression capture, OCR or screen capture,
provider-based state inference, broader automated battle-state capture,
non-damage strategic utility, and multi-turn or turn-engine planning.

Practical-1.2 does not claim automated battle-state capture, strategic
completeness, or exhaustive Pokemon simulator completeness.

## Next phase

Practical-1.2 is complete under this scope. Future work remains separately
planned post-1.2 product, capture-automation, strategic-utility, or turn-engine
work; none is implied by this final declaration.
