# Experimental legal-candidate context prototype v1

This task reuses the existing `learned_legal_set_context` implementation; it
does not invent a second architecture or reinterpret past evaluation results.
`CandidateContextPrototype(source, opt_in=True)` is an offline score-inspection
facade. It is not imported by the production advisor, LearnedPolicy loader or
trainer, and has no learn/train/save/infer method. Existing Foundation and 16K
checkpoints retain their original classes, features, weights and Adam states.
No historical 96/288-case sealed observations or strength results are inputs.

## Why candidate C's owned PP did not affect A versus B

`ActionObservationEncoder._move` transports current owned PP/maxPP only when
the native move slot is supplied. Candidate rows for that move (including its
native transformation aliases) receive the ratio. The shared global context
and other candidates' nominal move-pool features do not receive that slot's
current PP: the latter call `_move` without a native slot. The categorical
entity/move bindings preserve identity but do not add a cross-candidate PP pool.

The original inherited `PublicHistorySequenceExtractor._actor` computes
`z_i = scorer([context(c), row_i])` independently for each row. With `c`, row A
and row B fixed, changing only row C cannot change `z_A-z_B`. Softmax can change
both individual probabilities through its denominator, but their odds ratio
and relative logit gap stay fixed. The original critic already pools legal
candidate rows and may respond. Foundation also already has public history
summaries/a stateless sequence; this is not a memoryless-policy diagnosis.

## Reused minimum path

```
g   = existing_context(c)
h_i = existing_scorer_without_output([g, row_i])  # 64 joint features
u   = sum(where(native_legal_i, h_i, 0)) / legal_count
g'  = g + W u + b                                # 64 -> 64
z_i = existing_scorer([g', row_i])
```

Only the existing 4,160 residual parameters (64*64+64) are added in an
independent in-memory copy. The scorer, critic, predictions, encoder and
native action mapping are reused. W/b begin at zero. The optional fixed
diagnostic is W=0.05I/b=0; it is not fitted or selected by battle outcomes.
There is no optimizer update or model save. The facade guards its copied
optimizers; it neither retains a PPO object nor enables training opt-ins.

`use_context=False` uses an independent copy of the original Foundation path;
zero W/b on the enabled path reproduces it. Raw logits are captured from the
maintained policy's action-net output, and its own fused forward supplies
probabilities and value. No new masking/softmax/value algorithm is introduced.

This is not a common scalar added to every logit. For nonlinear scorer f,
the derivative of z_A-z_B with respect to u is
`(D_g f(g', row_A) - D_g f(g', row_B)) W`. It can be nonzero because the
two candidate rows can activate different nonlinear responses. This proves
capacity, not that every pair, feature direction or learned W must respond.

## Boundaries and tests

Only one authenticated public view enters `score_public`. The maintained
public-input validator and original Foundation encoder both validate that view;
projecting fields first must not hide forbidden roots from encoder validation.
Existing Unknown/absence/padding semantics remain;
missing required data fail closed rather than inventing facts. The encoded
test seam is not an observation authority and is never a live-policy route.
Implicit and explicit masks must agree with the transported own native mask.
Empty/nonbinary masks and malformed/nonfinite transports fail closed. Finite
illegal/padding rows are excluded from the context pool; illegal probabilities
remain zero. Forced switches and a single legal choice are covered explicitly.

Aligned candidate-row permutations preserve the context mean and equivary
scores/probabilities, up to normal FP32 reduction rounding. All candidate blocks
and the mask must move together while global context stays fixed. This is
different from permuting physical move slots in the native request, which can
change inherited ordered own-move context. The previously documented 50/867
slot sensitivity is not fixed or hidden here. No sorting/remapping is added.

For a permutation P, joint features and mask become Ph and Pm; their masked
sum and legal count are unchanged, hence g' is unchanged and z becomes Pz.
Masked rows contribute exactly zero to u. The transported mask is validated as
binary and nonempty before pooling, so the denominator is an integer 1..35;
an empty mask is rejected rather than assigned a synthetic fallback action.

Retained TRAIN-only fixtures verify original logits/probabilities/value bytes,
original model/Adam independence, C-PP routing versus fixed A/B, illegal-C
nonresponse, permutations, missing/unknown traits and native mask boundaries.
Not every C change must matter: zero projection, excluded C, or a direction
ignored by learned weights can leave the gap unchanged. A capacity probe
does not certify useful choices or battle improvement.

`MEGA_SOL -> UNKNOWN` in the frozen heuristic compatibility parser remains a
separate residual issue. Neither heuristic policies nor completed evaluations
are changed. Any future learning or native evaluation needs separate approval.
