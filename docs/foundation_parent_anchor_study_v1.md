# Frozen-parent Foundation PPO comparison v1

Opt-in training objective `showdown-foundation-frozen-parent-kl-v1` adds
`alpha * KL(parent_legal || current_legal)` to the maintained Foundation PPO
loss. The reference sees the **same current encoded own public observation and
native action mask**, in eval/no-grad mode. No actor/value input, native reward,
GAE target, detached prediction-head contract or model tensor shape changes.
Illegal actions have no KL mass; a single legal action has zero penalty.

This differs from existing `beta * KL(U_legal || current_legal)`: the uniform
term preserves exploration support, whereas this reference term softly
preserves the particular pretrained policy. Neither is a strategy oracle.

The implementation uses the existing entropy-loss seam and restores it after
each update; it does not copy PPO's train or GAE implementation. A zero alpha
calls the historical implementation exactly. Positive alpha requires the
existing positive entropy coefficient. True entropy is logged independently
of the composite entropy seam. KL is based on detached parent probabilities
and normalized masked log probabilities, not sampled action imitation.

## Persistence and privacy

`ParentAnchoredFoundationPPO` is explicitly dispatched by checkpoint metadata.
Loading its archive as the historical base algorithm fails closed. Contract,
feature fingerprint, encoder version, parent ZIP SHA and parent Adam clock are
validated. The reference cache is excluded from the ZIP; continued training
reopens the SHA-bound original checkpoint. Inference does not need to reopen
the parent. Both parent weights and the full Adam state signature are checked
at checkpoints. The reference cannot share learner tensor storage and all its
gradients are disabled. Old Foundation/V3/V4 loaders remain unchanged when the
new metadata is absent.

SB3 applies archive data and explicit load kwargs after the constructor. The
custom class therefore validates again after `load()`, rather than relying on
constructor validation. Resume must match the serialized contract. Explicitly
enabling this objective from the original parent preserves its compatible
weights and Adam, while starting fresh rollouts/native episodes; this is not
an exact interrupted-rollout/RNG restoration. Historical checkpoints are not
rewritten or silently given a new training source fingerprint.

## Fixed first experiment

The user's new authorization supersedes `authorized_to_execute: false` in the
historical proposal without modifying that proposal. Freeze the following
before learning in an external immutable study plan:

* Original Foundation parent ZIP `9b3eb94a...0ccf`, Adam clock 32,768.
* C/T continuation repetitions 96031 and 96032, 65,536 trained transitions
  each; 262,144 total. These are two repetitions from one trained parent.
* Historical control uses the historical Foundation algorithm. Treatment uses
  the identical model/Adam plus alpha **0.01**. Existing uniform beta **0.001**.
  Alpha's rough loss scale at previously observed final parent KL 0.28–0.75
  nats is 0.0028–0.0075; this motivates a conservative coefficient, not a claim
  that loss magnitudes measure causal gradient influence.
* Same 256-team subset, ten opponent episode slots, sparse terminal reward,
  gamma 1, GAE .95, LR 5e-5, entropy .01, rollout 128×4, batch128, epochs4 and
  targetKL .03. No BC, fresh optimizer, or architecture transfer.
* Initial, 32,768 and 65,536 checkpoints; final Adam 34,816 if all normal
  updates complete. The trainer verifies actual optimizer and trained-rollout
  counters rather than inferring success from collected decisions.
* Counterbalanced sequential order C96031,T96031,T96032,C96032; four workers,
  CPU50%, RAM12GiB, CPU device, no automatic failure restarts. One 3,600-second
  combined learning window, then one 3,600-second evaluation window.

The same optional `PublicSignalRecorder` is enabled in both arms. Atomic gzip
rollout files join public feature SHA, legal mask, action, old logp, value,
reward, return and advantage with update-boundary Adam clocks. Episode/revision
labels are explicitly **after-step** identities. At most 128 actual own public
views are saved; no hidden supervision infos or enormous full-feature dumps.
Last-minibatch clipped parameter-group gradient norms distinguish actor-only,
critic-only, shared and prediction parameters. These are combined-loss group
measurements, not an exact causal loss-gradient decomposition. Existing
Foundation all-minibatch finite/gradient/auxiliary profile diagnostics remain.

## Evaluation and decision

Before learning, audit prior consumed native identities and freeze 32 train
plus 96 heldout case clusters. Existing bank teams/sets may overlap previous
panels; quantify those overlaps and do not call the study species/set-unseen.
No sealed final assets are opened. The original 6,912-game panel and its
diagnostic cases are consumed and excluded as fresh native case identities.

Five policies (parent and four fixed endpoints) ×128 clusters ×2 actual seats
×3 fixed rivals =3,840 argmax games. Secondary: 32 of the heldout clusters ×2
seats ×Champions ×2 shared sampling-uniform streams ×5 models =640 games.
Sampling streams exclude model identity for pairing; downstream battle RNG
consumption need not match after actions diverge. Argmax and sampling are
analyzed separately, retaining repeated seats/rivals/streams in each case
cluster and reporting both continuation effects, not an inflated seed count.

Immutable per-game receipts, start/commit ledger and destination durable-write
preflight avoid silently losing results. An uncertain started game without a
receipt fails closed for explicit diagnosis; it is never automatically rerun.
Results are not used for checkpoint selection or changes to training.

Primary: heldout mean matched T−C argmax win difference, 20,000 case-cluster
bootstrap samples. Secondary: parent wins retained/lost, new wins, per-rival
and seat results, sampled outcomes, parent-forward KL and action changes.
Initial public-state distributions/masks/value estimates are preserved in
receipts; compare their feature hashes before treating them as same-state
probes. Trajectory KL on differently visited states is descriptive.

GO for a further **bounded research** stage requires a positive primary lower
95% bound, positive point effects in both repetitions, no material loss of
parent capability and no correctness regression. Otherwise NO-GO for scaling;
mixed/underpowered evidence remains inconclusive, not equivalence. Lower KL
or greater parent imitation alone never proves strategic improvement. There
is no production promotion and no extra learning authorized by this owner.

Launch the source owner from the independent Windows desktop using an external
frozen `plan.json`, approved CPU Python runtime and `--owned`. Verify
`control.json` has `inherited_job=false`, the PID's ancestry and real progress.
The Windows Job belongs to that owner and kills its children on exit; the
Codex/terminal lifetime must not own it. After one meaningful checkpoint,
record measured throughput/ETA and end the T3 turn rather than polling.
