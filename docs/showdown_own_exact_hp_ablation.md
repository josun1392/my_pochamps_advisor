# Own exact HP: separate opt-in V4 contracts

The original `showdown-public-categorical-observation-v4` remains unchanged.
Two extended encoders use the same `OwnExactHPCategoricalPolicy` architecture:

- `showdown-public-categorical-observation-v4-own-exact-hp-v1`
- `showdown-public-categorical-observation-v4-own-exact-hp-ablated-v1`

The 15,692 original transport values are an unchanged prefix. The appended
24 values contain six rows ordered by the original V4 own-record identities:
`current / 1024`, `maximum / 1024`, `current_known`, `maximum_known`.
Scaling is fixed, not current/max division (which would erase the maximum).
Native integer HP up to 4096 is supported without clipping. Invalid known HP
fails closed. The categorical bit fields and all 35 action indices are unchanged.

The only HP authority is the player-owned native policy request. Its `side.id`
and each exact `ident` must match the current native player role. The existing
own identity reconciler supplies the record binding, including bench and own
Illusion identities. No opponent request, public percentage, species maximum,
checkpoint, hidden set or previous episode supplies missing values. A native
`0 fnt` establishes zero current HP but leaves the unreported maximum unknown.
Padding remains zero with the existing V4 presence flags. Absent request data
is unknown. The control zeros **all** added values and knowledge flags on every
encoding, while applying the same request validation.

The policy appends these six identity-bound HP rows to context and gathers the
corresponding row into each candidate's own-entity features. Actor and critic
share this public boundary. Parameters increase from 383,130 to 388,762;
input dimensions increase to 15,716. Added transport is numerical; existing
categorical transport must not be normalized or reinterpreted.

`transfer_own_hp_weights` strictly accepts the original categorical V4 parent.
Every compatible tensor is copied. New actor context, candidate and critic
columns start at zero, preserving logits, probabilities and values within
floating-point matrix multiplication rounding. Both arms use fresh Adam;
this is not an uninterrupted historical optimizer resume. Subsequent same-
contract loading uses the existing optimizer and regularizer resume machinery.
Different control/treatment fingerprints prevent a silent semantics swap.

The autonomous source trainer supports these versions through `transfer_model`
with `fresh_optimizer: true`. Rewards, gamma, GAE, masks, native mechanics,
zero-avoiding regularization and production recommendations are unchanged.
The bounded study uses one matched seed, 65,536 transitions per arm and fixed
endpoints. Evaluation-case uncertainty cannot establish training-seed robustness.
External manifests contain exact model/config/bank hashes and results; neither
encoder nor model is enabled in the live advisor by this integration.
