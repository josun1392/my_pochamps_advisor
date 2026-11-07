# Checkpoint RNG continuation safety

Historical critic verification loads reseeded the learner after4K/8K/12K.
The original results remain preserved and confounded; this change does not
regenerate, relabel, or repair those outcomes.

## Supported boundaries

- `LearnedPolicy` and `ActionableActor` already preserve RNG and are unchanged.
- `ResidualActor` and `CriticTrainableActor` now use `rng_neutral_load` around
  the SB3 constructor. Python, global NumPy and CPU Torch states, plus already
  initialized CUDA states, are restored on success and exception.
- The autonomous trainer's device/worker-count load fallback uses the same
  helper, with an explicit n_envs override and no env argument. The existing
  post-validation set_env attaches the vector without reseeding it.
- Passing a live env to this helper is rejected: restoring global generators
  cannot undo SB3's mutation of a vector's pending seeds/local RNG. CUDA loading
  without an existing capturable CUDA RNG state is likewise rejected.
- Explicit new seed-addressed runs/generations may initialize from historical
  weights and compatible Adam. They are new continuation experiments, not exact
  interruption recovery. Existing initial seed selection remains explicit.

## Unsupported interruption recovery fails closed

The legacy autonomous ZIP/state.json do not persist all global RNG states,
local Gym/native RNG, case indices and sampler cursors, pending rollout and GAE
state. Model.seed is an initialization label, not any of these states. Adam
restoration alone cannot establish execution continuity.

Therefore `run(...,resume=True)`, the CLI `--resume` and detached resume now
reject before launch, lock/STOP/state mutation or seeding. This deliberately
includes completed autonomous runs: inspect their receipts rather than launching
them again. An incomplete snapshot-league generation is refused before its
generation event/config is written. Already-completed league generations still
skip, and separately declared fresh generations retain their existing contract.
Pilot owners already refuse existing started/completed outputs; no recovery
fallback is added. No flag or invented seed bypasses this refusal.

Exact native cold resume is **not implemented by this patch**. Enabling it
requires an independently validated owner for the complete native/Gym/sampler/
rollout state, model/Adam/config SHA bindings and atomic commit ordering. There
is no partial RNG-only sidecar advertised as a complete execution checkpoint.

## Validation scope

Synthetic tests reconstruct checkpoints at4K/8K/12K while preserving the live
execution state and compare global/local RNG, full minibatch permutations and
synthetic optimizer/sampler progress with uninterrupted execution. A negative
control reproduces the old reseeding divergence. The progress ledger is not
an actual Adam update. Fake constructor integration checks both real actor
loader entry points without loading or inferring a combat model.

Cold native resume tests assert fail-closed behavior and unchanged STOP, locks,
state and counters. They do not claim native cold-restart equivalence. Tests
also cover exception restoration, live-env rejection, worker overrides and
completed-generation skipping. No battles, PPO/Adam steps, actual model
inference, evaluation or promotion are part of this safety change.
