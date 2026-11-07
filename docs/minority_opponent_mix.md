# Minority stochastic frozen-opponent matched study

`minority-stochastic-opponent-mix-controlled-ppo-v1` reuses the original shared
set-context A, its strict frozen-parent transfer, standard full-minibatch
advantage normalization and residual-only fresh Adam. Only the two residual
tensors (4,160 parameters) learn. Critic, encoder, prediction heads, terminal
reward, GAE(.95), PPO, entropy and uniform KL(.001) are unchanged. No parent KL,
temperature adjustment or actionable-only normalization is enabled.

Existing A_s1/A_s2 endpoints (seeds116051/116053) are reused, never retrained.
Treatment Am_s1/Am_s2 each receive exactly16,384 transitions and512 PPO Adam
steps, from the same original Foundation and fresh Adam. The maintained
16-template/16-team V8 TRAIN schedule, native seeds and four workers remain
unchanged. Intermediate4K/8K/12K/16K checkpoints retain weights and optimizer;
their verification loads preserve Python/NumPy/Torch RNG. Unsupported native
cold resume remains fail-closed. No automatic restart is authorized.

The existing TRAIN-only adapter receives explicit slots `[argmax,argmax,argmax,
masked_sample]`. Each native episode's case index modulo4 selects its opponent,
without an assignment RNG draw. The independent PCG64 stream is separately
addressed by the maintained TRAIN sampler. Constructor/reset episodes are not
silently removed from accounting. Actual started/terminal/administrative episode
fractions, native-decision fractions and collected PPO-transition fractions are
reported separately: differing episode lengths do not imply25% transitions.
The new recorder joins each PPO row to the predecision native trace/episode,
including terminal rows followed by VecEnv auto-reset. It does not demand old-A
rollout bit identity after an opponent changes, or alter old logp/GAE/returns.

Before training, original A's retained contract and current argmax-only path are
checked offline; initial weights/logits/probabilities/value/masks and fresh Adam
must match. An inactive typed-loader guard is distinguished from a learning
change. Source legality/identity and a new deterministic evaluation schedule are
frozen before performance is observed. Logical source seed116091 admits the
first160 eligible teams from one native-generated200-candidate batch, excluding
all maintained banks and prior pilot/development/sealed-source identities,
including the quality-pilot teams and all previous generated candidates.
Sealed outcomes are never opened. No redraws, outcome-based admission, source
shrinking or replacement games are supported.

Evaluation: Foundation plus four A/Am endpoints, two frozen rival modes,80new
team pairs, both roster owners, two native seeds, both actual seats:6,400 starts,
1,280/model,640/model/rival. Candidates always argmax. Rival sampling uses the
same independent PCG64 seam under a new116091 namespace shared across candidate
models. Initial native/public states are paired, but post-divergence native RNG
consumption need not match. Every choice is recorded before execution; illegal
mass, rejection, truncation, missing/duplicate results or provenance failure
stops the owner without unauthorized retries.

Primary: Am−A terminal return versus argmax; secondary: versus sampled rival.
Both repetitions remain inside each of80team-pair clusters in20,000 bootstrap
draws(seed116095). A primary interval containing0 is not evidence of improvement.
Sample-only gains are not general combat improvement; a positive primary is a
development signal, not sealed superiority or promotion. First-action changes
do not isolate first-action causal effects.

The detached owner uses CPU50%, RAM12GiB, four training workers (sequential
DummyVecEnv), one evaluation worker, GPU off and a2h wall cap. Models, Adam,
source, raw traces and receipts stay in the external artifact directory. The
previous quality study's source/receipts and historical checkpoints are hashed
before/after. Extra learning, evaluation, ratio tuning and promotion require
separate T1 authorization.
