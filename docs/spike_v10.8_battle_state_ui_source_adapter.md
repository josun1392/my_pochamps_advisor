# v10.8 Battle State UI Source Adapter

## Purpose

Add a narrow adapter that converts the current UI-selected `battle_input`
shape into a safe `battle_state_context` using only visible species and HP
percent. This is not UI checkbox integration.

## Adapter

Location:

```text
llm/advisor_battle_state_context.py
```

Function:

```python
build_battle_state_context_from_ui_selected_state(battle_input)
```

Input:

- current UI-selected `battle_input` mapping
- expected source path: `pokemon.my_active` and `pokemon.opponent_active`

Output:

- final `battle_state_context` helper output
- `kind == "battle_state_context"`
- `confidence == "limited"` when any visible species or HP source is accepted
- `confidence == "unknown"` when no safe source exists

## Source Handling

Accepted sources:

| Source path | Output field | Source |
| --- | --- | --- |
| `pokemon.my_active.name_en` | `self_active.species.name` | `visible_ui` |
| `pokemon.my_active.hp_percent` | `self_active.current_hp_percent.value` | `visible_ui` |
| `pokemon.opponent_active.name_en` | `opponent_active.species.name` | `visible_ui` |
| `pokemon.opponent_active.hp_percent` | `opponent_active.current_hp_percent.value` | `visible_ui` |

The adapter strips blank species names and accepts numeric HP percent values.
Missing or malformed values are omitted from helper input so the existing
helper emits explicit unknown fields.

## Unknown Field Policy

The adapter does not populate:

- status
- boosts
- item
- weather
- terrain
- screens
- hazards
- room
- known conditions

The helper keeps these as explicit unknowns:

```python
{"known": False, "value": "unknown"}
```

`known_conditions` remains `[]`.

## Forbidden Source Policy

The adapter does not read:

- `item_profiles`
- `damage_estimate`
- `ko_context`
- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`
- common set or meta data
- species sample assumptions

It does not create hidden item, EV/IV/nature, status, boost, field state, RNG,
speed tie, Quick Claw activation, item consumption, post-turn HP, full turn
result, or resolved outcome fields.

## Scope Not Implemented

v10.8 does not implement:

- existing limited-context checkbox connection
- `enable_battle_state_context` UI mapping
- `build_ui_advice_payload(...)` call-flow changes
- prompt guard changes
- UI label, tooltip, or status copy changes
- actual advice-flow behavior changes
- actual Gemini, Vertex AI, provider, or network calls

## Tests

Implemented in `tests/test_advisor_battle_state_context.py`:

- extracts self species as `visible_ui`
- extracts self HP percent as `visible_ui`
- extracts opponent species as `visible_ui`
- extracts opponent HP percent as `visible_ui`
- output keeps `kind == "battle_state_context"`
- output is `limited` when visible source exists
- status, boosts, item remain unknown
- field state remains unknown
- `known_conditions == []`
- missing species/HP produces unknown context
- damage estimate, KO context, and other optional contexts are not used as
  hidden-state sources
- forbidden fields and forbidden sources remain absent

## Next Recommendation

Recommended next milestone:

```text
v10.9 Battle State UI Checkbox Mapping
```

Scope:

- connect the existing limited-context checkbox to `enable_battle_state_context`
- call the v10.8 adapter only when the checkbox is on
- keep species/HP as the only battle-state UI sources
- keep item/status/boosts/field/known conditions unknown
- verify with mocked/offline tests before any actual provider call

Alternative:

- v10.9 Battle State UI Integration Offline E2E
- v10.9 Battle State UI Copy Update
