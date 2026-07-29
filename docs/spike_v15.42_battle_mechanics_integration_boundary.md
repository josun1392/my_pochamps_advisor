# v15.42 Battle Mechanics Integration Boundary

## Decision

The project remains authoritative for observations, provenance, unknowns,
candidate identity, and advice ranking. Use the existing pinned
`@smogon/calc` package behind a versioned local adapter as the calculation
reference for a **fully specified**, generation-scoped damage result. The
repository already pins `@smogon/calc` 0.11.0 in `tools/smogon_bridge`; its
strict request/response schemas make a small integration seam possible.

This does not replace the repository-native Q12 engine. `advisor.damage` and
`advisor.probability` remain supported deterministic implementations and
parity/reference material. A future slice must not silently change the source
or defaults of an existing estimate.

## Current mechanics inventory

| Area | Existing responsibility | Boundary observation |
| --- | --- | --- |
| Damage/modifiers | `DamageContext`, `calc_damage_rolls`, `Field`, type, ability, item, weather, screen, critical, and Q12 helpers | Pure Python; concrete inputs cannot express unknown facts. |
| Probability | `advisor.probability` consumes damage-roll outcomes for KO calculations | Downstream of a resolved distribution; never an inference source. |
| Parity bridge | `advisor.parity` calls `tools/smogon_bridge/calc.js` with strict `DamageRequest`/`DamageResponse` | Local Node subprocess, not remote service; request presently requires concrete stats, ability, item, boosts, and HP. |
| Candidate route | `TurnSnapshot` -> `build_snapshot_damage_input` -> `evaluate_move_candidate` | Snapshot identity, ownership, detached copying, and unavailable reasons already belong to the product. |
| Legacy estimate | `llm.advisor_damage_estimate` supplies level-50/31-IV/zero-EV defaults | A legacy presentation lane; not a hidden-default policy for the future adapter. |
| Provider route | evidence bundle -> structured payload -> grounding validation | The LLM may rank immutable evidence; it never computes mechanics. |

## Candidate sources and selection

| Candidate | Suitable responsibility | Update/operational model | Decision |
| --- | --- | --- | --- |
| Existing `@smogon/calc` bridge | Generation-aware damage rolls and supported battle modifiers | Pin package/lockfile; upgrades require fixture and parity review | **Recommended calculation reference** for complete inputs. |
| Existing Python engine | Current product calculations, Q12 mechanics, probability composition | Project-owned source/tests | **Retain**; no rewrite in this milestone. |
| Pokémon Showdown simulator/Dex | Upstream game/format data and simulator semantics | Fast-moving TypeScript repository with broad execution surface | **Reference only**; do not embed the simulator in UI/provider flow. |
| PokéAPI | Display/ancillary species, move, and type metadata | Public API and generation-related resources | **Optional metadata supplement only**, never mechanics authority or runtime prerequisite. |

`@smogon/calc` is the public Pokémon Showdown calculator core and includes a
generation data layer. The two-part authority is intentional: upstream calc
data decides a complete formula, while this project decides whether evidence is
complete enough to call it and how incompleteness is exposed. A library default
can never upgrade an unknown item, ability, stat, boost, or HP fact.

Sources: [Smogon damage-calc](https://github.com/smogon/damage-calc),
[`@smogon/calc` package](https://www.npmjs.com/package/%40smogon/calc),
[Pokémon Showdown](https://github.com/smogon/pokemon-showdown), and
[PokéAPI v2](https://pokeapi.co/docs/v2).

## Ownership and architecture

```text
BattleState / TurnSnapshot
        -> MechanicsInputAdapter (authority, identity, generation, completeness)
        -> MechanicsEngine (pure deterministic; no LLM, UI, session, or network)
        -> MechanicsResult (known / bounded / conditional / insufficient / unsupported)
        -> CandidateEvaluator (slot order and reasons; no fact rewriting)
        -> structured LLM payload (immutable mechanics evidence only)
```

External/imported ownership is species/move/type/ability/item metadata,
generation rules, base formula, accuracy/priority, stage multipliers,
status/weather/terrain modifiers, and damage rolls. Project ownership is
observation capture, `TurnSnapshot`, evidence/authority, unknown policy,
candidate/ranking behavior, grounding-v1, UI/session safety, the adapter/result
contract, release pinning, and parity tests.

The future engine concept is `evaluate(MechanicsInput) -> MechanicsResult`.
Neither interface accepts provider clients, widgets, sessions, request tokens,
reducer/ledger state, or raw observations. A bridge implementation is allowed
only behind this pure adapter.

## Unknown-aware result contract

| Status | Meaning | Safe content |
| --- | --- | --- |
| `known` | Required facts are authoritative | generation label, roll range, optional KO probability, applied logical paths |
| `bounded_range` | Product supplied explicit finite alternatives | inclusive range plus named alternatives, without claiming a current one |
| `conditional` | Authoritative unresolved branches determine outcome | branch condition paths and a result per branch |
| `insufficient_context` | A required fact is unknown/insufficiently authoritative | allowlisted missing paths/reasons; no numeric damage or KO claim |
| `unsupported_mechanic` | Outside implemented capability | stable capability/limitation identifier only |

Missing EVs, IVs, nature, item, ability, boosts, or HP are never defaulted.
Only `known` may create an unconditional damage/KO fact. `bounded_range` and
`conditional` remain deterministic evidence but cannot become confirmed runtime
facts. Mapping these states to existing candidate `resolved`/`partial`/
`unavailable` remains a project-adapter concern.

## Proposed adapter/API contract

`mechanics-input-v1` contains explicit generation/format, canonical attacker
and defender identities, the exact owned move slot, authoritative field facts,
allowlisted unknown paths, and a supported capability. `mechanics-result-v1`
contains the status, capability, permitted damage/KO facts, dependencies or
missing paths, and internal-only pinned engine provenance.

The strict bridge request is constructed only for `known` inputs. Existing
bridge `raw_calc_desc` and all subprocess output are discarded at the adapter
boundary; they cannot enter a mechanics result or provider payload.

## First bounded vertical implementation unit

Implement one offline-tested selected damaging-move calculation:

1. Accept a frozen player-vs-active-opponent snapshot, exact owned move slot,
   known species/base metadata, known type data, and explicit generation.
2. Support only direct single-hit damage/type effectiveness for a non-dynamic
   damaging move. Exclude switching, prediction, turn simulation, status moves,
   multi-hit, item triggers/consumption, and speed-order claims.
3. Unknown final stats, ability/item, boosts, current HP, or required field
   yields `insufficient_context` (or an explicitly supplied branch), never a
   legacy default-stat estimate.
4. Complete inputs call the local pinned bridge through the adapter; normalize
   roll range/KO/type facts into immutable candidate evidence.
5. Where both engines claim the same complete capability, add parity tests;
   disagreement blocks rollout rather than being selected by an LLM.

## Risks and fallback

| Risk | Safeguard / fallback |
| --- | --- |
| Node/bridge unavailable | Return a sanitized unavailable/unsupported result; retain Python behavior; never hidden defaults. |
| Upstream data drift | Pin lockfile; record internal test provenance; upgrade only with fixture/parity review. |
| Python/Smogon disagreement | Keep offline parity tests and block that capability. |
| Incomplete snapshot | Gate bridge construction on completeness and expose only allowlisted missing paths. |
| Raw description leak | Drop `raw_calc_desc` and raw subprocess output before `MechanicsResult`. |
| Simulator scope creep | Limit first slice to one direct calculation; no simulator, switching, prediction, or turn execution. |

## Non-goals and validation

This is design only: no production mechanics, request schema, prompt,
grounding, UI/session flow, bridge dependency, or default estimate changes. No
credential lookup, provider call, or mechanics network call occurred. The next
milestone needs adapter/result contract tests, complete/unknown fixtures, a
source-pin test, and a narrow parity matrix. Any actual-provider smoke requires
separate T1 approval.

## v15.42 implementation: first direct-damage slice

The implemented route is `TurnSnapshot -> direct_mechanics_context ->
evaluate_direct_damage_mechanics -> candidate.mechanics_result ->
candidate_comparisons[].mechanics_result`. The context must explicitly provide
`generation: "gen9"`, ability/item/status state, zero boosts, current/max HP,
and absent weather/terrain; existing trusted final-stat and level boundaries
provide the explicit calculation-stat basis. Nature, EVs, and IVs are not
inferred separately when exact final stats are supplied.

Only non-critical, single-hit physical/special direct moves are supported.
Missing facts produce `insufficient_context` with logical paths; status,
dynamic-power, and multi-hit moves return `unsupported_mechanic`. A `known`
result contains move, type multiplier, damage/percent range, verified one-hit
KO probability, source, and generation. Raw rolls, engine objects, provenance,
and bridge output are excluded from provider comparisons. Native Python Q12 is
production authority; the pinned local Smogon bridge remains reference-only.

Known non-absent ability, item, major-status, non-zero-stage, weather, or
terrain modifiers are also `unsupported_mechanic` in this first capability.
They are never accepted and then ignored. Explicit known absence/zero is the
only standard-direct modifier state this slice evaluates.
