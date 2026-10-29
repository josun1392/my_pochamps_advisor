# Foundation own move-slot presentation consistency v1

This is an opt-in training objective on the original 674,939-parameter Foundation
policy, encoder and named Adam states. It is not the legal-set residual actor.
Old checkpoints, native masks, observations, terminal rewards and PPO/GAE remain
unchanged. Inference always consumes the ordinary public native view.

## Transformation and authority

The fixed permutation reverses all four own active move slots. Native action
groups 6..9, 10..13, 27..30 and 31..34 follow the same new-to-old map. Switches,
wait, roster/lead/reserve order and opponent records never move. All aligned V4
candidate rows, V5 tactical rows and strategic reference rows move together.
The matching own active categorical record's first four known-move bit fields
move with them. Own HP, history, field state, prediction support and priors do
not change. Unused categorical capacity retains Unknown/padding, never an
invented confirmed absence. No hidden label or opponent mask is consulted.

Eligibility requires four distinct known move IDs exactly matching the bound
own active request record, no additional known moves, identical references/IDs
across all move families, and at least one native normal move choice. Missing,
administrative, transformed/mismatched or ambiguous bindings are excluded.
Singleton legal distributions have zero penalty. Explicit and transported
masks must agree, and empty or invalid masks fail closed.

This is a public *presentation renaming*, not a change to actual native party or
move order. A transformed action j corresponds to original PERMUTATION[j]. The
native request and execution remain original. No claim of identical future RNG
under a physically reordered native moveset is made. Raw public re-encoding of
eligible retained states must match the tensor transformation; the validation
also checks the involution and every candidate/mask/identity mapping.

## Learning objective and persistence

For mapped legal distributions p and q, m=(p+q)/2 and
JS(p,q)=0.5 KL(p||m)+0.5 KL(q||m). Both branches differentiate. Add
**0.01 * mean_eligible JS** to the maintained PPO loss through its established
entropy-loss seam. Neither branch overwrites policy.action_dist. No transformed
action, old logp, advantage, return or observation replaces an original PPO
sample. No new scorer, parameters, optimizer groups or prediction targets exist.

`MoveSlotFoundationPPO` carries the full objective contract and trained-progress
counter in its checkpoint. Strict loader/metadata validation selects this class
and rejects silently removed or altered objective metadata. A uses unmodified
FoundationCombatPPO. Both begin with the original Foundation ZIP/Adam exactly;
the additional objective has no initial forward effect. Restart is a durable
model/Adam boundary with fresh native episodes, not interrupted-RNG restoration.

## Frozen bounded comparison

- Two paired continuation seeds: **116021, 117037**, one common trained parent.
- A/B each 65,536 new trained transitions, total cap 262,144 and 8,192 Adam steps.
- Original V8 256-team subset, random ordered bring-three and original ten-slot
  seven-identity frozen mixture; CPU 50%, 4 Subproc workers, 12 GiB, no GPU.
- Fixed endpoints and 16,384-transition intermediate checkpoints; no best-model
  selection, coefficient search, reward change or promotion.
- New hash-bound 192-case panel, 96 TRAIN-domain excluded-team cases and 96 V8
  validation cases; all complete teams excluded from learner256. Three frozen
  rivals and both real seats yield 1,152 games/model, 576 validation games/model,
  5,760 total for parent and four endpoints. Prior case/seed use is audited;
  reused species/sets/previously examined team identities are disclosed.
- Primary: validation B-A mean over both continuation repetitions, bootstrap
  case clusters retaining seats/rivals/repetitions. Two seeds do not establish
  population-level training-seed uncertainty. B-parent is a separate comparison.

Consistency, semantic argmax sensitivity, entropy relative to legal count,
uniform-distance and action concentration are diagnostics, never strength
labels. A promising strength result requires positive directions in both seeds,
positive primary CI lower bound and intact safety contracts. Uncertain strength
is INCONCLUSIVE even if consistency improves. No automatic follow-up run.

## Verification and operational bounds

Focused tests cover identity/mask binding, unknown/padding, missing/duplicate
moves, involution, all action blocks, singleton legality, differentiable JS,
distribution isolation, paired accounting and strict restart. An optional
trusted fixed-buffer unit replay checks save/load/continue tensor-for-tensor;
it creates no native transitions and is not experimental training evidence.
The native study uses the existing rollout logp/value/GAE/ratio auditor, durable
per-game receipts, retry/progress watchdog and independent Windows Job owner.
The combined four-arm training ceiling is 5,400 seconds; the historical owners'
default and individual trainer limits remain unchanged. Evaluation ceiling is
5,400 seconds and whole-owner ceiling 10,800 seconds, automatic restarts zero.
Full model and Adam files remain outside Git. Protected files are not read.

The legacy owner's default rejects inherited launcher Jobs. The accepted
diverse/recombination pilots additionally support a persistent outer app Job
after the short-lived execution Job has exited. This study may use that path
only with a fresh matching Python breakaway-child survival receipt, bound by
SHA to the execution revision. CPU/RAM remain enforced by its own nested Job;
there is no desktop automation, detached-guard bypass or automatic restart.
