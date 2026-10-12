# Strong-policy research and integration choice

Reviewed 2026-10-12; native revision `942cda71d14bf0618bd57991708a2e2734b6daba`.

| Implementation | License / current integration evidence | Practical decision |
|---|---|---|
| [Metamon](https://github.com/UT-Austin-RPL/metamon), [paper](https://arxiv.org/html/2504.04395v2) | MIT; inspected revision `0a00a75`, v1.6.0. Gym <=0.29.1 conflicts with installed1.2.3; Kaizo helpers require fork-specific `Pokemon.previous_move`, absent here. OU datasets/9-action interfaces differ from M-C bring6/pick3 and35-action masks. Maintained intermittently; existing large checkpoints are not M-C experts. | Reuse diverse public trajectories and clipped advantage-weighted likelihood idea; do not import the framework, infer hidden replay sets, or download large OU weights. |
| [AlphaStar league](https://deepmind.google/blog/alphastar-mastering-the-real-time-strategy-game-starcraft-ii/), [released code](https://github.com/google-deepmind/alphastar) | Apache2 released architecture/offline tools; Linux/Python3.9/SC2 interfaces. Released repository does not provide online league training code. | Use a small fixed pool of SHA-bound historical opponents. This is diversity sampling, not a full AlphaStar league, Nash solver or exploitability claim. |
| [AWR reference](https://github.com/xbpeng/awr), [requirements](https://raw.githubusercontent.com/xbpeng/awr/master/requirements.txt) | MIT; TensorFlow1/Gym/MuJoCo stack incompatible with current PyTorch/Gym. Small exponential weighting formula is reusable. | Narrow masked Monte Carlo AWR-style pretraining using existing actor/value and Adam; complete-episode returns, detached weights and clipped20 cap. No custom PPO/Q/RNG implementation. |
| [RLlib MARWIL](https://docs.ray.io/en/latest/rllib/rllib-algorithms.html#marwil) | Apache2, maintained PyTorch weighted likelihood implementation. New runtime/model/checkpoint adapters would add substantial integration work. | Formula comparison; keep current SB3 runtime. |
| [imitation BC](https://github.com/HumanCompatibleAI/imitation), [d3rlpy](https://github.com/takuseno/d3rlpy) | MIT, maintained. Standard BC call does not pass our per-state masks. Inspected discrete d3rlpy target uses unmasked argmax. | Small masked BC control is cheaper than adopting another framework; discrete off-policy Q methods require validated mask-aware targets and compatible critic contracts first. |
| Native Showdown Champions random teams | MIT. Actual native pilot100teams:95Item-Clause rejections. Generator already implements role/move pairing, team typing, abilities and items. | Reject/retry complete teams using M-C TeamValidator. Preserve native generated spreads and explicitly label them coverage fixtures rather than expert usage data. |

## Bounded hypothesis and limitations

Earlier single-teacher imitation learned action biases but weakly related them to eventual wins. Collect both winning and losing episodes from multiple public-information policies; compare uniform BC with return-weighted likelihood, then apply equal maintained PPO budgets. These are executed actions, not counterfactual optimal labels. A Monte Carlo return depends on the behavior's continuation and opponent mixture; it is not an exact conditional action value. No action-type reward or legality modification is added.

The current small feedforward action-conditioned network compresses history. Metamon motivates future sequence memory and longer-horizon critics, but a compatible M-C dataset and empirical control come first. This experiment does not reproduce Metamon's Q critic, million-battle transformer, league search or human strength. Recurrent/off-policy learning remains a separate evidence-driven extension if the small adapter fails.

## Data and selection contract

Encoded observation/mask/action/discounted terminal return/episode group are the only row fields. Actor/value tensors have no full opponent sets, native checkpoints, queued choices or future seeds. Full episodes must terminate; truncations and unfinished prefixes do not produce Monte Carlo labels. File hashes, native pin, encoder/catalog version, source-policy SHA, gamma and training split bind the dataset.

Training data uses native-bank train teams. Checkpoint validation uses separate native-bank validation teams at44000. Additional validation scopes may use fresh validation offsets; reserved unseen species and final880000 stay unopened until model selection ends. Case-cluster bootstrap intervals retain all opponent strata; they are exploratory, not exact guarantees or corrected multiple-comparison claims.
