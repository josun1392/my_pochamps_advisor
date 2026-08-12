# Observed exact HP recovery

The bounded recovery transition accepts an explicit user-confirmed
`exact_hp_recovery_observed` result for one identity-matched Pokémon. It
contains exact pre- and post-recovery HP, and only permits an unchanged or
increased observed value from a nonzero, non-fainted Pokémon. The existing reducer verifies the exact pre-state
and, when maximum HP is known, rejects a post-recovery value above it.

Lifecycle confirmation, collection, and replay map this observation to the
canonical HP state transition. Later detached runtime and frozen state can
therefore consume the updated HP through existing KO, full-HP survival, and
healing-aware paths.

The observation does not infer that a recovery move succeeded, how much a move
would recover, an item or ability trigger, drain, Wish timing, or residual and
end-of-turn ordering. Unobserved or invalid HP values remain unknown.

Within this bounded model, a faint is valid only after exact current HP reaches
zero. Recovery cannot revive a zero-HP or already-fainted Pokémon, so an
ordered replay cannot produce a stale alive-HP state after a faint or a faint
state after a successfully restored HP value. Revival mechanics remain
unsupported.
