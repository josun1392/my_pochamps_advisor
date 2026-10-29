# Foundation GAE lambda matched PPO v1

This opt-in compares .95 with 1.0 from one immutable Foundation/Adam parent.
It changes the GAE estimator and critic lambda-return target together, not the
native reward, gamma, architecture, action masks, auxiliary losses or optimizer.
The historical Foundation algorithm still rejects lambda values other than .95.
Only the exact `GaeOneFoundationPPO` class with its versioned marker admits 1.0.
Checkpoint loading rejects missing/mismatched markers and buffer objectives.
The one-time original-parent transition is explicit; subsequent resumes must
match the new objective exactly. Parent tensors and Adam are SHA-checked.

The maintained SB3-contrib 2.7.1 rollout/GAE/train owners remain authoritative.
Terminal episodes never bootstrap; time limits receive the maintained public
terminal-value reward correction once; rollout cutoffs retain value bootstrap.
Lambda one is not an optimal-action label or an exact action-value estimator.

Four arms use seeds 120021 and 121037, 65,536 transitions each, total 262,144,
with at most 8,192 new Adam steps. No fresh Adam, parent KL, temperature change,
slot consistency loss, residual actor or network changes are enabled.
The common 256-team V8 curriculum, ordered bring-three and original ten-slot
seven-policy fixed mixture are preserved. CPU 50%, RAM 12 GiB, four workers,
CPU device. Completed-rollout counters, checkpoint SHA and Adam clocks persist.

The first matched rollout is checked before any B optimizer update. Public
observation hashes, masks, actions, old logp, values, rewards and boundaries must
be exact; advantages/returns are expected to differ. A mismatch fails closed.
All rollout GAE arrays are independently recomputed, and the actual minibatch
normalization inputs/statistics are recorded without altering training tensors.
Expected variance increases are diagnostic, not automatic failure conditions.

Before learning, freeze 192 new case/RNG identities, including 96 held-out team
cases, three frozen rivals and both real native seats, T=1 argmax. Five models
yield 5,760 games, 1,152 each, 576 held-out each. Audit prior consumed panels
and training-team overlap; never use sealed final assets. Whole-team exclusion
does not imply unseen species or individual sets. Use only fixed 65,536 endpoints.

Primary: held-out mean-seed B minus A, 20,000 case-cluster bootstrap resamples
retaining rivals/seats/repetitions. Report individual repetitions, parent
comparisons and seat/rival summaries. A promising candidate needs both seed
points positive, combined primary lower bound above zero, positive mean B-parent
lower bound, and positive differences in both seats and at least two of three
rivals. Secondary contrasts are descriptive, not multiplicity-adjusted claims.
Two continuations do not establish training-seed population uncertainty.

The established bounded study owner records per-game start/commit receipts and
refuses duplicate campaigns. Automatic crash restarts are zero; durable resume
requires the unchanged frozen plan. Same native rejection/progress/resource
guards apply. No model promotion or subsequent experiment follows automatically.
