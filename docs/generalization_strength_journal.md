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

23:38–23:42 UTC: broader native audit exposed a real observation defect:
Scizor Swords Dance followed by Toxapex Haze left projected attack +2 despite
native `-clearallboost`. Executable regression failed before the fix. Public
boost-reset projection corrected; poke-env independently confirms the native
reset. No reducer, persisted event or live truth modifications. Shared native
boundary checkpoint: 124 passed, zero external connections.

Pilot stopped gracefully, artifacts retained but disqualified for selection:
43660 collected / 43520 PPO-trained transitions, 16384 teacher decisions, 5865
ended battles, 296.39 s, zero truncations/network attempts; peak process-tree
commit 2268553216 bytes. No final holdout inspected.

Pilot cold models fit teacher actions (v3 93.31%) but validation remained weak.
Added a narrow weight-transfer adapter: frozen v2 function embedded in v3 with
zero initial weights on added public features, fresh Adam moments. It reuses
upstream PPO and preserves tested legal distributions/value within float32
tolerance; no optimizer recovery is claimed across changed tensor shapes.

Revised clean run: cold v2/v3 seed101 (32768 PPO each), plus transferred v3
seeds101/211/307 (16384 each), 8192 teacher decisions each. Independent rollout/
demonstration/minibatch seeds share a declared frozen pretrained source. Seed307
uses the experimental tactical teacher; this factor is not causally isolated.
All candidates use corrected projection, new output `training_verified`.

Commits pushed: `11e0940` (broad curriculum/input) and `b79da4e` (Haze and
function-preserving transfer). Later targeted lifecycle/evaluation checks: 3
passed. Historical opponent now freezes a new budget's initial checkpoint where
available; optimizer-initialization metadata distinguishes restoration/transfer.

00:03 UTC verified experiment bundle completed in 791.66 s: 114688 actual PPO
transitions, 40960 teacher decisions, 15131 battles, no truncations. Peak commit
3075407872 bytes (below 3 GiB), tree CPU 868.30 s, external network attempts 0.
Validation wins/96: cold v2 39→43→38; cold v3 37→38→40; transferred v3 seed101
38→49, seed211 40→38, seed307 38→36. Warm-only checkpoints retained for seeds
211/307; their extra PPO regressed validation. No claim of isolated teacher gain.

Bounded continuation seed401 restored seed101 optimizer and trained against a
frozen version of that checkpoint plus original v2 and public baselines. 49152
new PPO transitions / 4858 battles in approximately 242 s. Validation 49→49→46→49
triggered plateau stopping; original 49-win source preserved. No final tuning.

Final selection locked BEFORE reading new test/unseen results: original seed101
v3 16384-PPO checkpoint (plus 8192 teacher decisions). Fresh v3 curriculum,
offset90000, 96 case clusters × 4 fixed rivals, test and disjoint unseen.
Predeclared primary comparisons: selected vs frozen v2 and maintained heuristic.
Other seeds, cold models, v1, random and adapted heuristic are diagnostics only;
final results will not select another model. All training processes completed.

00:13–00:18 UTC final evaluation completed: 7680/7680 battles terminated,
zero draws/truncations/external attempts. Selected vs original v2: test +6.0pp
CI[0,11.7], unseen -0.8pp CI[-3.9,2.6]. Heuristic superiority not established.
v1 improvement supported; native public tactical heuristic has modest independent
gain. No model reselection/tuning after seeing final results. Switching remains
a material learned-behavior weakness (selected 2/10 voluntary switches vs v2
30/80). Full evidence packaged in models/showdown_generalization_v3.

Final relevant regression checkpoint: 250 passed, offline guard attempts0.
Actual Qt inference/rollback proof passed, p50/p95 1.509/2.022ms; UI931ms.
Selected artifact fe52cd3b4e288c242176a6574769bdf1cd8fb5dbedad8b015496cb5b5dcfd57d,
16384 new PPO +8192 teacher decisions, 142338 parameters.
Active computations finished; next action: artifact reload check, exact stage,
commit/push, verify canonical remote and original master, Korean final report.

00:26:33 UTC packaged artifact reload/inference passed, legal native choice,
checkpoint unchanged, external attempts0. All three trainer control PIDs are
dead; final evaluation and Qt verification exec sessions finished successfully.
Result: PARTIAL strategic-strength objective; engineering/learning/evaluation
completed. Published artifacts are experimental, original v2 remains unchanged.

00:29:32 UTC final verification: migration worktree clean; local and canonical
remote both `cd533a504f88101dfe37aa289a82e358a58a6943`. Three validated milestones
`11e0940`, `b79da4e`, `cd533a5` pushed. Original master still
`691d2dfab74f0eaed0488dad9735d808be14927b`, same five pre-existing changes.
No running training/evaluation workers. Measured elapsed 72min01s from mission
start through final verification; this closing journal commit follows.
