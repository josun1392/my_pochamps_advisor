# v13.6 Burn, Weather, and Screen Modifier Integration

Trusted current-condition and current-field snapshots are the only sources.
Confirmed attacker burn halves physical damage; confirmed rain/sun applies only
ordinary Fire/Water 3/2 or 1/2 weather modifiers. Existing Q12 damage rounding
is reused after type-aware rolls, with burn followed by weather.

The existing screen helper requires `is_doubles`, but the trusted UI field
schema has no battle-format source. Reflect, Light Screen, and Aurora Veil are
therefore deliberately unavailable as `missing_battle_format_for_screen` rather
than guessed as singles/doubles. No screen modifier is applied.

This partial integration excludes ability/item exceptions (Guts, Facade, Cloud
Nine, Light Clay), terrain, critical, duration, survival, and between-turn
effects. Context-modified resolved rolls are used by the existing HP/OHKO/two-hit
helper, including its zero-HP not-applicable policy.
