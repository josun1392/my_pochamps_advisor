# v4.4 UI Selected State to TurnSnapshot Mapping Design

## Purpose

v4.1 introduced the `core.turn_state` contract. v4.3 added an optional top-level `turn_snapshot` adapter for LLM advice payloads. The remaining gap is building a `TurnSnapshot` from the current UI-selected state.

v4.4 designs that mapping. This is design-only: no code implementation, Gemini call, Vertex AI call, full Turn Engine, item trigger evaluation, item consumption, HP update logic, speed/order simulation, damage formula change, raw damage roll change, Q12 change, `ko_context` change, or payload filtering change was made.

## Current Data Sources

The current UI-selected LLM path is:

1. `ui/main_window.py`
   - `_build_llm_battle_input()`
   - `_panel_to_llm_payload(...)`
   - `_panel_moves_payload(...)`
   - `_selected_move_payload(...)`
   - `_item_profile_payload(...)`
2. `llm/advisor_damage_estimate.py`
   - `attach_selected_move_damage_estimate(...)`
   - `attach_opponent_known_move_damage_estimates(...)`
3. `llm/advisor_client.py`
   - `build_ui_advice_payload(..., turn_snapshot=None)`
   - `_build_ui_selected_prompt(..., turn_snapshot=None)`

The UI panels already hold the data needed for a first snapshot:

- `PokemonPanel.pokemon_view`
- `PokemonPanel.current_hp_percent`
- `PokemonPanel.selected_move_index`
- `PokemonPanel.selected_moves`
- `PokemonPanel.item_profile`
- `MainWindow.selected_slots`

## Field Availability

| Field | Current availability | Source | Mapping policy |
|---|---|---|---|
| active player species | available | `pokemon.my_active.name_en` or panel `pokemon_view.en` | map to `PokemonBattleSlot.species_id` and `species_name` |
| active opponent species | available | `pokemon.opponent_active.name_en` or panel `pokemon_view.en` | map to opponent slot |
| player slot index | available | `selected_slots["team_my"]` / `pokemon.my_active.slot_index` | map to `slot_index` |
| opponent slot index | available | `selected_slots["team_enemy"]` / `pokemon.opponent_active.slot_index` | map to `slot_index` |
| selected move id/name | available for player selected move | `moves.my_selected_move.move_id` | map id to `TurnInput.selected_move_id`; name remains in payload, not snapshot v4.5 |
| opponent selected move | partial | opponent panel has selected index and known moves, but advisor action is player-side | keep `TurnInput.acting_side="player"` and `target_side="opponent"` in v4.5 |
| player current HP percent | available | `pokemon.my_active.hp_percent` / panel `current_hp_percent` | map to `current_hp_percent` |
| opponent current HP percent | available | `pokemon.opponent_active.hp_percent` / panel `current_hp_percent` | map to `current_hp_percent` |
| player known item | available | `item_profiles.my_active` | map user-confirmed `item_id`; otherwise preserve status without inventing item |
| opponent known item | available/unknown | `item_profiles.opponent_active` defaults to unknown | map `unknown` or user-confirmed status |
| item status | available but vocabulary differs | `unknown`, `system_default_none`, `none`, `user_confirmed` | normalize to snapshot item status |
| stat stages | not available | no current UI control | `{}` |
| major status | not available | no current UI control | `None` |
| volatile conditions | not available | no current UI control | `[]` |
| weather | not available | no current UI control | `None` |
| terrain | not available | no current UI control | `None` |
| field conditions | not available | no current UI control | `{}` |
| turn number | not available | no current UI control | `None` |

## Mapping Candidate

### Player Slot

```text
PokemonBattleSlot(
    side="player",
    slot_index=pokemon.my_active.slot_index,
    species_id=pokemon.my_active.name_en,
    species_name=pokemon.my_active.name_ko or pokemon.my_active.name_en,
    current_hp_percent=pokemon.my_active.hp_percent,
    known_item_id=item_profiles.my_active.item_id if status allows it,
    item_status=normalized item status,
    stat_stages={},
    major_status=None,
    volatile_conditions=(),
)
```

### Opponent Slot

```text
PokemonBattleSlot(
    side="opponent",
    slot_index=pokemon.opponent_active.slot_index,
    species_id=pokemon.opponent_active.name_en,
    species_name=pokemon.opponent_active.name_ko or pokemon.opponent_active.name_en,
    current_hp_percent=pokemon.opponent_active.hp_percent,
    known_item_id=item_profiles.opponent_active.item_id if status allows it,
    item_status=normalized item status,
    stat_stages={},
    major_status=None,
    volatile_conditions=(),
)
```

### Turn Input

```text
TurnInput(
    selected_move_id=moves.my_selected_move.move_id if present,
    acting_side="player",
    target_side="opponent",
)
```

### Battle State

```text
BattleState(
    active_player=player_slot,
    active_opponent=opponent_slot,
    weather=None,
    terrain=None,
    field_conditions={},
    turn_number=None,
)
```

### Turn Snapshot

```text
TurnSnapshot(
    battle_state=battle_state,
    turn_input=turn_input,
    notes=("Built from UI-selected state.",),
    limitations=(
        "No full turn simulation.",
        "No item trigger evaluation.",
        "No item consumption.",
        "No post-damage HP update.",
    ),
)
```

## Item Status Normalization

The UI item profile vocabulary is not exactly the snapshot vocabulary.

Recommended mapping:

| UI item profile status | Snapshot `item_status` | `known_item_id` |
|---|---|---|
| `user_confirmed` | `user_confirmed` | profile `item_id` |
| `unknown` | `unknown` | `None` |
| `none` | `absent` | `None` |
| `system_default_none` | `unknown` for battle state, not `absent` | `None` |
| other / missing | `unknown` | `None` |

Rationale:

- `system_default_none` is a calculator assumption, not confirmed battle state.
- `none` is user-confirmed no item and can be represented as `absent`.
- `unknown` must stay unknown and should not become no item.

## Builder Location Options

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| A. Build directly in `ui/main_window.py` | Has direct panel access; simple first implementation | Couples UI widget shape to snapshot contract and makes testing harder | Avoid as primary design |
| B. Build in `llm/advisor_client.py` from `battle_input` | Close to payload adapter | Makes LLM layer own state mapping and can blur battle-state truth boundary | Not preferred |
| C. Separate helper module `llm/advisor_turn_snapshot.py` | Can convert existing `battle_input` to `TurnSnapshot`; easy tests; avoids UI widget coupling | Still lives near LLM boundary rather than pure core | Recommended v4.5 MVP |
| D. Factory in `core/turn_state.py` | Centralizes contract and mapping | Core would learn current advisor payload shape, which is too specific | Avoid for now |
| E. `core/turn_snapshot_builder.py` | Pure shared helper possible long-term | May be premature until UI/payload shape stabilizes | Candidate after v4.5 |

Recommended v4.5 location:

```text
llm/advisor_turn_snapshot.py
```

Reason:

- The first implementation can consume the existing `battle_input` shape.
- It keeps `core.turn_state` as a clean contract module.
- It avoids direct UI widget imports.
- It can be tested without Qt.
- It can later move toward `core` if the mapping becomes stable and non-LLM-specific.

## Migration and Fallback Policy

v4.5 should preserve current advisor behavior:

1. Build the existing `battle_input` exactly as today.
2. Build a `TurnSnapshot` from that `battle_input` in a helper.
3. Pass it to `build_ui_advice_payload(..., turn_snapshot=snapshot)` and `_build_ui_selected_prompt(..., turn_snapshot=snapshot)` only after tests prove absent behavior is unchanged.
4. If snapshot construction fails in the UI flow, log/report safely and continue with no snapshot rather than blocking advice generation.
5. In tests, keep builder validation strict so invalid mapping bugs are visible.
6. Do not feed snapshot fields back into damage estimate, `ko_context`, item context helpers, or filtering.

Fallback distinction:

- contract/helper tests should fail fast on invalid values
- user-facing UI flow may omit snapshot and preserve advice flow if a non-critical mapping error occurs

## Limitations Wording

Even after UI mapping, the snapshot is not a full engine result.

Forbidden implications:

- exact post-turn HP
- item was consumed
- full turn simulation completed
- guaranteed move order
- exact item trigger result
- exact status resolution

Allowed phrasing:

- selected/pre-turn state indicates...
- known HP percent is...
- known item status is user-confirmed...
- unknown fields are not assumed
- stat stages/status/weather/terrain are not connected unless present

Existing v4.3 prompt guard is sufficient for v4.5 if the snapshot remains selected/pre-turn context only.

## v4.5 MVP

Recommended milestone:

```text
v4.5 UI Selected State TurnSnapshot Builder Implementation
```

Scope:

- Add `llm/advisor_turn_snapshot.py`.
- Implement a helper such as `build_turn_snapshot_from_battle_input(battle_input)`.
- Map:
  - player/opponent species id/name
  - player/opponent slot index
  - player/opponent HP percent
  - player/opponent item status and user-confirmed item id
  - selected player move id
  - `acting_side="player"`
  - `target_side="opponent"`
- Keep stat stages `{}`, major status `None`, volatile conditions `()`, weather `None`, terrain `None`, field conditions `{}`, turn number `None`.
- Add tests for full mapping, unknown/none/system_default_none item status normalization, missing selected move, missing optional fields, and absent snapshot fallback.
- Optionally connect the helper to the UI advice path only after preserving no-snapshot behavior in tests.

Out of scope for v4.5:

- full Turn Engine
- trigger result model
- item consumption
- post-damage HP updates
- speed/order simulation
- damage estimate or `ko_context` changes

## Future Path

After v4.5:

1. Add UI controls or payload fields for known stat stages and major status.
2. Add a separate item trigger result contract.
3. Design Shell Bell / healing berry post-damage HP integration.
4. Connect Quick Claw / Focus Band trigger timing only after trigger results exist.
5. Keep `TurnSnapshot` as selected/pre-turn state and add separate objects for derived engine outputs.
