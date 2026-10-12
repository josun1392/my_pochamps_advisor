# General M-C strategy / efficiency journal

Start 2026-10-12 02:12:38 UTC. Verified clean migration worktree, local and
canonical remote9a3e1c6a052ff8a313ffab9922b5b694dd3f4360. Original master
691d2df... and five existing changes preserved. No protected-file reads/writes.

Current milestone: profile existing native/encoder/sampling/update costs and
CPU scaling before optimization. Hardware verified9800X3D8C/16T,5070Ti16GB,
driver610.88,64GBRAM. Separate temporary PyTorch2.8/cu128 install; existing CPU
environment unchanged. Official PyTorch2.7+ supports Blackwell/cu128; actual
kernel compatibility and speed must be measured, not assumed.

Existing evidence: v4 tactical gain did not generalize; failed healing26/147,
including full-HP choices that can also be legitimate against faster attacks.
Never change native legal masks or add action-frequency rewards.

Design candidates, conditional on profiling/validation: public per-action HP
gap/healing and boost interactions, explicitly observed move-order/history
signals, broader legal coherent sets, maintained SB3 SubprocVecEnv sampling.
No model version release unless measured outcome evidence justifies it.
Old final180000/280000/90000 are inspected and excluded from tuning/final use.
New validation27000; a fresh final plan/offset will be locked before evaluation.
Policy default/exact evidence/live observations remain unchanged.

Local output `%LOCALAPPDATA%/PokeAdvice/training/general_mc_2026-10-12`.
Native CPU benchmark1024 transitions per condition,1/2/4/8 workers,dummy/spawn,
CPU50%,RAM12GiB,300s hard watchdog. CUDA install exec71831, no GPU training.
Next: read summarized profiles, run bounded actual CUDA/PPO benchmark, accept
only useful parallel/data changes, then independent bounded learning/evaluation.

03:10 UTC checkpoint: actual uninstrumented native sampling dummy1=274/s,
spawn4=571/s,spawn8=677/s before optimizations. cProfile separately identifies
native projection/deepcopy/feature encoding costs. Initial 12-process job cap
failed spawn4 Git children; replaced with bounded worker-aware cap, not removed.
CUDA2.8/cu128 sm120 executes real kernels on5070Ti. Current2048-transition PPO:
CPU1=10.74s,CPU4=9.39s,CUDA1=10.13s. Batch1 inference CPU0.275ms vs CUDA1.334ms;
larger656k-parameter batch128 compute-only update20x CPU1.669s/CUDA0.035s.
GPU remains optional, CPU remains default. Results under local gpu_benchmark/.

Found/fixed a real privacy side channel: Gym info.native_outcome contained both
projected private requests. Now only public outcome/reward scalars leave Gym;
trusted native coordinator API unchanged. Cached static native move metadata.
Added maintained SB3 spawn/async vector execution, worker-safe frozen SHA paths,
configurable CPU/device/memory limits and correct parallel episode accounting.

Prototype observation-v4 extends old observation-v3 with public historical
move order/fail/heal/setup/wish and per-action HP/boost/switch/hazard interactions.
Not an announced new model generation. Transfer preserves old actor/value to
float32 tolerance; native legal masks including full-HP heal untouched.
New curriculum-v5:55 training species,20 species-disjoint unseen; role-conditioned
items and bring-three choices. Native rejected9 draft species; Toxic Orb also
absent in pinned M-C. Draft errors corrected, Goodra/form Species Clause handled.
46 related tests passed, no external network attempts. Tiny parallel trainer:
512 PPO/128 teacher transitions,57 ended battles,checkpoint reload passed12.2s.

Running matched_rl_pilot: CPU37.5%,8GiB,4spawn workers,torch4,900s hard cap.
Seeds1237/1301 x old/new encoding,8192 PPO transitions each,zero additional
imitation,fresh optimizer both,same v4 initialization; stable opponents V4/V3
plus max-power/champions/tactical heuristics. Validation27000/24cases/4rivals.
No final test used for selection. Next: inspect summarized validation, extend
only justified candidates, lock fresh final plan, complete performance/regressions.

03:29 UTC: both bounded learning pilots finished. Four genuinely independent
learning seeds1237/1301/1423/1559 (each matched old/public encoding),81920 PPO
transitions and8192 teacher decisions,7297 ended training episodes,no truncations.
PPO-only189.1s/631.5 tree CPU seconds; broader warm-start280.4s/873.3CPU seconds.
Peak committed memory5.16GiB. Extra training often regressed; keep immutable best.
Common separate validation32000/32cases/five rivals chooses warm_control1423
90/160 and warm_public1423 88/160; oldV4 81/160,tactical heuristic99/160.
No strength claim from selected validation. All8 candidate scores saved locally.

CPU after changes: dummy1/2/4/8=268/282/259/236 transitions/s;
spawn1/2/4/8=239/387/574/742. Same seed/episode counts; single-pass timings,
not confidence intervals. CUDA trainer512PPO/128teacher passed13.2s,54 ended,
96.4MB peak Torch GPU,6.6GiB total Windows job commitment.6GiB job cap earlier
surfaced CUDA OOM;8GiB smoke passed. No uncontrolled GPU job left running.
Fixed cross-device weight transfer; changing4 to8 rollout workers now uses
maintained SB3 load(env=...) to restore optimizer with new rollout shape.
Actual8-worker restart1024PPO/85ended passed10.3s,8.32GiB peak commitment.

Broad offline405 passed; one new test initially read a nested proof key at the
wrong level (test defect fixed). Focused UI/public24 passed and final public9
passed, including hidden-set/seed isolation and action-row permutation.
Next: commit engineering, lock fresh final V5test/unseen plus legacy V3broad
offset680000/64cases/five frozen rivals; never retune after inspecting final.
