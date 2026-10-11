# Experimental action-conditioned policy/value model

This artifact is opt-in. It does not change PokeAdvice's guaranteed-first policy.
Use the shared pinned native Dex at `../showdown_initial_v1/catalog.json`.
Model SHA256: `364e30469d8a30106f90c04e0fc59a601b92f541af8b41235d08bd67af06d667`.

SB3-contrib MaskablePPO2.7.1 / CPU Torch2.8.0;122626 parameters.
Observation v2:321 pooled public-context features +35 action rows×140 features.
Shared action scorer128/64, context64, critic128/64; bounded discounted-return value.
Native action schema v1 and complete public history are required. Unknown opponent
items/moves/sets/RNG are never policy inputs. Static type priors come from Showdown.

Selected by validation only:71 wins/96 episodes; seed73;8192 visible heuristic
demonstrations/12epochs/768 optimizer updates, then32768 PPO transitions/1024 updates.
Teacher-data agreement97.58% is a fitting diagnostic, not strategic win probability.
Save/reload and actual Qt inference/rollback were verified on this exact hash.

Fresh test offset30000,64 independent case clusters×3 reference opponent strata:

| Policy | Test W/L | Unseen-species W/L |
|---|---:|---:|
| This model |130/62 (67.7%)|130/62 (67.7%)|
| v1 model |102/90 (53.1%)|96/96 (50.0%)|
| Prior action model |123/69 (64.1%)|119/73 (62.0%)|
| Visible heuristic |133/59 (69.3%)|140/52 (72.9%)|
| Random |70/122 (36.5%)|49/143 (25.5%)|

All192 episodes per policy/split completed; zero draws/truncations. Versus v1,
case-cluster bootstrap95% intervals for win-fraction differences are+8.3…20.8pp
(test) and+9.4…25.5pp (unseen). Improvement versus the prior action model is not
statistically established. This model remains below the heuristic, especially on
unseen species. The pooled Wilson interval60.8…73.9% is descriptive because the
three rival strata share each case; paired comparisons retain those case clusters.

Value-return MSE0.530/0.586 remains uncalibrated. Neither value nor action softmax
is an exact win probability. Training includes10 species; unseen evaluation uses6
disjoint species, not the entire M-C roster or a tournament-strength opponent pool.
The policy does not learn team preview selection or recurrent belief memory.

Inference p50/p951.023/1.263ms over1000 calls; actual Qt dispatch85ms/end-to-end845ms.
Runtime/ledger remained immutable and disabling the opt-in restored identical default
output. Twelve further native smoke episodes10W/2L included attacks, switching,
forced replacements, waiting, Mega, statuses, ability/item and weather events.

All earlier checkpoints remain in the task-owned AppData run directories. The
original v1 artifact remains untouched for rollback. See `training_summary.json`,
the evaluation files, `readiness.json`, and `../../docs/autonomous_learning.md`.
Historical rival identity in this release was reconstructed from the single-run
ordered validation-selection history; new trainer checkpoints persist/freeze it
directly. Interrupted rollouts are discarded on resume, never represented as exact
native episode restoration.
