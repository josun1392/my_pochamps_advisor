# v10.7 Battle State UI Integration Design

## Purpose

Design how the existing limited-context checkbox should enable
`battle_state_context` in a future implementation. This is design-only:

- no production code change
- no UI integration
- no UI source adapter implementation
- no payload adapter change
- no prompt guard change
- no actual Gemini, Vertex AI, provider, or network call
- no hidden-state inference
- no full Turn Engine behavior

## v10.6 Inventory Summary

v10.6 found a narrow safe UI source set:

- `self_active.species`: visible selected own Pokemon
- `self_active.current_hp_percent`: visible own HP percent
- `opponent_active.species`: visible selected opponent Pokemon
- `opponent_active.current_hp_percent`: visible opponent HP percent

The following sources require future design or should remain out of the first
integration:

- user-confirmed item profiles need separate item-boundary design
- status has no current explicit UI source
- boosts have no current explicit UI source
- field weather, terrain, screens, hazards, and room have no current explicit
  UI source
- `known_conditions` has no current explicit UI source

Unsafe sources remain forbidden:

- common set, usage, or meta guesses
- hidden-state guesses
- damage or KO reverse inference
- selected move, hidden moveset, or opponent set inference

## Checkbox Mapping Design

Use the existing `LLMAdvicePanel` limited-context checkbox. Do not add a new
checkbox and do not change the default unchecked state in the first
implementation.

Unchecked:

```text
enable_turn_pipeline = False
enable_turn_order_context = False
enable_opponent_move_context = False
enable_battle_state_context = False
battle_state_context omitted
```

Checked:

```text
enable_turn_pipeline = True
enable_turn_order_context = True
enable_opponent_move_context = True
enable_battle_state_context = True
battle_state_context included only when safe visible species/HP source exists
```

Rationale:

- `battle_state_context` is limited visible state snapshot context, not a
  resolved simulation.
- The existing checkbox already controls limited context surfaces.
- Keeping one checkbox avoids a misleading separate "battle state" switch.
- Copy/tooltip should be updated in a later UI copy task because the current
  copy mentions candidate events, turn-order helper info, and opponent move
  candidates, but not visible HP/Pokemon snapshot context.

## Source Extraction Design

Future extraction should read only existing UI-selected `battle_input` facts,
not damage estimates, KO context, sample assumptions, or helper outputs from
other optional contexts.

Allowed first-pass sources:

| Context field | Source location | Source trust | Output |
| --- | --- | --- | --- |
| `self_active.species` | `battle_input["pokemon"]["my_active"]["name_en"]` or selected own `PokemonPanel.pokemon_view` | `visible_ui` | `{"source": "visible_ui", "name": my_species_name}` |
| `self_active.current_hp_percent` | `battle_input["pokemon"]["my_active"]["hp_percent"]` or `PokemonPanel.current_hp_percent` | `visible_ui` | `{"source": "visible_ui", "value": my_hp_percent}` |
| `opponent_active.species` | `battle_input["pokemon"]["opponent_active"]["name_en"]` or selected opponent `PokemonPanel.pokemon_view` | `visible_ui` | `{"source": "visible_ui", "name": opponent_species_name}` |
| `opponent_active.current_hp_percent` | `battle_input["pokemon"]["opponent_active"]["hp_percent"]` or opponent `PokemonPanel.current_hp_percent` | `visible_ui` | `{"source": "visible_ui", "value": opponent_hp_percent}` |

Recommended implementation location for v10.8:

- add a narrow source adapter near the UI/advice boundary
- prefer consuming the already-built `battle_input` dict to avoid duplicating
  direct widget reads
- adapter returns helper input or a ready helper output; T2 should choose the
  exact shape in v10.8

## Helper Input Shape

The future adapter should feed `build_battle_state_context(...)` with only
species and HP percent:

```python
self_active = {
    "species": {"source": "visible_ui", "name": my_species_name},
    "current_hp_percent": {"source": "visible_ui", "value": my_hp_percent},
}
opponent_active = {
    "species": {"source": "visible_ui", "name": opponent_species_name},
    "current_hp_percent": {"source": "visible_ui", "value": opponent_hp_percent},
}
field = None
known_conditions = []
```

The helper should keep every missing active, field, and condition field in its
existing explicit unknown representation.

## Unknown Field Policy

The first UI integration should keep these fields unknown:

- `self_active.status`
- `self_active.boosts`
- `self_active.item`
- `opponent_active.status`
- `opponent_active.boosts`
- `opponent_active.item`
- `field.weather`
- `field.terrain`
- `field.screens`
- `field.hazards`
- `field.room`
- `known_conditions`

These must not be inferred from species, base stats, item contexts, move data,
damage estimates, KO context, turn event candidates, turn-order hints, or
opponent move candidates.

## Item Handling Decision

v10.7 basic UI integration should exclude item from `battle_state_context`.

Reason:

- item has a sensitive hidden/confirmed boundary, especially for opponent item
- existing `item_profiles` and item-specific contexts already carry item
  information with their own guards
- `system_default_none`, explicit `none`, `unknown`, and `user_confirmed` need
  a separate mapping decision to avoid promoting defaults to battle truth

Future optional item integration may allow:

- self item only when `item_profiles.my_active.status == "user_confirmed"`
- opponent item only when `item_profiles.opponent_active.status == "user_confirmed"`
- explicit no-item only after a stable battle-state no-item value convention is
  chosen

Default unknown and system-default item states must remain unknown in
`battle_state_context`.

## Payload Flow

Future v10.8 flow:

```text
UI selected state
-> _build_llm_battle_input()
-> safe species/HP source extraction
-> build_battle_state_context(...)
-> run_ui_selected_advice(..., battle_state_context=context, enable_battle_state_context=checkbox_on)
-> build_ui_advice_payload(..., enable_battle_state_context=True, battle_state_context=context)
-> serialized prompt payload
-> battle_state_context prompt guard
-> mocked/offline advice flow first
```

If the checkbox is off, the adapter should not build or pass a battle state
context. If the checkbox is on but safe source data cannot be built, omit the
context rather than inserting an empty or unknown-only context.

## Prompt Guard Flow

No new prompt guard is required for the first integration because v10.4 already
adds the guard conditionally when top-level `battle_state_context` is present.

Expected behavior:

- context absent: no serialized `battle_state_context`, no battle-state guard
- context present: serialized `battle_state_context` and v10.4 guard appear
- guard continues to preserve unknown fields and forbid hidden-state,
  damage/KO reverse-inference, and resolved simulation claims

## Coexistence

The checked checkbox path should allow all four limited contexts to coexist:

- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`
- `battle_state_context`

They must not overwrite each other. `battle_state_context` must not be generated
from the other three contexts.

## Test Plan for v10.8

Required tests:

- checkbox default unchecked
- checkbox off maps `enable_battle_state_context=False`
- checkbox off omits `battle_state_context`
- checkbox off omits battle-state prompt guard
- checkbox on maps `enable_battle_state_context=True` with
  `enable_turn_pipeline`, `enable_turn_order_context`, and
  `enable_opponent_move_context`
- checkbox on builds `battle_state_context` from species/HP only
- self/opponent species use `source == "visible_ui"`
- self/opponent HP percent use `source == "visible_ui"`
- status, boosts, item, field state remain explicit unknowns
- `known_conditions == []`
- opponent hidden/default item remains unknown
- `turn_pipeline`, `turn_order_context`, `opponent_move_context`, and
  `battle_state_context` coexist
- prompt guard appears when `battle_state_context` appears
- checkbox toggle alone does not call Gemini/provider
- mocked advice flow does not call actual provider
- no hidden item, EV/IV/nature, weather, terrain, boost, status, hazards,
  screens, room, damage reverse inference, post-turn HP, item consumption, RNG,
  speed tie, Quick Claw activation, or full turn outcome claim is introduced

## Safety Boundary

v10.7 does not implement:

- production UI integration
- UI source adapter
- checkbox behavior change
- new checkbox
- payload adapter change
- prompt guard change
- actual Gemini, Vertex AI, provider, or network call
- full Turn Engine
- resolved turn order
- post-turn HP calculation
- item consumption
- RNG or speed tie resolver
- Quick Claw activation resolution
- hidden item inference
- EV/IV/nature inference
- weather, terrain, boost, status, hazards, or screens inference
- damage reverse inference
- species/common-set/meta-based state generation
- opponent set, hidden moveset, or selected opponent move inference
- damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering
  change

## Next Recommendation

Recommended next milestone:

```text
v10.8 Battle State UI Source Adapter
```

Scope:

- implement a narrow adapter that extracts only visible self/opponent species
  and HP percent from existing UI-selected state
- keep item out of first implementation
- keep status, boosts, field, and known conditions unknown
- wire no actual provider calls

Alternative:

- v10.8 Battle State UI Integration Offline E2E
- v10.8 Battle State UI Copy Update

Actual Gemini calls should remain out of scope.
