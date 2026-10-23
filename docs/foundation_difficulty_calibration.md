# Frozen Foundation opponent-difficulty calibration v1

This is a training-only measurement prerequisite, not a new strength holdout or
a PPO campaign. Its external authorization/plan binds 128 frozen cases from the
existing 256-team TRAIN subset, seven unchanged opponents, and both actual native
seats: exactly 1,792 games, zero optimizer updates. The separate planned 5,760-game
strength evaluation is not used. Original unapproved proposals remain immutable;
an additional user-authorization receipt binds their hashes.

The runner reuses `evaluate_showdown_policy.evaluate`, actual seat swapping,
`LearnedPolicy`, legal masked sampling, native progress/rejection guards,
Windows Job limits and durable receipt primitives. A new optional
`transition_observer` receives detached player-public snapshots only after the
original native step; it does not alter either policy, requests or native retry
recovery. With the hook omitted the historical evaluator behavior is unchanged.

Foundation samples its legal masked distribution with an explicitly hash-seeded
NumPy stream per case/rival/seat, approximating the training action-selection
distribution rather than claiming the exact historical PyTorch RNG stream.
Neural rivals remain argmax; heuristics keep the existing native evaluator seeds.
Neither side sees the other side's private request. Coordinator trace archives
contain each owner's own visible request, public events, sampled action,
probabilities, masks, decision/revision cursors and outcome; no hidden simulator
checkpoint, future RNG or synthetic labels enter inference.

Each game has a start/commit ledger pair, immutable result, compressed decision
trace and SHA hashes. An uncertain started game cannot be replayed automatically.
Input identities and in-memory learner parameters/Adam plus frozen rival weights
are checked before/after. No source checkpoint is written. One independent Windows
owner contains one native worker, CPU ceiling 50%, aggregate RAM 12 GiB, CPU device,
one 3,600-second launch and zero automatic restarts. STOP/deadline interrupts safely;
an interrupted active game is explicitly uncertain, not silently run again.

Eight rejections without native decision progress still stop immediately; public
request updates do not reset that counter. Accepted progress resets the run but
preserves episode totals. Rejection rate above 1% in a 512-attempt block also stops;
the block spans games. Truncations stay censored and never become draws/losses.

Analysis is predeclared in `ANALYSIS`: resample 128 case clusters preserving all
seats/rivals, report all 21 paired differences and Bonferroni simultaneous family
95% intervals. Three tiers are permitted only if adjacent cross-tier pairs have
positive simultaneous lower bounds and at least 5 percentage points point gaps.
Any truncation or inadequate separation yields unknown tiers. These conservative
criteria may reject an otherwise descriptive ranking; they never force a three-way
split or claim equivalence from overlapping intervals. Only supported calibration
permits freezing the separately authorized matched curriculum study. Calibration
results do not prove strategic generalization or justify model promotion.

Offline tests use stub transitions only; their fixtures spend zero native games.
