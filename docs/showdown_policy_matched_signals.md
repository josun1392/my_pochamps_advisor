# Foundation policy-matched counterfactual signals v1

Opt-in replay of the32 existing TRAIN snapshots from5e35f83. No new decision
collection, PPO, optimizer step, model save, independent battle evaluation or
promotion. Existing actors, critic, masks, native mechanics and rewards stay intact.

Before native execution verify all source SHA, behavior actor/critic tensors,
public feature/mask SHA, old logp/value and original GAE buffer row. Reconstruct
frozen learned opponents by their recorded ZIP identities and original argmax
inference. Stateful heuristics whose root RNG was not captured are excluded,
not approximated by a new seed or another policy.

The historical actor's exact T=1 distribution is recovered; its original global
Torch RNG state was not archived. New paired local categorical streams are
explicit Monte Carlo samples, not recovery of its original random trajectory.
Native root PRNG is preserved; eight new future PRNG samples are predeclared.
Force the recorded own first action versus sample the first action from the
captured behavior distribution. Both consume the same first categorical draw,
then use the SAME captured actor and recorded opponent on their OWN public views.
No current parent/final-policy substitution. Native hidden truth is replay-only.

Preserve Gym automatic wait aggregation (no actor draw for automatic wait).
Report sparse reward return with gamma1; terminal has no bootstrap, native time
limit adds the same captured critic's player-visible timeout value. Also compute
the finite rollout lambda target with lambda.95 and original horizon128-t;
this is a new diagnostic estimate, never the original recorded GAE.

Full policy-relative advantage is mean Q(forced first action)-V(sampled policy
first action), both continued under the same frozen policies. Also report
Q-critic and finite-lambda analogues to expose value-baseline/GAE bias. These are
different estimators; no optimal-action labels or automatic arithmetic-defect
claim. Root-conditioned true hidden state is not a public-information posterior.

Allocation is fixed before results:8 paired samples plus root binding, original
suffix replay and one exact repeated forced branch =19 native units per eligible
root. Expected24 eligible roots use456 units; reserve16 for regressions. Global
authorization512; script cap496. Failures consume a slot; no automatic retry or
new root collection. A started output refuses duplicate execution.

Root-cluster bootstrap20,000 times keeps stochastic pairs inside their roots.
Do not treat repeated samples as independent states or training-seed replication.
Report Monte Carlo uncertainty and rare-action limits. Do not discard bootstrap
draws with undefined correlations. Predeclared evidence gate:at least8 roots
with a nonzero paired terminal difference and an estimable correlation95% CI
excluding0; otherwise INCONCLUSIVE. Failed authority/reconstruction is DATA_GAP,
not permission to fill missing state. Evidence is not model promotion or strength.
