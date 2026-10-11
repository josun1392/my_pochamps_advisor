# Initial learned policy/value system — 2026-10-12

COMPLETE for the first bounded learning/inference/evaluation pipeline. This is
not completion of a strong strategy model or authorization to replace production
ranking. No policy/value GPU training, public battles or provider calls occurred.

## Baseline and reuse

Verified clean migration worktree and canonical remote at
`907d259f4948dd72f29ad051902a978a841a2232`, branch
`codex/showdown-mc-integration-v1`, remote
`https://github.com/josun1392/my_pochamps_advisor.git`. Original master remained
`691d2dfab74f0eaed0488dad9735d808be14927b` with its original five changes.
Showdown remains pinned to `942cda71d14bf0618bd57991708a2e2734b6daba`;
native `gen9championsbssregmc` remains legality/mechanics/RNG authority.

| Implementation | Executed evidence | Integration decision |
| --- | --- | --- |
| [SB3-contrib MaskablePPO](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html) 2.7.1 | Original masked toy environment: 256 learning steps, parameter L1 change 8.149; actual checkpoint | Reuse algorithm, rollout buffer, masked distributions, optimizer and serialization unchanged |
| [CleanRL](https://docs.cleanrl.dev/) `fe8d8a03c41a7ef5b523e2e354bd01c363e786bb` | Original `ppo.py`: 512 CartPole transitions, four CPU updates, 2,789–2,936 steps/s | Runnable, but needs mask-aware algorithm edits; not selected |
| [poke-env learning example](https://poke-env.readthedocs.io/en/latest/examples/reinforcement_learning.html) | Original 12-feature embedding and masked actor/critic executed on native protocol; native heuristic decision | Reuse 0.10.0 Battle parser, SimpleHeuristicsPlayer and MaxBasePowerPlayer offline; no Player constructor/client |
| ai-vgc existing source | Doubles/107-action transformer, Python >=3.13/data/version requirements; no license found in inspected checkout | Do not copy or force-fit doubles/human-dataset machinery |

poke-env 0.16.1's newer Gym dependency conflicts with SB3's supported Gym range.
The tested 0.10.0 parser/heuristics are sufficient; fixed 35-action request mapping
remains the existing native interface. No second battle simulator or PPO engine
was implemented. Windows poke-env initialization creates an asyncio loopback
self-pipe; subsequent training/evaluation/test network calls were blocked and
recorded zero attempts. The pipe is not a battle-server connection.

## Observation/model contract

The existing `ShowdownEnvironment` is retained. Its two-sided trusted coordinator
state is never fed to the model. The encoder accepts one
`showdown-policy-observation-v1` view with its own request and publicly revealed
opponent information, retaining Unknown separately from confirmed absence.
It excludes episode/session identities and all seeds, RNG, queues, checkpoints,
unrevealed sets and private rival requests. Hidden-set/seed variations produce
identical features and probabilities when their public views are identical.

`showdown-learned-observation-v1`: 787 float features, public Dex base stats/types,
own legal move features/PP, visible HP/status/stages, public preview and item/ability
revelations, field knowledge, phase and native mask. Static type priors are native
Dex facts, not ability-aware damage or exact outcome evidence. The first flat MLP
does not encode every volatile/revealed-move history or learn recurrent beliefs.

MaskablePPO actor [64,64], critic [64,64], 111,524 parameters; 35 native actions.
CPU Torch 2.8.0, one Torch thread; four independent native workers in DummyVecEnv.
128 rollout steps/environment, batch 128, four PPO epochs, gamma .99, LR 3e-4,
entropy coefficient .02 and target KL .03. Native win/loss/draw rewards +1/-1/0;
budget truncation is distinct from loss. Waiting through rival forced replacement
is handled by the Gym adapter; own switches/pivots remain actual masked decisions.

`showdown-learned-model-v1` binds ZIP SHA256, catalog fingerprint, encoder/action
versions, engine pin and training metadata. Trusted-source compatibility is
checked before SB3 pickle loading. `showdown-learned-inference-v1` provides action
probabilities and uncalibrated discounted return, never exact probabilities.

## Actual learning and bounded corrections

Training uses ten legal species, varied selected teams (six choose three), move
orders, nature/stat spreads/items and random/max-power/heuristic rivals. Species-
disjoint testing uses Blastoise, Gardevoir, Metagross, Sylveon, Salamence, Swampert.
Validation/test use different indexed configurations; no hold-out sets enter updates.

| Stage | Actual learning data | Optimizer steps | Completed native episodes | Wall time |
| --- | ---: | ---: | ---: | ---: |
| PPO seed 17 | 2,048 transitions | 64 | 144 | 6.68 s |
| Continued PPO | 8,192 transitions, cumulative 10,240 | 256 | 588 | 21.56 s |
| Visible heuristic distillation seed 31 | 4,099 complete-episode decisions, 12 epochs | 396 | 462 | 12.00 s |
| Additional PPO candidate (not selected) | 8,192 transitions, cumulative 18,432 | 256 | 712 | 22.43 s |
| Frozen-policy value fitting | 4,099 own-policy decisions, eight epochs | 264 critic updates | 396 | 15.57 s |

All 2,302 training/collection episodes completed without truncation. Total stage
wall time about 78.24 seconds, including collection/loading; setup/research/tests
are separate. Selected artifact includes 10,240 PPO transitions + distillation +
critic fitting. Tested PPO candidate includes extra updates but is not the release.
Final actor optimizer lineage has 716 steps; critic has 980. Real finite parameter
changes, optimizer counters, deterministic repeated 256-step runs and exact saved/
reloaded action/value equality verify learning rather than a scripted policy claim.

On 24 validation cases × three rivals: untrained 11/72, initial PPO 23/72,
continued PPO 25/72, distilled 41/72, extra-PPO candidate 38/72; heuristic 54/72.
Distillation lowered teacher cross entropy 1.364→0.799. The extra PPO improved
critic MSE but reduced validation wins, so it was not selected. Frozen-policy
critic fitting kept every actor parameter identical; training return MSE fell
0.673→0.201 and validation MSE 1.038→0.983. This is modest, not calibration proof.

## Independent evaluation

Release policy/critic were frozen before new case indices 64–127 were evaluated.
Each split contains 64 cases × three rival policies = 192 battles per model.
Each row below reports the same paired team/seed/rival grid. There were zero
draws/truncations in these evaluations.

| Player | New sets W/L | Species-unseen W/L |
| --- | ---: | ---: |
| Untrained checkpoint | 51 / 141 | 36 / 156 |
| Random | 78 / 114 | 33 / 159 |
| Max base power | 74 / 118 | 115 / 77 |
| Upstream heuristic | 146 / 46 | 143 / 49 |
| Released learned model | **94 / 98 (49.0%)** | **105 / 87 (54.7%)** |
| Previous extra-PPO checkpoint | 98 / 94 | 100 / 92 |

Per-stratum Wilson intervals and paired case-cluster bootstrap intervals are
stored in the evaluation artifacts. Descriptive pooled Wilson 95% intervals:
release new sets 42.0–56.0%, unseen species 47.6–61.6%. Paired release-minus-random
differences: +8.3 pp (case-bootstrap 95% -0.5–17.2 pp), +37.5 pp (28.6–46.9 pp).
Release-minus-untrained: +22.4 pp (13.5–31.8), +35.9 pp (27.1–44.3).
Release is substantially weaker than heuristic and unseen max-power. The first
new-set random comparison does not establish a clear superiority interval.

Earlier independently frozen distilled actor also scored 99/192 on test indices
0–63 and 102/192 unseen. Those results remain as initial artifacts; the final
critic used no such episodes for updates. Same actor means identical final vs
pre-critic wins for each individual case; critic-only changes are evaluated on
fresh indices. No retuning or selecting a model on final held-out wins occurred.

Final discounted-return MSE: new sets .942 versus pre-critic .931; unseen .870
versus 1.012. Improvement is mixed. These are episode-average discounted-return
errors, not Brier scores or calibrated win probabilities. A single training seed,
limited curriculum, small validation set, flat fixed-slot model, teacher imitation
and weak critic generalization remain limitations. No broad strategic strength is
claimed. Evaluation frequencies/intervals are statistical evidence, not exact odds.

## Experimental PokeAdvice integration and compatibility

Explicit nested `showdown-learned-config-v1` with `enabled: true` and expected
model SHA enables inference beside existing native v2 shadow evidence. One native
root is projected into one own-side view before rival hypothetical actions execute.
`showdown-learned-strategy-v1` binds session/runtime/capture/decision/context,
scenario, checkpoint, action/phase and model identities. Stale/contradictory proof,
masked probability mass, wrong phases, nonfinite values and incompatible models
fail closed. Missing learning dependencies/model preserve native samples and exact
recommendations. Two trusted CPU models are cached; no per-turn reload or training
occurs inside UI inference.

The existing Qt background path and explanation panel render policy-choice
probability (explicitly **not win rate**) and uncalibrated discounted return.
The UI smoke fixture keeps legacy decision deferral and shows hypothetical Air
Slash; unknown item hypotheses give identical policy distributions, as intended.
Legacy exact ledger, orchestration, guaranteed-first frontier, observation/reducer,
session and replay responsibilities remain unchanged. Legacy is not a complete
episode policy, so direct legacy battle win-rate comparisons would be misleading.

Minor correctness fixes: public Mega forme/detail updates now reach policy views;
missing/null private item or ability fields preserve Unknown rather than invent
known absence. These affect only the native projection, not recorded reducer truth.
Upstream random fallback state is locked/restored for parallel baseline safety;
constructor failures close native resources; learning budgets/output overwrites
and incomplete-episode collection are bounded.

## Validation, performance and next work

Focused tests cover actual updates/reload/reproducibility, hidden-input invariance,
Unknown/absence, native legality, forced replacement, pivot/queued actions,
terminal/truncation, checkpoint continuity, disabled imports, model failures,
evidence contradictions, existing ranking equality and Qt rollback. The broad
offline checkpoint and final focused results are recorded in `training_summary.json`.
Broad checkpoint: **7,846 passed / two known baseline Qt desktop-layout failures**
in 623.83 seconds, zero network attempts across parent/four workers. Final related
native/Gym/strategy/UI checkpoint: **109 passed** in 46.67 seconds. After final
schema/formatting/expected-hash checks: **40 passed** in 10.30 seconds. Without the
learning extra: **two fallback tests passed** in 1.73 seconds. Both desktop-layout
failure IDs match the preceding simulator baseline; there were no new failures.

The readiness artifact records actual Qt analysis and native battles, inference
latency, worker RSS, phase/status/ability/item/Mega events, save/read immutability
and rollback equality. Model ZIP is about 1.34 MiB; public catalog .67 MiB. Initial
measurement: 1,000 inference calls p50 .45 ms, p95 .86 ms; worker peak RSS 140 MiB;
CPU model load about 1.47 s. Final artifact is rechecked after release installation.

Final release recheck: 12 complete native battles (8 W / 4 L), 164 native decisions,
123 attacks, 19 own forced replacements, 22 waiting decisions, three public status
applications and ten Mega events. Inference p50 **.459 ms**, p95 **.753 ms**;
1,000 calls used .516 Python CPU seconds. Model load 1.392 s; actual Qt dispatch
105 ms and end-to-end native/learned display 1.014 s. Peak Node RSS 140.2 MiB;
Python peak 552.3 MiB includes Torch, poke-env and Qt. Rechecking default rollback
preserved the exact displayed text, runtime snapshot and empty observation ledger.
The smoke sample is a functional check, not additional strength evidence. Total
evaluation runs exercised **7,176** native episodes; final held-out grids account
for 2,688 of them (seven policies × 192 episodes × two splits).

Use the artifact README for local training/evaluation/manual UI smoke commands.
Next: action-conditioned/permutation-aware features, recurrent public history,
stronger opponent mixtures, critic calibration and multiple training seeds, then
fresh independent evaluation. Prefer that bounded architecture/evaluation work
before large training. Larger compute, changing production ranking, or calibrated
win-rate use requires a separate T1 decision. Initial learning infrastructure is
ready; the model is not ready to replace guaranteed-first recommendations.
