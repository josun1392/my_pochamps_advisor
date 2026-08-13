# Toxic progression authority

Practical 1.1 adds a reducer-owned, identity-bound `toxic_progression` record.
It stores the exact **next** toxic stage for one Pokemon, not an inferred count
from its current `toxic` condition.

An explicit trusted `condition_applied_observed` result may initialize stage 1
only when it is a newly applied toxic condition with a positive trusted turn
number. Replay sequence keeps that observation before a later confirmed
first-end-of-turn phase. A Pokemon merely observed as toxic has unknown
progression and remains incomplete for scalable toxic residual damage.

At each later confirmed first end-of-turn phase, the active matching Pokemon
with exact HP/max HP takes `floor(max_hp * stage / 16)`, clamped at zero; the
stored next stage then becomes `min(stage + 1, 15)`. The phase record prevents
replaying the same tick. Exact stage authority can also feed the existing
post-hit residual KO evidence path; Poison Heal remains its independent fixed
one-eighth recovery rule.

Progression is cleared when that Pokemon switches out, when its toxic
condition is removed, and when it is explicitly fainted. A replacement identity
never inherits it. Runtime and frozen projections carry only the active
identity's detached record. This does not add condition inference, toxic
duration tracking, a general status-instance engine, weather residuals, or a
general turn simulator.
