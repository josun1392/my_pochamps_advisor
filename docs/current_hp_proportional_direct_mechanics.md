# Current-HP proportional direct damage

The native direct-damage evaluator now supports Eruption, Water Spout, and
Dragon Energy when exact frozen attacker current and maximum HP are available.
It applies the canonical `max(1, floor(150 * current HP / maximum HP))` move
power before the existing Q12 damage, KO, and danger evaluation.

This is an attacker-owned current-state transition only. Unknown, malformed,
or impossible HP authority remains incomplete; a known fainted attacker is not
a supported acting state. Bracket-power, speed, weight, field, status, counter,
and all other dynamic-power moves remain outside this bounded slice.
