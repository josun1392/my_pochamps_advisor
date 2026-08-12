# Faint-terminal observed move-result timing

The reducer now treats an explicitly observed faint as terminal for later
same-identity HP, major-condition, absolute stat-stage, known-move, and held
item transitions in the ordered replay. A valid sequence remains exact HP
reaching zero, followed by the explicit faint observation. Any later HP,
condition, stat-stage, known-move, or item result for that fainted owner
conflicts atomically instead of leaving stale state for residual, damage,
legality, or action-order consumers.

This is an ordering rule for already trusted observations; it does not infer a
faint from damage, a move hit, a secondary effect, immunity, or a revival. It
also does not model revival, switch-reset timing, item activation, or general
turn simulation. Explicit observations that occur before a faint keep their
existing canonical reducer behavior.
