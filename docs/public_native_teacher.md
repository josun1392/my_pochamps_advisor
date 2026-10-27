# Bounded public native terminal teacher v1

The existing public teacher consumer and Foundation PPO are unchanged. This
provider does not implement ISMCTS, a hidden-set posterior or a new simulator.
ISMCTS samples information-set determinizations; that does not itself prove
the universal robustness required here. Existing pinned native TeamValidator,
statModify, legal preview, request action mapping, JSON fork and constant-RNG
proof are reused. No external implementation or engine is transplanted.
The [original paper](https://pure.york.ac.uk/portal/en/publications/information-set-monte-carlo-tree-search/),
[authors' implementation interface](https://www.aifactory.co.uk/newsletter/2013_01_reduce_burden.htm)
and [MIT C++ library](https://github.com/sfranzen/ismcsolver) were reviewed.
The latter two still need game-specific determinization/legal-action adapters;
neither supplies M-C reconstruction or an exhaustive support certificate.
No external code was copied or downloaded into this project.

## Attempted model scope and public boundary

One motif only: Heracross with known Guts, no status/boost, known empty item or
Leftovers, and legal Seismic Toss, against a publicly recharging last Charizard.
Both sides must have exactly two distinct publicly fainted selected teammates;
there is no omitted living switch target. Both active typings are ordinary,
field is known empty, and a restricted public prefix excludes unmodeled effects,
ability changes, transformations and identity ambiguity. Unknown trapping is
preserved; it cannot change this non-switch terminal action with no living bench.
Unknown active effects other than trapping are not silently treated as absent.

The provider receives only the native observation adapter's actor view. Its
constructor supplies pinned engine/catalog and a local budget ledger, never the
real native state, opponent request, selected-three, logits or RNG. The original
decision/observation/mask/policy/time binding is reused. Labels include conditions,
public provenance and hashes of native proof evidence. Unsupported cases abstain.

An explicit enditem/gain event establishes current possession; a later heal
attributed to a consumed berry does not restore that item. This narrow teacher
interpretation does not alter historical V4's lossy known-item summary/features.

## Current-state model checks, not a certified public teacher

* The pinned native Champions statModify enumerates HP points 0..32 (IV31,
  level50). All distinct legal max HP and every current HP whose native public
  CURRENT health display matches the observation are tested. This does not
  establish compatibility with all earlier public damage/heal observations.
* Charizard's pinned ordinary ability domain must be exactly Blaze/SolarPower.
  If unobserved, both are tested. A public incompatible ability abstains. No
  ability prior or neutral hidden modifier is assigned.
* Every representative team passes native M-C TeamValidator. Own base sets are
  legal witnesses to the exact authenticated own stats/moves/item; they are not
  the opponent's true set. Fainted/unselected members are nuisance variables.
* Public mustrecharge and closed three-member rosters eliminate all move/switch
  responses. Each native hypothesis independently verifies the sole request is
  Recharge. Unknown other moves/PP are not declared known or used as features.
* All legal opposing speed endpoints exceed observed own speed, so order is
  fixed. Other non-HP spreads are nuisance variables: fixed level damage has no
  attack/defense dependency, no incoming attack executes, and a native getStat /
  storedStats guard rejects any non-speed hidden stat read during the branch.
* Existing proveConstantRNG rejects nonconstant draws, including tie/random
  order. Every world must immediately terminate in +1. This saturates native
  sparse terminal return; it does not prove other actions lose or uniqueness of
  an optimal action. It is not a sampled continuation win-probability estimate.
* The complete reconstructed public view must match the supplied view, including
  history, own request, HP displays, identities, PP, choices and mask. Only the
  existing transport fields are ignored. A contradiction yields no label.

The final causal audit exposed a decisive gap: the initializer copies the supplied
public log, without demonstrating a native causal prefix for each constructed
world. For example, a low-max-HP world can match the current percent but contradict
an earlier observed fixed-50-damage transition. Copying that transition into the
world's log is not a reconstruction proof. Full view equality is necessary but
insufficient. Thus even a backend `proven` result refers ONLY to the current-state
model. The final provider ALWAYS ABSTAINS with
`causal_public_history_witness_unavailable` after such a model proof. It generates
no approved target, including on synthetic fixtures. Provisional development
receipts predating this audit are not training labels.

These attempted reductions do not certify complete public-consistent hypotheses,
arbitrary hidden sets, middle-game reconstruction or long-term action quality.
No continuation platform or broad mechanics interpreter is added. This teacher
path is closed in the bounded scope; do not propose another extension experiment.

## Receipts, consumer and stopping rule

Proofs are local, SHA-bound and keyed by full public view plus native-owner source
hashes. Corrupt receipts fail closed; completed proof batches can be inspected
without repeating native worlds. The consumer uses only the public view and the
legal target distribution, not the hypothetical state/proof fields. All native
construction/fork attempts and branch decisions reserve the shared micro ledger
before execution. Native execution is off by default; receipt rechecks cannot
silently launch another batch. No Adam is needed for provider verification.

Synthetic native fixtures are separate from preserved actual TRAIN decisions.
The 512-row audit uses every public_before row in frozen file order. Actual
approved targets must reach >=16 different decisions and >=2 situation families
with independent TRAIN/held-out cases before any micro learning. Otherwise no
PPO or evaluation is launched. Do not expand this teacher path after a failed
coverage gate. Compare a teacher-free four-component learnability micro task
(frozen self-play, T=1 exploration, opponent prediction, public tactical features)
as the bounded alternative; no such follow-up is automatically authorized.
