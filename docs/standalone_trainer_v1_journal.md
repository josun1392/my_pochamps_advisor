# Standalone trainer V1 progress

Mission started 2026-10-12 11:04:16 UTC. Baseline local/remote
`9654d41c68dd534eaf7f2dc79cecf06031bbd848`, canonical migration branch.
Master's five pre-existing changes are outside this worktree and untouched.

Implemented separate lightweight Qt GUI, detached Windows owned worker, existing
trainer progress callback, optional public-action telemetry, validation-only
selection, and external-data onedir builder. Default: eight CPU workers, four
tensor threads, 50% process-tree CPU cap, 12 GiB aggregate memory, two-hour budget.
No production recommendation/model replacement, no learning algorithm changes.

Packaging V1/V2 build issues repaired: installed Node notice absent (ship pinned
notice); PyInstaller requires `--copy-metadata`. V3 exposed incompatible Poppler
ICU from ambient Codex PATH and missing SB3 `version.txt`. V4 restricts the build
PATH to verified toolchains/system and collects SB3 package data.

Independent lifetime test: direct PowerShell ShellExecute inherited Codex job and
correctly failed closed. Dispatch through an actual Explorer browser's COM
Document.Application produced GUI parent Explorer and worker `inherited_job=false`,
own kill-on-close job. Actual learning/lifetime/STOP/resume tests follow on V4.
No unattended campaign is running. Task-owned outputs are under
`C:\Users\jsp33\.codex\artifacts\pokeadvice-ai-trainer-build-v*` and
`trainer-desktop-qa-v*`, outside the repository.

Pre-V4 focused regression: 31 passed; desktop contracts: 5 passed. No learning
success is claimed until packaged real PPO/evaluation/weights tests pass.

Next: build V4, real Explorer-launched packaged training, GUI-close continuity,
STOP/reopen/resume/validation, crash recovery, regression checkpoint, documentation,
exact-stage source commit and canonical push. No mission commit yet.

11:53 UTC checkpoint: V4 packaged learning verified (after a reproducible packaging
post-step creates empty `.git/refs`, which PyInstaller omits). Portable native Git
checks use `GIT_OPTIONAL_LOCKS=0` so they do not change the hashed index. Builder V5
includes both corrections and post-build portable Git checks.

QA V5 root (distribution V4): seed53053, eight real native workers, 4096 trained PPO
transitions, 337 completed training battles, five fixed validation passes (8 each),
zero truncated validation samples. First optimizer chunk: 32 optimizer updates,
parameter L1 change52.7633. GUI closed at2048, independent worker completed4096
afterward. Peak aggregate RAM10,209,820,672bytes; CPU tree128.7seconds; main trainer
wall35.26seconds. Original initial checkpoint remained validation-best; no strategic
improvement claim from this packaging test.

QA V6: seed53059, actual GUI STOP at1024; 81 completed training battles and complete
checkpoint saved, native tree cleaned up. Reopened GUI/resume advanced beyond5120
with model and optimizer restoration; final result/manual evaluation pending.

Tests: 37 focused desktop/core/parallel/full-roster passed, 122 additional
model/public-observation/native/Qt live-app regressions passed; offline guards report
zero external-network attempts and no leftover native workers. V5 build adds
collapsible training controls, readable table columns, saved PPO diagnostic tab,
clear missing-runtime errors and startup diagnostics. Packaging outputs remain
external, source/models protected.

12:03 UTC checkpoint: final-source V7 bundle is building. V5 release QA used fresh
initialization and8 workers. Injected forced exit only after verifying owned EXE
path/PID and a complete1024-transition checkpoint. GUI was already gone. All27
owned trainer/Node/console processes exited; independent second enumeration
confirmed zero survivors. Reopened GUI recovered optimizer/model and completed6144
trained transitions /356 recorded training battles, best validation5/8 (not strategic
superiority; tiny packaging sample), peak10,281,922,560bytes. Validation-best/current
are independently recorded. Manual best-model validation completed successfully.

V6 STOP/resume case completed5120 /423 training battles; validation reevaluation
completed8 battles, zero blocked external-network attempts. Missing-runtime V5
test correctly failed with a clear native-checkout error. Source regression now
includes seven desktop tests (manual wrong domain/encoder rejection, RAM floor,
single-run ownership, telemetry, export and responsive Qt button).

Final-source changes: no-console Node/Git subprocesses restricted to separate app,
strict desktop V7/V8 + V3 contracts, historical model preflight, pre-import resource
validation. Final V7 is a packaging iteration, not a new learned policy version.
Next: packaged fresh species-disjoint STOP/resume test on final V7, resource/child
cleanup check, exact evidence summary, source-only commit and canonical push.

## Verified release closure

Final distribution V7:954,021,953bytes, build196.52seconds, peak1.57GiB,
CPU139.73seconds. EXE SHA256:
`9ef25d1f8ee851c218fa2cb8482198a74ec65ec64daf3c67f9ba4e7bd4d1fcd6`.
Portable native revision/tracked cleanliness and system-ICU packaging checks pass.
Desktop shortcut:
`C:\Users\jsp33\OneDrive\Desktop\PokeAdvice AI Trainer.lnk`.
Exe/output path and normal usage are in `standalone_trainer_v1.md`.

Final packaged fresh V7 species-disjoint study, seed53081: actual GUI Start,
STOP1024, reopen/resume5120,303 completed training battles, six saved checkpoints,
48 completed validation battles including manual best reevaluation. All four rivals
use fixed validation identities; no final test runs. Fresh policy remains weak
(best0/8); plateau stopped training and preserved its earlier tied best checkpoint.
This is a packaging/learning/recovery test, not evidence of strategic superiority.
Parameter L1 changes were positive for every PPO checkpoint, minimum56.3535;
optimizer state continued after resume. Real best ZIP/manifest/report export works.
Independent launch ownership remained `inherited_job=false`; GUI ticks continued
while training; all recorded worker/Node descendants exited. No process belonging
to any of the trainer build directories remains running at closure.

All successful packaging QA runs combined (persisted complete checkpoint counts):
20,480 PPO transitions,1,419 completed training battles,192 validation battles.
Interrupted unsaved rollout activity is excluded, not fabricated as recovered.
Peak aggregate job RAM10,311,585,792bytes (9.60GiB), CPU cap50%, GPU allocation0.
Verified trainer run sections17–35seconds per launch, excluding cold boot/import
preparation (first launch can take about a minute). GUI remained responsive during
preparation. Automatic checkpoints, plateau, initial-best retention, save/load,
manual validation, STOP/resume and injected-crash recovery all exercised.

Final tests:38 focused desktop/core/parallel/full-roster passed (42.85s),122 broader
model/observation/native/live-Qt regressions passed (58.77s). Ruff and task-code diff
whitespace checks pass. The verbatim upstream Node notice retains its original
space-before-tab on line354; it is deliberately not edited. Offline guards:zero
external attempts, no leftover native workers.
No known baseline UI failures were encountered by this selected regression set;
full unrelated suite was not run. Protected master five-file inventory is unchanged.
Original model artifacts and guaranteed-first live recommendation code are unchanged.

Limitations: local unsigned onedir, no clean-VM or multi-hour endurance test,
CPU-only verified distribution, per-registry rather than machine-wide multi-user
scheduling, strict version-matched resume, interrupted native rollouts restart.
There is no blocker to user-launched bounded CPU training on this verified PC.
No global learned policy promotion is authorized or performed.

Mission started11:04:16 UTC; engineering/packaging/testing closure around12:15 UTC,
about71minutes wall-clock including local builds and automated learning. Source-only
commit/push verification follows; no generated binaries or old artifacts are staged.
