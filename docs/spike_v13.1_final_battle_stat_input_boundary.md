# v13.1 Final Battle Stat Input And Calculation Boundary

## Inventory

Species base stats are read from repository/cache data. The existing Champions
stat-profile UI and `stat_profiles` path can already supply six user-confirmed
final stats to `llm.advisor_damage_estimate`; damage estimates use them when a
complete profile is available, and `speed_context` can compare confirmed raw
Speed. That legacy path has its own Champions point assumptions and remains
unchanged.

Current stat stages are not applied to damage or speed calculation. Existing
ability, item, weather, and field contexts are not generalized as resolved
modifiers. Raw rolls, Q12, damage formulas, KO handling, and order calculation
are unchanged.

## V13.1 Contract

Added `user_confirmed_final_battle_stat`: a direct user-confirmed, positive
integer stage-unmodified final stat. Supported IDs are hp, attack, defense,
special-attack, special-defense, and speed. HP means maximum HP, never current
or post-turn HP. A broad 1..9999 structural bound is used because v13.1 does
not infer species, level, EVs, IVs, nature, items, or abilities.

The limited-context gate controls the new UI/session confirmation, normalized
`final_stat_context.current_final_stats`, prompt guard, and structured
`Current final stat | side | stat | value` acknowledgement. A pure adapter
returns separately validated `base_final_stats` and `current_stat_stages`; it
does not apply multipliers or calculate effective stats, damage, or order.

## Verification

- `uv run pytest`: 1984 passed, 2 deselected in 32.18s (offline full suite).

## Next Step

v13.2 should decide how complete direct final-stat input may safely join the
existing deterministic damage/speed adapters, without treating stages or
temporary modifiers as already resolved.
