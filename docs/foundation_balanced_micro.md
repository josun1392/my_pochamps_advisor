# Balanced reciprocal Foundation micro v1

Opt-in composition of `pilot_foundation_fixed_micro.train/eval_phase`, native
Gym, existing frozen opponents, T1 logp/value/GAE audit, checkpoint saver and
actual-seat evaluator. No teacher, new mechanic, network, reward or optimizer.
Ordinary training and the original micro default case cycle are unchanged.

One configuration is chosen from V8 TRAIN by static shared-species/move overlap,
before new performance: six distinct roster pairs, same three brought species
per pair, full six and move slots untouched. Two pairs TRAIN, two development,
two independent. Full roster membership does not cross these partitions.
Species/set overlap and past parent exposure are not excluded. This is a small
conditional learnability study, not a population benchmark. Each pair appears
with both roster owners and both actual native seats. Fixed ordered bring-three
is not preview learning. Native seeds are shared across reciprocal ownership
directions; phase namespaces separate TRAIN/development/precheck/final.

Development uses 128 starts (cap256), precheck128 (cap128). Both gates are frozen
before any outcomes: overall wins35–75%, each direction20–80%, each pair-direction
10–90%, no truncations, and each direction >=16 attack/switch opportunities and
>=8 recovery/setup/defense opportunities. These are design gates, not confidence
tests of strength. No case replacement, tuning or second candidate after failure.

After both gates pass, final Foundation baseline128 starts, one PPO mini of
4,096 transitions / <=128 Adam calls / <=512 TRAIN starts, final Micro128 starts.
The final256-start panel includes TRAIN and independent pairs, with new native
seeds. Frozen Foundation and Micro are paired on rival, native seed, owner and
seat. Fixed rivals: Foundation argmax25%, Foundation T1 sample25%, tactical25%,
Champions25%; training episode cycle is unchanged except reciprocal case cycle.
Original weights and Adam are restored; fresh episodes/rollout bookkeeping
are not byte-exact uninterrupted resume. New checkpoints retain model/Adam.

Primary paired independent-team difference uses both reciprocal directions and
actual seats as one pair/rival/native-seed cluster, bootstrap within pair/rival.
Only two independent roster pairs and one training seed: uncertainty conditions
on these fixed pairs, not team-population or training-seed variation. A positive
TRAIN difference plus independent CI lower>0 supports
BALANCED_MICRO_LEARNING_COMPLETE; otherwise MICRO_INCONCLUSIVE. Regression is
reported explicitly. Completion of execution does not establish strength.

CPU50%, RAM8GiB, max4 native workers, CPU only, one3600-second launch. Shared
durable native-start and Adam intents enforce budgets; no automatic retries or
duplicate launch. STOP preserves completed checkpoints. All models/traces/raw
native and evaluation artifacts stay outside Git. Inference inputs retain the
original public boundary; private auxiliary labels remain loss-only.

The first launch completed development128 (62 wins,48.4375%) and precheck128
(66 wins,51.5625%). Development passed. Precheck pair5 ownership directions
were 3/32 and31/32, violating the predeclared pair-direction10–90% gate despite
the balanced overall mean. No TRAIN start, PPO transition, Adam call or final
evaluation occurred. All256 completed games had no native rejection, draw or
truncation. Verdict BALANCE_GATE_BLOCKED. No configuration was replaced after
results. Static shared species/move overlap did not establish equal set strength
or eliminate policy/slot/bench asymmetry. This is not evidence against PPO
learnability; the composed learner path remains unexecuted in this study.
