# v13.5 Deterministic STAB and Type Effectiveness Integration

## Scope

The v13.5 adapter derives ordinary STAB from the UI-selected attacker's resolved
types and the selected move type, then derives base effectiveness from the
cached Gen 9 type chart and the UI-selected defender types. It supports one or
two resolved types and treats chart immunity as a resolved `0x` result.

The v13.3 base-only calculation remains in `base_damage_estimates`. When type
sources resolve, `damage_estimates` is the primary type-aware result with
`base_damage_stage_stab_type`; otherwise the type-aware record is separate and
unavailable. No result substitutes species defaults for an unresolved form/type.

## Integer calculation convention

The existing `base_damage` helper creates the v13.3 base value. Each existing
85..100 integer roll uses Q12 `apply_damage_modifier` for STAB (3/2 or 1/1),
then integer-floor application of the exact type-chart rational (0, 1/4, 1/2,
1, 2, or 4). The cached chart helper is reused; legacy formula, Q12, and raw
roll semantics are unchanged.

## Boundaries

Included: level, move power/category/type, confirmed final stats/current stages,
ordinary STAB, and base type chart. Excluded: ability/item type overrides,
Adaptability, Protean, Libero, Tera, weather, terrain, screens, burn, critical
hits, accuracy, survival effects, and between-turn effects. PoChamps' no-Tera
rule remains unchanged.

HP percentage, 16-roll OHKO, and 256-pair within-two-hits assessments reuse
type-aware rolls. The v13.4 zero-current-HP policy remains not-applicable.

## Result boundary

`[Deterministic Results]` separately acknowledges `STAB`, `Type effectiveness`,
damage range, and any HP/KO results. The parser exact-compares each category.
Advice must not recalculate values or claim ability/item/Tera type overrides.

## Verification

- `uv run pytest -q`: `2034 passed, 2 deselected`.
- Focused v13.5 and related v12/v13 regression selection: `559 passed`.
