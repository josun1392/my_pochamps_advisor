# Bounded V4 fixed-opponent continuation

`showdown-native-training-subset-v3` adds exactly 256 V8 **train** teams to the
existing 1/16-team v1 and 64-team v2 contracts. Use
`extend_native_training_subset(parent64_path, parent64_sha, membership_seed=...,
seed_namespace=..., excluded_train_indices=...)`. It verifies the original 64,
retains them in order, inherits earlier exclusions and appends 192 deterministic
unique train indices. The external contract binds the parent SHA, indices,
individual team hashes, V8 bank/engine/format, random ordered bring-three and
seed namespace. The loader rejects weakened inherited exclusions. Historical
subset contracts and the native generator are unchanged.

The existing `scripts/train_showdown_snapshot_league.py` also accepts an opt-in
`showdown-fixed-continuation-windows-v1` plan. It reuses the same bounded trainer,
append-only generation ledger and child validation. Only chain `F-s1` is allowed
in this plan; `generations` means 1–2 sequential fixed-opponent windows, each
1024–1,048,576 trained transitions, divisible by 1024. The original V0 league
contract retains its four-chain/four-generation/262,144 limit. No snapshot pool
or inference backend is expanded.

Each window restores its actual previous V4 checkpoint/Adam, retains beta .001
when configured, and records collected versus trained counts separately.
Native episodes and partial rollouts are not exact RNG restores. A durable
fixed-budget endpoint is selected by exact timesteps, PPO stage, config identity
and model hash, even if STOP interrupted its validation. A validation-best or
preceding evaluated checkpoint is never substituted. Ambiguous/missing durable
endpoints fail closed.

For the initial scaling study, the parent is the untouched Stage 2 F-s1 **fixed
endpoint** (convention, not a best-model claim). One explicit categorical V3→V4
weight transfer creates an immutable, pre-update V4 checkpoint with fresh Adam.
Subsequent windows use `initial_model`, never `transfer_model`, and preserve that
V4 optimizer. Encoder V4, native 35 masks, gamma1, GAE .95, original LR/rollout/
batch/epochs/target-KL, terminal reward and beta .001 remain unchanged. The
original five fixed/heuristic episode slots remain the cost baseline.

Study controls: two nominal 1,048,576-transition windows, eight CPU workers,
50% Windows Job CPU cap, 12GiB aggregate RAM, CPU device, 3600 seconds per
launch. Any bounded runtime resume must retain the same plan/checkpoint lineage;
no 10M budget, 4096-team training, production promotion or automatic next study.
STOP/resume is tested at both an intermediate and an exact window endpoint.

The evaluation plan/banks are frozen outside Git before main learning. Use
`fixed_fixture_policy_seats_v1`: canonical teams/previews stay fixed while the
candidate actually controls p1 and p2. Preserve both seats/rivals within each
bootstrap case cluster. New complete native-valid teams can share species and
individual sets; neither new offsets nor team novelty establishes species/set
generalization. Final fixed-budget results are interpreted separately from
learning health, and no effect is attributed specifically to V4 without an A/B
control. Sealed final assets remain unused.

Tests: `tests/test_v4_scale_continuation.py`, existing snapshot league, ladder,
categorical V4, public-isolation, truncation and autonomous trainer regressions.
Actual plans/checkpoints/reports remain external under
`C:\Users\jsp33\.codex\artifacts\selfplay-v1-scale-v4-bounded-v1-20261015`.
