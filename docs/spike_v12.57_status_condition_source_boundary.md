# v12.57 Status/Condition Source Boundary and Contract Foundation

## Purpose

Define a source-bound foundation for future Pokemon status/condition context.
This milestone adds validation only. It does not add status UI, runtime payload
mapping, prompt serialization, parser/replay support, or effect resolution.

## Current Source Inventory

| Location | Current meaning | v12.57 treatment |
| --- | --- | --- |
| `battle_state_context.self_active/opponent_active.status` | Generic source-tagged active-side field | Existing seam only; UI-selected adapter keeps it unknown. |
| `battle_state_context.known_conditions` | Generic trusted-condition list | Existing generic structure; no new status source is connected. |
| UI-selected Pokemon/item/field profiles | Species, HP, item, and field inputs | No direct status/condition input exists. |
| Damage, KO, speed, item, ability, species/meta data | Calculation, candidate, or general context | Never a source of known current condition. |
| Battle log/parser/replay/Turn Engine | Not implemented for conditions | Future source candidates only; currently unsupported. |

Move category `status` and item legality/support metadata are move/item facts,
not evidence that a major condition is currently known. Volatile concepts such
as confusion, flinch, Leech Seed, Substitute, Taunt, Encore, Disable, trapped,
and recharge remain deferred. In particular, flinch is an event-like outcome,
not a persistent current major condition.

## Meaning Boundary

The future model distinguishes:

- `unknown_condition`: no trusted current-condition fact.
- `known_current_condition`: a user-confirmed present condition only.
- `observed_condition_event`: a separately confirmed application/tick/event.
- `resolved_condition_effect`: an engine-applied result.
- `post_turn_condition_state`: a later resolved state.

`known_current_condition` is not an application event, activation/tick,
resolved damage/effect, post-turn HP/state, duration counter, RNG result, or
speed-order result. Therefore known burn does not prove burn damage; known
paralysis does not prove full paralysis or final order; and known sleep does not
prove a sleep counter or wake-up turn.

## Current Contract

`normalize_user_confirmed_current_condition(...)` accepts only:

```python
{
    "side": "self" | "opponent",
    "condition_type": "burn" | "poison" | "toxic" | "paralysis" | "sleep" | "freeze" | "none" | "unknown",
    "status": "user_confirmed",
    "source": "user_confirmed_current_condition",
}
```

It returns `confidence="known"`. Future source names such as
`explicit_user_condition_event_confirmation`, `battle_log`, `parser`,
`imported_replay`, and `future_turn_engine` are explicitly rejected until each
has its own source contract.

Forbidden fields are recursively rejected: exact status damage/post-turn HP,
application/trigger flags, full paralysis, sleep duration/wake-up, freeze RNG,
generic RNG, final speed order, resolved effects, and post-turn state.

## Inference Prohibition

No current condition may be inferred from species/meta, moves, damage/HP,
speed, item, ability, common sets, or model guesses. Flame Orb possibility does
not establish burn, a Toxic move does not establish toxic, and a slow result
does not establish paralysis.

## Status

`COMPLETE` - inventory, boundary design, validation foundation, and offline
contract coverage are complete. Runtime UI/payload/prompt integration remains a
separate future phase.
