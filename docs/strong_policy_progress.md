# Stronger general policy learning: durable progress

- Started: 2026-10-12 05:27:14 UTC (14:27:14 KST).
- Verified migration local/canonical remote: `990273ac4b72f492da97ce5f6a0d4f752ca68d59`; clean branch `codex/showdown-mc-integration-v1`.
- Original master `691d2df` retains the same five pre-existing changes. Protected files are not read or edited.
- Current milestone: native curriculum reuse and narrow public-trajectory offline learning contract.
- Pilot completed: external `PokeAdvice/training/strong_policy_2026-10-12/pilot`,9experiments (PPO/BC/AWR x independent seeds2393/2477/2591), each32768newPPO transitions. Current bounded extension: `extension_plan.json` / `extension`, only the3PPOseeds,98304additional transitions each, restored Adam. Dedicated limits8spawn/4tensor threads/CPU50%/RAM12GiB/1200s total.

## Decisions and verified evidence

- Reuse the pinned Showdown `RandomChampionsTeams`, not a custom species/moveset generator. Native executable pilot: 100 complete teams, 5 legal and 95 rejected solely by Item Clause. Reject/retry complete native teams; do not override legality or implement battle mechanics.
- Preserve the existing 20-species unseen pool. Additional unseen species will be reserved before training. Native generated sets are varied legal coverage fixtures, not real ladder usage or expert optimal teams.
- Compare dedicated parallel PPO control with offline mixed-policy BC and terminal-return advantage-weighted regression followed by the same PPO budget. Retain current action-conditioned encoder/policy and maintained MaskablePPO optimizer/checkpoint machinery.
- Collect only each acting player's partial observation, native legal mask, actually executed action, and subsequent observed terminal reward. No native snapshot, unrevealed opponent set, future seed or hindsight optimal-action label enters learning data.
- Use complete episodes and discounted terminal returns; discard truncated/incomplete episodes. No action-category bonuses. Return weighting is an empirical learning objective, not exact action probabilities or optimal labels.
- Metamon/AMAGO whole-stack import is incompatible with the existing Gym/poke-env contracts and is far beyond this CPU budget. Reuse its diverse synthetic-data/return-weighted learning idea, not OU policy weights or replay backfilling. AWR reference requires TensorFlow 1; adapt its small weighted log-likelihood formula to the existing maintained masked PyTorch policy. RLlib MARWIL provides a maintained comparison but adding its whole runtime is unnecessary. d3rlpy discrete bootstrap lacks this environment's native per-state action masks without additional integration.

## Experiment separation

- Existing final offsets (90000, 180000, 280000, 20000, 30000, 680000) are excluded from selection and new final claims.
- New validation: offset 44000. New final: offset 880000, locked now, opened only after selection. Native curriculum uses separately generated train/validation/test/unseen banks.
- Multiple learning seeds and frozen SHA-bound opponents; matched control budgets. Stop or revise if validation deteriorates; preserve v2/v3/v4/general control artifacts.

## Next concrete actions

1. Build and validate native generated curriculum banks and preservation tests.
2. Implement a versioned encoded public-trajectory dataset and narrow masked BC/AWR adapter; integrate opt-in with autonomous trainer.
3. Focused native/isolation/recovery tests, small pilots, then justified bounded multi-seed learning.
4. Independent paired final evaluation, negative results, resource evidence, regressions, exact staging and canonical push.

## Completed engineering checkpoint

- Native bank:2048train/256validation/512test/512unseen complete6-member teams;231available basic species,191train and40unseen (old20plus fresh20).92,179generation attempts recorded exactly in manifest; native validator accepts only legal teams. Build70.27s/treeCPU71.77s/peak344MiB. Compact immutable bank447kB.
- Actual blocker fixed: poke-env0.10 lacks `Malamar-Mega` and other new Champions forms. Private public-Dex overlay fixes parsing without mutating shared Gen9metadata.64battle smoke passed after fix.
- Collected32768retained public decisions,3352complete battles (1644W/1708L),32800executed transitions,32incomplete rows discarded,0truncations. Seven actual behavior policies including frozen v2/v3/v4/generalcontrol. Collection80.98s/~405decisions/s, treeCPU278.91s, peak9.53GB under12GiB cap. External memory-mapped dataset remains outside Git; manifestSHA `ba780bb7b8887a359f640980ae43a1938b7ecf14d0eb6603a3f3968f728631a8`.
-41focused native/learning tests passed (45.32s), external network attempts0. Exact split offline-epoch save/reload matches uninterrupted parameters bit-for-bit; hash/mask/version failures reject input.
- Fresh final880000 remains unopened. Next: finish pilot, balanced secondary validation at a fresh validation offset, extend only justified configurations, then lock final evaluation.

## 2026-10-12 06:18 UTC checkpoint

- Engineering commit `4ff302b` pushed to the verified canonical migration branch. Master remains unchanged.
- Pilot completed294912newPPO transitions and30550terminal battles (14834W/15716L),51automatic validation checkpoints.791.25s wall,4275.16s treeCPU,peak9.997GBcommitted RAM,GPU0,external attempts0. Six offline fits each8epochs x32768rows; actual new Adam/PPO updates tracked in checkpoints.
- Native537related offline regressions passed in178.38s; no external calls. Separate real stop/resume proof: persisted offline epoch4 -> restored epoch8 ->128nativePPO transitions; completed successfully. Bit-for-bit epoch restart unit proof also passed.
- Balanced secondary validation completed: fresh53000,48native+48coherent+24tactical cases,6fixed opponents,17policies =12240native battles. PPO2477native158/288 vscontrol139,coherent156/288 vs159,tactical104/144 vs105. PPO2591native156/288,coherent154/288,tactical106/144. BC/AWR broadly weaker; no extra compute allocated to them.
- The modest, repeated native PPO gains with small older-scope losses justify one controlled extension; retain all earlier best checkpoints. No unrestricted/1M run or new encoder is introduced.
- Additional upstream reuse feasibility: native Gen9 BSS factory100teams (hypothetical M-C point allocations) only1legal; unavailable items, IV requirements, Tera Blast and learnsets reject99. Do not silently import OU/BSS experts into M-C; keep Champions generator authority. POC is research-only, not training data.
- Next concrete actions: finish extension, evaluate3new candidates on the same secondary validation scopes, select once, lock the fresh880000 final plan, compare all retained baselines with uncertainty, preserve artifacts/tests/resources, final canonical push.

## 2026-10-12 06:36 UTC final evaluation lock

- Extension completed294912additionalPPO transitions/30777terminal battles in488.61s; treeCPU3094.45s,peak9.934GBcommitted,GPU0,network0. Total primary learning589824PPO transitions,3independent seeds,12bounded experiments; earlier best models preserved.
- Selected checkpoints by equal-weight mean of native/coherent/tactical validation:2393at65536native new transitions,2477at98304,2591at32768. Best validation candidate2477. Its secondary results158/288native,165/288coherent,103/144tactical; control139/288,159/288,105/144. Do not equate this selection with independent strength proof.
- Final plans and choices are immutable files in external run root: `final_lock.json`, `final_plan.json`, `fresh_final_plan.json`, `matched_final_plan.json`. Offset880000;96cases/scope,6SHA-bound/reference rivals. Matched-budget final separately compares all9pilot end checkpoints at32768PPO transitions each. No further training or selection after final results.
- Important exposure correction: the40species excluded from current v6training contain3seen in earlier55species pretraining (Dragonite/Excadrill/Skarmory). Label this scope current-training-disjoint, not globally unseen. Fresh17species exclude all known prior training pools and old inspected unseen species; a separate native generated bank is final-only and rejects training/validation use.
- Fresh17native bank512unseen teams built7.01s/7.70s treeCPU/182MiB peak;10,327totalnative generation attempts. Existing v6bank, models and observations remain unchanged. Native execution remains authoritative; poke-env emits `MEGA_SOL` unknown-public-effect warnings in this scope, an opponent/feature limitation rather than a native battle failure. Do not change opponents during locked evaluation.
- Final evaluators run independently with each12.5%CPU/4GiB caps and hard900–1500s runtimes. All training jobs have exited. Next: summarize full paired evidence, tactical diagnostic on validation only, actual UI inference smoke, preserve selected/negative artifacts, final regressions and push.

## Final engineering/evaluation checkpoint

- Final39744native battles all terminal (19807W/19937L),0draw/0truncation. No training/selection after final. Selected2477: native300/576,current-disjoint40species314/576,strictfresh17species328/576,coherent327/576. General control283/313/320/322 respectively. Every candidate−control95%paired interval includes0; current40species−v4 +5.38pp [1.74,9.20] is scope-specific evidence.
- Equal32768PPO-budget3seed comparisons show BC/AWR no reliable superiority with seed+case bootstrap. Keep negative experiment artifacts and all old policies.2393coherent280/576is a regression;2591retains its earlier checkpoint. No new named model version or default promotion.
-32validation snapshot states/96native branches: setup-interest states model attacked15/15 (10wins) versus teacher setup7wins; switch8/11vs6/11;recovery3/6vs4/6. Fixed continuations, never optimal labels or training targets.
- Actual PokeAdvice explanation path loaded selected model `c7f120d7ff5f14c127e030affb1887412c55012eea818dd40b6d98e1242df151`; exact/default recommendation and source truth identical. Packaged checkpoint reload reproduces native choices/outcomes on a locked2case verification subset. Public-effect warning summarization changes logging only.
-537broad related tests +33fresh-bank related tests passed; ruff and diff checks pass. Native rollback, real epoch stop/resume and exact split-epoch tests preserved. Four previous model hashes unchanged. All owned training/evaluation sessions exited; no unmanaged learning remains.
- Training programs21m20s wall including automatic validation; treeCPU7369.61s; peak9.31GiB committedRAM; GPU0. Final evaluators ran concurrently (901.19/290.14/319.40s). Overall elapsed is recorded at the final Git verification; engineering/compute overlap is not falsely subtracted.
- Evidence and selected/rejected models: `models/showdown_strong_policy_experiment`; external1GiBsource data/allcheckpoints: local `PokeAdvice/training/strong_policy_2026-10-12`. Report: `docs/strong_policy_result.md`. Next research should improve M-Cpublic data/long-term value or memory before blind1M+PPO expansion. No fundamental T1 decision needed for completed work; production policy change remains separate.
