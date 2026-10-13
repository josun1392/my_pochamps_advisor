Public own-move identity ablation is an opt-in research contract. Existing V3
encoders, native battle mechanics, rewards and live guaranteed-first ranking
retain their previous meanings.

Both `showdown-own-move-class-observation-v1` (control) and
`showdown-own-move-id-observation-v1` (treatment) use `OwnMoveTokenPolicy`, the
same shared action scorer, categorical table and parameter count. They retain
V3 tactical features and append ten binary transport bits per action row before
the final legal indicator. Only a categorical embedding decodes these bits;
raw IDs/bits never enter a Linear layer as ordinal values.

Control maps public own-request moves to equivalence classes of the existing
static V3 move descriptor. Treatment maps each known own-request move to a
distinct token. Neither arm adds opponent unrevealed moves, hidden sets,
checkpoint state, private rival requests or future randomness. Known absence
and Unknown item/ability semantics remain the existing V3 semantics. Unknown
legal own-request move IDs fail closed. Showdown's public forced `recharge`
request is explicitly supported separately from selectable Dex moves.

`transfer_v3_to_own_move` copies V3 weights and initializes new projection
columns to zero. Both arms require fresh Adam; it does not restore the source
optimizer's moments. The categorical embedding remains nonzero so subsequent
updates can learn the new projections. Initialization is checked for paired
parameter, action-distribution and value equality, native masks, row
permutation, gradient flow and save/reload. Small floating-point differences
from the original narrower V3 matrix are tested with numerical tolerance;
paired arms must produce identical initialization outputs.

Every new checkpoint binds its separately versioned `feature_contract`, token
map, base catalog fingerprint, engine/action versions and model SHA. An old V3
checkpoint remains loadable without the new field. Cross-arm contracts are
rejected. Old packaged Trainer executables do not automatically gain support
for these new experimental checkpoints; this source change does not replace
the user's existing distribution or models.

The autonomous trainer accepts a hash-bound `validation_case_bank` with
`validation_case_bank_sha256`. The bank must declare validation scope and
pinned native authority; final access is rejected. Native legality is the
trusted builder's TeamValidator attestation plus content binding, not a new
Python legality implementation. `evaluate(..., case_provider=...)` changes
only coordinator scenario sourcing; the native evaluator, observations,
choices and outcomes are reused. Defaults use the original curriculum path.

Study artifacts, frozen manifests, checkpoints and independent results are
stored outside the repository at:
`C:/Users/jsp33/.codex/artifacts/public-move-id-ablation-v1`.
The experiment uses three paired seeds, at most786,432 new transitions, and
at most18,432 validation/final battles. Validation-selected checkpoints are
descriptive; the primary comparison uses fixed131,072-transition checkpoints.
Fresh team hashes do not imply unseen species or unseen individual sets.

No checkpoint is promoted to production by this experiment. Experimental
policy probabilities are action distributions; their value is a discounted
return estimate, not exact win probability.

The completed three-seed study collected786,432 comparative PPO transitions
and65,424 ended training battles. Periodic validation4,608 plus independent
final13,824 battles met the18,432 evaluation ceiling. Treatment minus control
on fresh broad cases was−0.72pp (paired seed/case bootstrap95%−3.04,+1.58).
Only one seed was positive; the declared improvement gate failed. The separate
collision stress panel was+1.56pp (−4.43,+7.68), inconclusive. Trained identity
embeddings did distinguish native aliased choices, but this budget did not
establish strategic superiority. Existing models/default policy were retained.
