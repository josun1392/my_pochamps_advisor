# Generalization and strength V1

Started 2026-10-11 23:17:31 UTC. Baseline local/remote
`1df1ac79925aaa37ba194159de03eb6f9887b40c`, migration branch clean.
Original master and its five pre-existing changes preserved.

Current milestone: broaden native-validated curriculum and public tactical input;
retain v1/v2 artifacts, default guaranteed-first policy and offline trainer.

Plan: legality/provenance tests → bounded independent CPU pilots → validation
checkpoint selection → once-only fresh held-out paired evaluation → regressions.
Current authorization excludes multi-hour training. Planned individual trainer
budget at most 30 minutes, one Torch thread, four native workers, 12.5% CPU and
3 GiB process-tree commit. No claimed detached survival under Codex host job.

Previously inspected v2 test offsets 20000/30000 are not tuning targets. New
curriculum namespace v3, validation offset 11000, final offset 90000. Final
results must not be used to tune or select among experiments.

Known baseline UI failures: two smaller-desktop layout assertions.

23:31 UTC: 54 species (40 training, 14 disjoint unseen), 822 native team
validations passed. Corrected unavailable species and illegal M-C moves rather
than accepting mainline learnsets. Native Dex tactic metadata and versioned
7411-dimensional v3 input implemented; masked shared actor architecture reused.
Initial focused tests 60 passed; added v3 update/reload/UI tests 9 passed.

Public-tactics pilot: 16 validation case clusters × 4 rivals × 4 players = 256
battles, zero truncations. Heuristic 47/64, adapted heuristic 46/64, frozen v2
46/64, v1 42/64. Adaptation is not proven stronger (paired heuristic difference
-1.56 pp, CI [-4.69, 0]). Retained as diversity opponent; matched seed-101
architecture comparison uses the original maintained heuristic teacher.
Seeds 211/307 compare the tactical teacher as an exploratory alternative, not a
causal isolated teacher comparison. No final-test results inspected.

23:33 UTC focused boundary checkpoint: 84 tests passed, explicit offline socket
guard recorded zero external connection attempts. Native hidden-set/seed
isolation, v3 optimizer updates/reload, UI evidence acceptance, exact-ledger and
preferred-frontier rollback equality passed. Original master untouched.

Next: focused compatibility checkpoint, commit, four bounded experiments
(v2 seed101; v3 seeds101/211/307), each 8192 teacher decisions + 32768 PPO steps.
Program-managed validation 24 clusters/4 rivals; no test-set-based tuning.
