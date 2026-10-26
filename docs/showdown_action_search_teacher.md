# Foundation first-action teacher feasibility v1

This opt-in TRAIN-only pilot ends PPO-signal re-diagnosis. It estimates native
action returns when the **original frozen Foundation** is the future own policy.
No new model, PPO/GAE target, optimizer update, independent sealed evaluation,
production recommendation or general MCTS engine is introduced.

Reuse24 previously replayable snapshots with exact frozen learned opponents.
They were collected by a PPO continuation, not independently sampled from the
original Foundation or new teams. Other heuristic roots lack root RNG state and
are not substituted. Native hidden state is replay-only, never a candidate or
actor input. Fixed-real-hidden-state results are a privileged teacher upper-bound
probe, not demonstrated public-information live search.

Before outcomes, Foundation's own public35-action distribution selects argmax,
highest-probability different action, and highest-probability remaining family
if available (otherwise next remaining action). Native choices must be distinct.
No hidden move, set, opponent request or future outcome selects candidates.

Declare6 search seeds and10 disjoint confirmation seeds. Every candidate is
forced once per search seed, then both policies remain frozen. Pick highest
search terminal mean, preferring original argmax on ties. Seal all selections
and their SHA **before any confirmation**. On confirmation compare selected and
baseline with matched future seeds. If baseline is retained, reuse its single
result rather than rerun an identical branch. Record search optimism separately.
Truncated or initially rejected candidates have no completed-return label;
never count them as a draw/loss or silently replace them.

Reuse branch_candidate, exact snapshot binding/replay, NativeBudget receipts,
policy loaders and Windows hard limits. Up to24 roots x(3x6 search +2x10
confirmation +binding/replay/repeat)=984 native units; reserve16 tests under
global1024. One native worker, Torch1thread, CPU50%, RAM12GiB, no GPU, no
automatic restart. Protected user files are not opened or hashed; metadata-only
preservation checks are distinct from a content-hash claim.

Primary statistic is selected-minus-baseline confirmation return, uniform over
all valid roots, with20,000 root-cluster bootstrap draws. Search results are not
pooled with confirmation. Show per-root observed improvement, worsening, tie,
and paired-seed uncertainty, including baseline-retained roots. Signal gate:
confirmation root CI lower>0 and at least4 positive roots. CI upper<0 is
UNSUPPORTED; otherwise INCONCLUSIVE. No status promotes a policy.

Reuse review: repository native branching/visibility tests and prior public
best-response/reference audits. No third-party code is copied. The MIT
[Metamon repository](https://github.com/UT-Austin-RPL/metamon) and its
[offline-learning paper](https://arxiv.org/abs/2504.04395) motivate data/policy
reuse if no credible teacher signal is found. Their datasets/formats and
dependency stack do not establish Champions M-C compatibility; importing their
weights, simulator or full training framework is outside this pilot.
