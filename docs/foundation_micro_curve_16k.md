# Frozen Foundation micro learning curve to 16k

The exact opt-in `foundation-frozen-micro-ppo-learning-curve-16k-v1` contract
extends the existing 4,096-transition checkpoint by 12,288 new transitions,
at most384 new Adam calls and1,024 new TRAIN starts. Original micro defaults
remain4,096/128/512. The only accepted extension has checkpoint boundaries
at4,096/8,192/12,288 additional transitions, yielding cumulative8k/12k/16k.
Neither rollout length, batch, epochs, target KL, loss nor masks change.
Native episodes/rollouts restart from the restored current policy, not old data;
weights and Adam resume exactly, not the original uninterrupted RNG trajectory.

Frozen rivals remain the original Foundation argmax and T1 sample plus tactical
and Champions heuristics, equal per episode cycle. The resumed4k learner must
not accidentally replace the original frozen Foundation opponent. Original
teams, ordered bring-three, reciprocal owner directions and actual seats stay
fixed. No teacher, model, reward or hyperparameter changes; no performance gate.

Before learning, independently SHA-freeze curve and final panels with different
native seed namespaces from TRAIN and all consumed prior panels. Curve:
128 roots×2real seats×5models=1,280 starts (Foundation,4k,8k,12k,16k). Final:
64 roots×2real seats×2models=256 starts (Foundation,predeclared16k). Every model
in a panel shares rival, initial native seed, owner and actual seat. Opponent
sampling RNG is case-addressed without the evaluated-model identity. Shared
initial native seeds do not imply shared downstream RNG after actions diverge.

Final16k is fixed before learning; curve results cannot select another checkpoint.
Primary final independent-team paired win-fraction difference is reported with
root clusters retaining both reciprocal directions and actual seats, bootstrap
within fixed pair/rival strata. Curves are descriptive, multiple repeated panel
comparisons are not separate final confirmations. One training seed and only
two independent roster pairs cannot establish population superiority/equivalence.

Existing hard Windows protections:CPU50%,RAM8GiB,max4native workers,CPU only.
Durable native-start and pre-Adam intents count actual consumption. No unbounded
restart, extra training or automatic promotion. Models, receipts, public/native
traces and coordinator-only auxiliary labels stay in external artifacts.

Completed native run and audit (2026-10-27/28):12,288 new rollout transitions,
384 Adam calls,669 TRAIN starts (661 terminal,4 unused constructor resets,
4 open at stop); cumulative micro budget16,384 transitions/512 Adam calls.
All1,280 curve and256 separate final games have matched start/result receipts;
no duplicate, missing, rejected or truncated evaluation games were found.
The frozen original Foundation and the4k resume ZIP/Adam were preserved.

Curve win counts (all/train/independent; denominators256/128/128):
Foundation148/85/63;4k157/89/68;8k167/94/73;12k165/95/70;
16k156/89/67. These repeated-panel observations do not select a checkpoint.
Separate final panel:Foundation67/128 versus16k78/128 overall; TRAIN38/64
versus49/64; independent29/64 versus29/64. The independent paired difference
is0.00pp, conditional root-cluster95% interval[-3.125,+3.125]pp.
Verdict:`LEARNING_CURVE_INCONCLUSIVE`. Training-team gain does not establish
generalization, and the conditional interval does not prove equivalence.

Checkpoint `model_seed` and `curriculum_version` retain inherited metadata
(95017 and legacy v2). They are not this continuation's execution manifest:
the SHA-bound plan records continuation seed104029 and the actual native
episode identities bind V8 TRAIN cases. Read those provenance records together;
do not infer the active sampler from the inherited checkpoint fields alone.
External audit/report root:
`C:\Users\jsp33\.codex\artifacts\foundation-frozen-micro-ppo-curve-16k-v1-20261027`.
No promotion or subsequent training was launched.
