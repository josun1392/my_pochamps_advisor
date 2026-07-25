# v15.26 Used-Move and Exact HP-Transition Producers

The private confirmation boundary now accepts explicit production confirmations:
`ui_used_move_confirmation` for self-owned used moves and
`ui_exact_hp_transition_confirmation` for exact non-increasing HP transitions.
Both require `user_confirmed_observation`, session/owner identity, and valid
payloads; they get canonical IDs/sequences only after validation.

Selected moves, current HP, percentages, Q12, and damage inference never create
these records. HP transitions may carry an explicit related damage observation
ID, but no automatic linking or correction occurs. Opponent move ownership,
switch/faint UI, and snapshot collection remain gaps. No state/store/reducer/UI
mutation or provider call occurs.
