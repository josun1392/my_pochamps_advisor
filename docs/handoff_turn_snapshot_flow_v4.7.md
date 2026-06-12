# v4.7 TurnSnapshot UI Flow Handoff

## Purpose

TurnSnapshot was added as the bridge between today's selected-move advisor flow and a future Turn Engine / Battle State layer.

The current advisor can calculate selected-move damage, limited `ko_context`, and item-context advice, but it does not yet track turn sequence, trigger timing, item consumption, post-damage HP, or status/state transitions. TurnSnapshot gives the LLM a small selected/pre-turn known-state surface without pretending that full turn simulation exists.

## Current Implementation State

### v4.1 Contract

`core/turn_state.py` defines the shared state contract:

- `PokemonBattleSlot`
- `BattleState`
- `TurnInput`
- `TurnSnapshot`
- `to_dict()` / `from_dict(...)`
- `normalize_turn_snapshot(...)`

The contract validates side values, item status values, HP percent, stat stages, turn number, and string tuple fields.

### v4.3 Payload Adapter

`llm/advisor_client.py` supports optional top-level `turn_snapshot`:

- `build_ui_advice_payload(..., turn_snapshot=None)`
- `_add_turn_snapshot_to_advice_payload(...)`
- `_build_turn_snapshot_prompt_guard(...)`

If `turn_snapshot` is absent, the default advice payload is unchanged. If present, the snapshot is normalized and serialized into top-level `turn_snapshot`, and selected/pre-turn limitations are added.

### v4.5 UI-Selected Builder

`llm/advisor_turn_snapshot.py` builds a snapshot from the existing UI-selected `battle_input`:

- `build_turn_snapshot_from_battle_input(...)` is strict and raises on invalid state.
- `try_build_turn_snapshot_from_battle_input(...)` is user-facing fallback and returns `None` on invalid state.

`run_ui_selected_advice(...)` attempts to build the snapshot and passes it to `_build_ui_selected_prompt(...)`. If snapshot construction fails, advice generation continues without a snapshot.

### v4.6 Smoke Verification

`tests/test_advisor_turn_snapshot.py` verifies:

- valid `battle_input` creates a snapshot
- top-level `turn_snapshot` is added when present
- snapshot limitations are added when present
- invalid input falls back to `None`
- absent/fallback payload behavior is preserved
- damage estimate, `ko_context`, item contexts, and filtering remain unchanged except for the optional snapshot section and snapshot limitations

No actual Gemini call was run for v4.6.

## Data Flow

```text
UI selected state
  -> MainWindow._build_llm_battle_input()
  -> attach_selected_move_damage_estimate(...)
  -> run_ui_selected_advice(...)
  -> try_build_turn_snapshot_from_battle_input(battle_input)
  -> _build_ui_selected_prompt(battle_input, turn_snapshot=...)
  -> build_ui_advice_payload(..., turn_snapshot=...)
  -> optional top-level turn_snapshot
  -> prompt guard: selected/pre-turn snapshot only
```

The snapshot is additional context. It does not feed back into damage estimate, `ko_context`, item-context generation, or payload filtering.

## Currently Mapped Values

Player and opponent `PokemonBattleSlot`:

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

Default / not-yet-connected fields:

- `stat_stages={}`
- `major_status=None`
- `volatile_conditions=()`
- `weather=None`
- `terrain=None`
- `field_conditions={}`
- `turn_number=None`

## Item Status Mapping

- `user_confirmed` stays `user_confirmed` and preserves `known_item_id`.
- `system_default_none`, `none`, and `absent` map to battle-state `absent`.
- `inferred` stays `inferred` and preserves `known_item_id`.
- `consumed` stays `consumed` but does not invent a known item id.
- unknown, unconfirmed, missing, or unsupported statuses map to `unknown`.

## Current Limitations

TurnSnapshot is selected/pre-turn known-state context only.

It does not implement:

- full Turn Engine simulation
- item trigger evaluation
- item consumption
- HP update logic
- post-turn state
- speed/order simulation
- exact item trigger results
- exact post-turn HP
- guaranteed move order
- exact status or volatile condition resolution

The prompt guard explicitly tells Gemini not to infer those results from `turn_snapshot` alone.

## Safety Policy

- Snapshot construction failure must not break user-facing advice.
- If snapshot construction fails, `try_build_turn_snapshot_from_battle_input(...)` returns `None`.
- If snapshot is absent, `build_ui_advice_payload(...)` preserves the previous payload behavior.
- If snapshot is present, only top-level `turn_snapshot` and snapshot limitations are added.
- `damage_estimate`, raw damage rolls, Q12 multipliers, `ko_context`, item contexts, and payload filtering remain unchanged.
- Actual Gemini calls are not required to verify the snapshot plumbing.

## Recommended Next Step

Recommended next milestone:

```text
v4.8 TurnSnapshot UI Dry-run / Local Debug Snapshot Report
```

Rationale:

- The payload connection is implemented, but there is no local debug report that lets T1/T2 inspect the exact snapshot produced by a UI-selected state without making a Gemini call.
- A dry-run report can show `battle_input`, normalized `turn_snapshot`, and payload presence/absence safely.
- This should remain local-only and avoid full Turn Engine behavior.
- It will help judge selected-state quality before v5.0 Turn Engine design or implementation.

Later candidates:

- `v5.0 Minimal Turn Engine MVP Design`
- item trigger planning layer design
- UI state controls for stat stages, status, weather, terrain, and field conditions

## Verification

v4.7 is documentation/handoff cleanup only.

No production code changes were made. No actual Gemini call or Vertex AI call was run.
