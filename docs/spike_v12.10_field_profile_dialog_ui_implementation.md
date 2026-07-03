# v12.10 Field Profile Dialog UI Implementation

## Purpose

Implement a standalone Field Profile Dialog that can collect user-confirmed current field context for weather, terrain, room, screens, and hazards.

This milestone implements the dialog UI and result API only. It does not connect field profiles to `battle_state_context`, `battle_input`, prompt generation, or provider calls.

## Implemented Files

- `ui/widgets/field_profile_dialog.py`
- `tests/test_field_profile_dialog.py`
- `docs/spike_v12.10_field_profile_dialog_ui_implementation.md`
- `docs/PROGRESS.md`
- `docs/advisor_payload_contract.md`
- `docs/handoff_next_session_prompt_v1.9.md`

## Dialog Behavior

`FieldProfileDialog` provides:

- weather single-select
- terrain single-select
- room single-select
- screens side-specific input for `self` and `opponent`
- hazards side-specific input for `self` and `opponent`
- `Apply`
- `Cancel`
- `Reset unknown`

The dialog exposes a `field_profiles` property after apply. The caller owns session-local persistence. v12.10 does not add a main-window button or any runtime mapping.

## Field Options

Weather:

- `unknown`
- `none`
- `sun`
- `rain`
- `sandstorm`
- `snow`

Terrain:

- `unknown`
- `none`
- `electric_terrain`
- `grassy_terrain`
- `misty_terrain`
- `psychic_terrain`

Room:

- `unknown`
- `none`
- `trick_room`
- `magic_room`
- `wonder_room`

Screens:

- `reflect`
- `light_screen`
- `aurora_veil`

Hazards:

- `stealth_rock`
- `spikes`
- `toxic_spikes`
- `sticky_web`

## Returned Field Profiles Shape

The dialog returns the v12.9 contract shape:

```python
{
    "weather": {
        "status": "user_confirmed",
        "source": "user_input",
        "value": "rain",
    },
    "terrain": {
        "status": "user_confirmed",
        "source": "user_input",
        "value": "electric_terrain",
    },
    "room": {
        "status": "user_confirmed",
        "source": "user_input",
        "value": "trick_room",
    },
    "screens": {
        "status": "user_confirmed",
        "source": "user_input",
        "value": {
            "self": ["reflect"],
            "opponent": ["light_screen"],
        },
    },
    "hazards": {
        "status": "user_confirmed",
        "source": "user_input",
        "value": {
            "self": [],
            "opponent": ["stealth_rock"],
        },
    },
}
```

## Unknown vs None Behavior

`unknown` means unconfirmed or not entered:

```python
{"status": "unknown", "source": "user_unconfirmed", "value": "unknown"}
```

`none` means user-confirmed absence:

```python
{"status": "user_confirmed", "source": "user_input", "value": "none"}
```

For screens and hazards, each group has an explicit mode:

- `Unknown`: returns unknown profile
- `None`: returns user-confirmed known absence, `{"self": [], "opponent": []}`
- `Selected`: returns selected side-specific values

## Apply / Cancel / Reset Behavior

- Apply builds and stores `field_profiles`, then accepts the dialog.
- Cancel rejects the dialog and leaves `field_profiles` as `None`.
- Reset unknown clears weather, terrain, room, screens, and hazards back to unknown without accepting the dialog.
- Initial `field_profiles` are loaded into the widgets when supplied.

## Tests Added

`tests/test_field_profile_dialog.py` covers:

- default unknown output
- single-value weather/terrain/room output
- `none` as known absence
- side-specific screens/hazards output
- reset unknown behavior
- cancel behavior
- initial profile loading
- absence of duration/expiration/post-turn/damage precision/resolved outcome fields

Existing contract tests remain green:

- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_ui_turn_pipeline_flag_flow.py`

## Non-goals

v12.10 does not implement:

- main window button
- `battle_input["field_profiles"]`
- UI-selected `battle_state_context` field mapping
- limited-context checkbox changes
- prompt guard wording changes
- payload builder call-flow changes
- battle log/parser support
- duration, expiration, post-turn, damage precision, or resolved outcome behavior

## No Mapping Implementation

The dialog is standalone. No runtime path reads its result yet.

## No Actual Gemini Call

No actual Gemini call, retry, second provider call, Vertex AI call, network/provider call, or token-log output is part of v12.10.

## Next Recommendation

Recommended next:

- v12.11 Field State UI Mapping Design

Reason:

- the dialog can now produce field profile metadata, but connecting it to the existing limited-context checkbox and UI-selected battle-state adapter should be designed before implementation.

Alternatives:

- v12.11 Field Profile Dialog UI Smoke Tests
- v12.11 Field State UI Mapping Implementation
