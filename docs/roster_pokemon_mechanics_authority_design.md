# Roster Pokémon Mechanics Authority Contract

## Status and purpose

This contract is implemented as a private request-start projection for future
switch evaluation.  It adds no reducer, evaluator, provider, ranking, or UI
behavior.  Its purpose is to prevent an active
Pokémon's authority from being reinterpreted as authority for a bench target.

The source-of-truth rule is:

`Pokémon-owned fact -> session-bound Pokémon identity -> frozen roster record`

An active mechanics view is only a projection of that record for the active
identity.  It is not a second owner and cannot be copied from A to B during a
switch.

## Implementation status

`llm/advisor_roster_mechanics.py` provides
`build_self_roster_mechanics_context_projection(...)`, strict request handoff
normalization, and `active_self_roster_mechanics_view(...)`.  Runtime roster
identity/HP/fainted/condition/item facts seed bounded records.  Type, final
stats, and ability remain unknown unless an already identity-bound supplied
record validates against the same session, side, slot, and Pokémon ID.  This
is deliberate: active-only contexts are never promoted to a bench record.

`advisor_turn_snapshot.py` freezes an optional private
`self_roster_mechanics_context`, excludes it from provider-facing snapshot
summaries, and `advisor_switch_transition.py` carries only the selected B
record as detached `target_roster_mechanics`.  No incoming evaluator is called.

## Existing authority inventory

| Authority | Current shape | Owner today | Roster contract |
| --- | --- | --- | --- |
| Current type | `current_type_context.current_types` | active side input; capture provenance binds active slot/identity | Pokémon-owned record, explicit known/unknown/malformed state |
| Final stats | `final_stat_context.current_final_stats` | active side input; user-confirmed, stage-unmodified | Pokémon-owned record, one value per stat with identity provenance |
| Temporary stages | `stat_stage_context.current_stages` | current combat/active state | separate volatile combat authority; never placed in final stats |
| Ability | `ability_context.current_abilities` | active side input | Pokémon-owned record; unknown remains unknown |
| Item | roster `known_item` and active item context | Pokémon-owned when trusted | preserve target-owned current item state only |
| Exact HP | `current_hp_context.current_hp` | active side input | Pokémon-owned HP provenance record |
| Fainted/condition | runtime roster fields | Pokémon-owned | retain separate tri-state fainted and persistent condition |
| Known moves | `known_move_context` | already slot/Pokémon/session-bound | precedent; unchanged |
| Screens, Tailwind, hazards | side/field contexts | side-owned | never copied to roster records |
| Weather, terrain, Trick Room | field contexts | shared field-owned | never copied to roster records |
| Selected move, candidates, pairs, ranking | request/action evidence | action/request-owned | excluded |

`build_q12_input_adapter` already distinguishes explicit `current_type_context`
unknown from legacy omitted type handling and requires trusted final stats.
Therefore an active A entry cannot be used to make B Q12-ready.  Repository
base stats/types remain metadata only and cannot manufacture B final stats or
override B's explicit unknown current type.

## Canonical frozen record

The future private request-start handoff is an ordered collection, not a
species-keyed map:

```text
self_roster_mechanics_context = {
  schema_version,
  session_id,
  entries: [
    {
      side: self, slot_index, pokemon_id,
      current_type_authority,
      final_stat_authority,
      ability_authority,
      item_authority,
      hp_authority,
      fainted_authority,
      persistent_condition_authority,
      groundedness_authority (only if an existing trusted producer owns it)
    }
  ]
}
```

The identity tuple `(session_id, side, slot_index, pokemon_id)` is mandatory.
Duplicate species are independent records.  A stale session or a slot/Pokémon
identity mismatch is rejected; same species names never authorize reuse.

Each authority retains its own `complete`, `insufficient_context`,
`unsupported_mechanic`, malformed, or existing legacy-omitted semantics.  No
global `bench_mechanics_complete` flag is authoritative.

## Per-authority rules

### Current type

The record stores a canonical exact type set only when trusted for that
identity.  Explicit unknown stays unknown after A-to-B transition; it cannot
fall back to A or species typing.  Existing legacy omitted behavior remains
limited to the evaluator paths that already explicitly permit it.

### Final stats and temporary stages

`final_stat_context` is explicitly stage-unmodified in the existing contract.
Its future roster record remains persistent Pokémon-owned authority.  Temporary
stages are not final stats: they remain a separately owned combat layer and
are subject to the manual-switch reset contract.  No stage value is persisted
or copied merely because a final stat is known.

### Ability, item, HP, fainted, and condition

Ability and item remain identity-bound and are never inferred from species or
another slot.  HP authority preserves its source and precision: exact trusted
current/max HP, percent-only/approximate, explicit unknown, stale/mismatched,
and malformed are distinct.  It must not be collapsed to a raw integer.

Fainted remains a separate tri-state authority.  This contract introduces no
`HP == 0` to fainted inference in either direction.  Persistent conditions are
Pokémon-owned; B keeps B's condition and never receives A's.  Volatiles remain
outside this record until a structured owner exists.

## Lifecycle and active-view projection

Roster records survive active -> bench -> active transitions under their own
event lifecycle.  B's known HP/type/etc. remains B-owned while benched and may
be projected again on switch-back; unobserved intervening changes are not
invented.  A new session starts fresh identity records and rejects S1 data.

For a future authorized A-to-B transition:

1. select B's frozen record by the complete identity tuple;
2. derive post-switch active mechanics view from B's record;
3. preserve side/shared field authority separately;
4. do not copy or mutate A's record.

The request projection is detached and bounded: it contains mechanics facts
needed by a future defender adapter, not provider payloads, repository caches,
ranking evidence, pair matrices, or UI objects.

## Incoming-evaluator compatibility

| Existing defender need | Future B roster source |
| --- | --- |
| Current type/effectiveness | `current_type_authority` |
| Final defensive stats | `final_stat_authority` |
| Ability / defender blockers | `ability_authority` plus separately owned groundedness if supported |
| Item modifiers | `item_authority` |
| Damage/KO/probability HP | `hp_authority`, retaining exactness/provenance |
| Already fainted check | `fainted_authority` |
| Persistent condition | `persistent_condition_authority` |
| Screens, terrain, weather | existing side/shared contexts, not B record |

Partial B authority is valid evidence.  A future adapter may use fields that
are sufficient for a specific existing mechanic and must report the remaining
supportability; it may not fill missing fields from A, defaults, metadata, or a
provider.

## Population and boundaries

Current UI capture may populate active-only mechanics for several fields.  It
does not make bench mechanics known.  The future implementation must add
identity-bound trusted capture before a bench value is present; until then the
roster record represents explicit unknown/omitted state as the existing
contract requires.

No provider payload/schema, ranking, switch selectability, presentation, or
incoming evaluator behavior changes in this design slice.  The next bounded
implementation is a private frozen roster-mechanics projection and validation
layer; only after that may the switch incoming adapter reuse the existing
opponent evaluator against B.
