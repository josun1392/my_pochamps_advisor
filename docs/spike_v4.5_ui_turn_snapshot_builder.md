# v4.5 UI Selected State TurnSnapshot Builder

## Purpose

v4.5 connects the existing UI-selected `battle_input` shape to the v4.1 `TurnSnapshot` contract and the v4.3 optional payload adapter.

This is not a full Turn Engine. It only turns known selected/pre-turn UI state into a serializable snapshot for Gemini context.

## Implemented

- Added `llm/advisor_turn_snapshot.py`.
- Added `build_turn_snapshot_from_battle_input(battle_input)` for strict conversion.
- Added `try_build_turn_snapshot_from_battle_input(battle_input)` for user-facing fallback.
- Connected `run_ui_selected_advice(...)` to pass the snapshot into `_build_ui_selected_prompt(...)`.

## Mapped Fields

`PokemonBattleSlot` for player and opponent:

- `side`
- `slot_index`
- `species_id`
- `species_name`
- `current_hp_percent`
- `known_item_id`
- `item_status`

`TurnInput`:

- `selected_move_id`
- `acting_side="player"`
- `target_side="opponent"`

`BattleState` defaults:

- `weather=None`
- `terrain=None`
- `field_conditions={}`
- `turn_number=None`

Unconnected state stays empty or `None`:

- stat stages
- major status
- volatile conditions
- weather
- terrain
- field conditions
- turn number

## Item Status Mapping

- `user_confirmed` stays `user_confirmed` with `known_item_id`.
- `system_default_none`, `none`, and `absent` map to battle-state `absent`.
- `inferred` stays `inferred` with `known_item_id`.
- `consumed` stays `consumed` without a known item id.
- unknown, unconfirmed, missing, or unsupported statuses map to `unknown`.

## Fallback Policy

- The strict helper raises validation errors for invalid input.
- The fallback helper returns `None` for invalid input.
- User-facing advice generation uses the fallback helper.
- If snapshot construction fails, the existing advice flow continues without `turn_snapshot`.
- If no snapshot is present, v4.3 preserves the previous payload output.

## Non-Goals

v4.5 does not implement:

- full Turn Engine simulation
- item trigger evaluation
- item consumption
- HP update logic
- speed/order simulation
- damage formula changes
- raw damage roll changes
- Q12 multiplier changes
- `ko_context` changes
- payload filtering behavior changes

## Verification

Actual Gemini calls were not executed.

The implementation is covered by `tests/test_advisor_turn_snapshot.py` plus existing TurnSnapshot, payload contract, and damage estimate regression tests.

## v4.6 Smoke Verification

v4.6 adds smoke/preflight coverage without production code changes and without actual Gemini calls.

The smoke path verifies:

- valid UI-selected `battle_input` creates a `TurnSnapshot`
- top-level `turn_snapshot` is present when a snapshot is supplied
- player/opponent species, HP percent, selected move, and item id/status serialize into the snapshot
- selected/pre-turn snapshot limitations are added only when the snapshot is present
- invalid snapshot input returns `None` through the user-facing fallback helper
- absent/fallback snapshot behavior preserves the existing payload
- damage estimate, `ko_context`, item context, and filtering output remain unchanged apart from the optional snapshot section and its limitations

Full Turn Engine behavior, item trigger evaluation, item consumption, HP updates, and speed/order simulation remain unimplemented.
