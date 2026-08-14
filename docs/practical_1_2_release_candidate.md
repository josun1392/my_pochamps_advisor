# Practical 1.2 Release Candidate (Superseded)

**Status:** SUPERSEDED BY PRACTICAL-1.2 FINAL
**Final record:** [`practical_1_2_final.md`](practical_1_2_final.md)
**Package version:** `1.2.0`
**Release baseline:** `b4a4061` (`test: add practical 1.2 UI integration scenarios`)
**Offline validation:** 3647 passed, 2 deselected

Practical 1.2 improves trusted-state capture and recommendation readiness for
the existing deterministic Move-vs-Switch advisor. It makes already-supported
explicit authority easier to provide without inferring battle state, changing
recommendation ranking, or expanding Pokémon mechanics. It remains a
practical advisor, not a complete Pokémon battle simulator.

## Added bounded scope

- a read-only structured readiness projection from canonical deterministic
  incomplete and unsupported results;
- grouped presentation of confirmable authority, unavailable authority, and
  unsupported mechanics;
- readiness-linked held-item capture through the existing item-profile flow;
- paired exact current/max HP capture for the active self and opponent Pokémon;
  and
- session, slot, and Pokémon-identity protection for stale readiness routes
  and HP records.

All capture remains explicitly confirmed. Opening a route, cancelling a
dialog, or leaving a side unticked does not mutate authority. Successful
confirmation refreshes the current frozen readiness evaluation; resolving one
gap leaves other material gaps visible.

## Preserved contracts and validation evidence

- The Practical 1.2 UI integration scenarios cover multi-gap presentation,
  explicit confirmation routes, paired and partial HP capture, held-item route
  identity checks, stale/cancel protection, detached readiness projection, and
  conservative unavailable/unsupported handling.
- The full offline suite passes: 3647 passed, 2 deselected.
- Practical 1.1 deterministic mechanics, danger-only cross-action ranking,
  same-tier Move preference, and conservative unknown/incomplete semantics are
  unchanged.
- Readiness does not create a second authority model, infer values, autofill,
  use species fallback, ask a provider to guess state, or automatically capture
  battle state.

## Post-1.2 boundaries

Practical 1.2 intentionally excludes same-turn event capture UX,
provenance-aware toxic-progression capture, OCR or screen capture,
provider-based state inference, broader automated battle-state capture,
non-damage strategic utility, and multi-turn or turn-engine planning.

Practical 1.2 does not claim automated battle-state capture, strategic
completeness, or exhaustive Pokémon simulator completeness.

## Historical next phase

Practical 1.0 and Practical 1.1 final records remain the historical release
evidence for the deterministic core. Practical 1.2 may proceed to separately
authorized release validation and final declaration under this bounded scope.
