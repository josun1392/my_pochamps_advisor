# Overnight autonomous learning journal

Start: 2026-10-11 16:37:59 UTC (2026-10-12 01:37:59 KST).
Hard mission deadline: 2026-10-11 22:37:59 UTC. Six hours is an upper bound.
Verified baseline/remote: de72731e39f2f5e686dfe9c09d0ddae82a00d879,
codex/showdown-mc-integration-v1; canonical josun1392/my_pochamps_advisor.
Master 691d2df and its five original changes preserved.

Current milestone: standalone bounded trainer first; action-conditioned v2 next.
Run directory: C:/Users/jsp33/AppData/Local/PokeAdvice/training/overnight_2026-10-12
Runtime environment: existing isolated Python 3.11 / CPU Torch / pinned Showdown.
Resource plan: one Torch thread, four native workers, <=12.5% aggregate CPU and
3 GiB job memory on this 16-logical-CPU / 64 GiB host; <=six-hour wall deadline.

Plan: implement atomic checkpoint/state commits, locking, deadline/stop/resume,
validation-only selection/plateau control, reference/historical rival mixtures;
prove detached parent-job independence before unattended execution. Never claim
partial rollouts were restored. Final tests use a fresh versioned curriculum.

Identified compatibility gap: old curriculum used additive split seed offsets.
Long-running arbitrary episode indices can overlap train/validation configurations.
Keep v1 replay semantics; introduce explicit hash-namespaced curriculum v2.

Checkpoint at ~2026-10-11 17:04 UTC: standalone loop and v2 shared action policy
implemented. Related native/learning/UI regressions: 96 passed in 35.47s.
Pilot: 512 PPO transitions +256 teacher decisions, 64 completed battles;
checkpoint reload and optimizer preservation verified. Test pipeline also restored
a trained v2 optimizer and continued from 256 to384 transitions.

Windows breakaway probes remained in an inherited job (including the real Python
interpreter). Detached continuation after Codex exit is not guaranteed; fail closed.
Foreground managed runs retain hard lifetime/CPU/memory limits and restart artifacts.

Long experiment config: external experiments.json; seeds11/29/47; v1 warm-start,
v2 pure PPO, v2 warm-start comparisons. Validation32 cases×3 rivals, untouched final
test/unseen64 cases×3 each. Plateau4;16,384 transition checkpoints;45min cap.
Stopped at28,912 collected transitions /3,291 battles to verify safe restart and
apply per-experiment plateau accounting. Peak job memory1.53GiB; tree CPU114.9s;
100.2s launch wall; native workers all closed (active job processes1 before exit).
Latest resumable checkpoint: experiments/experiment_00/checkpoint_0002_ppo_28912/model.zip.
Best current validation56/96 is a small pilot result, not a strategic-strength claim.

Next: resume from verified checkpoint; finish controlled seed comparisons; inspect
summary once complete, preserve validation best, then independent final evaluation.
Commit identifiers and final output paths will be recorded at validated checkpoints.

Validated core milestone committed/pushed:48318c21e4335efdec1b43656dc14f7a9075cfce.
Standalone lifecycle tests additionally proved complete-run idempotent resume and
new-budget optimizer continuation (512→768 PPO transitions);11 focused tests passed.
Thirty-second deadline probe completed under the configured budget; artifacts will
be summarized after managed experiments. Full offline regression is running with
network-blocking in all four pytest workers.

Encoder optimization: cache only repeated calculations inside one public view.
413 native decision views across32 new train episodes (309 move/104 switch phases)
were bitwise identical before/after; p50 encoding1.287→0.653ms, p951.969→1.005ms.
No cross-episode cache or policy-contract reinterpretation. Current already-loaded
training continues with equivalent uncached features; new runs/UI use the faster path.

Broad offline checkpoint:7860 passed/2 known baseline layout failures,509.42s;
zero attempted external network connections in parent/four workers. Native/learning/
UI focused checkpoint51 passed; new standalone trainer tests12 passed in24.17s.
Deadline proof:30.059s wall,4571 collected/4480 trained rollout transitions,
321 battles,34.72s aggregate tree CPU,1.11GiB peak job memory; workers closed.

Evidence-driven follow-up started ~17:31 UTC: warmrate.json/output warmrate.
Source is immutable run-A validation-best seed47 PPO32768 (66/96 validation wins).
Compare unchanged source, additional teacher fit at3e-4 vsPPO5e-5 (seed59),
fresh seed73 at those separate rates. At most20min; plateau3;65536-step budgets;
8192 teacher decisions/12epochs; reference includes the preserved source checkpoint.
Final tests use fresh offset30000 and remain uninspected until selection completes.
The two brief overlapping CPU jobs each have12.5%/3GiB hard caps (<=25%/6GiB total)
on the16-logical-CPU/64GiB host; all foreground and resumable, no persistence promise.
Run-A final-test files will not be used to tune the follow-up.

Core hardening committed/pushed:7bfd3eee00d80b51ee076c9e1b91d9ddf5c6c5b5.
Run-A now completed:311536 collected/311296 trained PPO transitions,33907 ended
or truncated training episodes;32768 teacher examples across four configurations.
Best is seed47 PPO32768,66/96 validation wins; later96k was not promoted.
Do not claim the older training episode counter excludes truncations: it did not
persist their breakdown. New launcher checkpoints explicitly record outcome tallies
without relabeling older records. Independent final evaluation records retain full
W/L/draw/truncation data and are available after model selection.

Remaining concrete work: finish run-B selection/final evaluations, release the
validation-selected artifact, run actual Qt/rollback/latency smoke, final focused
tests, exact-stage/push artifacts and Korean report. No uncontrolled detached jobs.

Final snapshot:2026-10-11 18:00:24 UTC. Wall4945s; implementation/validation
session excluding only explicit idle waits4879s; explicit waits66s.
This is session activity (including overlapping compute), not separately measured
LLM-only time. Main local training jobs accumulated2368.84 CPU seconds.

Run-B finished:115200 PPO transitions,16384 teacher examples,15023 ended/truncated
episodes. Total main runs426736 collected/426496 trained transitions,49152 teacher
examples,48930 ended/truncated episodes. All four main/pilot/deadline PIDs are dead;
no run locks or uncontrolled jobs remain. Original master/pre-existing files untouched.

Release models/showdown_action_v2/model.zip:SHA364e30469d8a30106f90c04e0fc59a601b92f541af8b41235d08bd67af06d667.
Validation-selected seed73:teacher8192 +PPO32768,1792 optimizer updates.
Fresh test/unseen each130W/62L; v1 counterparts102/90 and96/96; heuristic133/59 and140/52.
Existing v1 improvement established; stronger-than-heuristic claim rejected.
Native Qt readiness12 episodes10W/2L, runtime/ledger unchanged, exact rollback;
inference p50/p951.023/1.263ms, UI845ms. Final related tests53pass/30.34s;
after final seed/binding hardening13trainer tests passed/24.09s. Broad baseline2fail retained.

Next user action: standalone CPU launcher from a separate PowerShell, sample config
or new budget initialized from the released artifact. Recommended next research is
wider legal roster/stronger rivals/independent seeds before large GPU training.
No further T1 policy approval was required; production ranking remains unchanged.

Final artifact/workflow commit pushed and remote verified:
9a7685c434a8bb07994dd296fa503918baa44bc6. Migration worktree clean after that commit.
Original master remained691d2df with the same five pre-existing changes.
Final reporting checkpoint:2026-10-11 18:04:43 UTC; wall5204s, activity5138s
(excluding only66s explicit idle). This journal closes the mission: COMPLETE
engineering/actual learning; v1 strength improvement proved; heuristic superiority not proved.
