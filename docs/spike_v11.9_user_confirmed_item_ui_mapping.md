# v11.9 User-confirmed Item UI Mapping

## Purpose

Connect the existing limited-context checkbox path to the v11.6 user-confirmed
item source adapter option. When battle-state context is enabled, user-confirmed
item profiles can now flow into `battle_state_context.item`; when disabled,
`battle_state_context` remains omitted.

## Mapping Location

- `llm/advisor_client.py`
- `_build_ui_selected_prompt(...)`

The automatic battle-state generation path now calls:

```python
battle_state_context = build_battle_state_context_from_ui_selected_state(
    battle_input,
    include_user_confirmed_items=enable_battle_state_context,
)
```

## Mapping Behavior

- `enable_battle_state_context=False`: no battle-state context is generated.
- `enable_battle_state_context=True`: battle-state context is generated from
  UI-selected species/HP and opt-in user-confirmed item profiles.
- Existing `MainWindow`, `LLMAdviceWorker`, checkbox default, checkbox label,
  tooltip/status copy, and payload builder call flow are unchanged.

## Checkbox Off Behavior

Checkbox off still omits:

- `battle_state_context`
- serialized battle-state prompt block
- battle-state guard
- known item values inside battle-state context

This remains true even when top-level `item_profiles` contains user-confirmed
items.

## Checkbox On Behavior

Checkbox on includes `battle_state_context` with:

- self/opponent species as `visible_ui`
- self/opponent HP percent as `visible_ui`
- field state unknown
- `known_conditions=[]`

Item behavior depends on profile metadata.

## Allowed Metadata Behavior

Known item is included only when all metadata is present:

- `status == "user_confirmed"`
- `source == "user_input"`
- non-empty string `item_id`

The final normalized item shape is:

```python
{"known": True, "source": "user_confirmed", "value": "<item-id>"}
```

## Malformed/Forbidden Metadata Behavior

The item remains unknown when metadata is missing, malformed, or uses a
forbidden source such as:

- `visible_ui`
- `calculated_from_visible`
- `context_derived`
- `legality_gate_guess`
- `resist_berry_inferred`
- `damage_reverse_inference`
- common/meta/usage/hidden item sources

The UI mapping does not read legality gate output, resist berry context,
damage estimates, `ko_context`, turn contexts, common sets, usage, or meta
assumptions as item sources.

## Prompt Behavior

When checkbox on and item metadata is allowed:

- serialized `battle_state_context` includes known user-confirmed items
- known items appear as context facts, not inferred hidden items
- existing battle-state prompt guard appears unchanged

When checkbox off:

- no serialized `battle_state_context` appears
- no battle-state guard appears

## Safety Boundary

Known user-confirmed item context does not imply:

- item activation
- item consumption
- post-turn HP
- RNG result
- speed tie result
- Quick Claw activation
- selected opponent move
- full turn outcome

No hidden item inference or damage reverse inference is introduced.

## Tests Added

- checkbox off omits `battle_state_context` even when `item_profiles` are
  user-confirmed
- checkbox on includes species/HP and known self/opponent user-confirmed items
- checkbox on serializes known items in prompt
- checkbox on + no `item_profiles` keeps item unknown
- checkbox on + malformed `item_profiles` keeps item unknown
- checkbox on + forbidden item source keeps item unknown
- known item does not create item consumption, post-turn HP, RNG, speed tie,
  Quick Claw, or full outcome fields
- existing `turn_pipeline`, `turn_order_context`, and `opponent_move_context`
  coexistence remains covered
- mocked provider only; no actual Gemini call

## No UI Copy Change

v11.9 does not change checkbox label, tooltip, status/help copy, default state,
or add a new checkbox.

## No Actual Gemini Call

No actual Gemini, Vertex AI, provider retry, second provider call, or network
call was executed.

## Next Recommendation

Recommended next: v11.10 User-confirmed Item UI Copy Update.

The limited-context checkbox copy should now safely mention that checked context
may include user-confirmed item snapshots, while making clear that this does not
mean hidden item inference, activation, consumption, or resolved turn outcome.
