# Bounded public categorical experience reuse

The collector defaults remain numerical V3 / gamma .99 / dataset-v1. Opting in
to `showdown-public-categorical-observation-v3` and gamma1 publishes dataset-v2,
binding the immutable encoder contract, native engine, catalog, sparse terminal
objective, frozen actor identities and collection/source hashes.

Only complete native terminal episodes without any rejected joint request or
unsupported encoding are retained. Truncated and incomplete episodes receive no return labels. Dropping
the entire rejected episode is conservative: the existing public service does
not identify which submitted side was rejected. Accepted choices can still
fail, miss, be interrupted or not execute a move; these are actual native battle
consequences, not reasons to relabel a legal decision as optimal or remove it.

The five existing arrays are unchanged. `public_diagnostics.jsonl` binds each
retained row to owner-visible availability/selection, executed public moves and
failure counts. No opponent private request, team/set, checkpoint or future RNG
is recorded. Diagnostics are coordinator analysis only; neither actor nor critic
receives them. Own diagnostics survive VecEnv auto-reset without entering Gym
info. Dataset-v2 loading rejects encoder/objective/provenance/hash mismatches.

Revival Blessing can leave a populated unpositioned own alias when the native
terminal request is empty. V3 correctly refuses this ambiguous terminal record;
its identity/encoder semantics are unchanged. The collector may transport the
previous valid features administratively on a true terminal only, then exclude
that entire episode. VecEnv resets before another actor call; these terminal
transport features are never a dataset row, critic input, return target or
truncation bootstrap. Ordinary online training still fails closed on unsupported
encodings. A separate versioned terminal-identity design is needed for that gap.

The existing offline seam trains masked likelihood plus .5 Monte Carlo value
regression and .01 entropy. BC uses unit actor weights; AWR uses the detached,
temperature1 exponential of native terminal return minus current public critic
value (cap20). Batches128 and epoch-addressed permutations match between modes.
These are empirical returns/advantages, never exact win probabilities or optimal
action labels. Ineffective actions in eventual wins can receive large weights;
the study must quantify this rather than treating every winning move as good.

Explicit `record_initial_checkpoint` permits verifying the identical policy and
restored Adam before offline fitting. New studies from compatible same-V3
checkpoints preserve gamma/GAE and optimizer unless fresh Adam is explicitly
requested. Old source-bound runs are not silently resumed under changed code;
historical models remain loadable. A new study records the new source identity.

The six-arm study compares restored seed-specific V3 controls: PPO-only,
two offline BC epochs + PPO, and two offline AWR epochs + PPO. Offline modes use
the same frozen dataset and number of updates. New online PPO budgets match.
Checkpoint selection cannot substitute for the fixed-budget comparison.
