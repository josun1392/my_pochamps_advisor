# Controlled critic trainability pilot

This opt-in experimental contract preserves the accepted set-context A actor and
historical loaders. Existing A controls are reused, never retrained. The new
policy has exactly the same 679,099 parameters: only the existing 4,160 residual
actor parameters and `mlp_extractor.critic.*` / `value_net.*` are trainable.
All other tensors, including prediction heads and shared representation, remain
frozen. No new observation, critic layer, reward, or PPO loss is introduced.

Both treatment continuations start independently from the original Foundation
weights, with fresh Adam and the original A optimizer defaults. Seeds 116051 and
116053, original TRAIN cases and RNG namespaces, four sequential native workers,
16 x 1,024-transition windows, and PPO settings remain unchanged. The first 512
transitions count toward the 16,384 budget and must match the retained A first
rollout bit for bit before any optimizer step. Each arm permits exactly 512
optimizer steps. Every step checks frozen tensors and records actor/critic
gradients, clipping and parameter deltas. Global clipping at 0.5 includes the
newly trainable critic; its interaction with actor gradients is an intended
consequence of this treatment, not an independently isolated mechanism.

Historical residual-only and new critic-trainable checkpoints use distinct strict
loaders and metadata. The new loader reinstates trainability on reload and checks
weight, frozen-block and Adam identities. Checkpoints at 4K/8K/12K/16K are reloaded
without extra updates. Interrupted runs preserve partial checkpoints but do not
automatically replay uncertain native starts or optimizer steps.

The separately frozen source admits the first 160 legal teams from one 200-team
batch generated from logical seed 116061, mapped by maintained `seed4` to native
four-word RNG. Admission excludes semantic full-team, species roster, and joint
moveset identities against all registered banks, pilot, sealed *identity assets*
and previous Q_dev_new. No sealed results are read. Individual sets may recur;
finite-source composition and reuse are descriptive, not distribution equivalence.
Failure to obtain 160 teams blocks execution. The external source contract and
native generation/validation receipts precede the training/evaluation plan.

Evaluation is 80 team pairs x two owners x four RNG x two real native seats x five
frozen models = 6,400 starts, with Foundation argmax as opponent. Trace recording
is reused from the accepted Q_dev_new owner and promoted to a small shared helper;
it records player-visible first inputs and selected-to-native-action links.
Any missing, duplicate, rejected, truncated or uncertain game stops execution.
No unapproved replacement is scheduled.

Primary analysis is Aprime-A terminal return, retaining both repetitions and all
owners/RNG/seats inside each of 80 bootstrap clusters (20,000 draws, seed 116063).
Two seeds do not establish training-seed population uncertainty. First-action
changes are not causal counterfactual effects. No sealed claim or promotion follows.

Critic diagnostics separate training GAE-target MSE, identical-input retained
TRAIN validation, and policy-dependent visited-state terminal MSE. The validation
contains 15 exact-feature public snapshots from the earlier frozen-policy TRAIN capture: they
were never used by an optimizer, but were previously inspected diagnostically.
Their recorded GAE targets are not exact state values or independent terminal
truth. One of 16 historical public transports no longer matches its captured
feature SHA and is excluded before training in append-only contract revision 02;
no states or labels are repaired or replaced. This small common-input panel cannot by itself establish useful critic
learning or combat strength. The new 6,400-game source is never used to fit models.

CPU hard cap 50%, at most four native workers, RAM 12 GiB, CPU inference/update,
no GPU/provider calls. Original Foundation/Adam, all historical checkpoints,
master and protected files remain untouched. Artifacts and private native source
teams live outside Git. Only the narrow policy, audit, runner, tests and this
contract document belong in the source commit.
