# PREVIEW_V1: learned ordered bring-three

This opt-in offline system leaves the live advisor and its 35-action battle
policy unchanged. A separate preview policy learns one decision per complete
native battle. Infrastructure correctness does not establish playing strength.

## Native authority and ordering

The pinned `942cda71d14bf0618bd57991708a2e2734b6daba` engine and
`gen9championsbssregmc` TeamValidator validate the **full six**, including native
species/item/format clauses. `inspect_preview` constructs a temporary native
Battle at its actual `teampreview` phase, before either player's choice. Each
owner gets only its own six-member request and public preview events. It does
not create an execution episode or expose the other player's private request.

Execution uses the existing `createLegalBattle`: native
`battle.choose('p1', 'team XYZ')` and the corresponding p2 choice. No selected
team is reconstructed in Python. Lexicographic permutations of slots 1..6 give
120 actions (`0 -> [1,2,3]`, `119 -> [6,5,4]`). The first is the lead and the
remaining two preserve party order; the native picked team contains only three.
All 120 actions are legal for the supported native-validated full-six contract.
Other roster sizes/phases fail closed.

The pinned `Side.chooseTeam` records the positions in order. Native Illusion
selects the last eligible brought party member to its right: `[Zoroark,A,B]`
and `[Zoroark,B,A]` can display different disguises. Therefore neither the
reserve order nor any of the 120 actions is silently collapsed.

## Public observation and model

`showdown-public-preview-observation-v1` and
`showdown-ordered-bring-three-actions-v1` are separate contracts from all battle
encoders/models. Twelve ordered records preserve the original roster slots:
own six, then the opponent's six public `poke` entries.

Own species/form, four move slots, ability, item, and six **native owner-request
stats** are available. Opponent moves, item, ability, and actual stats remain
Unknown. No selected-three list, scenario ID, seed, opponent request, future
history, hidden set, or coordinator label enters actor or critic. The encoder
accepts a closed DTO; extra root/entity fields fail validation. Opponent shiny,
gender, and ball details are not features. Own nature/EV/IV are not separately
encoded; their legitimate effects are reflected in native own stats.

Exact category tokens reuse the V3 append-only vocabulary and binary embedding
transport. Known no-item and unknown item use distinct tokens. Numerical
features contain public species base stats/types and own native stats and
nominal move power/accuracy/category; there is no damage calculator. Feature
dimension is 1,428. Shared embeddings bind identities to individual records;
an ordered three-record actor scores 120 actions. The critic uses the same
preview-visible information. Categorical bit fields never enter linear layers
as ordinal numeric strengths. `VecNormalize` is not used.
The preview network has 115,802 trainable parameters; the V4 battle network is
a separate frozen object.

The upstream SB3-contrib MaskablePPO algorithm is reused. The new lightweight
network is freshly initialized, not transferred from a battle policy. The
battle V4 ZIP is independently loaded, hash checked, put in evaluation mode,
and all its parameters have `requires_grad=False`.

## Objective, bounds, save and restart

One Gym transition executes a whole native battle under the frozen battle
policy versus a named frozen visible opponent. Native win/loss/draw rewards are
`+1/-1/0`, gamma=1, GAE=.95. Real native termination is required. A 4,096-decision
artificial cutoff raises an explicit error and supplies no false draw/loss or
Monte Carlo label. This version does not recover a partially executed battle.

`scripts/train_showdown_preview.py` reuses WindowsJob limits, local-network
guards, SubprocVecEnv, and RuntimeLimit. Configurations bind source hashes,
native pin, feature contract, V8 subset, battle-model SHA, seed and rivals.
The bounded pilot uses eight CPU workers, 50% CPU and 12 GiB RAM. It saves the
initial model and every completed PPO rollout/update. All data is external to
the repository. STOP is acknowledged at a durable rollout boundary; the
watchdog can kill a blocked job after its grace period.

```powershell
python scripts/train_showdown_preview.py --config frozen.json --output OUT
# Request stop by creating OUT/STOP. Preserve/rename that marker before restart.
python scripts/train_showdown_preview.py --config frozen.json --output OUT --resume OUT/checkpoint_00001024.zip
```

Resume verifies model/config identity and restores Adam moments/step counters.
It starts fresh native episodes at explicit subsequent worker case indices.
It is **not** a claim of exact interrupted rollout/RNG replay. The current
session-owned job must stay running: no Codex-disconnection survival guarantee
is made. A user-launched source process can run independently of inference or
any token-consuming service. There is no new preview control in Trainer.exe.

## Paired evaluation and reuse

`scripts/evaluate_showdown_preview.py` reuses the actual fixture-seat evaluation
contract: p1 and p2 control different native teams and private requests. It
never relabels a winner to simulate a swap. Uniform-random, initial, and final
preview policies share the frozen battle policy, canonical full rosters,
opponent preview selections, opponent policies and initial native seeds.
Downstream RNG consumption may diverge after different choices.

New native-generated scenarios and input hashes must be frozen before training.
Report complete-team/joint-moveset and individual-set overlap with prior banks.
Species overlap is expected; these are not species-unseen or competitive-usage
benchmarks. A consumed evaluation panel is never a still-sealed final set.
Bootstrap case clusters retain both seats and rivals, and cannot quantify
between-training-seed variation from one pilot.

Reuse review: VGC-Bench (`cameronangliss/vgc-bench`, MIT,
`d79f9532947ac114dce1dda2456a590afcd375b2`) separates optional preview control
from battle control, but its two successive doubles choices and four-member
preview API are incompatible with Champions singles. Those components were
not copied. This implementation uses native Showdown choices and existing
PokeAdvice public categorical, legality, model-loading and resource owners,
with upstream SB3-contrib learning, rather than a parallel simulator or RL
algorithm.

## First bounded pilot (2026-10-15)

Seed 75011 completed 32,768 terminal preview episodes on the existing 256-team
V8 train subset. A deliberate STOP at 1,024 and explicit reload preserved Adam
state (32 steps); final Adam steps were 1,024. All 32 durable checkpoint parents
were checked. No original battle checkpoint was modified. The frozen V4 battle
ZIP SHA was `acb98005c664bd9f272d9a35871b0a60d618af37b64213da44960c4ad884aa2a`.

Feature fingerprint:
`151fa5fb690453a4e70b5242b207f030c623f534c7beb04eae2d0d7f1389f5ad`.
Final preview ZIP:
`e5a2b9a9601d4a77f5ece48861ca4373894837af982383bcb0d68921b7c07ded`.

Fresh native-generated panel: 128 clusters, two actual seats, two visible rivals
(tactical and Champions), 512 games per model. Random preview won 249/512,
untrained deterministic preview 266/512, and fixed-budget trained preview
292/512. Trained-minus-random was +8.40 percentage points (nominal cluster
bootstrap 95% interval [+2.93,+14.06]); trained-minus-initial was +5.08 points
([-1.56,+11.33]). The latter is inconclusive. No draws, truncations or native
action rejections occurred in evaluation. A separate consumed 64-cluster
training-distribution probe completed 768 more games.

There was no complete-team/joint-moveset overlap with audited consumed banks
or V8 train. Of 1,530 distinct fresh individual sets, 137 also occur in V8
train (12 in the actual 256-team subset). Species overlap is expected. This is
one seed and two heuristic rivals, with two predeclared comparisons and nominal
intervals; it does not establish broad competitive superiority or production
readiness. These panels are now consumed, not sealed.

Learning took 643 seconds across the smoke and continuation, approximately
51 preview episodes/s overall, peaking at 9.42 GiB under the 12 GiB/50% CPU job
limits. Native training action retries totaled 116; three recorded cases were
replayed with matching outcomes and decision/retry counts. Their formerly
request-legal actions caused refreshed public masks. This is not a diagnosis
of all historical retries. Both evaluation panels totaled 2,304 games.
