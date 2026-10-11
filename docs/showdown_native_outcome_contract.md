# Native outcome evidence v1

The existing exact selected-action ledger owns conditional action probability
and a private post-action view. Native seeded execution does not supply that
probability. The default backend and guaranteed-first policy remain unchanged.

`showdown-native-outcome-evidence-v1` binds a captured runtime/session, D0 branch,
actor/comparison target/action, native source phase, explicit choices, scenario
assumptions and immutable native checkpoints. Native target semantics belong to
Showdown (a self-heal targets the actor even though a strategy pair has an opposing
comparison target). Every represented state remains hypothetical.

Evidence classes are separate:

- `native_seeded_execution`: a precise native execution at a particular complete
  state/choice/seed, with no probability mass or guarantee about other seeds.
- `native_conditional_exact`: a proven complete distribution within the named
  scope. The first slice proves one complete native move attempt by rejecting any
  nonconstant RNG request. Its mass is one because no uncertain RNG was used,
  not because one sample happened to succeed. Constant RNG calls may advance the
  native PRNG but must provably return a constant value to their caller. The
  checkpoint preserves one native seed for continuation; the claim does not
  cover a distribution over future PRNG states.
- `native_monte_carlo_estimate`: existing sampled shadow evidence, separately
  labeled, excluded from exact selected-action consumers and ranking.
- `legacy_guaranteed_exact`: existing authority retains its compatible consumer;
  native data never self-declares this class.

The proof runs the existing native queue/progression path. It observes the native
PRNG entry points, permits only singleton integer draws and constant Bernoulli
predicates, and rejects raw/unproven RNG, forced randomChance and Math.random.
It copies no battle mechanics or PRNG algorithm. It stops after the full native
runAction callback and retains deferred opponent/residual/pivot queues.
RNG rejection yields no partial evidence or truncated probability mass.

The first legacy consumer replacement is opt-in plain direct healing. It requires
the same fresh D0, native first actor/move identity, matching observed HP/max HP,
and an unchanged native participant/field view except the actor's HP and spent PP.
Additional effects, status-gate cancellation, known PP projection or phase changes
outside the compatible view fail closed. The full native checkpoint stays attached
for native continuation. The compatibility projection changes no live state.
Explicitly bound stochastic-proof rejection retains the original compatible backend
under its existing action-opportunity gate. Transport unavailability can be handled
by calling that original backend directly. Other unsupported projections fail closed;
resolved contradictory or misclassified evidence is rejected.

Sixteen fixed-crit damage rolls and the status callback evaluator retain their
existing narrow probability scopes; neither becomes a full action/KO ledger.
No general exhaustive battle/RNG enumerator is introduced.

The opt-in seam is `family_authorities.native_direct_heal_outcome` on the
selected-action executor, or `extension_authorities.native_direct_heal_outcomes`
(optionally keyed by action ID) on the gated executor. A proof from the root is
never rebound after a gate changes the detached state. Existing production
orchestration does not automatically supply these records. Native evidence keeps
its class/scope through the compatible path and cannot declare an unconditional
guarantee across hypothetical sets. Disabling the seam calls the unchanged legacy
materializer. Monte Carlo shadow configuration/rollback remain separate.

Upstream investigation: pinned Showdown `sim/prng.ts`, native progression and
`sim/tools/exhaustive-runner.ts`; Champions Lab's serialize/reseed factory;
pkmn/engine's Generation I Chance/Calc/FixedRNG functionality. The latter does not
provide a Champions M-C adapter, and the exhaustive runner covers test combinations
instead of proving battle probability mass. No additional upstream source is copied.

Sources: [pinned PRNG](https://github.com/smogon/pokemon-showdown/blob/942cda71d14bf0618bd57991708a2e2734b6daba/sim/prng.ts),
[exhaustive runner](https://github.com/smogon/pokemon-showdown/blob/942cda71d14bf0618bd57991708a2e2734b6daba/sim/tools/exhaustive-runner.ts),
[pkmn/engine Gen I design](https://github.com/pkmn/engine/blob/main/src/lib/gen1/README.md),
[Champions Lab](https://github.com/joshuamatalon/champions-lab).
