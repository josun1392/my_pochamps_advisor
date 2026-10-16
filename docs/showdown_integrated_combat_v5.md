# Integrated combat V5 v1

Opt-in contract: `showdown-public-categorical-observation-v5-integrated-v1`.
The production advisor, categorical V4 and historical experimental encoders are
unchanged. This version is one integrated model for both transferred and scratch
initialization; it is not a new simulator, preview policy or recurrent PPO.

The completed four-arm study remains frozen under that **v1** identity and
fingerprint. A separately opt-in
`showdown-public-categorical-observation-v5-integrated-v2` repairs one later
observed appearance-support boundary without changing architecture, token IDs,
PPO or historical v1 semantics. Both versions are supported by the strict loader.

## Public transport and architecture

The 24,535-dimensional float transport preserves the original 15,692-dimensional
categorical V4 prefix, including its history summaries, action-conditioned
tactics, native priority/PP, public weather/terrain/screens/hazards, typing and
known item/ability interactions. It reuses:

* authenticated own HP: six identity-bound rows, separate current/max knowledge;
* causal six-turn, tail-64-event history and the stateless shared-embedding GRU16;
* ten candidate features using own request stats and confirmed public current
  opponent typing, plus revealed-move defensive type priors;
* public legal-domain supports and known-value transport for prediction heads.

The new offensive index combines nominal native move power, an own request
attack stat, type-chart prior and nominal STAB. It is **not damage, a roll, a KO
guarantee or exact speed order**. Request stats are unboosted registered stats;
unknown opposing defenses, EVs, items and abilities are never filled in. Exact
damage is explicitly unavailable and modifier uncertainty is flagged. Existing
V4 observed-order and priority features remain historical evidence, not a true
speed oracle. Masked actions stay masked; even full-HP recovery stays legal.

The action-conditioned V4 scorer and critic remain. The GRU/HP/candidate features
and a 64-wide prediction latent extend their input pathways. Four heads predict:

1. the opponent's next **publicly executed** move family or switch (six classes);
2. its current active ability ID;
3. its current held item ID, including confirmed absence;
4. marginal membership of each current move, not a joint legal guessed moveset.

Expected shared categorical embeddings, action-family probabilities and entropy
summaries feed the actor and critic. Predictions are estimates, never promoted
to public facts or passed as true sets to a damage calculation. Known public
ability/item values override estimated decision distributions. Past revealed
moves are not forced current after publicly observed move-copying changes.

Both variants have exactly **600,000 parameters**. V4-compatible weights are
copied for the pretrained variant, and all new actor/critic/scorer input columns
are zero at transfer. Old logits, probabilities and values are preserved up to
FP32 rounding. Changed-shape Adam moments are not copied. Both variants start
with fresh Adam. Scratch weights are generated independently without V4 loading
or distillation; the same frozen V4 may legitimately be a reference opponent.

## Supervision and privacy

Only public features enter policy, value and prediction forward passes. Native
action masks are unchanged. Species/form learnability and the format-wide item
domain come from the pinned native inventory. Illusion ambiguity widens public
support to possible preview species; public runtime transformations widen it
conservatively. A private target outside this support is skipped, never used to
change the observation mask.

Current transformed-form abilities use the inventory's **public native Dex**,
not its starting-set `abilities` eligibility list. The latter describes the base
set needed to reach a Mega and can differ (e.g. Glimmora → Adaptability).
A public formechange invalidates an older revealed ability's *current* binding
until newer public ability evidence; the historical V4 prefix is preserved.
Glimmora/Gardevoir Mega routes are verified in both seats. The first pre-correction
96,256 trained-transition run was stopped, preserved and excluded from the
matched study; all four corrected arms start anew under the corrected fingerprint.

The frozen evaluation later found one additional case: with Illusion in the
public preview, v1's preview-union ability support omitted the displayed Mega
Kangaskhan's Parental Bond. Its 14–20 unavailable loss targets per final model
were skipped, never used to reveal or widen a policy input. These are a documented
limitation of the completed **v1** study. In **v2**, the support is the union of
preview possibilities **and** the public displayed form's pinned native ability
domain. Native fixtures verify both seats and preservation of Illusion uncertainty.
The v2 feature fingerprint is different; v1 models are never silently relabeled,
converted or replayed as v2. V2 has focused native learning/reload tests, not the
four-arm 262k performance study. Additional training should use a newly declared
v2 experiment; the v1 experimental outcomes remain evidence about v1 only.
An explicit `transfer_combat_v5_appearance_weights` route copies v1 tensors into
v2 with fresh Adam and new metadata. Unaffected public inputs preserve outputs;
repaired support states can change predictions and decisions. This migration is
not an uninterrupted optimizer resume. The original v1 ZIP and fingerprint remain
loadable and unchanged.

`ShowdownLearningEnv` opts into a separately named **coordinator loss-only** info
channel for V5. It extracts only ability/item/move tokens from the opponent's own
predecision native request. No private stat, request, checkpoint, seed or hidden
team is a forward input. A native switch's hidden targets stay bound to the
outgoing active; they are not mislabeled with the incoming Pokémon's set.

The next-action label uses delivered public execution events before the next
learner decision. Cancelled/unobserved actions, `cant`, forced `drag` and called
move events do not invent original selections. A `switch` includes an observed
replacement: this head predicts public response family, not a private intent or
which hidden three were selected at preview.

Targets and public predecision features are aligned in time-major rollout order
by the maintained callback. Labels never enter the rollout observation array,
reward, GAE or value target. Partial rollout restart discards both sides of that
alignment. Private current targets are not serialized in model ZIPs.

## Learning and persistence

`IntegratedCombatV5PPO` reuses maintained MaskablePPO/GAE and the existing bounded
entropy-loss seam. Native terminal return, gamma=1, GAE=.95, clipping, LR, epochs,
target-KL and zero-avoiding beta=.001 remain. A separate coefficient **.02** times
the mean available supervised losses is added; auxiliary gradients into reused
public representation are scaled by **.1**. Existing global gradient clipping
and target-KL safeguards remain. No auxiliary reward or optimal-action target is
introduced. Logged composite entropy loss includes auxiliary terms; use the
separate `train/true_action_entropy` for actual action entropy.

The versioned `integrated_auxiliary` checkpoint contract is mandatory. The
strict loader restores the customized training class and optimizer; loading V5
through base PPO cannot silently drop supervision. Inference requires no labels.
STOP/resume restores durable model/Adam state, resets native episodes and starts
a fresh rollout; it is not byte-exact mid-episode replay.

This is a source-trainer opt-in, not a rebuilt Windows Trainer distribution.
Use the existing `scripts/train_showdown_autonomous.py --config <config.json>
--output <external-directory>` entry point with `encoder_version` set to the V5
contract above. A fresh run omits `initial_model` and `transfer_model`; a V4
transfer declares `transfer_model`, its `transfer_model_id`, and
`fresh_optimizer: true`. An existing V5 `initial_model` or durable `--resume`
uses the strict custom algorithm loader. Keep the declared gamma, regularizer,
catalog, source and objective bindings compatible. The maintained trainer's
`BudgetCallback` is required to align the loss-only labels with each rollout;
calling base PPO learning without that collection contract fails closed.

Inference continues through `LearnedPolicy(model_zip, catalog)`. It requires
only a player-visible observation and does not request supervised labels or
opposing private state. No model is installed into the live advisor by training
or by loading one for evaluation.

Held-out diagnostics score first up to eight non-wait decisions per battle.
Hidden-head metrics exclude already revealed ability/items and known moves.
Accuracy is accompanied by log loss, Brier aggregates, confidence bins, class
coverage and out-of-support counts. These are trajectory-dependent prediction
metrics, not proof that an auxiliary head improves battle strength.

## Reuse decisions

[Jaxcalibur's author write-up](https://jaxcalibur.github.io/) motivates compact
public history and opponent/hidden-information prediction, but code and weights
are not publicly released there. Its reported random-singles results are not
Champions evidence. No JAX engine, search or external code is imported.

[ai-vgc](https://github.com/Nisanth-Nimashakavi/Ai-vgc) documents move-conditioned
scoring, zero-initialized feature additions and an opponent head for doubles.
No root license was verified, so its code/weights are not copied. Its doubles
action schema and private/open-sheet assumptions are not reused.

[VGC-Bench](https://github.com/cameronangliss/VGC-Bench) has an
[MIT license](https://github.com/cameronangliss/VGC-Bench/blob/main/LICENSE).
Its frozen-pool and cross-team evaluation patterns are already represented by
PokeAdvice's snapshot league and paired evaluator. No doubles environment or
external training framework is transplanted. Optional one-turn search stays
disabled: earlier native branch rankings were hypothesis/RNG-sensitive.
