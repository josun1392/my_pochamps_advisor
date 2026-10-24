# Foundation argmax public selected-response predictor v1

An offline supervised diagnostic, never a battle opponent or production advisor.
No PPO updates, BR integration, strength games or policy promotion. The frozen
Foundation acts with its actual masked argmax. Selected choices are recorded
before native execution and remain distinct from executed public moves.

`advisor/learned_response_predictor.py` reuses the existing public projector,
787-dimensional numerical encoder, canonical move metadata, action families and
native request ownership. Exact apparent active species and publicly revealed
active moves are added. Appearance ambiguity remains unresolved. Forward inputs
are one observer's public state/history and own request only. The target's
request/mask are label-authentication channels, never input or softmax support.

Output vocabulary: each canonical move ID is eligible only after that active
identity publicly revealed it; five unrevealed move-family categories and a
voluntary-switch category remain available. No claim to know a complete private
moveset, move slots, current hidden disable/trap legality or switch destination.
Revealed-but-currently-unavailable choices can retain probability, reflecting
public uncertainty. No private-mask-conditioned normalization at any stage.

The standalone runner freezes 128 disjoint full-team pairs from the existing
TRAIN256 subset: 64 train, 32 validation, 32 test. Seven new native RNG/ordered
bring-three replicas per pair, both actual seats, total 1,792 starts. The original
seven identities and nominal 10/10/10/10/10/30/20 mixture are preserved through
predeclared within-fold integer quotas. RNG replicas are not independent team
clusters. No validation/test/sealed battle bank supplies training teams. These
teams were already exposed to the frozen combat model; this is predictor-team
separation, not species/set-unseen combat generalization.

One MLP (128/64 tanh), unweighted categorical CE, fresh Adam 3e-4, batch256,
maximum20 epochs, validation early stopping patience4. A single bounded scalar
temperature uses validation only. Fixed train-frequency+Jeffreys smoothing and
public nominal-power/type-prior/HP-gap heuristic are comparison distributions.
No class-weight search, model sweep or inferred optimal-action labels. All three
are scored on identical final test rows with NLL, multiclass Brier, top1,
family-specific recall and confidence calibration. Resample full-team pairs,
retaining replicas, both seats and opponents. Two-baseline familywise intervals
supplement ordinary95% intervals. Attack-majority accuracy alone is not success.
GO additionally requires at least300 revealed-move test labels across16 team
pairs and paired revealed-move NLL improvement over both baselines. Otherwise
any demonstrated narrower benefit remains CONDITIONAL GO with scope limits.

Dataset-health minimums: train4,000/validation1,500/test1,500 accepted rows and
at least24 independent full-team pairs per fold. If unmet, do not fit. Rare
actions and epistemically unknown information remain reported limitations.

Native collection reuses the paired evaluator, compact public audit hook,
original request retry guards, frozen `LearnedPolicy`, SHA-bound cases and Windows
Job ownership. One CPU native worker,50% CPU,12GiB RAM,CPU-only,one3,600s launch,
zero automatic restarts. Start/commit ledger and immutable receipt/trace hashes
make duplicate launches and uncertain started-game reexecution fail closed.
STOP may interrupt an active game; it is not silently counted as completed.
An interrupted fit or opened test requires explicit audit, never automatic
refit/retest. Completed native games are never rerun to recover an offline error.

Training archives contain original full owner requests for label validation;
the generated feature dataset contains public-only inputs/support and semantic
labels. Keep source archives restricted to coordinator use. All model/data/test
artifacts stay external. The offline predictor checkpoint stores its encoder,
plan/dataset hashes, optimizer and RNG state separately from combat checkpoints.
GO concerns probabilistic prediction only; battle strength needs another task.
