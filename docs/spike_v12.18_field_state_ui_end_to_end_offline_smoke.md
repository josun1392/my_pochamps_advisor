# v12.18 Field State UI End-to-End Offline Smoke

## Purpose

Verify that saved `FieldProfileDialog` field state travels through the
UI-selected advice path, the existing limited-context checkbox gate, and the
mocked provider prompt without an actual Gemini call.

This milestone is an offline smoke only. It does not change prompt guard
wording, `FieldProfileDialog` behavior, field mapping behavior, checkbox
default, payload builder flow, damage, KO, or turn-resolution behavior.

## Fixture Summary

The smoke fixture uses the UI-selected path with:

- self active: Garchomp, HP 100
- opponent active: Charizard, HP 87
- self item: `leftovers`, user-confirmed
- opponent item: `choice-scarf`, user-confirmed
- field profiles:
  - weather: `rain`
  - terrain: `electric_terrain`
  - room: `trick_room`
  - screens: self `reflect`, opponent `light_screen`
  - hazards: self empty, opponent `stealth_rock`

## Checkbox Off Result

With the limited-context checkbox off:

- `battle_state_context` is omitted
- top-level `field_profiles` is omitted
- raw `field_profiles` key does not appear in the prompt
- serialized field values do not appear in the prompt
- provider call is mocked only

## Checkbox On Result

With the limited-context checkbox on:

- `battle_state_context` is present
- `turn_pipeline`, `turn_order_context`, and `opponent_move_context` coexist
- user-confirmed items remain mapped in `battle_state_context`
- saved field profiles normalize into `battle_state_context.field`
- top-level `field_profiles` does not leak into the provider payload

## Prompt Behavior

The checkbox-on prompt serializes known current field context values inside
`battle_state_context.field`:

- weather `rain`
- terrain `electric_terrain`
- room `trick_room`
- screens `reflect` and `light_screen`
- hazards `stealth_rock`

The existing `battle_state_context` prompt guard remains present and unchanged.

## Mocked Provider Behavior

The test monkeypatches:

- `advisor_client.call_gemini`
- `advisor_client._log_advisor_call`

Expected provider-path call count:

- 2 mocked calls total: one checkbox-off prompt and one checkbox-on prompt

No actual Gemini, retry, second provider, Vertex AI, or network/provider call is
made.

## Response Safety

The mocked response says known field entries are user-confirmed current context
only and do not resolve:

- duration
- expiration
- post-turn state
- exact damage
- full turn outcome

The response safety assertions reject overclaims such as:

- rain lasting a fixed number of turns
- terrain expiring this turn
- Reflect definitely remaining after the turn
- Stealth Rock damage being precisely calculated here
- guaranteed damage
- resolved full turn outcome
- field inferred from damage
- hidden field existence

## Coexistence With Existing Contexts

The checkbox-on prompt keeps the existing optional-context stack:

- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`
- `battle_state_context`
- user-confirmed item context

No duration, expiration, post-turn, damage precision, resolved outcome, or full
turn result fields are created.

## Tests

Updated:

- `tests/test_ui_turn_pipeline_flag_flow.py`

Added smoke:

- `test_field_state_ui_end_to_end_offline_smoke_from_saved_dialog_state`

## Non-Goals

- No actual Gemini call.
- No Gemini retry.
- No second provider call.
- No Vertex AI call.
- No prompt guard wording change.
- No `FieldProfileDialog` behavior change.
- No field mapping behavior change.
- No new limited-context checkbox.
- No checkbox default change.
- No full Turn Engine.
- No `damage_estimate` or `ko_context` behavior change.

## Safety Boundary

- Known field is current context only.
- Known field does not imply duration.
- Known field does not imply expiration.
- Known field does not imply post-turn outcome.
- Known field does not imply damage precision.
- Known field does not imply full turn outcome.
- No field source comes from damage reverse inference.
- No hidden field guessing is introduced.

## Next Recommendation

Recommended next milestone:

- v12.19 Field State UI Phase Closure

Reason:

- field source contract, helper normalization, prompt fixture, UI inventory,
  dialog, mapping, button integration, copy update, and offline UI-selected
  smoke are now covered without actual provider calls.

Alternatives:

- v12.19 Controlled Field State Gemini Smoke Design
- v12.19 Item Activation/Consumption Boundary Design
