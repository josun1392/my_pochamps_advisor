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
