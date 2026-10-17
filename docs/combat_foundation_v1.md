# Combat foundation v1

The selected source-training contract is `showdown-combat-foundation-v1`.
It retains the public V5 strategic-v3 encoder and 674,939-parameter policy.
Engineering readiness and competitive superiority are separate decisions.
This contract does not install a model into the advisor or start long training.

## Architecture and information boundary

The encoder remains `showdown-public-categorical-observation-v5-integrated-v3`:
28,822 float transport entries, shared categorical embeddings, a stateless
six-turn/tail-64-event GRU16, authenticated own HP, 35 action-conditioned rows,
conditional reference availability, and public-support opponent predictions.
Its feature fingerprint remains the V3 fingerprint. The foundation's optimized
encoder skips the discarded parent prediction transport and preserves every
output bit. Foundation inference uses the existing combined actor/value forward
instead of decoding the same public state twice. There are no additional weights.

`FoundationCombatPolicy` and `FoundationCombatPPO` have explicit checkpoint
identities. A mandatory `combat_foundation` manifest field binds their contract.
Old V4/V5 ZIPs are not relabeled. Explicit weight transfer accepts categorical
V4 or compatible V5-v3 and creates fresh Adam; same-foundation resume restores
Adam. Scratch initialization remains available without loading a teacher.

Only a player's observation enters actor, critic and prediction forwards.
Native masks retain all 35 meanings, including wait and Mega X/Y. Hidden current
ability/item/move targets remain in the separate coordinator loss channel, bound
to the outgoing predecision active. Cancelled, called and unobserved move choices
do not become private-intent labels. Public support never expands from a target.
Unknown facts, Illusion ambiguity and unsupported reference effects stay explicit.

The retained reference ranges are conditional single-hit hypotheses, not bounds
on actual damage or KO probabilities. The inherited historical summary is not a
complete mechanics state; corrected public boosts drive the separate references.
No search branch rankings, privately sampled sets or damage ranges are labels.

## Learning and numerical contract

- Native sparse terminal reward: win +1, loss -1, draw/nonterminal 0.
- Gamma 1, GAE .95, rollout 128 per worker, minibatch 128, four epochs.
- Adam at constant 5e-5; PPO clipping .2, value coefficient .5, target KL .03.
- Entropy .01; legal-uniform reverse KL coefficient .001.
- V3 auxiliary coefficient .02: proper CE and unknown-cell move BCE.
- Prediction residuals remain bounded to +/-2 logits over TRAIN-only priors.
- PPO stops gradients at predicted distributions; auxiliary loss stops at the
  reused public trunk. Prediction weights may subsequently change decisions.
- Every participating gradient is checked before clipping; a nonfinite norm or
  invalid clipped norm fails before Adam steps. Max global norm is .5.
- Parameters and Adam state are checked after training, in addition to the
  maintained rollout/return/advantage and trainer finite-state guards.

Maintained `sb3-contrib==2.7.1` owns PPO, GAE, clipping, KL early stopping and
time-limit bootstrapping. The foundation does not copy or replace that algorithm.
True native termination stays distinct from public-continuation truncation.
Raw gradient norm, clipped norm, clipping frequency, update count, true action
entropy, KL, losses, explained-variance availability and action concentration
are observable. Constant-return explained variance is explicitly undefined.

## Persistence and sampling

The existing immutable model/manifest checkpoint and verified ZIP hash remain
the restart boundary. Trainer state publishes a checkpoint only after loading it
and checking inference. Incomplete writes cannot replace the previous published
checkpoint. Same-version model/Adam restoration is tested tensor for tensor.
STOP discards partial rollout/auxiliary alignment and resets native episodes.
It does not promise exact interrupted action/RNG replay or power-loss fsync.

Team-bank/subset hashes, frozen opponent ZIP hashes, native seeds, ordered
three-of-six selection and episode cursors bind sampling. Resume uses a declared
new scenario namespace from seed, trained progress and launch count. Opponent
mixture slots are cyclic by episode index, not IID or decision-balanced.
Frozen snapshots enter only between declared training windows.

The selected initialization is a function-preserving transfer from categorical
V4 `acb98005c664bd9f272d9a35871b0a60d618af37b64213da44960c4ad884aa2a`,
with fresh Adam and new actor/value input columns zero. This avoids selecting a
V5 winner from inconclusive short comparisons. It does not establish pretrained
superiority over scratch. Folder names such as `catalog_bindings/v4` are not
encoder identities; the manifest, policy type and hash are authoritative.

## Resource and performance contract

The selected long-training configuration uses four Subproc workers, one Torch
thread, CPU only, an aggregate 12 GiB Windows Job and a 50% CPU ceiling. Eight
workers remain a measured diagnostic, with materially less memory headroom.
No external training network calls are allowed. CUDA was unavailable in the
verified CPU runtime and was not used or assumed faster.

Profiles separate learner actor/value forward, public encoding, public observation
copies, native bridge waits, native-step-plus-opponent cost, PPO update and
auxiliary forward. Worker totals overlap in parallel; native bridge time includes
IPC/serialization and simulation and is not pure engine CPU. Auxiliary backward
is included in the joint update and is not separately attributed.

## Reproduce bounded readiness

Use the verified Python 3.11 runtime containing the pinned learning dependencies.
Keep all outputs outside the repository. A reference config supplies the verified
native checkout, catalog, subset and frozen opponent paths, not model semantics.

```powershell
$python = 'C:\path\to\verified-runtime\Scripts\python.exe'
$evidence = 'C:\path\to\new-foundation-evidence'
& $python scripts/verify_combat_foundation.py prepare --reference-config C:\path\reference.json --pretrained-model C:\path\categorical-v4\model.zip --pretrained-id acb98005c664bd9f272d9a35871b0a60d618af37b64213da44960c4ad884aa2a --output $evidence
& $python scripts/verify_combat_foundation.py smoke --output $evidence
& $python scripts/verify_combat_foundation.py assess --output $evidence
```

Preparation performs no learning. Smoke collects only 4,096 transitions, stops at
2,048 and resumes. Assessment consumes a hash-frozen panel once: 16 fresh case
identities from existing held-out/rare team pools, both seats and four rivals.
They are not species-unseen teams or a new strength benchmark. An interrupted
consumption remains marked; it is not silently reused for architecture selection.
`--initialization scratch` prepares the alternative with no pretrained arguments.

`long_training_stage1_NOT_STARTED.json` is a frozen, executable proposal with
1,048,576 transitions and a six-hour per-launch ceiling. It is generated only;
the readiness script never executes it. T1 must authorize the campaign separately.

## Research and reuse decisions

[Jaxcalibur](https://jaxcalibur.github.io/) supports investigating compact public
history, predictions and PPO exploration. Its author describes a JAX engine and
search; no reusable code/weight license was established from the write-up. Its
reported random-singles results are not evidence for M-C. No engine or search is
imported.

[ai-vgc](https://github.com/Nisanth-Nimashakavi/Ai-vgc) and its
[model implementation](https://github.com/Nisanth-Nimashakavi/Ai-vgc/blob/main/src/ai_vgc/nn/model.py)
illustrate move-conditioned scoring and zero-initialized additions. The public
repository was active in October 2026 but had no verified root license. Its
doubles/autoregressive action and team-sheet assumptions are incompatible here;
code and weights are not copied.

[VGC-Bench](https://github.com/cameronangliss/vgc-bench) has an
[MIT license](https://github.com/cameronangliss/vgc-bench/blob/main/LICENSE) and
[research on team generalization](https://arxiv.org/abs/2506.10326).
Frozen opponents, team diversity and independent evaluations are reused as
methodological principles, through PokeAdvice's existing infrastructure.
No doubles framework or dataset is transplanted.

[PPO](https://arxiv.org/abs/1707.06347),
[invalid-action masking](https://arxiv.org/abs/2006.14171) and
[maintained MaskablePPO](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html)
support retaining the existing learning path rather than replacing its arithmetic.
The repository pins and tests the installed 2.7.1 implementation.

## Frozen readiness evidence, 2026-10-17

The owned validation collected 4,096 transitions with a real 2,048-transition
STOP/resume boundary, plus a 2,048-transition resource profile and a 128-transition
probe in a new complete locked CPU runtime. Adam advanced 0 -> 64 -> 128 across
STOP/resume; every combat/prediction parameter group changed. Raw gradients were
finite, the global clipped norm stayed within FP32 tolerance of .5, and injected
NaN gradients stopped before parameters or Adam steps changed.

The frozen final panel completed 128 native games, both seats, zero truncations
and zero native choice rejections. Its 55 wins/73 losses do not establish improved
strength; the 4,096-transition endpoint is diagnostic, not the selected long-run
initialization. The B0 transfer remains the declared starting point.

All 933 test files were assessed under bounded independent pytest groups:
8,175 passed, one skipped, with three failures reproduced on the unchanged
9f2eda8 baseline (two responsive-layout assertions and an uninitialized adapter
mock missing collect_v5_supervision). No new failures or collection errors
remained. The new foundation's five tests also passed separately in the permanent
runtime. Parallel execnet teardown stalled in an earlier attempt; smaller serial
file groups completed without modifying those tests. A 300-second group timeout
was recovered in four smaller groups, all 350 cases passing.

Same-weight inference over 128 two-seat public views had zero probability
difference: CPU p50 10.08 -> 7.12 ms, p95 12.35 -> 8.96 ms. Four-worker warm
rollout/update throughput was 109.50 transitions/s, peak job memory 5.98 GiB;
eight workers reached 139.58/s and 10.75 GiB. The long plan selects four for memory
headroom. The conservative capacity allowance is 0.30-0.38M transitions/hour,
pending actual sustained measurement. No long campaign or promotion ran here.
