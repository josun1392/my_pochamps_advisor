# v13.7 Trusted Battle Format and Screen Integration

`user_confirmed_battle_format` accepts only `singles` or `doubles`. It supplies
the existing screen helper's format argument without inferring format from UI
layout or team size. Reflect is physical-only, Light Screen special-only, and
Aurora Veil applies to either category. Canonical precedence is Reflect/Light
Screen before Aurora Veil, so reductions never stack. Existing Q12 rounding
produces singles 1/2 and doubles 2/3 reductions after burn/weather.

Without a trusted format, the v13.6 unavailable boundary remains intact.

Production normalization maps only an explicit UI confirmation into
`battle_format_context.current_battle_format`, retaining `source` and known
confidence. The raw confirmation is stripped before serialization. With the
limited-context switch off, neither the normalized context, the format
acknowledgement, nor screen-aware deterministic results are emitted.

The structured acknowledgement is `Battle format | singles` (or `doubles`).
Applied reductions add exactly one deterministic line: `Screen modifier |
opponent | reflect | singles | 1/2`. The parser exact-compares format, side,
screen, multiplier, damage ranges, percentages, KO results, and calculation
scope. Advice may restate the confirmed format and the limited Reflect result,
but cannot claim inference, bypasses, duration, expiration, persistence, or
ability/item overrides.
