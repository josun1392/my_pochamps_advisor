# Trusted Known Move Context Design

## Status and inventory

This is a design-only contract. No battle reducer, UI, candidate generation, damage calculation, ranking, provider payload, or advice behavior changes in this phase. `BattleStateStore` already provides a detached, session-bound state snapshot and the private reducer state is organised by side, active slot, and Pokémon identity. It has no observed-move transition yet. Existing `opponent_move_context` is a limited LLM-context surface and must not be promoted to battle-session move authority.

## Canonical representation

Use Option A: an identity-bound **known move set**, never observed slot positions. Battle observations establish a canonical move identity but do not reliably establish slot 1–4, so exact slot modelling would invent authority.

At request start, `known_move_context` contains one detached active-Pokémon record per `self` and `opponent` side. Each record carries `side`, `slot_index`, `pokemon_id`, session binding, a unique bounded set of canonical move IDs, and a derived state:

- `unknown`: no trusted known moves; four remaining slots are unknown.
- `partially_known`: one through three trusted unique moves; the remaining slots are unknown, not empty or absent.
- `complete`: exactly four trusted unique moves, or an equivalent future explicit complete-set confirmation whose four identities are present.

The session store may retain a record under its owning `(side, slot_index, pokemon_id)` while it is switched out. A switch never copies moves to the incoming Pokémon; switching back may expose that same identity's session-bound record. A new session or reset clears all such authority.

## Authority and validation

Every known entry is a canonical move ID resolved by the existing move repository; metadata remains repository-owned and is not copied into the context. Accepted provenance is limited to user confirmation, an observed battle event, or a trusted reducer event. Species learnsets, competitive/common sets, defaults, caches, provider output, and likely-move language are not accepted provenance.

Input records must bind to the correct current side, slot, Pokémon identity, and session. Invalid canonical IDs, duplicate IDs in one bulk authority, more than four unique moves, stale sessions, side/Pokémon mismatch, conflicting complete declarations, or a complete record with fewer than four moves are malformed and must reject/fail closed. A repeat of the same already-applied single observation is idempotent; it does not add a move, consume an unknown slot, or imply completeness.

Omission remains distinct from explicit unknown in standalone compatibility paths. Within a session-bound request context, missing known moves means unknown remaining slots, never confirmed move absence. Negative inference may only be considered in a separate goal after complete-set authority is implemented.

## Snapshot, UI, and provider boundaries

Request capture deep-copies the context. An observation added after capture affects only a later request. A stale prior-session record cannot be captured.

UI-selected self candidate moves are recommendation input, not an observed-moveset event. Existing UI-visible/candidate opponent moves and the old `opponent_move_context` likewise remain non-authoritative unless a future trusted observation adapter explicitly emits a valid move event. This keeps current self selection and actual current moveset evidence separate.

The provider receives no new field in this phase and must not create known moves, completeness, provenance, unknown-slot counts, or absent-move inference. Future sanitized summaries, if separately authorised, remain application-owned.

## Future consumers and unsupported scope

This authority is a prerequisite only for later bounded work: known opponent-action candidate generation, incoming Q12, opponent action order, known priority/status threats, complete-set negative inference, and expected-outcome evaluation. None is implemented here.

Unsupported in this design phase: species/common-set inference, selected-opponent-move inference, probability for unknown moves, move-coverage risk, switch ranking, expected incoming damage, provider inference, and all ranking changes.

## Implementation prerequisites

A future implementation must first add a narrowly validated observed/confirmed-move reducer event plus session registry/snapshot projection that preserves `(side, slot_index, pokemon_id, session_id)` ownership. It must use the existing move repository solely to resolve canonical IDs and must retain the frozen request-start boundary. No adapter may use species learnsets or UI candidate selection as a fallback.
