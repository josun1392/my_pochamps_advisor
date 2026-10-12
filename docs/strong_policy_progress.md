# Stronger general policy learning: durable progress

- Started: 2026-10-12 05:27:14 UTC (14:27:14 KST).
- Verified migration local/canonical remote: `990273ac4b72f492da97ce5f6a0d4f752ca68d59`; clean branch `codex/showdown-mc-integration-v1`.
- Original master `691d2df` retains the same five pre-existing changes. Protected files are not read or edited.
- Current milestone: native curriculum reuse and narrow public-trajectory offline learning contract.
- Running pilot: external `PokeAdvice/training/strong_policy_2026-10-12/pilot`, program-managed 9 experiments (PPO/BC/AWR x independent seeds2393/2477/2591), each32768newPPO transitions. Existing dedicated CPU limits:8spawn workers,4parent tensor threads, CPU50%, RAM12GiB, total1800s runtime.

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
