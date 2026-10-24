# Masked training-temperature schedule v1

This opt-in experiment retains Foundation v1's V5-v3 public encoder, all 674,939
parameters, native35 masks, sparse terminal reward, gamma1/GAE.95, PPO settings,
restored parent Adam and fixed V8 256-team/opponent protocol.

`TemperatureFoundationPPO` wraps the maintained Foundation policy distribution
factory only during collection and optimization. Its action net is strictly
Identity: raw actor scores are divided by the declared positive temperature
before native masking. T1 performs no extra numerical arithmetic. The same T
is used for sampling, old logp, PPO ratios, entropy and legal-uniform KL. Values
and auxiliary prediction inputs/targets are unchanged. No private state enters
the policy; no opponent identity or schedule indicator is an input feature.

Outside collection/update the policy always uses T1. Positive temperature
preserves argmax at identical weights. Evaluation is native masked argmax T1;
this does not imply that a learned value is an exact greedy win probability.

The separate `masked_temperature` algorithm manifest binds the full schedule.
Each completed512 rollout advances `temperature_trained`; collected incomplete
rollouts do not. Control T1 and treatment T1.5 for49152 transitions then T1 for
16384 each start with the same parent weights and Adam. Seeds110021/111037 are
two stochastic continuation repetitions of one parent, not independent complete
training replications. T changes score gradients by1/T and state visitation,
so this intervention is not an entropy-coefficient experiment.

Every rollout stores raw scores, actual masked probabilities, actions, masks,
old logp, entropy, values, rewards and GAE labels outside Git. The updater
recomputes the entire rollout at its bound T before any Adam step; disagreement
over2e-5 in float32 logp/value fails closed. Sampled versus stored logp and an
independent float64 masked-softmax formula are also checked. Trained receipts
bind capture SHA, Adam clock and T. This adds no substitute simulator or labels.

The policy tensor layout is unchanged. Explicit adoption from the original
Foundation loads all compatible parameters and Adam into the versioned algorithm.
Same-contract reload restores progress and schedule. Metadata and class checks
reject silently loading an opt-in checkpoint through the base algorithm.
Inference defaults stay T1 for historical and new models. STOP discards partial
rollout state and does not claim an exact interrupted native/RNG trajectory.

The study reuses the detached parent-anchor native runner, strict checkpoint
validation, progress-based retry monitor, actual-seat evaluator, SHA receipts and
case-cluster statistics. Its only statistical primary is heldout-team mean(B-A).
All four fixed65536 endpoints and the untouched parent share192 cases ×2 native
seats ×3 frozen rivals =1152 games each,5760 total. Ninety-six cases per model
are primary heldout; the legacy `train` scope label denotes secondary in-domain
**excluded teams**, not permission to train on evaluation teams. Both complete
team pools are excluded from the learner256. Consumed historical cases are
audited and never described as still sealed; species/set overlap is disclosed.

Temperature1 exact-update equivalence, logp/mask/entropy/KL/gradient arithmetic,
wrong-temperature fail-before-update, save/load/continue,49152 boundary, aborted
rollout and paired-count statistics have focused offline tests. Optional existing
trusted capture fixtures generate no new environment transitions. The approved
online experiment is capped at262144 new transitions, with no automatic tuning,
third seed, model promotion, PPO expansion or Best-Response integration.

External artifacts contain frozen source/config/model identities, partition
audit, exact training and evaluation accounting, independent statistical closure
and resource costs. No performance result is implied by this implementation.
