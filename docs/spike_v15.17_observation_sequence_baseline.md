# v15.17 Observation Sequence Baseline

`_observation_sequence` is a session-local UI confirmation counter. Previous Damage creates one private observation ID and monotonic sequence; new battle resets the counter. It is neither an advice request token, battle-session number, candidate/Q12 order, nor a game turn.

Canonical observed damage now carries `observation_id`, nullable `observation_sequence`, and nullable `turn_number`. A turn is retained only from an explicit `ui_turn_number_confirmation` with user-confirmed observation trust; there is no default turn. Snapshot output sorts by sequence then ID, keeps equal damage at different IDs, and does not mutate HP/current state. Same-ID duplicate/conflict handling remains a future producer responsibility: this baseline never assigns a replacement sequence to hide a conflict.

No Turn Engine, reducer, automatic HP update, provider schema change, Q12 change, or inference is included. Future work needs trusted turn input plus switch/faint/condition/item/field events before replay/reducer design.
