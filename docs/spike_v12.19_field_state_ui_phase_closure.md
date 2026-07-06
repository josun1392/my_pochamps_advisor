# v12.19 Field State UI Phase Closure

## Purpose

Close the field state UI phase that ran from v12.3 through v12.18.

This closure records the completed field source contract, helper
normalization, prompt fixture, UI inventory, FieldProfileDialog, UI mapping,
button integration, limited-context copy update, and mocked end-to-end offline
smoke. It is documentation-only and does not change production code, payload
shape, prompt guard wording, provider behavior, damage, KO, or turn-resolution
behavior.

## Phase Scope

Closed scope:

- field keys: weather, terrain, room, screens, hazards
- allowed field sources: `user_confirmed`, `explicit_input`
- `field_profiles` metadata shape: `status`, `source`, `value`
- unknown vs none behavior
- FieldProfileDialog input surface
- MainWindow session-local field-profile state
- LLMAdvicePanel Field state entry point
- existing limited-context checkbox hard gate
- prompt serialization through `battle_state_context.field`
- mocked provider offline smoke

Out of scope:

- actual Gemini field-state smoke
- field duration or expiration tracking
- post-turn field updates
- battle log/parser field source
- imported replay field source
- damage engine consumption of known field
- full Turn Engine simulation

## Completed Milestones

- v12.3 Field State Source Design
- v12.4 Field State Contract Tests
- v12.5 Field State Helper
- v12.6 Field State Prompt/Offline Fixture
- v12.7 Field State UI Source Inventory
- v12.8 Field Profile Dialog Design
- v12.9 Field Profile Dialog Contract Tests
- v12.10 Field Profile Dialog UI Implementation
- v12.11 Field State UI Mapping Design
- v12.12 Field State UI Mapping Tests
- v12.13 Field State UI Mapping Implementation
- v12.14 FieldProfileDialog Button Integration Design
- v12.15 FieldProfileDialog Button Integration Tests
- v12.16 FieldProfileDialog Button Integration
- v12.17 Limited Context Copy Update for Field State
- v12.18 Field State UI End-to-End Offline Smoke

## Current User Flow

1. The user clicks the `Field state` button in `LLMAdvicePanel`.
2. `FieldProfileDialog` opens for weather, terrain, room, screens, and hazards.
3. The user applies current field context.
4. `MainWindow._field_profiles` stores the dialog result for the current
   session.
5. If the limited-context checkbox is off, field profiles are not sent to the
   LLM payload or prompt.
6. If the limited-context checkbox is on, valid field profiles normalize into
   `battle_state_context.field`.
7. Offline smoke coverage verifies known field values serialize only below the
   gated `battle_state_context`.

## Current Payload / Prompt Flow

```text
FieldProfileDialog
-> MainWindow._field_profiles
-> battle_input["field_profiles"]
-> limited context checkbox hard gate
-> battle_state_context.field
-> prompt serialization
-> mocked provider
```

Checkbox off:

- `battle_state_context` is omitted.
- top-level `field_profiles` is omitted.
- known field values are not serialized.

Checkbox on:

- `battle_state_context` is included.
- valid `field_profiles` normalize into `battle_state_context.field`.
- known field values serialize only under gated `battle_state_context`.
- top-level `field_profiles` does not leak into the prompt payload.

## Checkbox Gate Behavior

The existing limited-context checkbox remains the only gate for sending field
state to the advice prompt.

- Default state remains unchecked.
- No new limited-context checkbox exists.
- Toggling/opening the field dialog does not call a provider.
- Saved field profiles are inert until the checkbox enables
  `battle_state_context`.

## Field Profiles Behavior

The trusted UI shape is:

```python
{
    "weather": {"status": "user_confirmed", "source": "user_input", "value": "rain"},
    "terrain": {"status": "user_confirmed", "source": "user_input", "value": "electric_terrain"},
    "room": {"status": "user_confirmed", "source": "user_input", "value": "trick_room"},
    "screens": {
        "status": "user_confirmed",
        "source": "user_input",
        "value": {"self": ["reflect"], "opponent": ["light_screen"]},
    },
    "hazards": {
        "status": "user_confirmed",
        "source": "user_input",
        "value": {"self": [], "opponent": ["stealth_rock"]},
    },
}
```

Only valid `status=user_confirmed`, `source=user_input`, and valid `value`
metadata maps to `source=user_confirmed` known field envelopes. Missing,
malformed, untrusted, forbidden, `context_derived`, and
`calculated_from_visible` metadata remains unknown through helper mapping.
Direct payload validation still rejects forbidden known field sources.

## Unknown vs None Behavior

- `unknown` means unconfirmed, missing, or malformed input.
- `unknown` normalizes to an unknown envelope.
- `none` means the user confirmed no active effect for that field category.
- trusted `none` normalizes to user-confirmed known absence.
- screens/hazards both-side empty lists can represent user-confirmed known
  absence.
- unknown remains unknown after prompt serialization.

## Safety Boundary

- known field is user-confirmed current context only
- known field does not imply duration
- known field does not imply expiration
- known field does not imply post-turn outcome
- known field does not imply exact damage
- known field does not imply full turn outcome
- unknown remains unknown
- none means user-confirmed absence only
- no field source from damage reverse inference
- no field source from species/common/meta
- no field source from item inferred effects
- no field source from LLM/model guess
- no hidden field guessing
- no full Turn Engine
- no `damage_estimate` or `ko_context` behavior change

## Test Coverage Summary

Field state UI phase coverage includes:

- field source contract tests
- helper normalization tests
- malformed and forbidden metadata tests
- unknown vs none tests
- side-specific screens/hazards tests
- prompt/offline fixture tests
- FieldProfileDialog widget behavior tests
- button/session-state behavior tests
- checkbox gate tests
- top-level `field_profiles` no-leakage tests
- limited-context copy tests
- mocked end-to-end UI-selected prompt smoke

Current focused suites:

- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_field_profile_dialog.py`
- `tests/test_field_profile_button_integration_contract.py`
- `tests/test_ui_turn_pipeline_flag_flow.py`

## Known Limitations

- field state UI path is offline-smoke verified only
- no actual Gemini field-state smoke yet
- no field duration/expiration tracking
- no post-turn field state updates
- no battle log/parser field source
- no imported replay field source
- no damage engine consumption of known field
- no exact hazard chip damage implementation
- no full turn simulation

## Non-Goals

v12.19 does not implement or change:

- production code
- provider execution
- prompt guard wording
- FieldProfileDialog behavior
- field mapping behavior
- checkbox behavior or default
- payload builder call flow
- damage formula, raw rolls, Q12, `damage_estimate`, or `ko_context`
- item activation or consumption
- hidden field inference
- battle log/parser source

## No Actual Gemini Call

No actual Gemini call, Gemini retry, second provider call, Vertex AI call,
network call, or token-log output is part of v12.19.

## Final Phase Status

Field State UI phase status: CLOSED for offline UI path.

The app now has a checkbox-gated, user-confirmed field-state UI path from
dialog input to `battle_state_context.field`, verified through mocked provider
prompt smoke. The phase remains intentionally bounded to current context only.

## Next Recommendation

Recommended next milestone:

- v12.20 Controlled Field State Gemini Smoke Design

Reason:

- the UI-selected field-state path is closed offline; before any actual Gemini
  execution, the controlled one-call/no-retry actual smoke should be designed
  with strict pre-call checks and explicit T1 approval requirements.

Alternatives:

- v12.20 Item Activation/Consumption Boundary Design
- v12.20 Battle State Status/Condition Source Design
