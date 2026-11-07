# Actionable-decision advantage normalization v1

This experimental intervention changes one assignment in the locally installed,
pinned sb3-contrib 2.7.1 `MaskablePPO.train` AST. The source hash and unique original
expression are checked before deriving the function; its reverse AST must exactly
match upstream. No installed file or global class is patched. A narrow MRO seam
keeps the Foundation finite-gradient guard, auxiliary and legal-uniform KL owners
above this function. All other train statements, including normalization timing,
policy clipping, whole-minibatch mean, value/entropy losses and Adam, remain intact.
The upstream MIT notice is retained in the implementation.

For each original minibatch, select `legal_mask.sum(1) > 1` only for the mean and
sample standard deviation (PyTorch correction=1). Apply the original formula
`(advantage - eligible_mean)/(eligible_std + 1e-8)` to every row. Forced decisions
are neither deleted nor removed from policy/value/entropy reductions, rollout,
reward, return or GAE. Their masked single-action policy gradient stays zero.
When zero or one eligible row exists, all normalized advantages in that minibatch
are explicitly zero; there is no full-batch fallback. Other losses/rows remain.
This edge rule is deterministic and finite and does not estimate a variance from
one actionable sample. Invalid masks/nonfinite inputs or outputs fail closed.

The architecture is the original A set-context actor (679,099 parameters), with
only its 4,160 residual parameters trainable. Critic, shared encoder and prediction
heads remain frozen. Initialization and fresh Adam match original A. The two old
A final checkpoints are reused. Only An seeds116051/116053 receive16,384 new
transitions and512 Adam steps each. The first512 decisions per seed must match
retained A before any update. No new observation, reward, temperature, auxiliary
coefficient, sampler or optimizer setting is introduced.

Dedicated algorithm and metadata identities prevent silent resume through the old
normalizer. The historical Foundation train path rejects an experimental marker
loaded into its base class; checkpoints without that marker follow the unchanged
path. Inference still uses the same frozen public features and native35-action
mask. Actual per-minibatch normalization records bind raw/normalized advantages,
eligibility, sample actions and old logp to the existing PPO audit.

SB3 checkpoint construction calls `set_random_seed(model.seed)` and initializes
new modules. The original A owner did not reload intermediate checkpoints; the
shared critic owner does. Therefore this experiment's verification loader restores
Python, NumPy and CPU Torch RNG states even on exceptions. This ensures verification
loads have no effect on subsequent learner sampling. Pre-execution revision02
records this isolation; no old results/models are rewritten. The earlier critic
study has an additional checkpoint-load RNG confound, not a newly measured strength
result. Normalization is still the only intended training intervention here.

The bounded segment/checkpoint/evaluation owner accepts an explicit implementation
adapter and treatment prefix. Its default critic experiment is unchanged. New
plans disable that experiment's optional15-state value validation; this task does
not use those labels. Frozen evaluation trace and receipt machinery are reused.

Before learning, freeze a new160-team/80-pair native-validated source from logical
seed116071. Exclude semantic team, roster and joint-moveset identities against all
maintained banks, pilot, sealed identity assets, Q_dev_new and critic source.
Individual sets may recur. Five frozen models each play1,280 games against fixed
Foundation argmax, at both actual seats and reciprocal team ownership:6,400 total.
Primary An-A terminal return uses80 team-pair clusters with both repetitions,
owners, RNG and seats kept together. Two seeds do not estimate seed-population
uncertainty. First-action changes are not causal battle-outcome effects.

No architecture search, extra learning/evaluation, sealed result access or model
promotion follows. External source/plans/captures/checkpoints/results preserve
SHA-bound provenance; master/protected files and all historical models stay intact.
