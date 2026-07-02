# v12.3 Field State Source Design

## Purpose

Design safe source rules for future `battle_state_context.field` values:

- `weather`
- `terrain`
- `screens`
- `hazards`
- `room`

This is design-only. v12.3 does not implement field-state source extraction, battle log parsing, UI controls, payload builder changes, prompt guard wording changes, provider calls, or damage/KO behavior changes.

## Current Field Status

Current runtime behavior:

- limited-context checkbox default is off
- checkbox off omits `battle_state_context`
- checkbox on enables `battle_state_context` with the existing limited contexts
- checkbox on extracts self/opponent species and HP percent as `visible_ui`
- checkbox on can include valid user-confirmed item profiles
- field state remains unknown
- `known_conditions` remains `[]`

Current helper behavior:

- `build_battle_state_context(...)` creates required field keys through `_field_state(...)`.
- `BATTLE_STATE_CONTEXT_FIELD_FIELDS = ("weather", "terrain", "screens", "hazards", "room")`.
- Missing field entries become `{"known": False, "value": "unknown"}`.
- Provided field entries currently normalize through the general `_known_value_or_unknown(...)` helper.
- Helper-level field confidence can become `limited` when an allowed source is present.

Current UI-selected path:

- `build_battle_state_context_from_ui_selected_state(...)` does not read field state.
- It explicitly documents that it does not read field state or optional contexts.
- Existing `turn_pipeline`, `turn_order_context`, `opponent_move_context`, `damage_estimate`, and `ko_context` are not used as field sources.

## Inspected Files

- `docs/spike_v12.2_user_confirmed_item_actual_smoke_closure.md`
- `docs/spike_v11.12_user_confirmed_item_phase_closure.md`
- `docs/spike_v10.12_battle_state_context_ui_phase_closure.md`
- `docs/spike_v10.6_battle_state_ui_source_inventory.md`
- `docs/advisor_payload_contract.md`
- `docs/PROGRESS.md`
- `docs/handoff_next_session_prompt_v1.9.md`
- `llm/advisor_battle_state_context.py`
- `llm/advisor_client.py`
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_ui_turn_pipeline_flag_flow.py`
- `ui/main_window.py`
- `ui/widgets/llm_advice_panel.py`

## UI / Source Inventory

Current UI-visible sources:

- No current UI control exposes weather.
- No current UI control exposes terrain.
- No current UI control exposes screens.
- No current UI control exposes hazards.
- No current UI control exposes room effects.
- The existing limited-context checkbox only gates optional context inclusion.
- The checkbox is not itself a field-state source.

Current safe non-field UI sources:

- self/opponent species
- self/opponent HP percent
- user-confirmed item profiles

Current bounded contexts that must stay separate:

- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`
- `damage_estimate`
- `ko_context`
- item legality gate
- resist berry context

These contexts may mention conditions or calculations, but they must not be copied into `battle_state_context.field` as source-of-truth field state.

## Allowed Source Candidates

v12.3 recommends a field-specific source policy rather than reusing all currently allowed battle-state sources for field values.

Immediate future allowed candidates:

- `explicit_input`
- `user_confirmed`

Conditional future candidates:

- `visible_ui`: allowed only after an actual field-state UI display/control exists and the UI value is directly visible to the user.
- `battle_log_observed`: future only; requires a separate battle-log parser/source design.
- `parser_observed`: future only; requires a separate parser contract and tests.

Default stance:

- `calculated_from_visible` should remain forbidden for field state unless a later design proves a narrow deterministic mapping.
- Current field values should stay unknown unless a direct explicit/user-confirmed source exists.

Per-field notes:

| Field | Immediate safe source | Future candidate source | v12.3 decision |
| --- | --- | --- | --- |
| `weather` | `explicit_input`, `user_confirmed` | `visible_ui`, `battle_log_observed`, `parser_observed` | Keep unknown in current UI path. |
| `terrain` | `explicit_input`, `user_confirmed` | `visible_ui`, `battle_log_observed`, `parser_observed` | Keep unknown in current UI path. |
| `screens` | `explicit_input`, `user_confirmed` | `visible_ui`, `battle_log_observed`, `parser_observed` | Require side-specific value shape before implementation. |
| `hazards` | `explicit_input`, `user_confirmed` | `visible_ui`, `battle_log_observed`, `parser_observed` | Require side-specific value shape before implementation. |
| `room` | `explicit_input`, `user_confirmed` | `visible_ui`, `battle_log_observed`, `parser_observed` | Keep as current context only, not turn-order resolution. |

## Forbidden Sources

The following must not create known field state:

- damage reverse inference
- KO context inference
- turn order inference
- opponent move context inference
- turn pipeline candidate events
- species/common-set/meta inference
- item inferred effects
- legality gate result
- resist berry context
- hidden state guess
- model/LLM guess
- usage-based guess
- common weather/terrain setter assumptions
- HP-loss reverse inference for hazards/screens
- damage-range reverse inference for weather, screens, or terrain
- item or ability availability as implicit weather/terrain/room state

## Payload Shape Proposal

Keep the existing top-level field shape:

```python
{
    "field": {
        "weather": {"known": False, "value": "unknown"},
        "terrain": {"known": False, "value": "unknown"},
        "screens": {"known": False, "value": "unknown"},
        "hazards": {"known": False, "value": "unknown"},
        "room": {"known": False, "value": "unknown"},
    }
}
```

Known future envelope:

```python
{"known": True, "source": "user_confirmed", "value": "<field-state>"}
```

Recommended future values:

```python
"weather": {"known": True, "source": "user_confirmed", "value": "rain"}
"terrain": {"known": True, "source": "user_confirmed", "value": "electric"}
"room": {"known": True, "source": "user_confirmed", "value": {"trick_room": True}}
```

Side-specific screens/hazards should use a side-explicit value inside the existing known envelope:

```python
"screens": {
    "known": True,
    "source": "user_confirmed",
    "value": {
        "self": ["reflect"],
        "opponent": ["light_screen"],
    },
}
```

```python
"hazards": {
    "known": True,
    "source": "user_confirmed",
    "value": {
        "self": ["stealth_rock"],
        "opponent": ["spikes"],
    },
}
```

Do not change the field shape in v12.3. The side-specific nested shape should be locked by future tests before helper changes.

## Source / Confidence Policy

Unknown:

- no trusted field source exists
- value remains `{"known": False, "value": "unknown"}`
- field does not contribute to `confidence=limited`

Limited:

- explicit/user-confirmed field source is present
- field context is a current-state snapshot only
- the overall `battle_state_context.confidence` can remain `limited`

Known field limitations:

- known field does not imply duration accuracy unless duration source exists
- known field does not imply future expiration
- known field does not imply future activation
- known field does not imply final turn order
- known field does not imply damage precision unless a later damage-engine integration explicitly consumes it
- known field does not change `damage_estimate`, raw rolls, Q12, or `ko_context` in this phase

## Safety Boundary

- known weather/terrain/screen/hazard/room is current context only
- known field does not imply future duration
- known field does not imply post-turn expiration
- known field does not imply damage calculation precision unless a future separate design wires it into the damage engine
- unknown field remains unknown
- no field inference from damage
- no field inference from KO context
- no field inference from species/common sets
- no field inference from item effects
- no hidden state guessing
- no model/LLM field guessing
- no full Turn Engine behavior
- no resolved turn order
- no post-turn HP
- no item activation or consumption

## Future Contract / Helper Test Plan

Recommended v12.4 tests:

- default field remains unknown
- explicit weather can be preserved
- user_confirmed weather can be preserved
- explicit terrain can be preserved
- user_confirmed terrain can be preserved
- explicit screens can be preserved side-specifically
- user_confirmed screens can be preserved side-specifically
- explicit hazards can be preserved side-specifically
- user_confirmed hazards can be preserved side-specifically
- explicit room can be preserved
- user_confirmed room can be preserved
- forbidden field sources become unknown at helper level
- forbidden field sources are rejected at payload adapter level if injected into payload
- `visible_ui` field source is rejected until a real field UI source exists
- `calculated_from_visible` field source is rejected by field-specific policy
- known field does not create duration fields
- known field does not create expiration fields
- known field does not create post-turn outcome fields
- known field does not modify `damage_estimate`
- known field does not modify `ko_context`
- known field appears in prompt only when allowed source is present
- existing checkbox off/on behavior remains unchanged

## Future UI Integration Considerations

Do not connect field state to the existing checkbox until after contract tests and helper rules are locked.

If UI integration is later approved:

- add explicit field controls or verified visible field display first
- keep limited-context checkbox default off
- checkbox off must still omit `battle_state_context`
- checkbox on may include field state only when allowed field metadata exists
- missing/malformed/forbidden field metadata must remain unknown
- UI copy must avoid implying duration, expiration, damage precision, or resolved outcomes
- no battle log/parser source should be treated as available until a separate parser design exists

## No Production Code Change

v12.3 changes documentation only.

No implementation is added for:

- field state source adapter
- field UI controls
- battle log parser
- parser observed source
- damage-engine field consumption
- prompt guard wording
- payload builder call flow

## No Actual Gemini Call

No actual Gemini, retry, second provider, Vertex AI, network, or provider call is executed in v12.3.

## Next Recommendation

Recommended next:

- v12.4 Field State Contract Tests

Reason:

- Field source rules should be locked with contract/helper tests before helper or UI integration work.

Alternatives:

- v12.4 Field State Helper
- v12.4 Item Activation/Consumption Boundary Design
