# v12.9 Field Profile Dialog Contract Tests

## Purpose

Lock the future Field Profile Dialog contract before any UI implementation or runtime field mapping.

This milestone tests `field_profiles` shape, `unknown` vs `none` semantics, trusted metadata mapping, malformed behavior, and safety boundaries for weather, terrain, room, screens, and hazards.

## Contract Scope

v12.9 covers only the metadata boundary for future dialog output:

- `field_profiles.weather`
- `field_profiles.terrain`
- `field_profiles.room`
- `field_profiles.screens`
- `field_profiles.hazards`

It does not connect `field_profiles` to the UI-selected payload path. The existing limited-context checkbox and payload builder call flow are unchanged.

## Field Profiles Shape

Locked trusted shape:

```python
"field_profiles": {
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

The helper `build_field_state_from_field_profiles(...)` normalizes this future dialog shape into the existing `battle_state_context.field` envelope shape.

## Unknown vs None Semantics

Locked semantics:

- `unknown` means the user did not confirm, did not enter, or supplied untrusted/malformed metadata.
- `unknown` normalizes to `{"known": False, "value": "unknown"}`.
- `none` means the user confirmed that no active field effect exists for that category.
- trusted `none` normalizes to `{"known": True, "source": "user_confirmed", "value": "none"}` for weather, terrain, and room.
- trusted empty side-specific screens/hazards values with both `self` and `opponent` present are known absence values.

Side-specific known absence example:

```python
{
    "known": True,
    "source": "user_confirmed",
    "value": {"self": [], "opponent": []},
}
```

Single-side empty values such as `{"self": []}` remain malformed because they do not confirm both sides and contain no known condition.

## Metadata Mapping

Locked mapping:

- `status=user_confirmed`
- `source=user_input`
- valid `value`

maps to:

```python
{"known": True, "source": "user_confirmed", "value": "<field-value>"}
```

`explicit_input` remains a fixture/manual API source. The Field Profile Dialog contract does not emit `explicit_input`.

## Malformed Behavior

The helper keeps unknown when metadata is:

- missing `status`
- missing `source`
- missing `value`
- `status` other than `user_confirmed`
- `source` other than `user_input`
- `value="unknown"`
- empty string value
- unsupported side-specific shape
- forbidden source such as `context_derived`, `calculated_from_visible`, `damage_reverse`, or `model_guess`

Payload validation still rejects direct malformed known field envelopes. The helper normalizes future dialog metadata before payload insertion.

## Tested Field Keys

Covered keys:

- `weather`
- `terrain`
- `room`
- `screens`
- `hazards`

## Screens/Hazards Side-specific Behavior

Locked behavior:

- `self` and `opponent` values are preserved inside the existing known envelope.
- lists of condition ids are accepted when at least one known condition is present.
- both-side empty lists are accepted as user-confirmed known absence.
- malformed side keys, scalar side values, missing known side values, and invalid list entries normalize to unknown.

## Safety Boundary

- known field is current context only
- known field does not imply duration
- known field does not imply expiration
- known field does not imply post-turn outcome
- known field does not imply damage precision
- known field does not imply full turn outcome
- unknown remains unknown
- no field source from damage reverse inference
- no field source from species/common/meta inference
- no field source from item inferred effects
- no field source from LLM/model guess
- no hidden field guessing

## Tests Added

Test locations:

- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`

Focused coverage:

- full `field_profiles` shape maps to known field envelopes
- `none` maps to known absence
- `unknown` maps to unknown
- missing `field_profiles` keeps all field entries unknown
- missing/malformed metadata stays unknown
- forbidden metadata stays unknown
- screens/hazards side-specific values are preserved
- screens/hazards both-side empty known absence is preserved
- duration/expiration/post-turn fields are not created
- species/HP behavior remains unchanged
- user-confirmed item behavior remains unchanged
- payload adapter accepts normalized known-none field state

## No UI Implementation

No Field Profile Dialog UI, widgets, button, checkbox, copy, or persistence behavior is implemented in v12.9.

## No Field Mapping Implementation

No runtime mapping from `battle_input["field_profiles"]` into the UI-selected `battle_state_context` path is implemented. That remains a future design/implementation step.

## No Actual Gemini Call

No actual Gemini call, retry, second provider call, Vertex AI call, network/provider call, or token-log output is part of v12.9.

## Next Recommendation

Recommended next:

- v12.10 Field Profile Dialog UI Implementation

Reason:

- the future dialog metadata contract is now locked enough to implement the UI without connecting it to runtime advisor payload mapping.

Alternatives:

- v12.10 Field State UI Mapping Design
- v12.10 Field Profile Dialog UI Smoke Tests
