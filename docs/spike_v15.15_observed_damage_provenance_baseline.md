# v15.15 Observed Damage Ingestion Provenance Baseline

## Purpose and inventory

The production `CurrentObservedDamageDialog` accepts a user-confirmed previous direct-damage integer (`damage`) and category. It is amount-only, labels the source as opponent and target as self, and has no used-move, HP-before/after, turn, sequence, battle-log, or automatic producer. `CurrentHPDialog` separately accepts exact integer current/max HP; panel `hp_percent` is display state only. Item events already use structured canonical ingestion. Q12 is a detached, snapshot-derived deterministic candidate result.

| source | HP/damage mode | provenance | structured availability | remaining gap |
|---|---|---|---|---|
| Previous Damage dialog | exact amount only | active opponent attacker + active self defender captured at confirmation | v15.15 private copied input | no used move/sequence/transition |
| Current HP dialog | exact current/max snapshot | side only until structured capture | current-state context | not an event history |
| panel HP percent | percentage display | selected panel | no observed-damage producer | cannot be converted to exact damage |
| Q12 adapter | calculated rolls | frozen candidate attacker/defender/move | internal candidate only | not observed evidence |

## Canonical boundary

Only `direct_move_damage_observed` events are accepted. They contain attacker and defender side/slot/Pokémon/session provenance, nullable `move_id` and `move_slot`, `source=ui_observed_damage_confirmation`, `trust=user_confirmed_observation`, observed/confirmed flags, and `{damage_amount, hp_unit: exact, mode: amount_only}` payload. A selected recommendation move is never attached. Percentage and HP-transition input are unsupported rather than converted; a future transition source must retain its unit and validate `after <= before` and amount consistency.

Validation requires both current active owners, matching session, opposite sides, non-negative integer amount, explicit confirmation, and the fixed source/trust pair. Wrong owner, stale session, untrusted move association, percentage, and HP transition data are excluded without retagging. Healing, indirect damage, recoil, and self-damage are out of scope. Zero is accepted by the normalizer for a future explicit UI source, though the existing dialog does not emit it. With no sequence source, only identical capture records collapse; equal damage amounts are not a general occurrence key.

## Isolation, boundaries, and gaps

The event is made from a detached private confirmation record, then copied into `TurnSnapshot.current_state.observed_damage_context`. New-battle rollover clears the private record. Legacy battle input/prompt, public dialog payload, provider schema/adapters, Q12 formula/API, and candidate ranking are unchanged.

Calculated Q12 (`source=deterministic_q12`, derived deterministic trust) and observed damage remain distinct blocks. Neither creates or overwrites the other. Observed values never infer final stats, item, ability, modifiers, EV/IV/nature, or a damage roll. Future comparison requires exact units, trusted used move and owners, turn/sequence, full final stats, and critical/spread/screen/weather context.

Focused tests cover valid amount-only capture, detached snapshot copy, owner/session filtering, percent and invalid-transition exclusion, conservative deduplication, untrusted-move non-association, and Q12/reverse-inference separation. Provider/network budget is 0. There is still no battle-log or automatic capture, exact HP transition producer, trusted used-move producer, multi-turn event sequence, or modifier integration.
