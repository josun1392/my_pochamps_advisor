# Foundation two-group opponent curriculum matched v1

One bounded comparison, using the frozen Foundation parameters **and restored
Adam** for all four arms. The completed 1,792-game calibration supports easy
`max_power` versus six competitive opponents, not a ranking within the six.
There are no new calibration games, parent KL, fresh Adam or model/reward changes.

## Frozen training design

Continuation seeds: **99221, 99222**; these are two stochastic continuations of
one trained parent, not independent full-training initializations. Each A/B arm
trains exactly 65,536 completed-rollout transitions, maximum total 262,144.
CPU50%, RAM12GiB, four Subproc workers, CPU device, same V8 256-team subset,
native ordered random bring-three, Foundation PPO and constant learning rate.

| Opponent | A throughout | B [0,32768) | B [32768,65536) |
|---|---:|---:|---:|
| max_power | 10% | 40% | 10% |
| champions_heuristic | 10% | 6 2/3% | 10% |
| tactical_heuristic | 10% | 6 2/3% | 10% |
| previous | 10% | 6 2/3% | 10% |
| historical | 10% | 6 2/3% | 10% |
| league_s0 | 30% | 20% | 30% |
| league_anchor | 20% | 13 1/3% | 20% |

A retains the original `case_index % 10` selection exactly. B uses the same
deterministic slot mechanism with 15 early slots (six easy, nine original
competitive slots), then the original ten. Conditional competitive weights
remain 1:1:1:1:3:2. Seven immutable identities remain in every stage; the
historical 12-entry top-level opponent-list limit is unchanged. The separately
versioned internal 15-slot schedule is bounded and strictly validated.

Stages use completed trained transitions in this experiment, not inherited model
timesteps, episode count or validation wins. Native episodes retain their selected
opponent to termination, so an episode may cross the nominal stage boundary.
Only subsequent resets use the new stage. Checkpoint chunks stop at boundaries,
including explicit resume from an intermediate checkpoint. No live hot-swap or
snapshot refresh occurs. Total early/easy exposure and temporal scheduling both
change; this is not a schedule-only effect at equal average opponent weights.

An opt-in coordinator receipt records every reset, slots, selected index,
probabilities, stage/cursor, model ID, case/scenario and learner-step count.
Initial construction/reset episodes with zero learner steps are distinguishable
from actual exposure. Completed/pending episode records preserve the same
receipt for cross-boundary and interruption audits. The receipt never enters
actor/critic observations, Gym policy info, rewards or auxiliary labels.

All four initial saved checkpoints are compared to the untouched original for
policy tensors, full Adam state/clock, global LR schedule and outputs on an
existing consumed public-state probe. New native games are not spent on this
preflight. Checkpoints at 0/32768/65536 are durable, with no validation selection.

## Frozen evaluation and decision

192 fresh case clusters (96 training-distribution and 96 non-training complete
teams), two real seats, three frozen rivals per case, five policies = **5,760**
games. Each model has 1,152 games including 576 held-out. Every case faces
`max_power` plus two competitive rivals. The six competitive opponents each
appear in 32 cases per stratum, using a predeclared balanced rotation; no
outcome-dependent allocation. Evaluation weights are easy 1/3, competitive 2/3
(each competitive 1/9); they intentionally differ from the training mixture.

Use strict masked argmax and fixed-budget endpoints. The original Foundation
and four final policies share cases, frozen opponents, initial native seeds and
actual seats. Divergent actions do not imply identical downstream RNG. Existing
consumed panels/initial scenarios are audited; reused banks/individual sets are
disclosed. No sealed final data or previous 1,792 outcomes are evaluation rows.

Primary: mean over the two paired continuation repetitions of **B−A held-out
team win fraction**. Resample case clusters retaining seats, rivals and all five
policies/repetitions together. Report per-seed, all-team, opponent and group
results and parent-win retained/lost/new wins. Two repetitions cannot provide a
precise training-seed-population CI. Other contrasts are descriptive.

GO for a subsequent bounded expansion requires positive primary 95% lower
bound, positive held-out point direction in both repetitions, nonnegative
overall and competitive-held-out B−A point differences, and clean completeness/
safety audit with no truncations. Otherwise NO-GO for expansion means insufficient
evidence; it is not equivalence or proven inferiority. No model promotion.

The existing detached owner enforces zero automatic restarts, 3,600s training,
5,400s evaluation and 9,000s combined ceilings. These are maxima, not permission
to exceed transition/game budgets. Receipt storage is preflighted before battles;
uncertain started games are never silently replayed. Existing native progress
retry guards remain authoritative; evaluation additionally uses the same public
transition guard and records rejected requests coordinator-side. On long healthy
runs, publish PID/rate/KST return guidance and end the T3 turn without polling.
