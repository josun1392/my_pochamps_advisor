# v13.3 Deterministic Limited-Scope Damage Estimate

## Inventory And Level Policy

- `advisor.damage.formula.base_damage(...)` owns the existing integer base
  formula. The full `calc_damage_rolls(...)` path additionally applies type,
  STAB, critical, field, ability, item, screen, and other modifiers, so v13.3
  does not call it.
- The existing raw-roll convention is the 16 integer factors 85 through 100;
  v13.3 reuses that order after the existing `base_damage` helper. Q12 is used
  by the full modifier path and remains unchanged.
- Legacy `advisor_damage_estimate` obtains stats from `stat_profiles` (or
  defaults) and attaches `damage_estimate` plus `ko_context`. v13.3 neither
  reads those stats nor alters those outputs.
- UI selected moves provide `move_id`, `category`, and `power`. The project
  already fixes UI-selected Champions stat profiles and legacy damage at level
  50 (`DEFAULT_LEVEL` / profile `level`); v13.3 documents and uses that same
  fixed project rule without importing legacy stat values.

## Contract

Only user-confirmed final stats, user-confirmed current stages, selected-move
metadata, and the documented level-50 rule feed the result. Physical maps
self Attack to opponent Defense; Special maps self Special Attack to opponent
Special Defense. Missing required stats and incomplete metadata are
`unavailable`; status, variable-power, fixed-damage, OHKO, and unresolved
multi-hit moves are `unsupported_move`.

The range is `base_damage(level, power, offense, defense)` followed by each
integer roll `base * factor // 100` for 85..100. It is emitted as
`base_damage_stage_only` and explicitly excludes STAB, type effectiveness,
critical, burn, weather, terrain, screens, item, ability, spread, Helping
Hand, Friend Guard, priority, and KO calculations.

## Result And Response Boundary

The separate `deterministic_calculation_context.damage_estimates` contains
only this result; it never replaces legacy `damage_estimate` or `ko_context`.
Resolved entries require an exact deterministic acknowledgement:

`Damage estimate | self | opponent | move | min-max | base-damage-stage-only`

The parser rejects changed sides, move, range, scope, duplicates, or missing
lines. The semantic boundary rejects claims that excluded modifiers, exact
damage, remaining HP, or KO outcomes were resolved. The sanitized CLI
evaluator can optionally exact-check the result block without changing its
stdout schema or exit codes.

## Verification

- New damage and sanitized CLI contracts: 23 passed.
- `uv run pytest -q`: 2010 passed, 2 deselected in 27.68s (offline full suite).
