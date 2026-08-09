# Trusted Known Move Context Design

## Implementation status and inventory

The bounded state layer is implemented. A canonical-repository-validated `used_move_observed` replay event becomes `record_known_move` in the private reducer and stores only `known_move_ids` on the side/slot/Pokémon-owned record. `BattleStateStore` remains detached and session-bound. Existing `opponent_move_context` remains a limited LLM-context surface and is not promoted to battle-session move authority.

## Canonical representation

Use Option A: an identity-bound **known move set**, never observed slot positions. Battle observations establish a canonical move identity but do not reliably establish slot 1–4, so exact slot modelling would invent authority.

At request start, `known_move_context` contains one detached active-Pokémon record per `self` and `opponent` side. Each record carries `slot_index`, `pokemon_id`, session binding, a unique bounded set of canonical move IDs, and a derived state:

- `unknown`: no trusted known moves; four remaining slots are unknown.
- `partially_known`: one through three trusted unique moves; the remaining slots are unknown, not empty or absent.
- `complete`: exactly four trusted unique moves, or an equivalent future explicit complete-set confirmation whose four identities are present.

The session store may retain a record under its owning `(side, slot_index, pokemon_id)` while it is switched out. A switch never copies moves to the incoming Pokémon; switching back may expose that same identity's session-bound record. A new session or reset clears all such authority.

## Authority and validation

Every known entry is a canonical move ID resolved by the existing move repository during replay planning; metadata remains repository-owned and is not copied into the context. The current producer accepts the existing trusted `used_move_observed` confirmation provenance. Species learnsets, competitive/common sets, defaults, caches, provider output, and likely-move language are not accepted provenance.

Input records must bind to the correct current side, slot, Pokémon identity, and session. Invalid canonical IDs, duplicate IDs in one bulk authority, more than four unique moves, stale sessions, side/Pokémon mismatch, conflicting complete declarations, or a complete record with fewer than four moves are malformed and must reject/fail closed. A repeat of the same already-applied single observation is idempotent; it does not add a move, consume an unknown slot, or imply completeness.

Omission remains distinct from explicit unknown in standalone compatibility paths. Within a session-bound request context, missing known moves means unknown remaining slots, never confirmed move absence. Negative inference may only be considered in a separate goal after complete-set authority is implemented.

## Snapshot, UI, and provider boundaries

`build_known_move_context_projection(...)` derives the active records from private reducer state. Request capture deep-copies and validates this context against the current session and active side/slot/Pokémon identity. An observation added after capture affects only a later request. A stale prior-session record cannot be captured. The context remains available to deterministic candidate snapshot transport but is removed from the provider-facing turn snapshot summary.

UI-selected self candidate moves are recommendation input, not an observed-moveset event. Existing UI-visible/candidate opponent moves and the old `opponent_move_context` likewise remain non-authoritative unless a future trusted observation adapter explicitly emits a valid move event. This keeps current self selection and actual current moveset evidence separate.

The provider receives no new field in this phase and must not create known moves, completeness, provenance, unknown-slot counts, or absent-move inference. Future sanitized summaries, if separately authorised, remain application-owned.

## Future consumers and unsupported scope

This authority is a prerequisite only for later bounded work: known opponent-action candidate generation, incoming Q12, opponent action order, known priority/status threats, complete-set negative inference, and expected-outcome evaluation. None is implemented here.

Unsupported in this design phase: species/common-set inference, selected-opponent-move inference, probability for unknown moves, move-coverage risk, switch ranking, expected incoming damage, provider inference, and all ranking changes.

## Remaining implementation prerequisites

Future mechanics consumers must use this frozen authority without treating partial absence as negative evidence. No adapter may use species learnsets or UI candidate selection as a fallback. The next bounded goal may add opponent known-move candidate generation; incoming damage, action order, threats, negative inference, and ranking remain separate goals.
