# TRAIN Foundation opponent diversity harness

This is an offline-validated option, not an authorized learning/evaluation plan.
No model, reward, inference feature, simulator or live advisor changes.

## Opt-in boundary

The existing controlled `learned_fixed_micro.training_vector` accepts an
optional `train_foundation_opponent` manifest. With the key absent, the exact
existing `league_s0`/`FrozenPublicActor` argmax branch remains in use. No policy
names are added to production baselines or evaluation rival registries.

The opt-in currently requires the maintained MATCHUP controlled factory, the
existing `opponents=['league_s0']` binding, and four explicitly addressed TRAIN
case factories. Their seed/worker/segment metadata must match the manifest.
Other old curricula are not silently reinterpreted. Future experiment owners
must pass a new manifest to the runtime adapter explicitly; historical plans
are not edited and existing owners do not automatically adopt a new mixture.

Required manifest keys (no defaults/extra fields):

- `schema_version`: `foundation-TRAIN-opponent-policy-diversity-v1`
- `scope`: `train`
- `model_SHA256`: verified frozen Foundation checkpoint identity
- `training_seed`: explicit integer continuation seed
- `rng_namespace`: explicit experiment stream namespace
- `policy_slots`: caller-supplied bounded list containing only the two names

`foundation_argmax` delegates to the current argmax execution and consumes no
sampling draws. `foundation_masked_sample` delegates to the maintained T1 masked
CDF sampler over the same model's probabilities. Native masks are authoritative;
illegal probability mass, empty masks or mismatched proof identity are rejected,
never repaired or replaced by random/uniform behavior.

Policy slots use case_index modulo list length, matching existing cyclic
episode selection. Duplicated slots can express caller-fixed weights; their
exact nominal probabilities and manifest SHA are recorded. This is not iid or
decision-weighted exposure, and finite-run actual exposure still needs audit.
**No study mixture, ratio, budget or training schedule is selected here.**

## Information and RNG

Only the original owner-visible view reaches Foundation.infer. Public session,
model, request revision and 35-action schema are bound before a sample is drawn.
The frozen model/Adam are never updated. Existing public_input and masked_sample
remain the validation/sampling authorities; no new neural network is present.

The stochastic policy owns a per-case NumPy PCG64 Generator, addressed by the
manifest namespace, training seed, worker, segment, case index, policy and model
ID. It never consumes learner/Python/global NumPy/Torch RNG. Native seed and team
hashes are coordinator audit metadata only: they do not influence the sampling
seed, candidate probabilities or forward inputs. Singleton stochastic choices
still consume one float64 draw, just like the existing T1 sampler.

AuditedPilotEnv records the selected policy/mode, model, team/case identity,
stream address and manifest. Its existing native trace copies opponent.last,
which includes the public proof, uniform draw and before/after RNG hashes.
No new data are added to policy observations, rewards or Gym info.

## Checkpoint boundary

The adapter's JSON state_dict stores its identity, PCG64 state, successful
selection/draw counts and bound public episode/revision with a content hash.
load_state_dict only accepts a fresh adapter with matching model/manifest/case;
it verifies the PCG64 state against the initial stream advanced by the recorded
draw count before changing state. Missing/corrupt/mismatched states fail closed.
Replaying an old state into a live adapter is refused.

This is trusted local adapter state, not a tamper-proof signature or a complete
native/rollout checkpoint. An unchanged public session is required after reload.
Use the already-safe RNG-neutral model loader. Legacy autonomous/pilot cold
resume remains fail-closed; this option does not enable it.

## Validation limits

Only synthetic public views, fake models and mock Gym wrappers are exercised.
Checks cover unchanged argmax inputs/outputs/RNG, exact maintained CDF samples,
singletons, illegal distributions, seed/session/model isolation, JSON reload,
stream/counter mismatch and default/opt-in wrapper provenance. Tests do not
authorize actual native starts, rollout/PPO/Adam, inference or evaluation.
Strategic diversity/strength, native throughput and learning effects remain
unmeasured and require a separately approved experiment.
