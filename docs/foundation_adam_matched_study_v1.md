# Foundation fresh/restored Adam comparison v1

This opt-in study uses the standard FoundationCombatPPO path, without a
parent-policy KL. Four continuations start from one immutable Foundation model:
restored Adam (A) and empty fresh Adam (B), paired at seeds 98111 and 98519.
Each trains 65,536 rollout transitions. They are two stochastic continuations of
one parent, not independent fresh-model replications.

`advisor/learned_adam_study.py` rejects non-optimizer differences. Both conditions
retain the parent's model timestep counter and the same constant learning rate.
The actual initial trainer archive is checked against the original parent:
all parameters, masked actor logits/probabilities and critic outputs agree;
Adam parameter-group options agree. A must preserve the exact Adam state; B must
have no optimizer state. Internal bias-correction differences are part of B.
Historical checkpoints are never overwritten. On resume, the existing trainer
loads the child's Adam rather than resetting B again.

The existing detached owner, operational retry monitor, Windows Job CPU/memory
limits, STOP checkpoints and immutable per-game receipts are reused through an
explicit study adapter. There is no automatic crash restart or uncertain-game
re-execution. A newly introduced `checkpoint_evaluation_mode` can disable
automatic checkpoint validation only in fixed-budget diagnostic mode with no
trainer final test. The default remains automatic validation. This prevents
unbudgeted evaluation while preserving native training/checkpoint semantics.

The external, hash-bound plan fixes 192 scenario clusters (96 from the training
256-team distribution, 96 from the non-training validation bank), three frozen
rivals, both real native seats and masked argmax: 1,152 games per model and
5,760 overall. Existing consumed panels and training episode identities are
audited before the plan is frozen. Bank reuse does not establish species- or
individual-set-unseen generalization. Sealed final assets are not accessed.

The primary contrast is the two-continuation average B minus A over all cases,
with held-out cases a required confirmation. Report both repetitions separately,
case-cluster bootstrap intervals retaining seats/rivals/repetitions, and parent
win retention/acquisition. These intervals do not estimate a population of
training seeds. Further-research GO requires positive primary and held-out
interval lower bounds, positive direction in both repetitions, and no material
safety/integrity regression. Otherwise scaling is NO-GO; uncertain evidence is
not equivalence or proof that optimizer choice never matters. No model promotion
is authorized by this study.

The training deadline remains 3,600 seconds. Prior measured evaluation throughput
was 1.31 games/s (~73 minutes for 5,760 games), so this adapter has a predeclared
5,400-second evaluation deadline and 9,000-second combined deadline. CPU, memory,
worker limits and zero automatic restart remain unchanged. Historical owner
defaults stay 3,600/7,200 seconds for evaluation/combined execution.
