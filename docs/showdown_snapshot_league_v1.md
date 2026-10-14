# Frozen snapshot continuation V0

`scripts/train_showdown_snapshot_league.py` chains the existing autonomous
trainer through at most four bounded generations. A SHA-bound external plan
declares B0, two continuation seeds, one native V8 subset, fixed opponents,
generation budgets and the shared regularizer. `--resume` verifies completed
snapshots and resumes only the first incomplete generation. It restores compatible
Adam state but resets native episodes and discards any incomplete rollout; this
is not bit-exact uninterrupted training. Artifacts and models stay outside Git.

The fixed chain retains five cyclic episode slots. The league has those same
five slots and five snapshot slots. Snapshot multiplicities are `[5]`, `[1,4]`,
`[1,1,3]`, then `[1,1,1,2]`: S0 remains an anchor, recent completed generations
receive more exposure. These are nominal episode probabilities, not IID samples
or per-decision weights. Every frozen path has an expected ZIP SHA. No pool or
checkpoint identity enters policy features. `generations.jsonl` is append-only
and hash-chained; each endpoint is checked against its actual parent.

The opt-in `zero_avoiding_beta` adds `beta * KL(U_legal || pi)` using the
maintained sb3-contrib 2.7.1 entropy-loss seam. It changes neither PPO clipping
nor terminal reward, GAE or the policy architecture. Beta is bounded to `[0,.01]`;
positive beta requires positive entropy coefficient. Beta zero calls the original
upstream update directly. `train/entropy_loss` includes the composite seam;
`train/true_action_entropy`, `train/legal_uniform_kl`, and
`train/regularization_loss` report its separate components. The checkpoint's
`training_regularizer` contract dispatches the actual training subclass through
`LearnedPolicy`; a base-class load containing a positive beta fails closed.
Legacy checkpoint manifests and inference retain their original meaning.

V2 training subsets support exactly 64 train teams with random ordered bring-three;
V1 1/16-team subsets are unchanged. `trained_rollouts_v1` transition budgets count
only updated complete rollouts while retaining separate collected-transition
counts. Older runs retain their collected-budget semantics.

Evaluation's `candidate_seat="p2"` swaps actual team/preview roles before native
reset, sends the candidate its p2 public request and remaps candidate-relative
outcomes. Internal roster/preview ordering and initial RNG seed are preserved.
Public histories cannot be reinterpreted by a seat swap. Both physical seats and
all rival strata must remain in each bootstrap case cluster. Initial RNG matching
does not imply identical downstream random consumption after actions diverge.

These continuations are repetitions from one trained parent, not independent
fresh-training seeds. Fixed-budget endpoints are compared; diagnosis does not
replace endpoints with validation-best models. No learned policy is promoted
to the live guaranteed-first advisor.
