# Frozen Foundation opponent quality pilot

`opponent-diversity-quality-pilot-v1` is an opt-in research evaluation, not a
TRAIN-manifest escape hatch or a production opponent change. It reuses
`FrozenPublicActor`, validated Foundation inference, the existing masked CDF
sampler, PCG64 addressing, native seats, bounded start intents, and idempotent
per-game result receipts. The TRAIN-only adapter remains TRAIN-only.

The frozen plan contains 160 native-valid complete teams, 80 pairs, two ownership
directions, two independently reproducible native seeds, both actual native
seats, and both candidate modes: exactly 1,280 starts, 640 per mode. Source
generation's logical seed is 116081, mapped by the maintained `seed4` function;
only the first 160 eligible teams in one immutable 200-candidate batch are
admitted. Semantic team, roster, and joint-moveset identities exclude maintained
bank partitions, prior pilot teams, sealed **source identities only**, and all
previous independent development sources/candidates. No sealed outcomes are
read. Reusing individual sets/species does not imply unseen-set generalization.

Only the validated owner's public view enters either policy. A forward pre-hook
records the existing action scorer's legal logits from that same inference;
there is no second counterfactual policy run. T=1 probabilities and argmax are
checked against those logits before recording. Native hidden state is serialized
only in the coordinator to compute initial-state digests; it is never an actor
input or a saved model. Initial native state, public input, legal logits and
probabilities must match between modes for each scheduled case/seat. Divergent
trajectories need not consume equal native RNG afterwards.

Sampling uses one private PCG64 stream per policy/case/actual seat/role, including
one explicit draw for singleton masks. Addresses contain no native seed, team,
or hidden state. Global Python/NumPy/Torch RNG is checked around every inference,
and checkpoint loading uses the existing RNG-neutral contract. Every decision
retains its policy, owner, legal mask, choice, same-logits argmax, probabilities,
entropy, family, draw and before/after RNG digests. Native execution must link to
the preceding two authenticated selections. Coordinator outcome receipts do not
export private requests. Original parameter/Adam digests and model ZIP/Adam
archive hashes must remain equal.

The primary comparison is sampled minus argmax terminal return, with 20,000
bootstrap draws (seed116085) resampling 80 team-pair clusters while retaining
ownership, native seed, real seat and policy pairing. Decision diversity is the
non-argmax fraction of sampled decisions with multiple legal actions. The
predeclared point screens are diversity >=5% and win difference >=-10pp. These
are exploratory screens, not noninferiority or PPO-learning benefit tests.

`scripts/pilot_opponent_quality.py` requires a frozen plan and offline PASS gate.
An exclusive detached owner runs one worker under CPU50%, RAM12GiB, GPU-off and
a bounded wall cap. It forbids learning, rollout collection, Adam updates and
model saves. Per-game results are persisted before cumulative progress delivery.
No retries, automatic restarts, native cold-resume fallback, source redraws or
budget increases are supported. Existing start/failure/completion records block
duplicate launch. Any missing result, rejection, truncation, provenance mismatch
or replay/RNG mismatch fails closed and preserves partial evidence. Only a
separate T1 approval may authorize subsequent PPO, additional evaluation or
promotion.

Raw teams, traces, native-state digests and model artifacts stay in the external
research artifact directory, never in Git. Final Git closure is performed only
after focused/nearest tests, compilation, diff checks and native receipt audit.
