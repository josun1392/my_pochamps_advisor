# PokeAdvice AI Trainer — standalone Windows V1

Separate application: **PokeAdvice AI Trainer.exe**. It uses the existing native
Showdown/M-C curriculum, public observation encoder, action masks, MaskablePPO,
parallel workers and evaluation code. It does not modify the live PokeAdvice UI,
production model, guaranteed-first ranking, observation truth or historical replay.

## User workflow

1. Open the distribution directory in Windows Explorer and double-click
   `PokeAdvice AI Trainer.exe`. Keep the entire `_internal` directory beside it.
   No terminal, Python, Node, Git, Codex session or provider account is required.
2. Choose full M-C (V8, team/set-based validation) or species-disjoint V7. Fresh
   initialization is available; compatible full-catalog bound PPO2477/v4/control/v3
   checkpoints are bundled. Historical warm starts can have prior species exposure:
   selecting V7 alone does not make an old model species-unseen.
3. Choose budget, seed, checkpoint/evaluation frequency and CPU preset, then click
   **학습 시작**. Default dedicated preset: eight independent native workers,
   four tensor threads, 50% aggregate CPU cap, 12 GiB aggregate process-tree RAM,
   262,144 new PPO transitions, maximum two hours. Interactive preset reduces
   workers/tensor threads/CPU/RAM to 2/1/25%/4 GiB. GPU is deliberately absent from
   this verified CPU distribution.
4. Monitor progress, completed battles, checkpoint validation, per-opponent sample
   wins and Wilson intervals, peak aggregate RAM and process-tree CPU time. The
   coverage tab distinguishes sampled sets from executed public tactical actions.
   Coverage is telemetry, never an input feature or reward.
   The existing `*_species` coverage keys count native roster identity strings
   including forms, not collapsed base species; counts can exceed231. Item counts
   can include the no-item sentinel. These are sampled configurations, not proof
   that every transformation/move was executed or that teams are competitive.
   Configuration can collapse to give the result table more space; the PPO tab
   displays saved optimizer, policy/value loss, KL and parameter-change diagnostics.
5. **안전 STOP** saves the latest complete model/optimizer checkpoint. Reopen this
   run and select **체크포인트 재개** to continue. Interrupted native rollouts restart;
   the program does not claim exact rollout/RNG recovery after a crash.
6. **Validation 재평가** uses the same fixed validation identities, never final test
   holdouts. **Best 모델 내보내기**, **평가 보고서** and **실행 / 모델 폴더** expose
   retained checkpoint ZIP/JSON, validation samples and reports. Export requires a
   new directory, so old models remain intact.

Training data, settings, reports and checkpoints default to
`%LOCALAPPDATA%\PokeAdviceAITrainer`, outside source and distribution. Reopening
the GUI attaches to its last run. Closing the GUI leaves the independently owned,
bounded worker running; use STOP before closing when training should stop.
Only one worker is allowed in a user run registry. A file lock also rejects racing
launches and is released by Windows after a crash. Multiple unrelated custom data
roots are not an aggregate machine-wide resource scheduler.
The desktop rejects insufficient RAM before allocating a job (minimum
`2048 + 1024 × workers` MiB); recommended dedicated memory remains 12 GiB.

Resume is supported only with matching trainer/config/domain/catalog/engine/source
identities. Keep the distribution that created a run for resuming that run.
To extend a completed budget, start a new run from its saved checkpoint. Only load
trusted local model ZIPs (upstream PyTorch/SB3 serialization is not a sandbox).

## Evaluation and selection meaning

Four fixed validation opponents: max-power, Champions observable heuristic,
tactical observable heuristic, and frozen compatible v4. Training adds a frozen
historical v3 opponent. Checkpoint selection reuses the existing non-truncated
validation comparison and plateau patience, preserving the strongest observed
validation sample checkpoint. It does not establish statistical superiority by
itself. Sample win rates are not exact win probabilities or accuracy; small sample
differences can be noise. Dedicated defaults use 32 cases per rival (128 battles
per checkpoint). Larger independent final evaluation remains a separate study.

The actor and critic receive only the established public observation contract.
Unrevealed opponent sets and future randomness remain coordinator/native state.
Bring-6/pick-3 selection still uses coordinator fixtures, not a learned preview
policy. No model is automatically promoted into live battle recommendations.

## Packaging and process safety

PyInstaller onedir bundles CPython, CPU PyTorch, SB3/contrib, Gymnasium, poke-env,
PySide6, pinned Node 22.20.0, Git-for-Windows runtime and the native Showdown
checkout plus compiled files/dependencies. Native revision is
`942cda71d14bf0618bd57991708a2e2734b6daba`; format `gen9championsbssregmc`.
Payload hashes, source/domain/catalog/model checks and native Git revision/dirty
checks fail closed. Engine replacement/download is not performed during training.

The worker is a separate detached process with its own Windows Job Object: hard
aggregate CPU/memory/process limits and kill-on-close cleanup for its entire native
child tree. It rejects inherited launcher jobs that could bind training to Codex.
Start directly from Explorer. A wall-clock watchdog includes preparation and kills
the job after a 30-second grace period if STOP/native I/O is stuck. Saved checkpoints
remain recoverable; a killed incomplete rollout is discarded.
Node/Git child consoles are hidden only in this separate executable; the existing
live app and command-line trainer retain their behavior.

Build outside the repository using the documented builder CLI (developer-only):

```powershell
python scripts/build_pokeadvice_ai_trainer.py --checkout PINNED_CHECKOUT --output NEW_EXTERNAL_BUILD_DIRECTORY
```

The builder requires the validated dependencies plus PyInstaller 6.22.3 and
pefile. It restricts DLL discovery PATH to verified toolchains and Windows system
directories: ambient Poppler ICU is incompatible with Qt's Windows system ICU.
Windows 10/11 system components remain prerequisites. The local EXE is unsigned;
SmartScreen/antivirus can request normal Windows trust confirmation. No installer,
auto-update, code signing or machine-wide multi-user scheduler is included.

License notices reside in `_internal/THIRD_PARTY_LICENSES`. Qt/PySide6 are LGPLv3
dynamic libraries left individually replaceable; GPL-only Qt modules are excluded.
Upstream engines/runtimes are unmodified. Notices include CPython, PyTorch/SB3,
Node and its dependencies, Git and Showdown. Consult notices before redistribution.
PyInstaller's bootloader exception permits packaging application code.

References: [PyInstaller runtime guidance](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html),
[PyInstaller license](https://pyinstaller.org/en/v6.22.3/license.html),
[Qt licensing](https://doc.qt.io/qt-6/licensing.html),
[Explorer execution example](https://learn.microsoft.com/en-us/windows/win32/shell/samples-execinexplorer),
[Node 22.20.0 notice](https://github.com/nodejs/node/blob/v22.20.0/LICENSE).

Release QA and measured results are recorded in `standalone_trainer_v1_journal.md`.

Local release output (not committed):

`C:\Users\jsp33\.codex\artifacts\pokeadvice-ai-trainer-build-v7\distribution\PokeAdvice AI Trainer\PokeAdvice AI Trainer.exe`

Keep its whole directory. Distribution:954,021,953bytes (909.83MiB),
EXE SHA256 `9ef25d1f8ee851c218fa2cb8482198a74ec65ec64daf3c67f9ba4e7bd4d1fcd6`.
PyInstaller6.22.3, CPython3.11.9, PySide6/Qt6.11.0, Torch2.8.0+cpu,
SB3/contrib2.7.1, Gymnasium1.2.3, poke-env0.10.0, Node22.20.0,
Git2.51.0.windows.2. Windows10/11 x64 is the target; a clean Windows VM and
multi-hour endurance run have not been tested in this mission. The native engine
and all required application runtimes are bundled; no external installation or
engine checkout is part of the normal workflow on the verified Windows machine.
