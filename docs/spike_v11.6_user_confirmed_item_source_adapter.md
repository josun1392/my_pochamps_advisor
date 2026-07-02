# v11.6 User-confirmed Item Source Adapter

## Purpose

Add an explicit opt-in path for the UI-selected battle-state source adapter to
carry user-confirmed item profiles into `battle_state_context.item`. The default
adapter behavior remains species/HP-only.

## Adapter Location

- `llm/advisor_battle_state_context.py`
- Function:

```python
build_battle_state_context_from_ui_selected_state(
    battle_input,
    *,
    include_user_confirmed_items: bool = False,
)
```

## Opt-in Behavior

When `include_user_confirmed_items=True`, the adapter inspects:

- `battle_input["item_profiles"]["my_active"]`
- `battle_input["item_profiles"]["opponent_active"]`

It converts only trusted user-confirmed item metadata into helper input:

```python
{"source": "user_confirmed", "value": "<item-id>"}
```

The final helper output uses the v11.4 known item envelope:

```python
{"known": True, "source": "user_confirmed", "value": "<item-id>"}
```

## Default Behavior Unchanged

The default call keeps existing behavior:

```python
build_battle_state_context_from_ui_selected_state(battle_input)
```

- extracts self/opponent species as `visible_ui`
- extracts self/opponent HP percent as `visible_ui`
- does not read `item_profiles`
- keeps self/opponent item unknown
- does not change checkbox mapping, UI behavior, payload builder call flow, or
  prompt guard wording

## Allowed Metadata

An item profile becomes known only when all conditions are true:

- `status == "user_confirmed"`
- `source == "user_input"`
- `item_id` is a non-empty string

Both self and opponent sides follow the same rule. Opponent item remains unknown
unless the user explicitly confirms it through this metadata.

## Forbidden Sources

The adapter does not read or derive item state from:

- `visible_ui`
- `calculated_from_visible`
- `context_derived`
- `species_common_set`
- `usage_based_guess`
- `meta_inferred`
- `hidden_state_guess`
- `damage_reverse_inference`
- `legality_gate_guess`
- `resist_berry_inferred`
- legality gate output
- resist berry context
- damage estimates
- `ko_context`
- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`
- species/common-set/meta assumptions

Malformed, incomplete, ambiguous, or forbidden metadata keeps item unknown.

## Helper Envelope

The adapter passes helper input, not the final normalized envelope:

```python
self_active = {
    "species": {"source": "visible_ui", "name": "Garchomp"},
    "current_hp_percent": {"source": "visible_ui", "value": 100},
    "item": {"source": "user_confirmed", "value": "loaded-dice"},
}
```

`build_battle_state_context(...)` remains responsible for normalizing the final
`known` envelope and safety fields.

## Tests Added

- default adapter call keeps item profiles ignored
- opt-in includes self user-confirmed item
- opt-in includes opponent user-confirmed item
- opt-in preserves species/HP `visible_ui`
- opt-in keeps missing profiles unknown
- missing `item_id` keeps item unknown
- empty `item_id` keeps item unknown
- wrong status keeps item unknown
- wrong source keeps item unknown
- `visible_ui`, `calculated_from_visible`, `context_derived`, legality gate,
  resist berry, and damage-reverse style metadata keep item unknown
- known item does not create consumption, activation, post-turn HP, RNG, speed
  tie, Quick Claw, or full outcome fields
- adapter opt-in output is accepted by the existing payload adapter contract

## No UI Integration

v11.6 does not change `MainWindow`, `LLMAdviceWorker`,
`run_ui_selected_advice(...)`, checkbox mapping, UI copy, or payload builder call
flow. Existing runtime UI paths continue to call the adapter without item
inclusion.

## No Actual Gemini Call

No actual Gemini, Vertex AI, provider retry, second provider call, or network
call was executed.

## Next Recommendation

Recommended next: v11.7 User-confirmed Item Prompt/Offline Fixture.

Before mapping item opt-in into UI runtime behavior, verify offline that known
user-confirmed items appear in payload/prompt safely and that the model-facing
guard still prevents hidden item inference, item consumption certainty, and
resolved simulation claims.
