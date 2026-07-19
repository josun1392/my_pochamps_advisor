# v13.7 Trusted Battle Format and Screen Integration

`user_confirmed_battle_format` accepts only `singles` or `doubles`. It supplies
the existing screen helper's format argument without inferring format from UI
layout or team size. Reflect is physical-only, Light Screen special-only, and
Aurora Veil applies to either category. Canonical precedence is Reflect/Light
Screen before Aurora Veil, so reductions never stack. Existing Q12 rounding
produces singles 1/2 and doubles 2/3 reductions after burn/weather.

Without a trusted format, the v13.6 unavailable boundary remains intact.
