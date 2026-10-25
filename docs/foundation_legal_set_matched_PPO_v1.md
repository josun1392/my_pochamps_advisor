# Foundation legal-set residual matched PPO v1

This study adds an explicit `legal_set_training` opt-in while preserving the
historical `showdown-foundation-legal-action-set-context-v1` architecture marker.
It does not reinterpret the offline v1 marker or enable training by default.
A is the original Foundation actor. B copies all original tensors and named
Adam states, adds the 4,160 zero residual parameters, and leaves only their Adam
states empty. A and B use the same maintained FoundationCombatPPO class.

Frozen continuation seeds: 113021 and 114037. Each arm trains 65,536 new rollout
transitions (262,144 total), in 16,384-transition durable checkpoint windows.
Temperature is exactly one; no temperature wrapper, parent KL, fresh Adam,
opponent schedule, reward, feature, critic, slot sorting or PPO change is used.
The original 256-team subset, ordered bring-three and ten-slot/seven-identity
fixed opponent mixture remain unchanged. Four Subproc workers, CPU 50%, 12 GiB,
CPU device; no automatic crash restarts. Each resumed checkpoint must retain its
architecture and separate training contract. The B Adam clocks are intentionally
mixed: inherited old parameters keep the parent clock, new residual parameters
count only new updates. Integrity checks bind steps by name, not one global
clock for every parameter.

The opt-in observational audit uses the existing public scalar recorder.
Before each update it verifies T=1 masked probabilities, sampled old logp,
values, and GAE/returns against the actual complete rollout. Minibatch ratios,
KL, entropy, clipping, Adam clocks, residual gradients and changes are recorded.
It returns identical loss tensors and never changes rewards, minibatch order,
random sampling, gradient clipping or optimizer steps. Retained-data clone tests
compare parameters and Adam bit for bit with the uninstrumented update. Hooks
are removed before checkpoints and on exceptions. No privileged labels or
coordinator fields enter policy inputs.

Evaluation is frozen before learning: 192 clusters (96 non-learning teams from
the train domain, 96 validation-team clusters), three fixed rivals, two actual
seats, five policies = 5,760 argmax games. All 384 complete team identities are
unique across clusters, and none belongs to learner256. Thus case clustering
also avoids repeated complete-team clusters. Set/species overlap is disclosed;
no species-unseen claim. Known consumed scenarios and both-seat native
identities are excluded; sealed final assets are not accessed.

Primary: held-out-team B-minus-A, separately for each continuation seed and
averaged across the two at paired case-cluster level (20,000 bootstrap draws,
keeping seats, rivals and repetitions together). Two continuations do not
estimate a training-seed population distribution precisely. A larger independent
validation is suggested only if both differences are positive and the primary
combined 95% interval supports improvement; otherwise
`NO_EVIDENCE_OF_IMPROVEMENT`. No model promotion or automatic expansion follows.

The maintained detached study runner owns STOP, resource bounds, immutable
plans, battle-start/committed receipts, and no-duplicate resume. A missing
receipt for a started game fails closed rather than silently rerunning it.
