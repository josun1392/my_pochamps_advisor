# Native learnability ladder, stage 1

`showdown-native-training-subset-v1` is an opt-in coordinator contract selecting
exactly 1 or 16 **train** teams from the immutable native V8 bank. It binds engine,
format, parent bank, indices, full team hashes, seed namespace and preview rule.
It cannot load test teams. Paths/hashes cross spawn; teams never enter policy info.
The one-team probe uses the same team on both sides and fixed ordered slots 1/2/3.
The sixteen-team probe independently samples teams and random ordered three-of-six.
This deliberately easy first probe also reduces preview diversity: a comparison
is a learnability ladder, not a causal isolation of team count alone.

`diagnostic_fixed_budget_v1` preserves fixed checkpoint curves without best-model
selection or plateau stopping. Historical `best_and_plateau` remains the default.
`validation_subset_probes` alternates consumed in-distribution diagnostic cases
with a hash-bound separate heldout bank, checking complete-team disjointness.
No sealed final set is used. Heldout teams originate from V8 train but are excluded
from these learners' subsets; frozen historical opponents may have seen them.

Fresh policy construction uses the existing PublicCategoricalPolicy and Adam.
There is no transfer, BC or offline warmstart. Historical PPO remains n_steps128
per worker, batch128, epochs4, target_KL.03, constant LR5e-5, entropy.01,
gamma1/GAE.95. Eight workers yield 1024 collected decisions/rollout and nominally
32 minibatch updates (0.03125/decision), subject to native masks/target-KL stopping.
PPO hyperparameter variants are not introduced in this experiment.

Optional `collect_rollout_diagnostics` records timing and pre-update probability
quantiles/entropy using **only existing public rollout arrays/masks**. Wait-only
rows are excluded from those distributions. It adds neither features nor rewards.
Timing separates native/vector rollout, PPO update intervals and diagnostics;
rollout time still includes Python policy inference/IPC, not pure engine time.
Public action-family counters are descriptive overlapping attack/setup/status
metadata, separate from recovery/defense selections and opportunities.

Artifacts, baselines, initial hash proof, fixed scenario membership, reference
model SHAs, checkpoint metrics and comparisons live outside the repository.
One foreground resource-controlled launch per distribution is bounded at5400s.
STOP/last durable checkpoint recovery remains available, but this task does not
automatically resume to fill the target or claim exact interrupted rollout replay.

VGC-Bench (Cameron Angliss, MIT) was inspected at
`d79f9532947ac114dce1dda2456a590afcd375b2`:
https://github.com/cameronangliss/vgc-bench . Its fixed-matchup/team-pool curricula
and opponent-stratified evaluation patterns inform this probe. Its VGC doubles,
server/OTS/model contracts and differing PPO schedule are not transplanted into
Champions M-C Singles; no external model/BC auto-download or public server is used.
