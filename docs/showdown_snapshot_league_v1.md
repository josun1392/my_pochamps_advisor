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

Seat assignments have explicit contracts. The original default
`own_team_preserving_native_seats_v1` retains its meaning and historical records.
For paired team-balanced benchmarks use `fixed_fixture_policy_seats_v1`: the
fixture's two native teams and ordered previews stay fixed while the candidate
and rival exchange actual p1/p2 request ownership. Each policy then plays both
teams in the cluster. Both modes execute native games; neither only relabels
winners. Reports must state which balance was tested.

These continuations are repetitions from one trained parent, not independent
fresh-training seeds. Fixed-budget endpoints are compared; diagnosis does not
replace endpoints with validation-best models. No learned policy is promoted
to the live guaranteed-first advisor.

## V4 combat continuation

The opt-in `showdown-v4-combat-snapshot-continuation-v1` plan runs one
`L-s1` chain (one continuation repetition, not independent fresh-training seeds).
It uses the same generation owner, five fixed slots, five snapshot slots and
bounded generations as V0. The verified V4 parent and its regularizer must match;
transfer and fresh-optimizer initialization are rejected. Completed V4 snapshots
become opponents only at the next generation boundary. `previous` and
`historical` remain hash-bound fixed models; each loads its original encoder.

Run `scripts/train_showdown_snapshot_league.py --plan <external-plan.json>
--output <external-chain-directory> --chain L-s1`; use `--resume` for a stopped
chain. `--stop-at-first-checkpoint` exercises durable interruption without
changing the reward or policy. All models, plans and generation events belong
outside Git. Runtime limits apply per generation/launch. This reuses random
ordered bring-three; it does not train or invoke the separate Preview policy.
Source execution owns its Windows job and checkpoints; it does not promise
survival after the hosting terminal/session is destroyed.

For a matched 30/20/50 control, use the separate opt-in
`showdown-v4-combat-fixed-snapshot-control-v1` plan with `--chain F-s1`.
It retains the same five fixed slots and five `league_s0` slots at every
generation. Only the learner follows the preceding endpoint; completed children
never enter this control's opponent pool. Its V4/Adam/regularizer checks and
bounds match the combat snapshot chain. Original `F-*` plans keep their
historical five-slot behavior and must not be described as this control.
