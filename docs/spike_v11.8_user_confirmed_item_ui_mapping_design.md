# v11.8 User-confirmed Item UI Mapping Design

## Purpose

Design when and how the existing limited-context checkbox should enable the
v11.6 `include_user_confirmed_items` battle-state adapter option. This is
design-only. It does not change production code, UI behavior, checkbox mapping,
payload builder call flow, prompt guard wording, or provider behavior.

## Current Flow

The existing limited-context checkbox is read in `MainWindow._start_llm_advice`.
The checked state is mapped to:

- `enable_turn_pipeline`
- `enable_turn_order_context`
- `enable_opponent_move_context`
- `enable_battle_state_context`

`LLMAdviceWorker` passes those flags to `run_ui_selected_advice(...)`, which
passes them to `_build_ui_selected_prompt(...)`.

`battle_state_context` is currently generated in `_build_ui_selected_prompt(...)`
when both conditions are true:

- no explicit `battle_state_context` argument was supplied
- `enable_battle_state_context` is true

The current call uses:

```python
battle_state_context = build_battle_state_context_from_ui_selected_state(battle_input)
```

Because v11.6 made `include_user_confirmed_items=False` the default, current
runtime behavior still extracts species/HP only and keeps items unknown.

## Recommended Mapping

Future implementation should set item inclusion at the battle-state generation
point:

```python
battle_state_context = build_battle_state_context_from_ui_selected_state(
    battle_input,
    include_user_confirmed_items=enable_battle_state_context,
)
```

This is the safest layer because:

- checkbox off means no `battle_state_context` is generated at all
- checkbox off therefore cannot leak item data into payload or prompt
- checkbox on already means the user asked for limited context
- the v11.6 adapter still accepts only direct user-confirmed item metadata
- malformed, missing, forbidden, legality-derived, resist-berry-derived,
  damage-derived, common/meta/usage, or hidden/default item data remains unknown
- no separate pre-scan helper is needed

Do not change `MainWindow`, `LLMAdviceWorker`, or payload builder call flow for
this mapping unless a future implementation needs a dedicated test seam.

## Behavior Matrix

| Checkbox | Item profile state | Expected behavior |
| --- | --- | --- |
| off | no `item_profiles` | no `battle_state_context` |
| off | user-confirmed `item_profiles` | no `battle_state_context`; no item payload or prompt item |
| on | no `item_profiles` | `battle_state_context` with species/HP; item unknown |
| on | malformed `item_profiles` | `battle_state_context` with species/HP; item unknown |
| on | forbidden item source | `battle_state_context` with species/HP; item unknown |
| on | user-confirmed `item_profiles` | `battle_state_context` with species/HP and known `user_confirmed` item |

## Off-path Guarantee

The off path should be guaranteed by preserving the existing order:

1. `enable_battle_state_context=False`
2. `_build_ui_selected_prompt(...)` does not call the battle-state adapter
3. no top-level `battle_state_context` exists
4. no serialized battle-state prompt block or guard appears
5. no item payload can appear through `battle_state_context`

Future tests should explicitly verify checkbox off with user-confirmed
`item_profiles` still omits `battle_state_context`.

## On-path Safety

Connecting `include_user_confirmed_items=True` when
`enable_battle_state_context=True` is safe if the v11.6 adapter remains the only
source of item data. The adapter allows known item values only when all metadata
is present:

- `status == "user_confirmed"`
- `source == "user_input"`
- non-empty string `item_id`

All other item metadata remains unknown. The adapter must continue not reading:

- legality gate output
- resist berry context
- damage estimates
- `ko_context`
- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`
- species/common-set/meta/usage assumptions
- hidden/default opponent item state

Known item means "user-confirmed item context" only. It does not imply item
activation, item consumption, post-turn HP, RNG result, speed tie result, Quick
Claw activation, selected opponent move, or full turn outcome.

## UI Copy Consideration

Future UI copy should mention the item addition once mapping is implemented.
Recommended meaning:

- limited context includes candidate events, turn-order helper info, opponent
  move candidates, current Pokemon/HP snapshot, and user-confirmed item snapshot
- user-confirmed items are not hidden item guesses
- known item does not mean activation, consumption, or resolved turn outcome

Do not change UI copy in this design step.

## Prompt Guard Consideration

The existing battle-state guard already forbids hidden item inference and
resolved simulation claims including item consumption. For future implementation,
consider adding or testing a clearer known-item semantic:

- user-confirmed item may be treated as known item context
- known item alone must not imply activation, consumption, post-turn HP, RNG,
  speed tie, Quick Claw activation, or full outcome

v11.8 does not change guard wording.

## Test Plan for Future Implementation

Recommended tests for the implementation step:

- checkbox off + no `item_profiles` -> no `battle_state_context`
- checkbox off + user-confirmed `item_profiles` -> no `battle_state_context`
- checkbox on + no `item_profiles` -> species/HP and item unknown
- checkbox on + malformed `item_profiles` -> species/HP and item unknown
- checkbox on + forbidden item source -> species/HP and item unknown
- checkbox on + user-confirmed self item -> known `user_confirmed` self item
- checkbox on + user-confirmed opponent item -> known `user_confirmed` opponent
  item
- prompt includes known item only on checked/on path with valid metadata
- prompt guard remains present when `battle_state_context` appears
- known item does not create activation, consumption, post-turn HP, RNG, speed
  tie, Quick Claw, selected opponent move, or full outcome fields
- checkbox toggle alone still does not call provider
- mocked provider only; no actual Gemini call

## Next Recommendation

Recommended next: v11.9 User-confirmed Item UI Mapping Implementation.

If implementation is not yet approved, the safe alternative is v11.9
User-confirmed Item UI Copy Design, covering tooltip/status wording before
runtime mapping.

## No Production Code Change

v11.8 is documentation/design only. It does not change production code, UI item
integration, UI source adapter wiring, checkbox flow, payload builder call flow,
UI copy, payload contract behavior, or prompt guard wording.

## No Actual Gemini Call

No actual Gemini, Vertex AI, provider retry, second provider call, or network
call was executed.
