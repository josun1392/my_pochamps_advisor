# First end-of-turn phase authority

`first_end_of_turn_reached_observed` is an explicit user/application-confirmed,
session- and turn-scoped lifecycle observation. The reducer records only that
the supported turn flow reached its first end-of-turn boundary; it records no
effect activation, item consumption, residual result, or recovery result.

The detached runtime and frozen request projections expose `reached` only for
the matching trusted current turn. A later turn receives `unknown`, so a phase
record cannot leak across turns. Replay rejects supported same-turn state
transitions after this boundary, preserving the approved ordering after action,
HP, faint, and other supported state updates.

This authority does not by itself authorize Leftovers, Sitrus Berry, ability,
weather, toxic-counter, delayed-effect, or general end-of-turn inference. The
existing bounded burn/poison/Toxic Spikes and Poison Heal paths remain
unchanged until an effect-specific deterministic activation contract exists.
