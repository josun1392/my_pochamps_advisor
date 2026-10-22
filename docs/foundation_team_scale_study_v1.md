# Foundation matched 256 versus 4,096-team continuation

This opt-in study composes the existing source trainer. It changes only the
training-team population. It does not change inference, PPO, rewards, auxiliary
objectives, native mechanics, preview or production recommendations.

## Frozen contract

- Common parent: Stage 1 Foundation endpoint, ZIP SHA256
  `9b3eb94aabea1fb25e75dfdba0b733c2a9acd45434ae368a86e14d8979950ccf`.
- Both arms restore identical model parameters and Adam (clock 32,768).
  These are new rollouts, not exact mid-rollout restoration.
- A retains the original SHA-bound 256-team subset. B uses all 4,096 teams in
  the existing native V8 TRAIN bank through the same `NativeTrainingSubset`
  case/ordered-three owner. Historical subset versions are unchanged.
- Continuation repetitions: 96021 and 96022, each paired across A/B.
  They share one trained parent and are not fresh-initialization replications.
- Order: A-96021, B-96021, B-96022, A-96022. Each trains exactly 262,144
  rollout transitions; total main-study ceiling 1,048,576.
- Four CPU Subproc workers, one Torch thread, CPU hard cap 50%, aggregate RAM
  12 GiB, 3,600 seconds per arm and 18,000 seconds per campaign launch.
- Same ten-slot frozen opponent mixture, 128-step rollouts, 128 minibatch,
  four epochs, LR 5e-5, gamma 1, GAE .95, entropy .01, reverse KL beta .001.
- No validation-best substitution, performance-based early selection, automatic
  crash restarts, automatic extra budgets or model promotion.

All models/configs/cases/results are outside Git under
`C:/Users/jsp33/.codex/artifacts/foundation-team-scale-matched-v1-20261022`.
`plan.json` binds source files, parent/optimizer identities, configs, populations,
frozen references and evaluation cases. Unsupported native/encoding cases fail
closed. The operations-v2 journal and original trainer watchdog remain active.

## Partition and evaluation interpretation

The expanded population exposes old TRAIN-only diagnostic exclusions; those teams
must no longer be called unseen for B. V8 validation/test/sealed partitions stay
outside training. Existing public priors retain their original 256-team provenance.

The predeclared evaluation has 64 case clusters for each of original-256,
full-4,096 and held-out V8-validation distributions. Six policies (V4, fixed
Foundation parent, A/B for both seeds), two actual native seats and three rivals
(Champions, tactical, frozen league anchor) give 6,912 games. Action selection is
masked argmax. Both seats preserve the candidate's own team assignment.

New native payloads were checked against 82,969 prior known Stage 1/alignment
payloads. These are fresh pairings/RNG from existing banks, not new species or
necessarily unseen individual sets. Previously sealed final/rare cases are not
generated. Periodic old consumed diagnostics do not select checkpoints.

Primary comparison: held-out B-minus-A, averaged over the two paired continuations.
Also report A-minus-parent (continuation), B-minus-parent, and all policies versus
V4, separately for each distribution/rival/seat. Case bootstrap retains all
seats/rivals/repetitions within each case. Report the two seed effects separately;
do not infer a precise population variance from two continuation repetitions.

## Independent process operation

`scripts/train_combat_team_scale.py --plan EXTERNAL_PLAN` launches a detached
real-interpreter owner using the maintained Windows breakaway flags. The owner
must have `inherited_job=false` before any training starts. Its own Job Object
retains the hard resource/process and kill-on-owner-exit limits. A separate probe
records whether its launcher has exited while the detached owner still operates.

On this Codex host, ordinary breakaway **and** a locally created Shell.Application
dispatch still inherited a launcher job and correctly refused to start. The
verified fallback is dispatch through the **actual Explorer desktop**
`ShellWindows.FindWindowSW(SWC_DESKTOP).Document.Application.ShellExecute`.
The external `launch_via_desktop.ps1` checks for an existing owner before dispatch;
the resulting Python owner must independently prove `inherited_job=false`.
The approved runtime site-packages are passed explicitly to the real CPython
interpreter. This does not use the venv redirector, Task Scheduler, a service,
elevation, machine-wide settings or a visible console. Probe failures are retained.

The campaign serializes four explicitly authorized arms and stops on any failed
or partial arm. There are zero automatic restarts. `campaign_control.json`,
`campaign_state.json`, `progress.json`, `checkpoint_monitor.jsonl` and each run's
`state.json`/operations journal provide durable status. Final paired evaluation
is deliberately pending until the user returns; no process silently promotes or
consumes the evaluation panel during training.

Use `--resume` only after inspecting the previous PID, failure/STOP records and
checkpoint identity. Completed arms are skipped; an incomplete arm uses the same
config/source and existing trainer's explicit model/Adam restore. Partial native
episodes and incomplete rollouts are not claimed recovered exactly. A PC restart,
sleep, user termination, hard limit or owner crash can interrupt the run; saved
checkpoints remain available. No scheduled task or persistence after OS shutdown
is installed.
