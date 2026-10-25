# Foundation standard-PPO update / native opportunity-cost diagnostic v1

This is opt-in instrumentation of the existing Foundation algorithm, not a new
actor, critic, reward, objective, residual, temperature or optimizer. The frozen
parent model/Adam remain immutable; only a diagnostic copy learns. Production,
Preview, JAX, master, sealed and historical evaluation panels are untouched.

## Predeclared execution

One continuation seed 117021, maximum 16,384 collected/trained transitions.
Keep four environments, n_steps128, effective rollout512 and all serialized PPO
settings, including existing entropy/uniform-KL/auxiliary terms. Four native
workers are driven by DummyVecEnv for direct env0 coordinator recording; this
changes IPC/execution scheduling, not PPO batching or loss. CPU50%/RAM12GiB,
Torch1thread, no GPU. No standalone evaluation or follow-up training.

One env0 snapshot per rollout (maximum32, below authorization64). First eligible
move request with >=2 legal actions at or after t=[0,32,64,96][update%4]. No outcome,
GAE, policy-change or advantage filtering is used to choose roots. All missing,
incomplete and native-rejected roots remain in the capture inventory; only
complete factual native suffixes with an accepted first action enter branches.

## Exact update binding

Reuse DecisionSnapshotRecorder before actor.forward and after maintained SB3 GAE.
Its old frozen-GAE scope stays the default; actual training opts into explicit
`new_standard_PPO_rollout_not_counterfactual_or_historical_label`. Root policy ID
is the SHA of the actual current parameter state, with parent ZIP SHA, update ID,
Adam clock and a saved behavior-policy state. Native payloads remain outside Git.

At each boundary require policy/Adam unchanged during collection. Join snapshot,
own public transport/encoded SHA, native mask/choices, actual sample/value/old
logp/GAE/return to the same time-major (t,env0) row. Probe raw logits, masked logp,
probabilities and critic value immediately before and after the **actual combined
PPO update** on exactly that public input. Deterministic probes preserve policy
mode and RNG. No private native data are inputs to either actor or critic.

Observe the original buffer `_get_samples` indices without modifying returned
tensors. SB3 env-major flat index for env0 is t. Record the selected row's actual
per-minibatch normalized advantage and optimizer-applied flag/Adam clock. Reuse
AuditedSignalRecorder for masks, old/new logp, ratios, GAE and optimizer checks.
No surrogate update or counterfactual loss is added. Restore hooks before model
checkpointing; save diagnostic parent/middle/final weights+Adam and all behavior
parameter states, together with SHA and lineage receipts.

Raw GAE sign is not the normalized minibatch sign. Shared parameters, other
rows/epochs, value loss, entropy, uniform KL, auxiliary loss, clipping and Adam
also affect the measured change. A negative selected logp shift despite positive
raw GAE alone is not a PPO/critic defect or a causal attribution to that row.

## Controlled counterfactuals

After learning finishes, reuse native replay/comparison owners. Bind the exact
checkpoint/public feature SHA and verify behavior logits/value/logp by loading
that root's stored **pre-update** parameters (not the final or parent policy).
Replay every original full native suffix once against the recorded original
trajectory before any alternative. This checks identity, HP/PP/status/order,
queue, PRNG, public observations and termination; partial suffixes fail closed.

Alternative is pre-update argmax when it differs from the sample; otherwise the
highest-probability other legal action of another family if available, else the
best other legal action. It is chosen before seeing branch outcomes. The first
recorded opponent action is held fixed by the coordinator. Thereafter both seats
use frozen parent Foundation argmax on their own public views. Use two paired
predeclared future native seeds, and repeat one factual terminal continuation.
Native truth is replay-only, never an actor feature, GAE target or optimal label.

For32 roots: binding32 + original suffix replay32 + paired continuations128 +
duplicate factual32 =224, under the240 script cap and256 total authorization.
Up to16 regression executions can fit the remainder. Failed starts consume
budget. Existing starts/receipts refuse duplicate execution or automatic restart.
STOP/deadline/failure preserves durable outputs; no further sampling is used to
make up sparse action classes or effects.

The maintained ProgressRetryMonitor observes native decision progress and request
updates after each vector step. Eight rejections without accepted progress still
stop; accepted progress resets that consecutive run. Episode totals and all retry
receipts are retained, and the original1% full-interval rate guard is checked.
Draining coordinator completion/retry telemetry changes no native request,
maybeDisabled/maybeTrapped flag, legal mask, recovery, reward or PPO feature.

## Interpretation

Report all32 rollout updates and snapshots, normalized advantages and logp/pair
gap changes; cluster paired return uncertainty by original episode/root with
native seeds nested. Record action/horizon coverage. Frozen-parent argmax
continuation returns and collector-policy GAE are different mathematical
quantities. Selected alternative outcomes never enter PPO rewards.

`UPDATE_SIGNAL_LINKAGE_READY` denotes sound linkage with useful variation;
`PARTIAL_UNDERPOWERED` is appropriate if policy or outcome variation/coverage is
too small to judge signal quality; `NO_GO` denotes failed integrity/reproduction.
Predeclare at least8 nontrivial policy shifts and4 episodes with any terminal
contrast for a descriptive signal assessment; these are coverage checks, not
strength/superiority gates. Neither status authorizes promotion or more PPO.
