# Trusted Current Type Context

`current_type_context` is a request-start, side-owned authority for a Pokémon's **current** typing. It is deliberately separate from repository species/base typing: species metadata is never a fallback.

- Each side starts as explicit `unknown` on a new session and after clear/reset.
- A known value has one or two canonical type IDs and either `user_confirmed_current` or `trusted_observed_current` provenance. Structured known entries are bound to the active slot, Pokémon identity, and session before capture.
- An explicit unknown has no type list and remains distinct from an omitted standalone context. Unknown, partial, approximate, stale, duplicate, empty, invalid, or conflicting input never becomes known.
- Request capture is detached/frozen. A later UI mutation or a previous session's bound entry cannot alter the captured context.
- `classify_current_type_dark_membership` is read-only and returns only `known_contains_dark`, `known_does_not_contain_dark`, `unknown`, or `malformed`.

The minimal UI offers an explicit Unknown / Known exact type(s) control for self and opponent. This context is copied through the candidate adapter but removed from legacy provider payloads. A separate bounded move-success gate may use the read-only classifier for Dark-type Prankster immunity only when the server-owned `prankster_applied` evidence is present for an opposing-single status move. It does not add STAB, type effectiveness, Terastallization, type mutation, or a general type-effect engine.
