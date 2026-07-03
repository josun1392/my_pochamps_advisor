# v12.13 Field State UI Mapping Implementation

## Purpose

Record and verify the field-state UI mapping implementation for the
UI-selected prompt path.

This milestone makes the v12.12 helper/client mapping seam the active
implementation boundary: when the existing limited-context checkbox enables
`battle_state_context`, valid `field_profiles` can normalize into
`battle_state_context.field`.

## Implementation Scope

Implemented scope:

- use the existing limited-context checkbox hard gate
- keep `include_user_confirmed_fields=False` as the default adapter behavior
- enable field-profile mapping only when `enable_battle_state_context=True`
- normalize valid `field_profiles` through
  `build_field_state_from_field_profiles(...)`
- remove top-level UI-only `field_profiles` from advice payloads
- preserve user-confirmed item mapping
- preserve existing optional-context coexistence

Out of scope:

- FieldProfileDialog button integration
- `MainWindow._field_profiles` session storage
- new limited-context checkbox
- UI copy changes
- prompt guard wording changes
- battle log/parser support
- damage or KO behavior changes

## Changed Files

- `llm/advisor_battle_state_context.py`
- `llm/advisor_client.py`
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_ui_turn_pipeline_flag_flow.py`
- `docs/spike_v12.13_field_state_ui_mapping_implementation.md`
- `docs/PROGRESS.md`
- `docs/advisor_payload_contract.md`
- `docs/handoff_next_session_prompt_v1.9.md`

## Mapping Path

Implemented path:

```text
UI-selected battle_input["field_profiles"]
-> _build_ui_selected_prompt(...)
-> build_battle_state_context_from_ui_selected_state(
       ...,
       include_user_confirmed_items=enable_battle_state_context,
       include_user_confirmed_fields=enable_battle_state_context,
   )
-> build_field_state_from_field_profiles(...)
-> battle_state_context.field
-> serialized prompt
```

`field_profiles` is UI-only metadata. It is removed from the prompt payload as a
top-level key and can only appear through normalized `battle_state_context`.

## Checkbox Gate Behavior

Checkbox off:

- `enable_battle_state_context=False`
- `battle_state_context` omitted
- top-level `field_profiles` omitted from the prompt payload
- field values do not reach the LLM

Checkbox on:

- `enable_battle_state_context=True`
- `battle_state_context` included when non-empty
- `include_user_confirmed_fields=True`
- valid `field_profiles` normalize into `battle_state_context.field`
- existing limited contexts still coexist

## Field Profiles Normalization Behavior

Valid dialog metadata:

```python
{"status": "user_confirmed", "source": "user_input", "value": "..."}
```

maps to:

```python
{"known": True, "source": "user_confirmed", "value": "..."}
```

Covered field keys:

- weather
- terrain
- room
- screens
- hazards

Side-specific screens and hazards preserve their `self` / `opponent` value dict.

## Unknown vs None Behavior

- missing `field_profiles`: field stays unknown
- `value="unknown"`: unknown envelope
- trusted `value="none"`: user-confirmed known absence
- both-side empty screens/hazards: user-confirmed known absence

## Malformed/Forbidden Behavior

The helper/client mapping keeps unknown for:

- malformed field metadata
- missing status/source/value
- `context_derived`
- `calculated_from_visible`
- `damage_reverse`
- `model_guess`
- other untrusted or forbidden metadata

Direct payload validation still rejects forbidden known field sources.

## No Top-level Leakage

`filter_context_for_default_advice(...)` removes `field_profiles` before prompt
payload serialization. Tests verify that `field_profiles` does not remain in the
prompt payload when the checkbox is off or on.

## Coexistence With Existing Contexts

Verified coexistence with:

- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`
- `battle_state_context`
- user-confirmed item mapping

## Tests

Focused tests cover:

- checkbox off omits `battle_state_context`
- checkbox off omits top-level `field_profiles`
- checkbox on maps valid weather, terrain, room, screens, and hazards
- weather `none` maps to known absence
- weather `unknown` remains unknown
- malformed and forbidden field metadata remains unknown
- user-confirmed item mapping remains unchanged
- existing limited contexts coexist
- no duration, expiration, post-turn, damage precision, or resolved outcome
  fields are created
- top-level `field_profiles` does not leak into advice payloads

## Non-goals

v12.13 does not implement:

- FieldProfileDialog button integration
- MainWindow field-profile persistence UI
- battle log/parser support
- new checkbox
- UI copy updates
- prompt guard wording changes
- full Turn Engine behavior
- damage calculation behavior

## No Button Integration

No FieldProfileDialog entry point was added. The implementation accepts
`field_profiles` only when a caller supplies that metadata in the UI-selected
battle input.

## No Actual Gemini Call

No actual Gemini call, retry, second provider call, Vertex AI call, or
network/provider call is part of v12.13. All provider-path checks are mocked or
payload/prompt assertions.

## Next Recommendation

Recommended next:

- v12.14 FieldProfileDialog Button Integration Design

Reason:

- field-profile metadata can now safely flow through the existing
  limited-context gate, but the user-facing UI entry point and session-local
  storage owner should be designed before wiring the dialog into MainWindow.

Alternatives:

- v12.14 FieldProfileDialog Button Integration
- v12.14 Field State UI Mapping Offline Smoke
