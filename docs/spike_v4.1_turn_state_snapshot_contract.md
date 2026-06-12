# v4.1 Turn State Snapshot Contract

## Purpose

v4.1 implements the first minimal contract from the v4.0 Turn Engine / Battle State design. It adds a small, serializable, validated turn-state snapshot model without connecting it to the existing advisor payload, damage estimate, item contexts, `ko_context`, or prompt generation.

This is contract/schema work only. It is not a full Turn Engine implementation.

## Module Location

The contract lives in:

```text
core/turn_state.py
```

Reason:

- Turn state is not LLM-only.
- Future UI selected state, deterministic trigger evaluation, and advisor payload generation should be able to share the same state contract.
- `core` already contains repository and shared domain contract modules, while `llm` should keep consuming state rather than owning battle-state truth.

## Added Structures

### `PokemonBattleSlot`

Fields:

- `side`
- `slot_index`
- `species_id`
- `species_name`
- `current_hp_percent`
- `known_item_id`
- `item_status`
- `stat_stages`
- `major_status`
- `volatile_conditions`

Validation:

- `side` must be `player` or `opponent`.
- `current_hp_percent` must be `None` or a number from 0 to 100.
- `item_status` must be `None`, `unknown`, `user_confirmed`, `inferred`, `consumed`, or `absent`.
- stat stage values must be integers from -6 to 6.
- volatile condition values must be non-empty strings.

### `BattleState`

Fields:

- `active_player`
- `active_opponent`
- `weather`
- `terrain`
- `field_conditions`
- `turn_number`

Validation:

- `turn_number` must be `None` or a non-negative integer.
- `field_conditions` is copied into an immutable mapping.

### `TurnInput`

Fields:

- `selected_move_id`
- `acting_side`
- `target_side`

Validation:

- `acting_side` and `target_side` may be `None`, `player`, or `opponent`.

### `TurnSnapshot`

Fields:

- `battle_state`
- `turn_input`
- `notes`
- `limitations`

This keeps placeholder metadata available without modeling trigger results, HP updates, item consumption, or turn simulation yet.

## Serialization

Each structure supports:

- `to_dict()`
- `from_dict(...)`

The module also exposes:

```text
normalize_turn_snapshot(...)
```

That helper accepts `None`, an existing `TurnSnapshot`, or a mapping and returns a `TurnSnapshot`.

## Intentional Non-Integration

v4.1 does not:

- add turn state to `advisor_client` payloads
- change damage estimate behavior
- change raw damage rolls
- change Q12 multipliers
- change `ko_context`
- change item-context filtering
- evaluate item triggers
- consume items
- update HP after damage
- simulate speed or turn order

The contract is deliberately inert until a later integration milestone.

## Test Coverage

Added `tests/test_turn_state_snapshot.py` covering:

- `PokemonBattleSlot` default and populated serialization
- `BattleState` nested serialization
- `TurnInput` serialization
- `TurnSnapshot` serialization
- HP percent validation
- stat stage validation
- invalid side validation
- invalid item status validation
- safe `None` / `unknown` preservation
- `from_dict` / `to_dict` round trip
- immutable collection normalization

Existing advisor payload and damage estimate regression tests remain unchanged.

## Next Step

Recommended next implementation direction:

```text
v4.2 Item Trigger Result Contract
```

Before implementing actual Shell Bell, healing berry, White Herb, Mental Herb, or Mega Stone behavior, define trigger result objects and timing windows that can attach to a `TurnSnapshot` without mutating current damage estimate behavior.
