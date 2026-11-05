# Candidate context residual-only TRAIN pilot v1

Separate opt-in experiment; no production loader/actor changes. It reuses the
Foundation PPO/GAE/auxiliary/uniform-KL objective, native Gym, own-player encoder,
strict transported masks, legal-set residual and existing execution audits.

A uses the legal mean of the existing scorer's 64 joint penultimate features.
B replaces that mean with the current candidate's own joint feature. Both use
the same original scorer twice, 64x64+bias residual, 679,099 total parameters,
4,160 trainable parameters, zero projection and fresh residual-only Adam.
Only the context source differs. Both are row-permutation equivariant at fixed
global context. B adds no new cross-candidate information route. Inherited
native move-slot sensitivity remains separate.

All original Foundation tensors, critic, prediction heads and original Adam are
frozen. The unchanged value/auxiliary losses are still measured but have zero
gradient to the new path by construction; this is not full-network PPO. Global
clipping, LR, entropy, uniform KL, rewards, GAE and frozen rival are unchanged.
The separate loader reconstructs requires_grad and optimizer bindings on reload
and verifies weights/Adam/encoder/mode SHA. Historical LearnedPolicy does not
accept these experimental checkpoints as production Foundation models.

Two paired seeds 116051/116053, each A/B 16,384 transitions, total65,536.
Each arm uses16 segments of1,024 transitions (two512-transition rollouts).
Four sequential native workers receive a fixed template for256 transitions per
segment. Sixteen reciprocal templates from8 TRAIN team pairs each receive
exactly1,024 transitions. PPO's existing rollout bootstrap is preserved; forced
segment resets are recorded, not counted as terminal wins/losses. Team exposure
quotas and order match A/B; on-policy trajectory and episode counts can differ.
Durable checkpoints at4K/8K/12K/16K; only16K endpoints are compared.

Eight disjoint TRAIN-domain development team pairs, both roster owners, four
RNG replicates and both actual native seats give128 games per final model,
512 games total. This is a small development comparison, not independent
generalization evidence. Freeze teams/seeds/selection before training. The
old96/288 source manifests/team assets are read only to create exclusion
fingerprints; no outcomes, policy observations or sealed results are inputs.
Unordered complete rosters and joint-moveset signatures plus all old case IDs
and native seeds are excluded. Development teams are disjoint from pilot
training teams but may have appeared in historical Foundation TRAIN material.

Preflight must prove zero-output equality, exclusive residual gradients and Adam
binding, original model/Adam preservation, strict masks, set-vs-local routing,
and save/reload/continued copied optimizer behavior before native training.
Tiny discarded copied-Adam contract tests are separate from the native PPO
budget. No offline branch teacher, tuned projection or model selection.

Hard CPU50%, RAM12GiB, four workers, CPU-only, no external providers;120-minute
execution deadline and STOP via existing RuntimeLimit. No automatic retries or
replacement seeds. Record starts, errors, terminal/truncation, all rollout
logp/value/GAE audits, residual updates and pair-cluster uncertainty. On failure
preserve completed checkpoints and report PARTIAL. No automatic followup run.
