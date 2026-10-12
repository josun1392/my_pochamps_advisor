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
