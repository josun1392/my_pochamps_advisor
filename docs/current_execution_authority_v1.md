# Deterministic current execution authority v1

`deterministic-current-action-authority-v1` is selection-only: it establishes
which actions are selectable at D0. It does not grant any authority to execute
them.

`deterministic-current-execution-authority-v1` is a separate, detached bundle
bound to the same session, decision fingerprint, decision owner, and active
Pokémon identity. The bundles can only be joined when every D0 binding agrees.

For a fresh attack, historical observed damage and other historical post-action
results are not present-tense predictive authority. Attack records therefore
remain `observation_required` in v1.

For a manual switch, an existing
`identity_bound_incoming_current_state_v1` authority can be frozen as current
predictive execution authority only when its owner and its explicit source
branch fingerprint match D0. The incoming authority retains its existing shape
for the switch materializer; the execution bundle does not create a parallel
battle-state model. Missing or incomplete incoming state remains
`execution_incomplete` and never changes selection legality.
