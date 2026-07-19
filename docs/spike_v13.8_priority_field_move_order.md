# v13.8 Deterministic Priority and Field-Aware Move Order

## Boundary

The v13.8 assessment is deliberately limited to selected-move priority,
user-confirmed final Speed, current Speed stage, trusted side-specific
Tailwind, and trusted global Trick Room. Its scope is exactly
`priority-stage-speed-tailwind-trick-room-only`.

Self priority is read from the selected move metadata. Opponent priority is
read only when the UI has an explicitly selected opponent move with trusted
metadata; missing opponent selection or priority returns
`missing_opponent_move_priority`, never a guessed priority zero. Final Speed
and stages reuse the v13.2 stage helper. Tailwind and Trick Room reuse the
strict current-field snapshot (`side_effects` and `global_effects`).

Priority decides first. Equal priority compares stage-adjusted Speed after a
side's Tailwind x2. Trick Room reverses only that equal-priority Speed
comparison. Equal effective Speeds return `tie`; no random winner is chosen.
Priority advantage resolves even where Speed data is absent.

Excluded: Choice Scarf, weather/ability/item speed effects, Prankster and all
ability priority changes, Quick Claw/Custap/random effects, paralysis speed,
move success, switching, forced switching, duration/expiry, and the turn
engine. The legacy speed comparison remains stage-only and unchanged.

## Acknowledgement

Known opponent selection is read back as `Opponent move | tackle | priority 0`.
Deterministic entries exactly read back known move priority, only available
effective speeds, and the move-order result/reason/scope. Current field
acknowledgements retain Tailwind side and Trick Room state. Parser exact-set
validation rejects identity, priority, field, speed, result, reason, scope,
duplicate, missing, and unavailable/result mutations.
