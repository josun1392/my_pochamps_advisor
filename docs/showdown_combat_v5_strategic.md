# Integrated combat V5 strategic contract v3

This opt-in contract answers the V5-v2 improvement task without changing released
integrated-v1/v2 meanings or the live guaranteed-first advisor. Its encoder ID is
`showdown-public-categorical-observation-v5-integrated-v3`. It has 28,822 input
values and 674,939 policy parameters. The native action schema remains 35 actions.

## Reused owners and conditional tactical references

The V4 public categorical prefix, authenticated own HP, causal six-turn history
GRU, nominal V5 tactical rows, shared category embeddings and native masks remain.
The new 35 × 42 rows add 24 numerical reference/availability fields and 18 nominal
incoming-type matchups. Existing type/power/STAB/PP/priority features are retained.

`learned_combat_v5_references.py` reads only the acting player's public view. It
reuses `advisor.damage` stat, field, item, ability and single-hit formula owners;
it implements no replacement battle simulator. Fixed power/callback eligibility
comes from the pinned native Dex. Showdown remains the execution and legality
authority. Formula checks use native fixed-context oracles only in coordinator
tests, never as inference-time private features.

Outgoing reference damage varies canonical legal independent defense/HP/nature
endpoints; incoming references use **only publicly revealed moves** and canonical
attack endpoints. Own stats/HP/items/abilities come from the owned request.
Public boosts, current typing, burn, weather/terrain and screens feed existing
owners. Public HP fractions are rounded observations, not opponent exact HP.
Speed references use own request speed/boosts, item/paralysis/Tailwind and a
canonical opponent range, with conditional Trick Room reversal. Priority is base
priority; this is not exact execution order under every ability/volatile.

The new `learned_public_boosts.py` projects causal public stage events including
Power/Guard/Heart Swap and Psych Up copying. Unknown stages stay unknown, public
entry/clear/faint resets are explicit, Illusion replacement carries only the
current public appearance's evidence, and unsupported Baton Pass state is
unknown. Actual two-seat native Power Swap tests confirm the new references
against a coordinator-only native checkpoint. Legacy V4 and V5-v1/v2 structured
summaries omit copy/swap and can accumulate impossible stages (a captured native
case reached a legacy −8). Those historical encoder semantics are preserved;
the corrected references use the separately versioned public stage projection.
The old summary is not silently asserted to be complete mechanics state.

These are explicitly **conditional noncritical single-hit reference ranges**.
Unknown modifiers are neutral hypotheses with an unknown flag, not known neutral
facts. The separate unsupported-effect flag covers unmodeled public conditions
and catalog modifiers. Availability is false for unsupported variable/callback
damage, multi-hit, special native choices and unavailable types/stats. Copied or
publicly replaced stat templates fail closed. Paradox/highest-stat and Supreme
Overlord references are unavailable. Neither the HP-depletion indicator nor a
16-roll range is an exact KO/action probability, guarantee or action label.

Switch rows use current bench HP and unboosted entry references. They do not
simulate hazards, switching timing, future recovery or future opponent choices.
Existing public side conditions remain available to the policy. Nominal incoming
type threat averages predicted move identities; variable move types and unknown
modifiers are not actual incoming damage. Unsupported effects are not silently
promoted to exact evidence.

## Public support and predictive priors

An unconfirmed appearance/slot join does not imply that all six preview species
could be active. Support uses the displayed current species/form plus preview
species whose pinned legal ability domain permits Illusion. A public confirmed
replacement resolves that ambiguity. Public move-copy evidence widens move
support; ability revelation does not by itself widen the move learnset.

`models/showdown_combat_priors_v3/catalog.json` is a small deterministic prior
asset, not a model checkpoint or authoritative hidden-set list. It is built from
the verified 256-team TRAIN subset, separate training-episode public execution
frequencies and the pinned native Dex. No validation/test data are inputs. Counts
are smoothed by 16 species pseudo-observations, a 50% global/uniform base and one
action-frequency pseudo-count. Move marginals have a sparse four-move base,
instead of an initial 0.5 score on hundreds of negatives. The switch rate is
normalized separately from the conditional move distribution; set marginals do
not spuriously inflate switch probability. Runtime support can remain broad.

These are distribution-dependent **predictions**, never disclosed hidden facts
or established calibrated beliefs. They are evaluated against frequency and
public-possibility baselines, including unseen complete teams/movesets. Individual
sets and species can overlap training; no species-unseen claim is made.

## Properly timed auxiliary learning and decision influence

The next-action head has 1,025 classes: exact canonical move token or an observed
switch. Targets are the next publicly announced/executed attempt, not private
intent, success or optimality. Cancelled, `cant`, drag, faint-before-action and
otherwise unobserved selections remain unlabeled. Forced replacement can be an
observed switch; this head is not a voluntary-intent classifier.

Hidden moves/ability/item labels come from the **predecision** opposing owned
request through a separate coordinator-only loss channel. Publicly revealed
values do not inflate unknown-field prediction scores. No labels, opposing
request, checkpoint, team fixture or future RNG are allowed in policy/value
forward inputs. Ground truth never widens forward support. Out-of-support targets
are counted and omitted, not silently reinterpreted.

Heads predict bounded residuals (±2 logits) over the frozen public prior. CE and
per-decision unknown-cell move BCE are proper likelihood losses; no arbitrary
rare-class weighting changes the target population. Public executed-family
stratification uses inverse-proposal, self-normalized weights. This is a finite
batch estimator with sampling variance, not exact class rebalancing.

PPO gradients stop at the prediction distributions; auxiliary gradients stop at
the reused public combat trunk. This prevents likelihood heads being freely
rewritten as PPO latent codes, and prevents private-loss gradients overwriting
the combat encoder. Expected shared categorical embeddings, predicted move/switch
features, uncertainty and action-conditioned nominal type threat still enter
actor and critic. Updated heads can change decisions; this is tested separately
from claims of useful strategic influence.

Auxiliary coefficient is 0.02 and is separate from native rewards, PPO returns,
advantages and learned values. Values remain learned expected terminal return,
not exact win probabilities. Gamma 1.0, GAE 0.95, beta 0.001 and maintained
MaskablePPO/GAE arithmetic are unchanged.

## Initialization, persistence and study

Strict V4 transfer copies compatible tensors and zeroes new actor/value input
columns. Actor logits/probabilities and values match within 5e-6 on native probes.
All altered-shape models use fresh Adam. The V4 continuation control also starts
with fresh Adam from the identical immutable V4 source. Later same-version resume
preserves Adam and the custom auxiliary/zero-avoiding class; metadata mismatch
fails closed. Episode/RNG/partial-rollout continuity is not an exact replay claim.

Two stochastic continuation seeds (89011, 89012) each receive a V5 and V4-control
262,144-trained-transition budget. They share the 256-team subset, ordered
three-of-six, ten-slot frozen opponent mixture, CPU/worker/resource bounds and
PPO hyperparameters. These are two continuations from a common pretrained parent,
not independent full-history pretraining replications. Original v1/v2, Preview,
JAX and production models remain unchanged. Search stays disabled.

Experiments and immutable model/data/evaluation identities live outside Git in
`C:/Users/jsp33/.codex/artifacts/pokeadvice-combat-v5-v2-strategic-learning-improvement-20261016/`.
`frozen_study.json`, `initialization_proof.json`, `signal_diagnostics.json`,
`study_execution.json`, and `evaluation/` separate preparation, trained updates,
fixed endpoint performance and prediction quality. Selection never substitutes a
validation-best model for the declared final endpoint. A successful implementation
does not establish improved competitive strength or authorize model promotion.

## Bounded study result (2026-10-16)

All four fixed endpoints completed: 1,048,576 collected/trained transitions,
81,887 native terminal episodes and one separately counted time-limit truncation.
The frozen 64-case × two-seat × four-rival panel produced 2,560 endpoint games:

| Policy | Wins / 512 | Sample win rate |
| --- | ---: | ---: |
| Original V4 | 238 | 46.48% |
| V4 continuation 89011 | 264 | 51.56% |
| Corrected V5 89011 | 261 | 50.98% |
| V4 continuation 89012 | 264 | 51.56% |
| Corrected V5 89012 | 279 | 54.49% |

Primary V5-minus-control differences were −0.59 and +2.93 percentage points.
Their two-repetition mean was +1.17 pp, case-cluster bootstrap 95% interval
[−2.15,+4.59] pp. V5 superiority, equivalence and noninferiority are unproven.
Both continuations improved over the original on this panel; that does not
isolate the contribution of V5 features or establish global competitive strength.
There were zero endpoint evaluation draws, truncations or native rejections.

Executed-action NLL improved over the same-input species/frequency prior
(2.599 vs 3.018; 2.598 vs 3.031). Move top-four recall improved from approximately
28% to 32%. Item NLL did not meaningfully improve; action-head ECE worsened to
approximately 0.21–0.22. Defense/recovery labels remained sparse and performance
on those conditional families did not improve consistently. These outputs are
not calibrated probabilities of opponent intent or optimal-action labels.

On 89 fixed public diagnostic inputs, zeroing the learned prediction residual
while retaining the prior changed the actor argmax only 1/0 times. Ablating the
conditional reference bundle changed it 7/6 times. These are sensitivity checks,
not strategic-quality labels or a causal estimate of battle gains. Improving the
connection from uncertain forecasts to candidate-specific risk is a more grounded
next development step than blindly increasing PPO volume.
