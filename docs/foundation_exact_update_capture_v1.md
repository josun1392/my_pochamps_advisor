# Foundation exact-update capture v1

This is opt-in diagnostic instrumentation, not a training algorithm, policy
feature contract, checkpoint promotion, or evaluation framework. Historical
Foundation/PPO owners are unchanged. The native owner collects exactly one
128-step × four-worker rollout (512 learner transitions), then exits. It never
calls the evaluator. A durable `native_started.json` prevents recollection after
either success or an uncertain failure. Do not delete this marker to retry.

## Capture and replay contract

`advisor.learned_exact_update.ExactUpdateCapture` observes the maintained
sb3-contrib 2.7.1 `train()` using removable instance-local hooks. It records:

- Full time-major public encoded observations, masks, actions, rewards, old
  values/log probabilities, episode starts, GAE advantages and returns.
- Original SB3 env-major minibatch indices and every actual auxiliary sample
  index/proposal weight. Auxiliary rows/observations remain time-major.
- Python/NumPy/CPU-Torch RNG, original loss coefficients and normalized
  minibatch advantages, raw logits, probabilities, values and loss scalars.
- Pre/post global-clip gradients and each original Adam step's pre/post model
  and optimizer state. A read-only frame inspection validates the exact pinned
  upstream `train` owner; an unsupported owner fails closed.

The recorder does not replace samplers, add a policy forward, change losses,
modify gradients, or execute optimizer steps. The source trainer's existing
`LearningEnvFactory`, `BudgetCallback`, public encoder, native team subset,
opponents, resource job, terminal transport and checkpoint writer are reused.
The diagnostic bypasses the autonomous trainer's automatic validation/checkpoint
selection loop so that **no independent evaluation games** are launched.

`training.pt` contains a separate `loss_only_auxiliary_labels` dictionary of
legitimate training-only supervision. Never concatenate it, RNG, identities or
coordinator records into actor/critic inputs. These are trusted local pickle
artifacts; do not load unknown downloaded files through `load_capture`.

The existing player-visible view is separately saved for reencoding, native
reward/action joins and privacy checks. GAE targets, sampled actions and
supervised labels are not optimal-action labels.

## Explicit phases

Using the approved CPU source Python runtime, invoke
`scripts/diagnose_foundation_exact_update.py PHASE --output ABSOLUTE_EXTERNAL_PATH`.
Each new native capture needs a separately authorized budget.

1. `prepare`: freeze source/input hashes and the predetermined first treatment
   final checkpoint plus compatible Adam; no environment is created.
2. `capture`: four Subproc workers, CPU 50%, RAM 12 GiB, CPU device, one Torch
   thread, 900-second hard watchdog. Maximum 512 native learner transitions.
3. `replay`: restore the full original buffer/auxiliary data/RNG/model/Adam and
   execute the **existing** PPO training owner offline. Compare sampler order,
   RNG, loss, output, gradient, clipping, weights and Adam exactly at every step.
4. `analyze`: only after exact replay passes, recompute loss gradients at the
   original 16 minibatches. First/last optimized minibatches receive independent
   single-Adam-step full-versus-one-loss-omitted controls from identical pre-step
   weights and Adam. No native environment is created in phases 3/4.

The offline loss expression mirrors the original nested entropy-seam arithmetic
order. Its full forward/loss/gradient and full Adam step must exactly match the
captured original before interpreting omissions. It is never used as the
production PPO trainer. The ordinary entropy loss is measured separately from
uniform KL, parent KL, auxiliary likelihood and value loss.

An omitted term is disconnected, rather than multiplied by zero. Parameters
with no remaining gradient retain `grad=None`, which Adam skips. A separate
zero-current-gradient control can measure carried Adam state, but it must not
be confused with omission or skipping an optimizer step.

## Interpretation and validation

Loss-specific gradients can align/cancel on shared parameters. Whole-network
cosines can hide conflicts in shared-only coordinates, so report both where
available. Global clipping couples otherwise disjoint parameter groups, and
Adam carries history and adapts its denominator. Neither gradient norm ratios
nor leave-one-term-out deltas are additive causal shares.

Frozen public-state forward probes measure local probability/logit sensitivity,
not battle strength. No coefficient tuning, longer learning or promotion follows
automatically. Results from one rollout and selected optimizer steps do not
explain long-term win-rate causality.

`tests/test_exact_update_capture.py` manually fills a synthetic buffer and never
calls a Gym reset/step or native engine. It verifies hooked/unhooked replay,
original sample order and Adam equality, exact loss/gradient/clip recomposition,
detach paths, no-auxiliary `grad=None`, bounded capture, and no overwrite.
The actual diagnostic additionally checks all 512 public views and the original
masked actions, and verifies a hook-free maintained-train replay independently.
