# v12.37 Explicit User Item Event Button Integration

## Purpose

Implement the real Item Event button/session-local UI path that was locked by v12.36, while keeping item event confirmations out of LLM payloads and prompts.

## Implemented Button

- `LLMAdvicePanel` now exposes `item_event_requested`.
- `LLMAdvicePanel` now has an `Item event` button with object name `itemEventButton`.
- The button is separate from `advice_requested`.
- Clicking the button opens the Item Event dialog path only.
- Clicking the button does not request advice and does not call a provider.

## MainWindow Session-Local State

- `MainWindow._item_event_confirmations: list[dict]` is initialized as an empty list.
- `MainWindow` connects `item_event_requested` to `_open_item_event_dialog`.
- `_open_item_event_dialog` opens `ItemEventDialog(current_events=...)`.
- The state is session-local UI state only.
- It is not persisted.
- It is not mapped into `battle_input`.
- It is not mapped into generated prompt payloads.

## Apply Behavior

- On dialog accept, `MainWindow` reads `dialog.item_event_confirmations`.
- The returned list is validated with `validate_explicit_user_item_event_confirmation(...)`.
- Valid observed candidates replace `_item_event_confirmations`.
- Stored events preserve:
  - `side`
  - `item`
  - `event_type`
  - `status=user_confirmed`
  - `source=explicit_user_event_confirmation`
  - optional `turn`
  - optional `note`

## Cancel Behavior

- Dialog reject returns without changing `_item_event_confirmations`.
- Previous session-local state is preserved.

## Reset Behavior

- Reset remains dialog-local.
- Reset + Cancel preserves previous `_item_event_confirmations`.
- Reset + Apply stores an empty list.

## Invalid Event Behavior

- Invalid dialog output is revalidated before saving.
- Invalid event output does not replace previous session-local state.
- Rejected cases include:
  - invalid source
  - invalid status
  - invalid event type
  - missing required fields
  - resolved item effect fields
  - post-turn state fields
  - exact HP/damage fields
  - RNG/order fields

## No Advice/Provider Call Boundary

- The Item Event button emits only `item_event_requested`.
- It does not emit `advice_requested`.
- It does not start `LLMAdviceWorker`.
- It does not call Gemini, Vertex AI, or any provider path.

## No Payload Mapping Boundary

- `_item_event_confirmations` remains UI-only.
- `item_event_confirmations` is not added to `battle_input`.
- `item_event_context` remains absent from prompt payloads.
- Observed item event claims are not written into prompts.
- No resolved item effect, post-turn item state, exact HP, exact damage, RNG, or speed/order result is generated.

## Existing Field State Behavior Unchanged

- Existing Field state button behavior remains separate.
- Existing limited context checkbox default and gate behavior remain unchanged.
- Existing `field_profiles` mapping through `battle_state_context.field` remains unchanged.

## Tests

- `uv run pytest tests/test_item_event_button_integration_contract.py -q`
- `uv run pytest tests/test_item_event_dialog.py -q`
- `uv run pytest tests/test_item_event_dialog_ui_contract.py -q`
- `uv run pytest tests/test_field_profile_button_integration_contract.py -q`
- `uv run pytest tests/test_ui_turn_pipeline_flag_flow.py -q`
- `uv run pytest tests/test_advisor_payload_contract.py -q`
- `uv run pytest tests/test_advisor_battle_state_context.py -q`
- `uv run pytest -q`

## Next Recommendation

Recommended next:
- v12.38 Item Event Payload Mapping Design

Reason:
- The dialog and button/session-local storage path now exists. The next safe step is to design when and how observed user-confirmed item events may enter payloads, including gate/source/status boundaries, before implementation.

## No Actual Gemini Call

- No actual Gemini call was executed.
- No retry was executed.
- No second provider call was executed.
- No Vertex AI call was executed.
- No provider/network call was executed.
