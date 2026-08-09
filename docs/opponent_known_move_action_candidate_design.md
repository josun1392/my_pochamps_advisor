# Opponent Known-Move Action Candidate Contract

## Scope and inventory

Frozen opponent action enumeration, side-reversal mechanics snapshots, and candidate-local read-only incoming-mechanics evaluation are implemented. They are not connected to self recommendation ranking, provider payloads, incoming-damage presentation, or threat aggregation. `opponent_move_context` remains legacy limited LLM context, not this authority.

## Candidate source and identity

Only frozen request-start `known_move_context.opponent` for the active opponent Pokémon may enumerate candidates. Each candidate identity is `opponent-action:{session}:{opponent_pokemon_id}:{canonical_move_id}:{stable_index}`. Stable index follows frozen known-move order; it is identity ordering only, never strength or probability ordering. Inactive Pokémon records, self known moves, species learnsets, common sets, UI candidates, provider suggestions, and unknown slots create no candidates.

Known move IDs resolve canonical metadata from the existing repository; the context stores IDs only. Metadata resolution failure yields an identity-known but mechanics-unsupported candidate, never a silent deletion. Status moves remain action candidates but not damage candidates. Formula, level-fixed, fixed, and unsupported mechanics retain their existing supportability boundaries.

## Completeness and supportability

`unknown` yields zero candidates and is not an empty moveset. `partially_known` yields exactly its one to three known moves and has `candidate_set_complete=false`; unknown slots are neither harmless nor synthetic candidates. `complete` yields four known moves and `candidate_set_complete=true`, but does not predict selection or strategy. Moveset completeness and evaluated-mechanics completeness remain distinct.

Candidate-local layers remain independent: known identity, action priority authority, move success, damage, deterministic KO, and exact probability. The evaluator consumes only the frozen side-reversal snapshot. It uses the original opponent as attacker and self as defender, including self HP for KO and exact Formula-roll probability. Complete priority blocks suppress successful damage/KO/probability evidence without deleting the known action; status moves are damage `not_applicable`; unresolved metadata remains an unsupported identity. Unknown combat authority does not erase a known action identity or receive species/default/stat/item/type fallback.

## Ownership and future consumers

For every future opponent action: acting side is `opponent`, target/defending side is `self`; opponent current type supports STAB and offense, self current type supports effectiveness and defense, self exact HP supports KO, opponent ability supports priority, and self terrain/groundedness/blocking ability/current type govern the applicable move-success gates. Target scope remains canonical; unsupported or complex targets are not rewritten as opposing-single.

Incoming Formula Q12 and already-supported direct mechanics reuse the existing attacker/defender helpers through the side-reversal adapter, not a new formula. Exact self HP yields existing deterministic KO and Formula by1/by2/by3 probability evidence; unknown self HP leaves damage intact while KO/probability are insufficient. Current implementation retains action priority authority for the opponent move but deliberately performs no opponent-versus-self candidate ordering comparison. A future consumer may compare a self candidate against only known opponent candidates. Neither future consumer may infer unknown moves, aggregate a worst case, rank threats, or change self recommendation ranking.

## Snapshot and external boundaries

Active opponent identity is frozen at request start. A later switch or observation affects only the next request. Opponent candidates live in a distinct namespace and never enter the provider selectable set or self candidate list. No provider field changes in this phase; provider cannot create moves, candidates, completeness, likelihood, or threat ranking.

Unsupported: unknown-move probability, move-choice probability, expected opponent action, species/meta inference, PP/lock inference, threat ranking, switch recommendation, expected outcome, and incoming-threat presentation. The canonical pairwise design is in `self_vs_opponent_pairwise_comparison_design.md`; implementation remains a separate bounded goal and does not change recommendation ranking.
