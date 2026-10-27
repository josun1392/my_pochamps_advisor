# Teacher-free fixed-scenario micro learnability v1

This opt-in experiment composes existing Foundation PPO, native Gym, public
trace/retry audit and seat-balanced evaluator owners. It introduces no teacher,
mechanics, policy architecture, reward or optimizer change. Ordinary training
entry points are unchanged.

`scripts/pilot_foundation_fixed_micro.py prepare` freezes a new external plan
before any native execution. Four disjoint V8 TRAIN roster pairs cover recovery,
setup, protection, switching and offensive pressure. Two pairs supply training;
two different pairs are mini-heldout, with separate native seed namespaces.
Ordered bring-three is fixed, not learned preview. These are deliberately small
conditional tasks. Neither species-unseen nor unseen-to-the-parent is claimed.

The four existing opponent identities cycle equally per episode: frozen
Foundation argmax, frozen Foundation T=1 sample, tactical and Champions
heuristics. Four native Gym workers execute sequentially in DummyVecEnv to
preserve 512-transition rollouts without four extra Python processes. Two case
families alternate in four-episode blocks to avoid rival/family confounding.
Native legality, retries, automatic wait and training-only prediction-label
ownership remain in their maintained implementations. Frozen opponents never
read the live learner. Per-case rival RNG resets exclude the evaluated model ID;
downstream RNG consumption may still differ after policies diverge.

The original Foundation weights and Adam are restored into an independent
learner. The plan binds their semantic hashes, original ZIP hash and PPO settings.
Four 1,024-transition windows yield at most 4,096 transitions and 128 Adam calls
(n_envs=4, n_steps=128, batch=128, epochs=4). Checkpoints retain optimizer state;
new learn calls restart rollout bookkeeping, not weights or optimizer. Durable
pre-start and pre-Adam intents cap TRAIN starts at 512 and updates at 128.
Native wait/retry submissions are recorded separately from PPO transitions.

Evaluation freezes 64 roots, four native seeds per family/scope/rival, both
actual seats and Foundation/Micro: 256 starts total. The first 128 Foundation
games establish fixed-task headroom; seen win fraction >=0.90 stops without
replacing cases. Candidate actions use T=1 argmax. Receipts are written after
each completed game using the existing cumulative/idempotent persistence owner.
Rerunning an already-started study fails closed; no automatic retry campaign.

Primary reporting keeps wins/losses/draws/truncations distinct. Paired bootstrap
resamples native seed roots within fixed family/scope/rival strata, clustering
both seats. Its interval is conditional on four fixed team pairs and does not
estimate team-population or training-seed uncertainty. One exploratory seed
cannot establish general superiority. Stable completion, positive seen change
and positive heldout CI lower bound are required for
`MICRO_LEARNING_DEMONSTRATED`. A negative heldout CI upper bound yields
`MICRO_NO_GAIN`; otherwise `MICRO_INCONCLUSIVE`. No promotion follows.

CPU only, Windows job CPU cap 50%, aggregate RAM 8 GiB, four native workers and
one 3,600-second launch ceiling. STOP preserves completed checkpoints. Public
rollout/action-mask/logp/value/GAE and finite-update audits remain active.
Models, traces, evaluation roots and raw receipts remain outside Git.

The first 2026-10-27 launch stopped at the preregistered headroom gate:
Foundation won 59/64 seen games (92.1875%), above 90%. Across all initial
games it won 116/128, with no draws, truncations or native rejections. No
TRAIN start, PPO transition, Adam call or learner checkpoint was produced.
The native evaluator and fail-closed gate ran; the composed learner path
was not exercised and its actual micro-study learning behavior is unverified.
The result is `BLOCKED`, not evidence that PPO cannot learn. The threshold
is a design rule, not a statistical proof of an intrinsic performance ceiling.
Cases were not replaced after seeing outcomes. Future authorization should
prefer reciprocal team assignments as well as real seat balance to reduce
fixed-matchup asymmetry, rather than search for losing teams post hoc.
