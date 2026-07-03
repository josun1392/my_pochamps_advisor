# v12.17 Limited Context Copy Update for Field State

## Purpose

Update the existing limited-context checkbox tooltip/status copy so it explains
that enabled limited context can include user-confirmed field state.

This milestone is UI copy and tests only. It does not change checkbox behavior,
`FieldProfileDialog` behavior, field-profile mapping, prompt guard wording,
payload builder flow, or provider behavior.

## Implementation Scope

Changed:

- `TURN_PIPELINE_HELP_TEXT`
- `TURN_PIPELINE_STATUS_TEXT`
- UI copy tests for the limited-context checkbox/status label

Preserved:

- existing limited-context checkbox label
- default unchecked state
- single existing limited-context checkbox
- `Field state` button behavior
- `field_profiles` mapping behavior
- `battle_state_context` prompt guard wording

## Changed Files

- `ui/widgets/llm_advice_panel.py`
- `tests/test_ui_turn_pipeline_flag_flow.py`
- `tests/test_advisor_payload_contract.py`
- `docs/PROGRESS.md`
- `docs/advisor_payload_contract.md`
- `docs/handoff_next_session_prompt_v1.9.md`

## Copy Before / After Summary

Before v12.17, the limited-context copy listed:

- candidate turn events
- turn-order helper context
- UI-visible opponent move candidates
- current Pokemon/HP snapshot
- user-confirmed items

After v12.17, it also lists:

- user-confirmed field state

The updated tooltip describes field state as current user-confirmed context for:

- weather
- terrain
- room
- screens
- hazards

## Field State Meaning

Field state means user-confirmed current field context only.

It can help the LLM see the user's current weather/terrain/room/screens/hazards
input when the existing limited-context checkbox allows `battle_state_context`.

It does not become field duration, expiration, post-turn field state, exact
damage, or a full turn simulation.

## Forbidden Implications

The updated tests guard that the copy does not imply:

- field state precisely calculates damage
- weather or terrain turn count is confirmed
- next-turn result is confirmed
- screens or hazards expiration is calculated
- full turn outcome is simulated
- field state infers hidden field state

## Tests

Updated tests:

- `tests/test_ui_turn_pipeline_flag_flow.py`
- `tests/test_advisor_payload_contract.py`

Covered behavior:

- checkbox default remains unchecked
- copy still mentions existing limited contexts
- copy mentions user-confirmed field state
- copy describes field state as current context
- copy mentions weather/terrain/room/screens/hazards meaning
- copy avoids duration, expiration, post-turn outcome, exact damage, and full
  outcome certainty
- Field state button remains present through existing v12.16 tests
- provider calls are not triggered by copy/button tests

## Non-Goals

- No actual Gemini call.
- No new limited-context checkbox.
- No checkbox default change.
- No `FieldProfileDialog` behavior change.
- No field mapping behavior change.
- No prompt guard wording change.
- No payload builder call-flow change.
- No full Turn Engine behavior.
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

- v12.18 Field State UI End-to-End Offline Smoke

Reason:

- button, storage, mapping, and copy are now connected; a mocked provider smoke
  can verify the whole UI-selected prompt path without an actual Gemini call.

Alternatives:

- v12.18 Field State UI Phase Closure
- v12.18 Controlled Field State Gemini Smoke Design
