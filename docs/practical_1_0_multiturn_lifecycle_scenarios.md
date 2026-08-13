# Practical-1.0 multi-turn lifecycle scenarios

`tests/test_v45_practical_1_0_multiturn_lifecycle_scenarios.py` exercises the
real observation-confirmation, reducer/replay, runtime-projection, and frozen
snapshot path across supported turn and identity changes.

Covered boundaries include turn-scoped same-turn events and first-end-of-turn
phase expiry; side-owned Tailwind and global Trick Room replacement; condition
and stat-stage ownership across an observed switch; complete hazard-state
replacement; detached frozen snapshots; and faint-terminal rejection of later
state updates.

The suite intentionally does not simulate unobserved turns, infer effect
activation, or add general turn-engine behavior. Unknown authority remains
unknown until an explicit trusted observation supplies it.
