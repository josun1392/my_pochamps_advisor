# Public faint-progress potential: bounded matched PPO v1

This is an experimental opt-in, never the production reward or policy default.
The original Foundation, native simulator, sparse rewards and historical model
contracts remain intact. Baseline source: `9c5807539dd5342e7fa90cce4f54c70c9abe361e`.

## Fixed potential and boundary

`PUBLIC_FAINT_PROGRESS_PHI_V1` counts delivered public `|faint|` events on each
side, capped at three. These are cumulative events, not current living counts.
Revival may legitimately cause another event. Names/Illusion do not supply
private identity or set information. No private request is a potential input.

`Phi = (0.10 / 3) * (min(opponent_faints, 3) - min(own_faints, 3))`.
At actual native termination, `Phi=0`. The coefficient is fixed, not tuned.
`r_shaped = r_native + Phi(next) - Phi(current)`, with gamma one and GAE .95.
For a complete episode the sum is the native return minus its initial potential.
Fresh native episodes start at zero. No clipping/normalization is introduced.

The opt-in Gym wrapper acts once outside the existing native wait/retry loop and
before VecEnv reset. Full owner history must contain one start, ordered turns,
valid faint roles and causal episode/revision/prefix bindings. Duplicate delivery
cannot increment a cached count; full history is recomputed. A repeated faint
without intervening public positive-health evidence is rejected. Missing or
ambiguous input fails closed. It is never interpreted as established absence.

True terminal, time limit and rollout cutoff differ. Time limits retain Phi and
use the maintained PPO's single shaped-value bootstrap. Rollout cutoffs retain
Phi and bootstrap normally. No potential is carried across VecEnv reset. The
opaque terminal feature array remains administrative; it supplies no value.

## Value/optimizer semantics

The B initial raw actor/value tensors and all named Adam states equal the parent.
No fixed `V-Phi` correction is inserted in training. Such a correction would
cancel the reward difference in TD/GAE, yielding a null coordinate experiment.
The existing critic instead learns shaped return, initially with a bounded
calibration mismatch. Approximation and finite PPO can change behavior despite
complete-return preservation; strategic improvement is an empirical question.

Checkpoint ZIP and JSON both bind the opt-in, trained counter and separate
reward/value objective. Removing the opt-in or changing its environment, lambda,
coefficient or parent is rejected. Original loaders/default A are unchanged.
The one explicit original-parent conversion preserves Adam and is not an exact
mid-rollout resume. Subsequent B resume preserves its own compatible optimizer.
`LearnedPolicy` reports raw `shaped_return_estimate` and a diagnostic native
coordinate `discounted_return_estimate = raw_value + current_public_Phi`. This
addition is inference reporting only, never a training/bootstrap correction or
an exact win probability. Actor inputs, features, masks and tensors are unchanged.

## One approved study

- Seeds 128021 and 129037; A native terminal, B fixed shaping.
- 65,536 trained transitions per condition/seed, total 262,144; at most 8,192
  new Adam minibatch updates. Same original Foundation/Adam, 256 teams, ordered
  random bring-three, frozen seven-opponent ten-slot mixture, T=1 and PPO settings.
- Initial and 16K/32K/48K/64K checkpoints. No validation-best substitution.
- Initial output/Adam proof uses preserved TRAIN public probes. Each B first
  512-transition rollout is checked against its seed's A first rollout before
  B's first update. Native rewards/observations/actions/logp/values must match;
  shaped rewards, GAE and targets intentionally may differ. No extra collection.
- Freeze 192 new native case/RNG clusters before training, 96 TRAIN-domain
  excluded-team and 96 validation-domain clusters; audit prior consumption and
  whole-team overlap. No sealed final data. Disclose historically seen teams/sets.
- Parent and four fixed endpoints: 1,152 games each, 576 heldout, total 5,760.
  Champions, tactical and frozen league-anchor rivals; both real native seats
  preserve the candidate's team. Native winners remain the evaluation outcome.
- Primary: heldout mean-seed B-A; 20,000 paired case-cluster bootstrap samples
  preserve rival/seat/repetition dependence. Both seed differences must be
  positive and the combined lower 95% bound above zero for a further independent
  verification candidate. Parent comparisons and breadth are separate diagnostics.
  Two continuations do not establish training-seed population uncertainty.
- CPU 50%, RAM 12 GiB, four training workers, one evaluation worker, no GPU.
  Training/evaluation ceilings 5,400 seconds each, overall 10,800 seconds.
  Durable STOP/checkpoints, existing finite/mask/retry-progress guards, no crash
  restart, no budget expansion, no policy promotion.

Raw native rewards, potential endpoints/difference, shaped environment rewards,
timeout correction and final buffer rewards are separate scalar receipts. Original
PPO logp/mask/GAE/ratio and Adam audits are reused. Complete-episode telescoping
and history integrity failures stop the run rather than silently excluding games.

Artifacts live outside Git under
`C:\Users\jsp33\.codex\artifacts\foundation-public-faint-potential-matched-v1-20261029`.
The immutable plan, cases, model/Adam SHAs, ledgers and final integrity audit bind
the actual execution. This document does not claim the experiment is completed.
