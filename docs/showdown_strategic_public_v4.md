# Categorical V4 strategic public state

Opt-in encoder `showdown-public-categorical-observation-v4` is distinct from
numeric `showdown-learned-observation-v4` and categorical V1/V2/V3. Pinned
Showdown `942cda71d14bf0618bd57991708a2e2734b6daba`, format
`gen9championsbssregmc`, remains the only mechanics/legality authority.

## Bounded coverage audit

| Information | Previous coverage | V4 treatment |
|---|---|---|
| Exact public species/forms, moves, abilities, items; Unknown/absence | Categorical V3 | Same token maps/shared embeddings; no catalog mutation |
| HP/status/boosts, turn, PP/priority/nominal power, nominal STAB/type priors | Encoded | Reused; catalog species priors are explicitly nominal, not current typing |
| Weather/terrain | Public projection, numeric encoding | Reuse projection; correct Snowscape, distinguish Hail and severe weather |
| Hazards/screens/Tailwind, Trick Room, public move-order sample/healing history | Encoded by tactics/interactions owners | Reused; no duration/damage/true-speed inference |
| Taunt/Encore/recharge/heal-block/sound restriction/trapping | Some consequences only in native request masks; public events not encoded | Public effect state as additional information; never recompute masks |
| Substitute/confusion/activated Flash Fire | Public events not encoded | Bounded public start/end/activation projection |
| Current changed/added/transformed types | Public events preserved, old nominal priors only | Separate exact public current type multi-hot + known flag |
| Supreme Overlord | Public activation/fallen events preserved | Separate activation **evidence**, explicit fallen count or Unknown; not an ordinary volatile or species-based inference |
| Effect remaining duration, hidden trap aura, silent passed volatiles, omitted type payload | Unknown/unsupported | Remain Unknown; explicit projection coverage markers |
| Exact damage, hidden item/ability/set, RNG, learned preview | Unsupported/not authorized | Not added |

## Contract and timing

`learned_strategic_public.py` consumes the same player-visible observation/history
as V3. `showdown_observation.py` is unchanged. The V4 projector only reduces a
small declared protocol vocabulary; it is not a general Dex effect interpreter.
Weather/terrain and old features retain their existing public-state owners.

Nine effect channels per **ordered self/opponent active appearance**:
Substitute, Taunt, Encore, confusion, publicly established trapping, recharge,
Heal Block (including Psychic Noise), Throat Chop, activated Flash Fire. Each is
`[known active, known absent, Unknown]`. Start/end events establish state only
from that point. Recharge uses `-mustrecharge` / `cant ... recharge`. A public
activation does not assert that its damage modifier is currently effective.

Fresh ordinary entry establishes absence for the eight ordinary volatiles.
Absence of a trapping announcement does not rule out a hidden aura; trapping
stays Unknown unless established. `maybeTrapped` is not evidence. A departing
possible trap source invalidates prior trap evidence instead of computing the
interaction. A native own `trapped: true` request is authorized own information.
Switch/faint/reset clear entry-local effects. Baton Pass/Shed Tail silent copying
is classified Unknown, without duplicating native copy rules. No timers or
random durations are invented. Supreme Overlord activation and explicit
`fallen1..5` are separate evidence; neither species nor visible team count is
used to infer activation or a missing count.

Current types use public switch/form/typechange/typeadd/Transform events. Unknown
Illusion appearances remain Unknown; own identity may use the player's own
request. Public replacement revelation preserves already announced changed
types and does not merge preview records. Transform copies only known public
target types; it does not rewrite the actor's species identity. Native Reflect
Type can omit its type payload: this stays Unknown and is classified explicitly.
In-turn Roost typing is conservatively Unknown until the next public turn.
No hidden target data is read. Legacy species/type/power features remain labeled
nominal priors; no second damage-strength calculator is introduced.

V4 transport: **15,692 floats**, versus V3 15,576. Original 35 action rows and
their last-column native mask are unchanged. Additional context is 116 floats:
56 per ordered active appearance (27 effect states, 19 current-type features,
3 activation-evidence states, 7 explicit fallen-count states), then four extra
weather indicators (Hail/Desolate Land/Primordial Sea/Delta Stream). Existing
numeric context column 8 now means pinned-native **Snowscape**, not `snow`.
All categorical tokens and transport bit widths are unchanged.

`StrategicPublicCategoricalPolicy` preserves separate entity latents, candidate
gathers, shared embeddings and action-row permutation symmetry. The extra
ordered active states reach both actor context and critic context. Parameter
count: **383,130**, versus V3 360,858 (+22,272; 6.17%).

## Transfer and checkpoints

Use source trainer `transfer_model` with V4 `encoder_version` and explicitly
`fresh_optimizer: true`, gamma 1 / GAE .95 as appropriate to the new experiment.
`transfer_strategic_public_weights` accepts categorical V3 only, with identical
token maps. All compatible learned tensors are copied. Added input columns are
zero initialized. Column 8 is corrected to Snowscape; its old native-dead `snow`
weights are zeroed in actor/critic. Pinned native protocol never sets the old
`snow` column, so this preserves V3 actor logits and values on native inputs,
including Snowscape. It does not promise equivalence for invented non-native
`|-weather|Snow` histories; V4 rejects that unsupported identity.

Changed input shapes require **fresh Adam**, not a Stage 2 optimizer resume.
V4-to-V4 normal resume retains its own optimizer. The existing legal-uniform KL
regularizer, objective metadata, strict feature fingerprint, policy class and
checkpoint loader still apply. Positive-beta files reload through the maintained
regularized algorithm subclass; no silent base-PPO continuation is permitted.
V1/V2/V3 feature meanings, fingerprints, policy classes and original files remain
unchanged. No production recommendation is enabled or altered.

## Verification and next scope

`tests/test_strategic_public_v4.py` covers both player seats, all declared effect
transitions, reset/timing, Unknown/pass/trap boundaries, public types/Illusion,
native legal effect routes, Snow expiration, unchanged masks, hidden-set/RNG
isolation, transfer logits **and** values, permutation, nonzero new-path gradients,
strict loading and real regularized native PPO save/reload/resume.

Runtime artifacts and the bounded source-trainer smoke are external to Git under
`C:\Users\jsp33\.codex\artifacts\obs-v4-lite-strategic-public-state-v1-20261015`.
They are engineering evidence, not a win-rate or policy-strength study.

Next SELFPLAY_V1_SCALE should first bind V4 generation manifests, one explicit
V3->V4 fresh-Adam transfer per common parent and V4->V4 optimizer continuation.
Keep the fixed mixture as the cost baseline, retain the V0 league as an optional
matched arm, and remeasure its near-12-GiB memory margin before pool expansion.
Use bounded checkpointed budgets and fresh independent evaluation identities.
No advantage of the league, competitive strength, preview learning or default
production promotion follows from this feature integration.
