# Public categorical training readiness

This prepares bounded **source-run** experiments; it changes neither live
recommendations nor historical models. Engine `942cda71d14bf0618bd57991708a2e2734b6daba`,
`gen9championsbssregmc`, V8 team bank and opponents remain unchanged.

## Objective and resume

New categorical experiments may explicitly set `gamma: 1.0`, `gae_lambda: 0.95`,
`objective: native_terminal_win_loss_draw_undiscounted_v1`. Rewards remain native
terminal +1/-1/0, with zero intermediate reward. Gamma 1 introduces no discount
preference for match length; GAE lambda remains an estimation choice, not reward
shaping. Values are learned return estimates, not exact win probabilities.

Checkpoint metadata binds actual serialized gamma/GAE, objective, encoder/category
fingerprints, native domain/engine and normalized source hashes. Restoring an
incompatible objective is rejected before changing the loaded model. Historical
gamma .99 artifacts retain their semantics and can still load without the new
objective field. V3/V4 weight transfer uses a **fresh Adam**; transferred critic
weights initialize the new objective, rather than converting old values into
undiscounted estimates. Historical optimizer state is not claimed to transfer.
Evaluation value-error diagnostics use the actual loaded model gamma. Legacy
fields containing `discounted_return` keep their names for compatibility; consult
`value_gamma` and `training_objective` for their precise scope.

## Artificial limits and upstream bootstrap

`max_decisions` closes the native environment with `truncated=true`,
`terminated=false`, reward 0, winner null. It is not a native loss or draw. A
separate `showdown-public-timeout-bootstrap-v1` payload supplies continuation
choices/masks derived exclusively from each player's existing visible request.
Normal execution masks remain closed, and stepping beyond the limit is rejected.
The Python adapter validates owner, revision and mask/choice binding, then gives
Gymnasium the public continuation features as its final observation. SB3's
DummyVecEnv/SubprocVecEnv set `TimeLimit.truncated` and `terminal_observation`;
MaskablePPO applies its existing gamma*V(final) correction and GAE. Missing
bootstrap information fails closed. True native terminal outcomes are unaltered.
Prior rollouts are not retroactively reinterpreted.

## Narrow own-identity compatibility fix

The integrated v1 encoder can fail on own `p1a: nickname` / `p1: nickname` aliases.
This was reproduced during real PPO2477 continuation, including native hitcount
references emitted after fainting. The opt-in
`showdown-public-categorical-observation-v2` retains the same tensors, embedding
architecture and numerical V4 features, but binds categorical own records to
unique player-visible own-request identifiers and the latest public appearance.
When a wait request has no roster, only an entirely empty unpositioned reference
with one matching positioned appearance is dropped. Populated ambiguous records
still fail closed. Opponent apparent records are never merged. Historical public
state/replay projections and v1 fingerprints remain unchanged. Both versions are
explicitly loadable; v1 weights cannot silently load under v2 metadata.

The shared embedding architecture remains 15,576 float inputs and 360,858 model
parameters. Bits pass unchanged through the raw FlattenExtractor and are decoded
only by embeddings/gather; nonbinary transport is rejected. No VecNormalize is
introduced. The six-record appearance and 16-known-move capacities still reject
unsupported states. Numerical/history coverage remains the established V4/public
state-v2 scope, not a complete Markov representation or recurrent memory.

## Distribution and reproducibility

V8 contains 4,096 training, 512 validation, 512 test and 512 rare-form assessment
teams. All 231 base species are eligible. Complete team identities and joint
species/moveset combinations are separated; individual sets/species can recur.
No species-unseen claim follows. The coordinator keeps seeded random ordered
three-of-six selection. There is no learned team-preview policy.

Checkpoint `episodes.json` records reconstructed initial scenario identity, team
hashes, ordered selections, native seed, frozen opponent identity, terminal versus
truncation outcome, and active episode cursors. These are coordinator records,
excluded from actor/critic features and Gym info. They bind the interval's endpoint
checkpoint, not every stochastic decision's changing policy. Source-run config
fingerprints also bind the encoder/trainer/evaluator source. Initial scenarios can
be regenerated; exact interrupted rollout replay cannot be claimed without action
logs, sampling RNG state and native mid-rollout checkpoints. Resume restores
model/Adam and starts fresh episodes under the established trainer protocol.

## Recommended first study (not launched here)

Use two independent seeds **73011, 73012**, **131,072** new transitions each:

- V2 public categorical encoder; explicit gamma 1, GAE .95; V8 unchanged.
- PPO2477 weights `c7f120d7ff5f14c127e030affb1887412c55012eea818dd40b6d98e1242df151`,
  fresh Adam, no imitation warmstart; LR 5e-5, entropy .01.
- Existing MaskablePPO rollout 128 per worker, batch 128, four epochs, target KL .03.
- Training mixture: max_power, champions_heuristic, tactical_heuristic,
  frozen compatible v4 (`986ea2ba562d0b34df50ec2ca88ae3171e37031f6f358e9aa5813ffe01412641`)
  and v3 (`fe52cd3b4e288c242176a6574769bdf1cd8fb5dbedad8b015496cb5b5dcfd57d`).
- CPU only, eight Subproc workers, one Torch thread, Windows CPU cap 50%,
  job memory cap 12 GiB, one-hour total wall ceiling, native max_decisions 256.
- Checkpoint every 32,768 transitions. Validation 32 paired cases per four fixed
  rivals, offset 73,300,000; masked argmax evaluation, stochastic PPO training.
- Plateau patience 12 keeps this small fixed-budget comparison from stopping
  just because five validation scores fluctuate. Preserve every checkpoint.
- `final_test_cases: 0`: no sealed final data consumed or automatic promotion.

Validate the generated JSON with the existing source trainer, then use its normal
`--config`, `--output`, `--resume` and `--stop` interface. Outputs belong outside
the repository. Wall-limited runs may end before their transition target; resume
under the same frozen config/source and record the new episode boundary.

The existing packaged Windows Trainer.exe predates this objective/V2 contract.
This task does **not** rebuild that distribution or make gamma-1 models eligible
for the live advisor. Use the verified source runtime for this study; packaging
can be a separate bounded follow-up. Existing opt-in UI and guaranteed-first
rollback remain intact. Readiness does not imply win-rate superiority at 131k.
