# Decision snapshot / GAE join v1

This opt-in coordinator diagnostic does not train or change policy, critic,
reward, observation, mask, or GAE semantics. Ordinary `ShowdownLearningEnv`
instances have `decision_snapshot_recorder=None`: no native saves or disk I/O.

## Timing and storage contract

1. The frozen collector callback calls `prepare` **before** the maintained
   MaskablePPO actor forward. Store native `save()` (including PRNG, queue,
   teams, phase, native decision budget and rejection state), current own public
   view/mask, encoded SHA, episode UUID/revision/turn, rollout/t and policy ZIP ID.
2. The optional native-step observer records the actual joint actions and the
   authoritative transition, both public-view fingerprints and full native
   checkpoint digest **after every native step**, including automatic waits and
   request retries. It continues through the original episode's end; partial
   suffixes are ineligible. It does not copy the checkpoint into Gym info.
3. The post-step callback binds the actual sampled action, input SHA, value and
   old logp. Only after existing SB3 `compute_returns_and_advantage` has completed
   may the exact (rollout,t,env=0) row supply GAE/return/reward labels. A mismatch
   is fatal. These are newly collected frozen-policy GAE, not historical GAE or
   counterfactual action-quality targets.
4. The capture owner enforces at most 32 roots and 32 MiB of checkpoint/trace
   bytes. The pilot uses one CPU worker, 1,024 transitions and at most 16 roots
   (first eligible move request with >=2 legal actions in each 64-decision block).
   Inputs and source hashes are frozen before capture. No eval bank is opened.

Private checkpoint gzip files and joint-action traces live in `capture/private`
outside **every Git worktree**; the owner rejects output beneath a `.git` ancestor.
Full native data include privileged training truth. They are local replay
material, never public model features, inference inputs, value targets or action
labels. `capture/public` contains only the acting owner's original public view;
`capture/joins` contains scalar bindings. No native payload is committed. This
separation is a data-flow boundary, not encryption; the local coordinator user
and machine administrators retain filesystem access. Record/inspect the local
ACL and keep the private folder out of synchronization/public uploads.

## Frozen collection and replay

`scripts/pilot_foundation_decision_snapshots.py` requires an external versioned
plan. It reuses `LearningEnvFactory`, original TRAIN subset/opponents,
`LearnedPolicy`, maintained MaskablePPO `collect_rollouts` and SB3 GAE. It changes
only collection parallelism to one environment; per-env 128-step horizon,
gamma=1, lambda=.95 and frozen stochastic T=1 behavior are retained. It calls no
`learn/train` and guards optimizer.step with an exception. Policy/Adam digests
must match before and after collection. The reference loader remains unchanged.

All complete original suffixes must replay twice with the original native RNG
and recorded joint inputs, matching every post-step native digest, public views,
request/mask and terminal result, before any counterfactual branch runs. Native
digest equality includes identity, exact HP/PP/status, execution queue, log order
and RNG, rather than only agreeing on the winner. Replaying recorded actions
does not claim to restore Torch's original stochastic action-sampling stream.

For each eligible root compare the sampled first action with one distinct legal
coverage-based alternative from existing `candidate_actions`, preferring another
action family. Three predeclared paired future seeds are used. The original
opponent's **already selected first action** is held fixed by the coordinator in
both branches; it is not predicted or passed to the Foundation actor. Thereafter
both seats use frozen Foundation **argmax on their own public observations**.
This is a controlled conditional continuation, not the original stochastic
rollout policy or a posterior over unknown opponent sets. Shared starting seeds
do not ensure identical downstream random draws after choices diverge.

The pilot allocates at most 16*(1 original-root binding + 2 original replays +
6 candidate continuations + 1 repeated factual terminal continuation)=160 executions, below the global 256
ceiling and leaving room for focused native regressions. Started units consume
budget even on failure. Receipts refuse duplicate execution; output with an
existing start is never automatically recollected/restarted. STOP/deadline leave
durable captures/GAE/receipts; incomplete rollouts/suffixes cannot supply branch
labels. Any reproduction failure closes the gate before alternatives. No
automatic extra samples, coefficient tuning or learning follows this pilot.

Public transport preserves mapping insertion order. Legacy numeric features can
depend on observed-Pokemon traversal order; sorting JSON keys can therefore
change features even though a canonical semantic hash matches. Neither the
encoder nor slot order is changed here. The native root binding must reproduce
the exact encoded SHA and value/logp. An explicitly authorized
`--capture-existing` route can reuse completed GAE records without collecting any
new transitions: restore the authenticated native checkpoint's original public
projection and verify its encoded SHA before using it. Original files remain
immutable, including failed diagnostics; new verified projections are written
separately. It does not approximate/reconstruct hidden state from public JSON.

## Required interpretation

Return labels exist only for native termination; timeout/truncation/rejected
initial choices have no terminal action-return label. Compare root-cluster
summaries with seeds nested inside roots. The small selected TRAIN sample and
simulator truth condition the results; no battle-strength/generalization or
critic-arithmetic conclusion follows. GAE and fixed-policy action differences
have different estimands and neither is an optimal-action label.

Focused tests cover default-off behavior, prepare-before-forward, unchanged
public input, mask/feature/action/value/logp/GAE joins, corrupt checkpoint/suffix,
episode completion, storage/output bounds, deterministic replay and STOP. Real
native both-seat/checkpoint continuity and the actual captured full-suffix replay
are validated within the explicit pilot/regression execution ledger.
