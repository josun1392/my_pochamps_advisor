# Tactical decision mission

Start: 2026-10-12 00:59:25 UTC. Verified clean local/canonical remote
`ecfa5c2f93aae668f36940c953baded38a6be15c`, migration branch only.
Original master and its five existing changes preserved.

Evidence: poke-env 0.10 `Move.target` is enum SELF, unequal to string `self`.
Its upstream setup gate therefore misses healthy favorable Scizor/Tyranitar
setup (native public matchup prior 1.1, Swords Dance available). Old benchmark
policies and artifacts retain their semantics. New tactical teacher corrects
this gate and adds explicitly heuristic public recovery/switch conditions.

Metamon audit: isolated shallow checkout
`0a00a759c9a4382a2877088d828302ec294a05a5` (2026-05-22), MIT, v1.6.0.
Gen1–4/9 OU support, forked poke-env and Gym<=0.29.1 conflict with existing
poke-env0.10/Gym1.2.3; native Champions pin/action contract differ. KaizoPlus
contains custom damage-equation machinery; do not duplicate it here. Reuse
public-state tactical coverage ideas, retain maintained MaskablePPO and existing
native environment. Its dense reward is not a policy-invariant potential;
terminal +/-1 remains unchanged in this experiment.

Current milestone: native V4 broad/tactical curriculum, teacher compatibility,
affordance-conditioned diagnostics. Prefixes use native legal choices only;
no HP/state/RNG edits. Half broad cases, paired safe/risky tactical starts;
unseen keeps the disjoint species pool. Encoder/model architecture unchanged.
Next: focused tests, fresh validation diagnostics, bounded independent seeds,
validation-only selection followed by locked fresh final test/unseen.

Task-owned local experiment root:
`%LOCALAPPDATA%/PokeAdvice/training/tactical_2026-10-12`.
No current trainer process. Old final offsets (90000/20000/30000) excluded.

01:12 UTC: 36 native/learning focused tests passed, external attempts0.
Fresh V4 diagnostic validation offset17000, 32 case clusters x5 rivals:
v2 96/160; v3 101/160; tactical heuristic101/160. V3 selected voluntary
switches21/112 unfavorable/better-bench states and recovery0/234 injured,
recovery-available states. Original teacher setup0; new teacher setup150,
recovery206, switch105. These are visited-state affordances, not optimal labels.
Metamon executable import refused current poke-env0.10, explicitly requires
fork0.8.3.3; do not bypass its compatibility safety check.

Training launched foreground, tracked exec10527, max1800s, CPU12.5%,3GiB,
4 native workers, Torch1thread. Seeds501/607/709, common frozen v3 source,
8192 teacher decisions x8epochs then up to24576 PPO transitions per seed.
Terminal rewards/gamma/encoder/network unchanged; Adam restored same encoder.
Validation48 cases x5 fixed rivals at17000; periodic8192 checkpoints. Final
test disabled in trainer; fresh final plan must be locked after validation.
Config/checkpoints: local task output `training_config.json`, `training/`.

01:21 UTC: engineering milestone `861deee` pushed to canonical branch.
Further focused UI/consumer tests61 passed; native branch/warm-start accounting
tests8 passed, external attempts0. Counterfactual368 complete native branches
(8 configurations/motif, fixed continuations) found both helpful and harmful
tactics: defensive physical recovery5/8 vs attack2/8; steel matchup switch5/8
vs attack2/8; intuitive fire switch4/8 vs attack8/8. Names are public-prior
coverage labels, not oracle annotations. No policy bonus for merely switching.
Seed501 validation149→158→168→157; source-independent seed607161→159→169→171
out of240. Third seed still running. Peak tree commit2.23GiB at433s; no failures.
Class-aware diagnostics and trainer template added; rewards/networks unchanged.
Final selection pending complete validation, no new final scenarios inspected.

01:23 UTC initial league run complete:73728 PPO+24576 teacher,8052 terminal
episodes(5157 wins/2895 losses),659.24s/treeCPU737.28s,peak2.45GiB,external0.
Validation-selected709 checkpoint174/240, SHA986ea2ba562d0b34df50ec2ca88ae3171e37031f6f358e9aa5813ffe01412641.
Locked league-only final plan offset180000 before starting broad evaluation.
403 broad offline regressions passed; unrelated baseline layout tests excluded.

Audit found later seeds' historical rivals freeze earlier seeds' best: legitimate
league behavior, not identical-condition independent replication. Corrected
earlier wording. Common initial weights/RNG seeds remain documented. Added
optional `historical_model`; omitted field preserves legacy league semantics.
Frozen identity/resume tests and native teacher accounting3 passed.

01:27 UTC launching independent replication:811/919/1021, all initial and
historical reference SHAfe52cd3b4e288c242176a6574769bdf1cd8fb5dbedad8b015496cb5b5dcfd57d,
8192 teacher decisions x8epochs +16384 PPO per seed,max1200s,CPU12.5%,3GiB.
Original league final is secondary, not inspected for tuning. Independent
selection/new primary final offset280000 will be locked before reading ANY
final results. Config `independent_config.json`, output `independent/`.

01:36 UTC independent run complete:49152 PPO+24576 teacher,6119 terminal
episodes(3932 wins/2187 losses),493.21s/treeCPU551.92s,peak2.46GiB,external0.
All historical SHAfe52 references verified, best165/174/163 of240 by seed.
01:37 primary selection locked: league709 retained on174-win tie with919.
Fresh primary offset280000,96 cases x5 rivals x11 policies x3 scopes.
No further learning/model reselection after lock. Original fixed/league models
remain intact; old finaloffset180000 only secondary. All trainer PIDs exited.

01:46 primary final complete:15840/15840 terminal battles, no draws/truncations,
external0. Tactical709324/480 vsv3 294/480, paired+6.25pp CI[1.46,11.04];
broad240 vsv3 249, unseen254 vsv3 243, both differences uncertain. All three
fixed seeds show tactical improvement but no broad general strength result.
Recovery/switching restored; setup/unseen and defensive/general strength remain
incomplete. Validation diagnosis64 games per policy:147 heals,93 requested at
fullHP,26 explicit native `-fail|...|heal`; v3/candidate both30/64 wins.
FullHP selections are not all wrong because faster incoming attacks can precede
healing. Keep this failure; no final-set tuning or false strength promotion.

Packaged four reloadable model/optimizer checkpoints, final summaries/raw hashes,
selection plans, training/resources, native branches and Qt readiness. Total
new122880 PPO +49152 teacher decisions /14171 training episodes /6912 updates.
Next final actions: published-artifact focused regression, exact stage/commit,
canonical push, original master/remote/process verification, Korean report.

02:02 UTC final focused23 tests passed, external0; four saved artifacts restore
SHA/action masks/native identity/optimizer without changing native checkpoints.
Original v1/v2/v3/tactics have no diff againstecfa5c2. Original master remains
691d2dfab74f0eaed0488dad9735d808be14927b with the same five pre-existing changes.
Trainer PIDs4484/40200 both dead; all tracked final/UI/profile sessions exited0.
This milestone is PARTIAL strategic strength, completed engineering/learning/
independent evaluation. No new candidate training after final lock; in-memory
regression-test training is verification only and excluded from study counts.
Actual elapsed at02:02:08 UTC:62min43s; final commit/push verification follows.
