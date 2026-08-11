# Ability Applicability and Interaction Authority

## Scope

`llm/advisor_ability_interaction_authority.py` defines a detached, request-safe
authority prerequisite for future ability consumers. It does not implement a
mechanic, derive switching permission, or alter existing ability consumers.

## Contract

Ability identity remains an independent authority. This contract records, for
one exact ability identity, both:

- `applicability`: `applicable`, `not_applicable`, or `unknown`.
- `interaction`: `affecting`, `not_affecting`, or `unknown`.

Every record is bound to `session_id` and the exact source and target
`side`/`slot_index`/`pokemon_id` identities. It is never species keyed. Source
and target must be on different sides. Missing, stale-session, malformed,
unsupported, or source/target-mismatched data normalizes to an exact detached
`unknown` record; absence never means `not_applicable` or `not_affecting`.

`ability_mechanic_prerequisite` returns `complete` only for
`applicable + affecting`. Explicit negative evidence returns `not_applicable`;
all unknown/malformed paths are `insufficient_context`. The helper never
returns a mechanic result such as a switch block or a switch permission.

## Lifecycle and freezing

The caller supplies the current request session and both current identities
when normalizing an authority. A session, source, target, or ability mismatch
therefore cannot be reused after an active or session change. Builders and
normalizers return deep-detached mappings, so a frozen consumer does not share
mutable observation data with a later live update.

## Production wiring

The canonical `battle-state-v1` reducer owns two separate current-state
contexts: `ability_applicability_context` and `ability_interaction_context`.
It accepts narrowly scoped `set_` and `clear_` events for each context, checks
the exact active source/target identities at reducer time, and rejects stale
slot occupants or malformed enum values atomically. Clear writes explicit
`unknown`; it does not infer a negative fact.

`project_ability_interaction_authority` combines the two validated reducer
facts only for the exact current opponent source and self target, then returns
a detached authority record. `advisor_turn_snapshot` normalizes that handoff
against the request's selected active identities before carrying it in frozen
`current_state`. Any unrelated reducer mutation conservatively clears positive
applicability/interaction evidence to `unknown`; active replacement therefore
cannot rebind an old record to a same-slot successor.

The production reducer → projection → frozen snapshot path is covered by tests
for complete, negative, unknown, mismatch, same-slot replacement, and live
post-freeze mutation cases.

## Shadow Tag prerequisite

Raw `Shadow Tag` identity is insufficient. A future Shadow Tag consumer may
continue only after this authority says its observed ability is both
`applicable` and `affecting`; it must still apply its own type, item, and
ability exceptions. Shadow Tag itself remains unimplemented here.

## Boundaries

There is no provider payload, provider call, UI control, switch-permission
change, Move-mechanics migration, topology engine, or suppression derivation
in this foundation. Future trusted capture or mechanics derivation may populate
this authority without changing its ownership contract.
