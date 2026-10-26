# Bounded Foundation self-play exploration pilot

Opt-in entry point: `scripts/pilot_foundation_selfplay_exploration.py --plan PATH
--owned`. It composes the existing autonomous source trainer, maintained
FoundationCombatPPO, LearningEnvFactory, native public-recorder hooks,
AuditedSignalRecorder and real-seat evaluator. It does not replace the trainer,
native mechanics, encoder, reward, PPO objective or model-loading owner.

One continuation seed, 65,536 additional trained rollout transitions, at most
2,048 new Adam steps. Four workers use a frozen episode-slot cycle: Foundation
argmax, Foundation T=1 masked sampling, tactical heuristic, Champions heuristic,
each nominally 25% of episode starts. The two frozen aliases share identical
Foundation weights; they are action-mode diversity, not independent teachers.
There is no live policy swapping. Sampling draws from existing probabilities
and masks only. Existing entropy, uniform KL and auxiliary objectives are kept;
no parent KL, temperature change, residual or new labels are introduced.

The first 512-transition rollout is audited before any update. The gate requires
128 multi-legal decisions, 10% nonargmax selection, normalized entropy at least
0.10, eight distinct selected legal slots and two meaningful action families.
Forced replacements/waits alone cannot satisfy the family requirement. A failed
gate exits DATA_GAP, without tuning thresholds or starting another run.

PilotEnvFactory/AuditedPilotEnv record intent before every native reset, including
the original Gym constructor reset. Each exclusive worker directory allows at
most 2,048 TRAIN starts. Native public decisions join episode/revision/owner,
submitted action, mask, public-input and feature hashes, native outcome and PPO
rollout rows. Native wait/retry attempts remain distinct from PPO transitions.
The original progress-aware retry guard remains authoritative. Open episodes at
training stop have no invented terminal label.

PilotSignalRecorder extends the existing T=1 logp/value/GAE/minibatch audit. It
adds native decision joins and an optimizer pre-step cap. Runtime adapters are
installed only inside this explicit entry point and restored afterward. The
serialized learner remains the original FoundationCombatPPO/Policy; its Adam
and objective metadata retain existing strict loader semantics.

Evaluation is fixed before training: 256 new TRAIN-source held-out team pairs,
512 complete teams disjoint from the learner's 256-team subset, two real seats,
four frozen rivals, parent and fixed endpoint = 4,096 starts. It uses no V8
validation/test/sealed bank. Teams are disjoint in this pilot, not claimed unseen
species/sets. No checkpoint selection or intermediate win-rate tuning occurs.
Primary metric is candidate minus parent argmax win fraction with paired team-
pair cluster bootstrap. Rival/seat, tactical, entropy and critic diagnostics are
secondary; one continuation seed gives no training-seed population interval.

CPU 50%, four workers, 8 GiB job memory, CPU device, one Torch thread. A 5,400s
owned-process ceiling and per-game intents/checkpoints bound execution. No crash
restart, uncertain-game replay, model promotion or extra experiment is automatic.
Original models, master and protected files are outside all write paths.

The first run stopped on the unchanged per-worker 512-attempt rejection-rate
guard after 63,488 runtime-trained transitions. Its latest durable model contains
57,344 new transitions, with 1,792 new Adam steps; runtime audits prove 1,984 new
steps were actually consumed. The 6,144-transition / 192-step difference was not
serialized as a model. It must not be subtracted from actual compute-budget use.
Completing the original endpoint from that checkpoint requires 256 steps, while
only 64 remain under the original 2,048-step cap. No automatic resume or evaluation
is authorized by this partial result. Strength and confidence intervals remain
unmeasured. Original run source hashes and receipts are preserved externally.

Closure instrumentation now writes the already-executed public native event
before either retry guard, and durably saves its row and rate counters when a
guard raises. It preserves progress-guard-first ordering, the eight-unresolved-
request stop and the 1%-per-512 rate stop. It exposes no native hidden state or
unavailable server error text, and does not change choices, masks or rewards.
This telemetry correction was tested offline; the failed run was not replayed.
# Explicit partial recovery

`foundation-selfplay-partial-recovery-v1` is an opt-in operational continuation,
not a new experiment or an uninterrupted RNG restoration. It copies the durable
57,344-transition state into a new output directory and uses the maintained
trainer's resume path, discarding partial rollouts and resetting native episodes.
Weights and Adam must match the saved checkpoint; scientific inputs, seed and
all PPO settings remain bound to the original plan. New RNG-stream provenance
is recorded before the first resumed rollout. No historical RNG is invented.

The resumed computation is capped at 256 Adam steps / 8,192 completed rollout
transitions. Counting the prior 1,984 computations, including 192 unsaved steps,
the lifetime cap is 2,240; the resulting retained model has 2,048 new Adam steps.
Four exclusive worker budgets permit at most 512 new TRAIN starts each, with
episode ordinals offset by the original durable start-intent counts. The original
plan/state/STOP/failure, models, traces and evaluation cases are never rewritten.

Only this opt-in owner uses `public-request-refresh-resolution-v1` for the
512-attempt rate guard. Both raw rejections and unresolved counts are retained.
A rejection is resolved only after the next actual native commit with identical
refreshed owner request/mask, unchanged public state/history at rejection, zero
rejection reward, continuous battle/actor/turn/revision/decision identity and a
proved maybeDisabled-to-disabled or maybeTrapped-to-trapped transition. Missing
proof remains unresolved. Pending events count immediately at window boundaries.
Six unresolved rejects in 512 attempts still stop; the existing eight consecutive
unresolved-request guard runs first. Native retry recovery, action selection,
legality, rewards and simulator mechanics are unchanged.

Evaluation receipts must follow the maintained evaluator's callback contract:
the legacy callback delivers a cumulative completed batch. Persist all rows
idempotently, and provide the required frozen case-provider `identity`. The
explicit `per_game_progress` option additionally delivers each completed game
before the batch ends; its default is false for existing callers. A duplicate
delivery verifies the immutable receipt rather than overwriting/counting it.
This protects completed games if later batch/report construction fails.
Unreceipted started games are never silently replayed or inferred from seeds.
