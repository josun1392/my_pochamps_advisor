# Known Opponent Threat Aggregation Contract

## Scope

This is implemented as the internal `advisor_known_threat_reducer.py`. It groups existing frozen pairwise evidence by exactly one self candidate. It summarizes trusted *known* opponent actions but does not select a worst move, create a scalar threat score, rank self candidates, infer unknown moves, or change provider/presentation behavior.

## Known scope versus global scope

Every summary must carry the opponent known-move state, known pair count, unknown slots, candidate-set completeness, and mechanical completeness. `known_*` means only the trusted frozen opponent actions that were enumerated. It is never a claim about the opponent's full action space unless the moveset is complete and every required pair is mechanically complete.

Unknown has zero pairs and is unavailable evidence, never no threat. Partial may establish positive facts over known pairs but is non-exhaustive. Complete has four trusted identities; if any required pair is insufficient or unsupported, mechanics remain incomplete even though identity coverage is exhaustive.

## Read-only input and grouping

The sole future input is the frozen pair-set output. The reducer must not re-run action order, move success, damage, KO, probability, or pair enumeration. Self candidates are isolated: all pairs with one `self_candidate_id` form one summary, and no evidence may cross to another self candidate.

## Raw capability and executed threat

Candidate-owned KO remains raw capability. An executed immediate opponent threat requires the pair to show opponent move success `allowed` and opponent action not `preempted`. A self-first allowed guaranteed OHKO may preempt an opponent's guaranteed-OHKO capability; that capability remains raw evidence but does not count as an executed immediate incoming threat. Unknown order does not suppress capability or invent an execution result.

## Categorical aggregates

Allowed set facts are categorical, not a score: known executable guaranteed-OHKO exists; known executable possible-OHKO exists; known opponent-first action exists; counts by deterministic KO horizon; self-preempts count; opponent-preempts count; and bounded `known_max_incoming_damage` only over complete damaging pairs. These remain explicitly `known_*` for partial sets.

Exact by1/by2/by3 probability stays pair-local supplemental evidence. No maximum, mean, weighted probability, expected damage, likely move, or opponent-choice probability is aggregated.

## Positive and negative inference

Positive existential facts may be established by one complete relevant pair, even for partial sets: for example, a known executable action has guaranteed OHKO capability.

Negative/universal facts require non-empty complete identity scope and complete required mechanics. They use tri-state `true | false | unresolved`. Examples: `no_known_guaranteed_ohko`, `all_known_actions_preempted`, and `all_known_actions_slower`. A partial set or any incomplete pair makes a negative claim unresolved; it cannot become a safety claim.

`all_known_actions_preempted` is never vacuously true for zero pairs. In a partial set it means exactly all *known* actions are preempted. In a complete, mechanically complete set it covers the current trusted moveset under the bounded deterministic model only—not accuracy, critical hits, residuals, recovery, or switching.

## Completeness and external boundaries

`known_threat_evaluation_complete` requires non-empty complete candidate identity scope and all pairs required by the selected categorical fact to be mechanically complete. `global_threat_complete` is false for partial/unknown scope and false when mechanics are incomplete. Positive evidence from other complete pairs remains visible despite an incomplete pair; only universal negatives are withheld.

Threat summaries stay internal. They are excluded from provider payloads, ranking/selectability, UI text, and recommendation selection. Future ranking requires a separate T1-approved policy (for example a complete-set deterministic policy, a partial-set cautious policy, or annotations without ranking); this contract selects none.

## Next bounded work

Threat aggregation and ranking integration remain independent goals. Any ranking policy must separately receive T1 approval and preserve the known/global scope distinction, tri-state universal facts, raw-versus-executed separation, and provider isolation.
