# Observed move-result condition transition

The production lifecycle accepts an explicit user-confirmed
`condition_applied_observed` result for an identity-matched active Pokémon.
Only the six major conditions `burn`, `poison`, `toxic`, `paralysis`, `sleep`,
and `freeze` are valid. The result is an observed fact, optionally linked to a
used-move observation; it does not infer that a move can apply a condition or
that it hit.

The existing replay policy maps this event to the canonical `set_condition`
reducer effect. The reducer writes the condition only to the exact target
identity, so later snapshots can feed already-supported burn damage, status
power, action-order, and first-residual consumers. Unknown conditions,
condition removal, secondary-effect chance, immunities, ability/item effects,
and multi-turn state remain outside this bounded transition.

An explicit observed faint is terminal for later condition transitions on that
same identity; replay rejects the contradictory ordered batch atomically.
