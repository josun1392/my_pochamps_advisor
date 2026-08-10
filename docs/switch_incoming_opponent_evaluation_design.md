# Switch Incoming Opponent Evaluation

Implemented in `llm/advisor_switch_incoming_evaluator.py`.

The adapter accepts only a complete detached authorized transition with
`self_switch_first`, a supported redirected `selected-pokemon` opponent action,
and a B record whose session/slot/Pokémon identity matches both post-switch
active identity and switch candidate.  It then adapts the redirected frozen
opponent candidate and delegates to `evaluate_opponent_action_candidate`.
There is no switch-specific Q12, move-success, KO, or probability formula.

Before delegation, active-A self authority is removed from the copied opponent
snapshot.  B's identity-bound current type, base stats (an explicitly supplied
mechanics prerequisite, never an inferred final stat), final stats, ability,
item, and exact HP provenance are the only defender source.  Missing B type or
stats remains insufficient context.  A known fainted B is rejected before any
damage call.  The original snapshot, transition, opponent action, and switch
candidate remain detached and unchanged.

The result is candidate-local: switch candidate ID, B target, opponent action
ID, direct move-success/damage/Q12 evidence, and separate supportability.  A
direct evaluator KO/probability result is direct-move evidence only.  Because
entry hazards, entry/exit abilities, and other entry effects are not executed,
`full_switch_outcome_supportability` is always `unsupported_mechanic` with
`entry_effects_not_applied`; the adapter never claims full post-switch survival
or probability certainty.

Unsupported redirection, stale or forged identity, ranking, provider payloads,
presentation, switch selectability, and incoming opponent prediction are all
outside this module.  The next policy boundary is move-vs-switch ranking.
