# Poison Heal first end-of-turn transition

The existing first post-hit status-residual transition now supports exact
candidate-B-owned `poison-heal` when B is trusted to be poisoned or badly
poisoned. It requires B-owned exact current/max HP, exact ability authority,
an authoritative qualifying condition, and a deterministic incoming minimum
damage value. After a proven nonlethal incoming hit, the transition restores
the canonical one-eighth of maximum HP, capped at maximum HP.

This is part of the same bounded first end-of-turn transition used by the
existing burn, poison, and Toxic Spikes residual path. A guaranteed direct
incoming KO terminates before any end-of-turn effect; it is therefore not
misreported as a residual result. The existing danger path only uses a proven
residual KO, so Poison Heal introduces no generic recovery reward or new
score.

Unknown condition, ability, HP, damage, or survival-effect state remains
incomplete. This slice does not model Poison Heal with untrusted status,
additional residual sources, item recovery, weather, Leech Seed, trapping,
turn counters other than the already-supported first Toxic Spikes tick, or a
general end-of-turn engine.
