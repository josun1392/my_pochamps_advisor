# v12.8 Field Profile Dialog Design

## Purpose

Design a future Field Profile Dialog that can collect user-confirmed current field context for `battle_state_context.field`.

This is design-only. v12.8 does not implement field UI, field mapping, battle log parsing, payload builder changes, prompt guard wording changes, provider calls, or damage/KO behavior changes.

## Inspected Files

- `docs/spike_v12.7_field_state_ui_source_inventory.md`
- `docs/spike_v12.6_field_state_prompt_offline_fixture.md`
- `docs/spike_v12.5_field_state_helper.md`
- `docs/spike_v12.4_field_state_contract_tests.md`
- `docs/spike_v12.3_field_state_source_design.md`
- `docs/advisor_payload_contract.md`
- `docs/PROGRESS.md`
- `docs/handoff_next_session_prompt_v1.9.md`
- `ui/widgets/item_profile_dialog.py`
- `ui/widgets/llm_advice_panel.py`
- `ui/widgets/pokemon_panel.py`
- `ui/main_window.py`
- `llm/advisor_battle_state_context.py`
- `llm/advisor_client.py`
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_ui_turn_pipeline_flag_flow.py`

## Dialog Scope

The dialog should solve the current UI source gap from v12.7:

- no current UI input for weather
- no current UI input for terrain
- no current UI input for screens
- no current UI input for hazards
- no current UI input for room state
- no current `battle_input["field_profiles"]`

The dialog should be a user-confirmed current field context entry surface. It should create metadata that a future adapter can map to `battle_state_context.field` only when the existing limited-context checkbox permits `battle_state_context`.

The first design scope is:

- weather current state
- terrain current state
- room current state
- side-specific screens
- side-specific hazards
- source metadata consistent with item profiles
- session-local field profile values

## Non-goals

v12.8 does not design or implement:

- exact field duration tracking
- turn-count entry
- post-turn expiration prediction
- damage calculator integration
- `damage_estimate` mutation
- `ko_context` mutation
- full Turn Engine state
- battle log parser
- replay parser
- hidden field inference
- field mapping into runtime payloads
- UI implementation
- new checkbox behavior
- prompt guard wording changes

Duration or turn count can be a future optional extension only after a separate contract defines its source, semantics, and expiration boundary.

## Field Value Options

These are design candidates, not a complete mechanics implementation.

### Weather

- `unknown`
- `none`
- `sun`
- `rain`
- `sandstorm`
- `snow`

### Terrain

- `unknown`
- `none`
- `electric_terrain`
- `grassy_terrain`
- `misty_terrain`
- `psychic_terrain`

### Room

- `unknown`
- `none`
- `trick_room`
- `magic_room`
- `wonder_room`

### Screens

Per side:

- `reflect`
- `light_screen`
- `aurora_veil`

Screens should be side-specific because self-side and opponent-side screens have different tactical meanings.

### Hazards

Per side:

- `stealth_rock`
- `spikes`
- `toxic_spikes`
- `sticky_web`

Hazards should be side-specific. A value under `self` means hazards on the user's side of the field. A value under `opponent` means hazards on the opponent's side.

## Unknown vs None Semantics

`unknown` and `none` must remain distinct.

`unknown` means:

- the user does not know the field state, or
- the user has not entered it, or
- the input is malformed, unsupported, or untrusted

`none` means:

- the user explicitly confirmed that no effect of that field category is active

Future adapter behavior should treat `none` as a known value only when metadata is trusted:

```python
{"status": "user_confirmed", "source": "user_input", "value": "none"}
```

For screens and hazards, a future design must decide whether a user-confirmed empty side-specific value is accepted as known absence:

```python
{
    "status": "user_confirmed",
    "source": "user_input",
    "value": {"self": [], "opponent": []},
}
```

Current v12.5 helper behavior requires at least one known side-specific screen or hazard condition for a known envelope. Therefore, known-none side-specific screens/hazards should be locked by future contract tests before implementation.

## Metadata Shape

The future dialog should reuse the item profile trust pattern:

- `status=user_confirmed`
- `source=user_input`
- field-specific `value`

Recommended future `field_profiles` shape:

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

Recommended unknown profile shape:

```python
{
    "status": "unknown",
    "source": "user_unconfirmed",
    "value": None,
}
```

Future adapter mapping candidate:

- trusted profile: `status=user_confirmed` + `source=user_input` + valid `value`
- output source: `user_confirmed`
- missing, empty, malformed, or forbidden metadata: unknown

`explicit_input` should remain reserved for fixture/manual API paths or a future explicit input surface that intentionally emits `explicit_input`.

## UI Behavior Proposal

Future dialog behavior:

- open from a future field-profile action or Battle State Panel
- prefill from current in-session `field_profiles` if present
- `Apply` updates the in-session field profile candidate
- `Cancel` discards dialog edits
- `Reset unknown` resets every field entry to unknown
- selecting `none` records explicit known absence for that field category
- weather, terrain, and room use single-select controls
- screens and hazards use side-specific multi-select controls for `self` and `opponent`
- selections persist for the current UI session only in the first implementation
- no disk persistence in the first implementation
- toggling the existing limited-context checkbox should still make no provider call

Suggested controls:

- weather combo box
- terrain combo box
- room combo box
- self/opponent screens checkbox groups
- self/opponent hazards checkbox groups
- `Apply`, `Cancel`, and `Reset unknown` actions

## Validation and Malformed Behavior

The dialog should not emit known field metadata for:

- unsupported option IDs
- missing `status`
- missing `source`
- missing `value`
- empty string values
- source other than `user_input` for UI-confirmed values
- status other than `user_confirmed` for known values
- non-list side values for screens/hazards
- side keys other than `self` and `opponent`
- hidden/model/context-derived values

Future adapter behavior should match the v12.5 helper boundary:

- trusted and valid field profiles may become known current context
- malformed field profiles normalize to unknown
- forbidden field sources remain unknown at helper/UI-adapter level
- direct payload known envelopes with forbidden field sources are rejected by payload validation

## Safety Boundary

- user-confirmed field is current context only
- field does not imply duration
- field does not imply expiration
- field does not imply post-turn outcome
- field does not imply damage precision
- field does not imply full turn outcome
- unknown remains unknown
- `none` is only known absence if user-confirmed
- no field source from damage reverse inference
- no field source from KO context inference
- no field source from turn order context inference
- no field source from opponent move context inference
- no field source from species/common/meta inference
- no field source from item inferred effects
- no field source from legality gate output
- no field source from resist berry context
- no field source from LLM/model guess
- no hidden field guessing

## Future Tests

Recommended v12.9 contract tests before UI implementation:

- default dialog state emits unknown field profiles
- weather `unknown` emits unknown metadata
- weather `none` emits trusted known absence metadata
- weather user-confirmed value emits trusted metadata
- terrain unknown/none/value behavior
- room unknown/none/value behavior
- screens side-specific multi-select metadata
- hazards side-specific multi-select metadata
- screens/hazards explicit empty known-none behavior is either accepted or rejected by contract
- malformed field profiles normalize to unknown in helper/UI-adapter layer
- unsupported option IDs normalize to unknown or are rejected before adapter
- `source=user_input` + `status=user_confirmed` maps to `user_confirmed`
- `explicit_input` remains non-dialog fixture/manual source unless a future explicit surface is designed
- known field profiles do not create duration fields
- known field profiles do not create expiration fields
- known field profiles do not create post-turn fields
- known field profiles do not change `damage_estimate`
- known field profiles do not change `ko_context`

## Future Implementation Plan

Recommended staged plan:

1. v12.9 Field Profile Dialog Contract Tests
2. v12.10 Field Profile Dialog UI Implementation
3. v12.11 Field State UI Mapping Design
4. v12.12 Field State UI Mapping Implementation
5. v12.13 Field State UI Offline Smoke

Keep the existing limited-context checkbox as the first hard gate:

- checkbox off omits `battle_state_context`, therefore field is omitted
- checkbox on can include known field only from valid trusted `field_profiles`
- checkbox on with missing/malformed/forbidden `field_profiles` keeps field unknown

UI copy should be updated only after the field UI and mapping contract are locked. Future copy can mention "user-confirmed field state" while avoiding duration, expiration, damage precision, or resolved outcome wording.

## No Production Code Change

v12.8 does not change production code, UI behavior, payload builder call flow, prompt guard wording, field helper behavior, damage estimates, KO context, or provider behavior.

## No Actual Gemini Call

No actual Gemini call, retry, second provider call, Vertex AI call, network/provider call, or token-log output is part of v12.8.

## Next Recommendation

Recommended next milestone:

- v12.9 Field Profile Dialog Contract Tests

Alternatives:

- v12.9 Field Profile Dialog UI Implementation
- v12.9 Field State UI Mapping Design

Rationale:

- the UI source inventory found no current field source
- the dialog design proposes `field_profiles` shape and unknown/none semantics
- tests should lock this shape before any UI implementation or runtime mapping
