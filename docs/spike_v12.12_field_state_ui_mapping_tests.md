# v12.12 Field State UI Mapping Tests

## Purpose

Lock the expected field-state UI mapping boundary before adding any
FieldProfileDialog button integration or MainWindow field-profile storage UI.

This milestone covers the limited-context checkbox gate, future
`field_profiles` mapping behavior, `unknown` vs `none` semantics, malformed
handling, coexistence with existing optional contexts, and resolved-outcome
guards.

## Test Scope

Tested layers:

- `llm.advisor_battle_state_context.build_battle_state_context_from_ui_selected_state(...)`
- `llm.advisor_client._build_ui_selected_prompt(...)`
- mocked UI checkbox flow in `tests/test_ui_turn_pipeline_flag_flow.py`

The tests lock the helper/client boundary only. They do not add MainWindow
session storage, a FieldProfileDialog entry button, or a user-facing mapping UI.

## Checkbox Gate Behavior

Locked behavior:

- checkbox off keeps `battle_state_context` omitted
- checkbox off omits `field_profiles` from the provider prompt payload
- checkbox on includes `battle_state_context`
- checkbox on can map valid `field_profiles` into `battle_state_context.field`
- checkbox toggle alone still does not call a provider

`field_profiles` is treated as UI-only metadata. It is removed from the advice
payload and can only affect the LLM prompt through normalized
`battle_state_context.field`.

## Field Profiles Mapping Behavior

Added the helper/client seam proposed in v12.11:

```python
build_battle_state_context_from_ui_selected_state(
    battle_input,
    include_user_confirmed_items=False,
    include_user_confirmed_fields=False,
)
```

Default behavior remains unchanged:

- `include_user_confirmed_fields=False` ignores `field_profiles`
- checkbox off still omits `battle_state_context`

Opt-in behavior:

- `include_user_confirmed_fields=True` reads `battle_input["field_profiles"]`
- valid `status=user_confirmed` + `source=user_input` metadata maps to
  `source=user_confirmed` known field envelopes
- `run_ui_selected_advice(...)` / `_build_ui_selected_prompt(...)` pass the
  field opt-in only when `enable_battle_state_context=True`

## Unknown vs None Behavior

Locked behavior:

- missing `field_profiles`: all field entries unknown
- `value="unknown"`: unknown envelope
- trusted `value="none"`: known absence
- valid weather `rain`: known weather
- valid terrain `electric_terrain`: known terrain
- valid room `trick_room`: known room
- valid screens side values: known side-specific screens
- valid hazards side values: known side-specific hazards

## Malformed/Forbidden Behavior

Locked behavior:

- missing field metadata stays unknown
- malformed field metadata stays unknown
- `context_derived` field metadata stays unknown at helper/client mapping level
- `calculated_from_visible` field metadata stays unknown at helper/client
  mapping level
- direct payload validation still rejects forbidden known field sources

## Coexistence With Existing Contexts

The checkbox-on mocked path verifies coexistence with:

- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`
- `battle_state_context`
- user-confirmed item mapping

User-confirmed item mapping remains unchanged and can coexist with known field
mapping in the same `battle_state_context`.

## Safety Boundary

- known field is current context only
- known field does not imply duration
- known field does not imply expiration
- known field does not imply post-turn state
- known field does not imply damage precision
- known field does not imply full turn outcome
- no damage reverse field inference
- no species/common/meta field inference
- no item-effect field inference
- no LLM/model field guess
- `damage_estimate` and `ko_context` are not changed by field mapping

## Tests Added

Updated `tests/test_advisor_battle_state_context.py`:

- field profiles are ignored without field opt-in
- field opt-in maps valid weather/terrain/room/screens/hazards
- field opt-in preserves trusted `none` and `unknown` semantics
- malformed/forbidden field profiles stay unknown

Updated `tests/test_ui_turn_pipeline_flag_flow.py`:

- checkbox off omits `battle_state_context` even when `field_profiles` exists
- checkbox off prevents `field_profiles` prompt payload leakage
- checkbox on maps valid field profiles into `battle_state_context.field`
- checkbox on preserves user-confirmed item mapping
- checkbox on keeps `turn_pipeline`, `turn_order_context`, and
  `opponent_move_context` coexistence
- checkbox on field metadata matrix covers missing, `unknown`, `none`,
  malformed, `context_derived`, and `calculated_from_visible` behavior
- duration, expiration, post-turn, damage precision, and resolved outcome fields
  are not created

## Implementation Limits

Implemented only the minimum helper/client boundary needed to make the tests
green:

- added `include_user_confirmed_fields=False`
- removed UI-only `field_profiles` from default advice payloads
- auto-generated field mapping is gated by `enable_battle_state_context`

Not implemented:

- `MainWindow._field_profiles`
- FieldProfileDialog button integration
- FieldProfileDialog result storage in MainWindow
- new limited-context checkbox
- UI copy changes
- prompt guard wording changes
- battle log/parser support
- damage or KO behavior changes

## No Button Integration

No button, menu item, toolbar entry, or MainWindow signal/slot was added for
FieldProfileDialog.

## No Actual Gemini Call

No actual Gemini call, retry, second provider call, Vertex AI call, or
network/provider call is part of v12.12. Provider behavior is covered only by
mocked tests.

## Next Recommendation

Recommended next:

- v12.13 Field State UI Mapping Implementation

Reason:

- the mapping gate, field-profile normalization, leak prevention,
  unknown/none/malformed behavior, item coexistence, and optional-context
  coexistence are now locked by tests.

Alternatives:

- v12.13 FieldProfileDialog Button Integration Design
- v12.13 Field State UI Mapping Closure
