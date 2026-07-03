# v12.11 Field State UI Mapping Design

## Purpose

Design how future `FieldProfileDialog` output should be stored and mapped into
`battle_state_context.field` without implementing that mapping.

This milestone is design-only. It does not add a field button, does not connect
`field_profiles` to `battle_state_context`, does not change prompt guard
wording, and does not run any provider call.

## Inspected Files

- `docs/spike_v12.10_field_profile_dialog_ui_implementation.md`
- `docs/spike_v12.9_field_profile_dialog_contract_tests.md`
- `docs/spike_v12.8_field_profile_dialog_design.md`
- `docs/spike_v12.7_field_state_ui_source_inventory.md`
- `docs/advisor_payload_contract.md`
- `docs/PROGRESS.md`
- `docs/handoff_next_session_prompt_v1.9.md`
- `ui/widgets/field_profile_dialog.py`
- `ui/widgets/item_profile_dialog.py`
- `ui/widgets/llm_advice_panel.py`
- `ui/widgets/pokemon_panel.py`
- `ui/main_window.py`
- `llm/advisor_battle_state_context.py`
- `llm/advisor_client.py`
- `tests/test_field_profile_dialog.py`
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_ui_turn_pipeline_flag_flow.py`

## Current UI/Profile State

Current item profile flow:

- `PokemonPanel` owns per-slot `item_profile` state.
- `ItemProfileDialog` writes user-confirmed item metadata back to the active
  `PokemonPanel`.
- `MainWindow._build_llm_battle_input()` collects active self/opponent
  `item_profiles`.
- `run_ui_selected_advice(...)` can generate `battle_state_context` from
  UI-selected state when the existing limited-context checkbox is enabled.
- Valid item profile metadata is mapped only because the current provider path
  passes `include_user_confirmed_items=enable_battle_state_context`.

Current field profile state:

- `FieldProfileDialog` is standalone.
- The dialog returns the v12.9 `field_profiles` shape.
- `MainWindow` does not yet store `field_profiles`.
- `_build_llm_battle_input()` does not yet emit `field_profiles`.
- `build_battle_state_context_from_ui_selected_state(...)` does not yet read
  `field_profiles`.
- No field button, field UI mapping, or battle-state connection exists.

Field state differs from item state because weather, terrain, room, screens, and
hazards are battlefield-level state, not per-Pokemon slot state.

## Proposed Storage Path

Future storage should be session-local and owned by `MainWindow`:

```python
self._field_profiles: dict | None
```

Recommended flow:

```text
FieldProfileDialog
-> MainWindow._field_profiles
-> gated UI-selected battle_input copy
-> build_battle_state_context_from_ui_selected_state(...)
-> battle_state_context.field
-> serialized prompt
```

Storage policy:

- `MainWindow` owns field profile persistence for the current session.
- `PokemonPanel` should not own `field_profiles` because field state applies to
  the shared battlefield.
- Opening the future dialog should pass the current `MainWindow._field_profiles`
  as initial dialog state.
- `Apply` should replace `MainWindow._field_profiles` with the dialog result.
- `Cancel` should leave `MainWindow._field_profiles` unchanged.
- `Reset unknown` should only affect persisted state if the user applies it.
- Applied reset output may be stored as a full unknown `field_profiles` dict,
  because the helper already normalizes trusted `unknown` values to unknown
  envelopes.

To avoid checkbox-off leakage, `field_profiles` should not be sent to the
provider path unless the limited-context checkbox enables battle-state context.
One safe implementation shape is:

```python
_build_llm_battle_input(include_field_profiles: bool = False)
```

where the default remains `False`, and the future advice path calls it with
`include_field_profiles=enable_battle_state_context`.

## Proposed Mapping Gate

The existing limited-context checkbox remains the hard gate.

Checkbox off:

- `enable_battle_state_context=False`
- top-level `battle_state_context` omitted
- `field_profiles` omitted from provider payload inputs
- no serialized field state appears in the prompt
- no battle-state guard appears because battle state is absent

Checkbox on:

- `enable_battle_state_context=True`
- `battle_state_context` included through the existing optional-context path
- valid `field_profiles` may map into `battle_state_context.field`
- missing `field_profiles` keeps field unknown
- trusted `unknown` values keep field unknown
- trusted `none` values map to known absence
- malformed or forbidden metadata normalizes to unknown at the helper layer
- existing `turn_pipeline`, `turn_order_context`, and `opponent_move_context`
  still coexist with `battle_state_context`

Toggling the checkbox alone must still not call Gemini.

## Future Helper/API Shape

Prefer a new keyword aligned with item mapping:

```python
build_battle_state_context_from_ui_selected_state(
    battle_input,
    include_user_confirmed_items=False,
    include_user_confirmed_fields=False,
)
```

Rationale:

- `include_user_confirmed_items` already gates item profile metadata.
- `include_user_confirmed_fields` describes the trusted field dialog source and
  avoids implying arbitrary field-profile ingestion.
- Default `False` preserves current behavior.
- The caller should pass `True` only when `enable_battle_state_context=True`.

Future implementation can:

```python
if include_user_confirmed_fields:
    field = build_field_state_from_field_profiles(
        battle_input.get("field_profiles")
    )
```

Then it can pass that normalized `field` into the existing
`build_battle_state_context(...)` helper.

The provider path can later align with the current item pattern:

```python
build_battle_state_context_from_ui_selected_state(
    payload,
    include_user_confirmed_items=enable_battle_state_context,
    include_user_confirmed_fields=enable_battle_state_context,
)
```

This is a future design target only. v12.11 does not implement it.

## Unknown vs None Mapping

Mapping semantics must preserve v12.9:

- missing key: unknown envelope
- missing `field_profiles`: all field entries unknown
- `value="unknown"`: unknown envelope
- malformed key: unknown envelope
- forbidden metadata: unknown envelope
- trusted `value="none"`: known absence envelope
- trusted screens/hazards `{"self": [], "opponent": []}`: known absence
- trusted side-specific screens/hazards lists: preserve side-specific value dict

Examples:

```python
{"known": False, "value": "unknown"}
```

```python
{"known": True, "source": "user_confirmed", "value": "none"}
```

```python
{
    "known": True,
    "source": "user_confirmed",
    "value": {"self": ["reflect"], "opponent": ["light_screen"]},
}
```

## Malformed/Forbidden Behavior

Helper-layer behavior:

- missing metadata normalizes to unknown
- malformed metadata normalizes to unknown
- untrusted status/source normalizes to unknown
- forbidden source metadata normalizes to unknown

Direct payload contract behavior:

- malformed known field envelopes remain rejected
- forbidden field sources remain rejected
- `context_derived` and `calculated_from_visible` remain rejected for known
  field values

Forbidden field sources remain:

- damage reverse inference
- KO context inference
- turn order inference
- opponent move context inference
- species/common/meta inference
- item inferred effects
- legality gate result
- resist berry context
- hidden state guess
- LLM/model guess
- context-derived field state
- calculated-from-visible field state

## Safety Boundary

- `field_profiles` are user-confirmed current context only.
- checkbox off means no `battle_state_context` field data is sent.
- known field does not imply duration.
- known field does not imply expiration.
- known field does not imply post-turn outcome.
- known field does not imply damage precision.
- known field does not imply full turn outcome.
- `none` means user-confirmed absence only.
- unknown remains unknown.
- no field source from damage reverse inference.
- no field source from species/common/meta inference.
- no field source from item inferred effects.
- no field source from LLM/model guess.
- no hidden field guessing.

## Future Tests

Recommended v12.12 Field State UI Mapping Tests:

- checkbox off omits `battle_state_context` and does not leak
  `field_profiles`
- checkbox on plus missing `field_profiles` keeps field unknown
- checkbox on plus valid weather `rain` maps to known weather
- checkbox on plus weather `none` maps to known absence
- checkbox on plus weather `unknown` keeps weather unknown
- checkbox on plus terrain maps to known terrain
- checkbox on plus room maps to known room
- checkbox on plus side-specific screens maps to known screens
- checkbox on plus side-specific hazards maps to known hazards
- checkbox on plus both-side empty screens/hazards maps to known absence
- checkbox on plus malformed `field_profiles` keeps field unknown
- checkbox on plus forbidden `field_profiles` source keeps field unknown
- known fields create no duration field
- known fields create no expiration field
- known fields create no post-turn field
- known fields create no damage precision or resolved outcome field
- known fields do not change `damage_estimate`
- known fields do not change `ko_context`
- user-confirmed item mapping remains unchanged
- existing `turn_pipeline`, `turn_order_context`, and
  `opponent_move_context` still coexist
- checkbox toggle alone still does not call a provider

## Future Implementation Plan

Recommended sequence:

1. v12.12 Field State UI Mapping Tests
2. v12.13 Field State UI Mapping Implementation
3. v12.14 Field Profile Dialog Button Integration
4. later UI copy update after the entry point and mapping behavior are stable

Button integration can also be done before mapping implementation if T2 chooses
to make the dialog visible earlier, but mapping tests should still guard the
provider payload boundary before any field data reaches the LLM path.

## No Production Code Change

v12.11 changes documentation only. It does not modify runtime code, tests,
checkbox behavior, UI copy, payload builder flow, helper API, prompt guard
wording, or provider behavior.

## No Actual Gemini Call

No actual Gemini call, retry, second provider call, Vertex AI call, or
network/provider call is part of v12.11.

## Next Recommendation

Recommended next:

- v12.12 Field State UI Mapping Tests

Reason:

- field profile UI and helper contracts now exist, but the checkbox gate,
  provider-payload omission behavior, unknown/none mapping, malformed handling,
  and coexistence with existing optional contexts should be locked before
  runtime mapping is implemented.

Alternatives:

- v12.12 Field State UI Mapping Implementation
- v12.12 Field Profile Dialog Button Integration
