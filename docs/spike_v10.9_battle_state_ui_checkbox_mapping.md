# v10.9 Battle State UI Checkbox Mapping

## Purpose

Connect the existing limited-context checkbox to the safe `battle_state_context`
path. This reuses the v10.8 UI source adapter and keeps the first integration
limited to visible species and HP percent.

## Checkbox Mapping

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
battle_state_context = build_battle_state_context_from_ui_selected_state(battle_input)
```

No new checkbox is added. The existing checkbox remains default unchecked.

## Source Adapter Usage

`run_ui_selected_advice(...)` now accepts `enable_battle_state_context`.

When `_build_ui_selected_prompt(...)` sees `enable_battle_state_context=True`
and no explicit context was supplied, it calls:

```python
build_battle_state_context_from_ui_selected_state(battle_input)
```

The adapter reads only:

- `pokemon.my_active.name_en`
- `pokemon.my_active.hp_percent`
- `pokemon.opponent_active.name_en`
- `pokemon.opponent_active.hp_percent`

## Species / HP Handling

Accepted values are converted to `visible_ui` source envelopes:

- self species -> `self_active.species`
- self HP percent -> `self_active.current_hp_percent`
- opponent species -> `opponent_active.species`
- opponent HP percent -> `opponent_active.current_hp_percent`

## Unknown Field Policy

The mapping does not populate:

- status
- boosts
- item
- weather
- terrain
- screens
- hazards
- room
- known conditions

The helper keeps those fields unknown, and `known_conditions` remains `[]`.

## Coexistence

The checked path can include all four limited contexts:

- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`
- `battle_state_context`

They remain separate top-level contexts. `battle_state_context` is not generated
from the other three contexts.

## Prompt Guard Reuse

No prompt guard wording was changed.

When `battle_state_context` is present, the existing v10.4 guard is included in
the prompt. When the checkbox is off and battle state is omitted, the guard is
also omitted.

## UI Copy

No label, tooltip, or status/help copy was changed in v10.9. Since the checkbox
now covers visible species/HP snapshot context, the next recommended milestone
is a copy update.

## Tests

Updated coverage:

- checkbox default remains unchecked
- checkbox toggle alone does not call provider
- unchecked advice flow omits `battle_state_context`
- checked advice flow includes `battle_state_context`
- checked advice flow still includes `turn_pipeline`, `turn_order_context`, and
  `opponent_move_context`
- battle state contains self/opponent species and HP as `visible_ui`
- status, boosts, item, field state, and known conditions remain unknown
- battle-state prompt guard appears only when battle state appears
- mocked provider only; no actual Gemini, Vertex AI, provider, or network call

## Safety Boundary

v10.9 does not implement:

- new checkbox
- checkbox default change
- UI label, tooltip, or status copy change
- prompt guard wording change
- payload adapter contract change
- full Turn Engine
- resolved turn order
- post-turn HP calculation
- item consumption
- RNG or speed tie resolver
- Quick Claw activation resolution
- hidden item inference
- EV/IV/nature inference
- weather, terrain, boosts, status, hazards, or screens inference
- damage reverse inference
- species/common-set/meta-based state generation
- opponent set, hidden moveset, or selected opponent move inference
- damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering
  change

## Next Recommendation

Recommended next milestone:

```text
v10.10 Battle State UI Copy Update
```

Reason:

- The existing checkbox copy still focuses on turn event candidates,
  turn-order helper context, and opponent move candidates.
- It should now mention visible Pokemon/HP snapshot context without implying
  resolved battle state.

Actual Gemini calls remain out of scope.
