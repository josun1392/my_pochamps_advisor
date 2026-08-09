# Opponent Known-Move Action Candidate Contract

## Scope and inventory

Frozen opponent action enumeration and an inert attacker/defender side-reversal mechanics snapshot are implemented. They are not connected to self recommendation ranking, provider payloads, incoming-damage presentation, or threat aggregation. `opponent_move_context` remains legacy limited LLM context, not this authority.

## Candidate source and identity

Only frozen request-start `known_move_context.opponent` for the active opponent Pokémon may enumerate candidates. Each candidate identity is `opponent-action:{session}:{opponent_pokemon_id}:{canonical_move_id}:{stable_index}`. Stable index follows frozen known-move order; it is identity ordering only, never strength or probability ordering. Inactive Pokémon records, self known moves, species learnsets, common sets, UI candidates, provider suggestions, and unknown slots create no candidates.

Known move IDs resolve canonical metadata from the existing repository; the context stores IDs only. Metadata resolution failure yields an identity-known but mechanics-unsupported candidate, never a silent deletion. Status moves remain action candidates but not damage candidates. Formula, level-fixed, fixed, and unsupported mechanics retain their existing supportability boundaries.

## Completeness and supportability

`unknown` yields zero candidates and is not an empty moveset. `partially_known` yields exactly its one to three known moves and has `candidate_set_complete=false`; unknown slots are neither harmless nor synthetic candidates. `complete` yields four known moves and `candidate_set_complete=true`, but does not predict selection or strategy. Moveset completeness and evaluated-mechanics completeness remain distinct.

Candidate-local layers remain independent: known identity, action order, move success, damage, deterministic KO, and exact probability. Unknown combat authority does not erase a known action identity or receive species/default/stat/item/type fallback.

## Ownership and future consumers

For every future opponent action: acting side is `opponent`, target/defending side is `self`; opponent current type supports STAB and offense, self current type supports effectiveness and defense, self exact HP supports KO, opponent ability supports priority, and self terrain/groundedness/blocking ability/current type govern the applicable move-success gates. Target scope remains canonical; unsupported or complex targets are not rewritten as opposing-single.

Future incoming Q12 must reuse the existing attacker/defender formula with a side-reversal snapshot adapter, not a new formula. Future action order must compare the self candidate against only known opponent candidates. Neither future consumer may infer unknown moves, aggregate a worst case, rank threats, or change self recommendation ranking.

## Snapshot and external boundaries

Active opponent identity is frozen at request start. A later switch or observation affects only the next request. Opponent candidates live in a distinct namespace and never enter the provider selectable set or self candidate list. No provider field changes in this phase; provider cannot create moves, candidates, completeness, likelihood, or threat ranking.

Unsupported: unknown-move probability, move-choice probability, expected opponent action, species/meta inference, PP/lock inference, threat ranking, switch recommendation, and expected outcome. The next bounded implementation goal may enumerate frozen known opponent action identities only, preserving these boundaries.
