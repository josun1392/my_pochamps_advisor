# v12.15 FieldProfileDialog Button Integration Tests

## Purpose

Lock the expected `FieldProfileDialog` button integration behavior before adding
the user-facing button or real `MainWindow._field_profiles` wiring.

This milestone is tests-first. It does not add the button, does not add
MainWindow session storage, does not change UI copy, does not change prompt
guard wording, and does not call any provider.

## Test Scope

Added seam-level tests for the future button handler contract:

- opening the field-profile dialog path
- Apply storing `field_profiles` into session-local state
- Cancel preserving previous `field_profiles`
- Reset unknown plus Apply storing unknown/default profiles
- saved `field_profiles` respecting the existing limited-context checkbox gate
- no provider call from open/apply/cancel/reset behavior
- unchanged limited-context checkbox default
- unchanged `battle_state_context` prompt guard wording

The tests use a test-only controller and fake dialog. This deliberately avoids
adding a production button, signal, or `MainWindow._field_profiles` attribute in
v12.15.

## Button Open Behavior

Expected future behavior:

- the selected entry point remains a secondary `Field state` button in
  `LLMAdvicePanel`
- button click should call the MainWindow-owned field-profile dialog handler
- the handler should instantiate/open `FieldProfileDialog`
- opening the dialog must not trigger Gemini, Vertex AI, or any provider call

v12.15 verifies this with a fake dialog factory and provider-call spy.

## Apply / Cancel / Reset State Behavior

Expected future behavior:

- Apply stores the dialog's `field_profiles` into session-local state
- Cancel leaves existing session-local `field_profiles` unchanged
- Reset unknown is dialog-local until Apply
- Reset unknown plus Apply stores the default unknown `field_profiles` shape

The stored shape remains the v12.9 contract:

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

## Checkbox Gate Behavior

The existing limited-context checkbox remains the only payload hard gate:

- checkbox off omits `battle_state_context`
- checkbox off omits top-level `field_profiles`
- checkbox off means saved field profiles do not reach the prompt
- checkbox on can map valid saved field profiles into
  `battle_state_context.field`

No new checkbox is added.

## No-Call Behavior

The button path is local UI state only:

- opening the dialog does not call Gemini
- Apply does not call Gemini
- Cancel does not call Gemini
- Reset unknown does not call Gemini
- no Vertex AI call, retry, second provider call, or network/provider call is
  part of this milestone

## Prompt Guard Unchanged Behavior

The tests lock the existing `battle_state_context` prompt guard string as the
field-profile button path is introduced. Field profiles remain current context
only and do not change prompt guard wording.

## Implementation Limits

No production UI was changed:

- no `LLMAdvicePanel` field-state button implementation
- no `MainWindow._field_profiles` implementation
- no production dialog handler
- no extra field mapping implementation
- no `FieldProfileDialog` behavior change
- no payload builder call-flow change
- no `LLMAdvicePanel` copy change

## Tests Added

- `tests/test_field_profile_button_integration_contract.py`

Covered behavior:

- field-profile button handler seam opens dialog and stores Apply results
- Cancel preserves previous session state
- Reset unknown plus Apply stores default unknown profiles
- saved profiles respect checkbox off/on prompt behavior
- checkbox default remains off
- battle-state prompt guard wording remains unchanged
- no provider-call seam is invoked by dialog open/apply/cancel/reset behavior

## Safety Boundary

- Field-profile button input is user-confirmed current context only.
- Checkbox off means no field-profile data is sent to the LLM payload.
- Known field does not imply duration.
- Known field does not imply expiration.
- Known field does not imply post-turn outcome.
- Known field does not imply damage precision.
- Known field does not imply full turn outcome.
- No field source comes from damage reverse inference.
- No hidden field guessing is introduced.
- No actual Gemini call was made.

## Next Recommendation

Recommended next milestone:

- v12.16 FieldProfileDialog Button Integration

Reason:

- button/session-state behavior is now locked at the seam level, so the next
  step can add the user-facing `LLMAdvicePanel` entry and MainWindow-owned
  session state while staying within the existing limited-context gate.

Alternatives:

- v12.16 Limited Context Copy Update for Field State
- v12.16 Field State UI End-to-End Offline Smoke
