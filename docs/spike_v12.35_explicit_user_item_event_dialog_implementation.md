# v12.35 Explicit User Item Event Dialog Implementation

## Purpose

Implement the standalone Item Event Dialog against the v12.34 UI contract.

This phase adds the dialog widget and dialog unit tests only. It does not add a
button, MainWindow wiring, `item_event_context` payload mapping, observed event
prompt mapping, provider calls, or any item effect resolution.

## Implemented Widget

New widget:

- `ui/widgets/item_event_dialog.py`

Implemented class:

- `ItemEventDialog`

The dialog validates the draft with the v12.33
`validate_explicit_user_item_event_confirmation(...)` helper before accepting.

## Fields

The dialog includes:

- `Side`
  - `self`
  - `opponent`
- `Item`
  - editable combo box
  - initial options: `focus-sash`, `quick-claw`, `sitrus-berry`,
    `yache-berry`, `leftovers`, `choice-scarf`
- `Event type`
  - `item_activation_observed`
  - `item_consumption_observed`
  - `item_recovery_observed`
  - `item_prevention_observed`
  - `item_reveal_observed`
- `Turn`
  - optional positive integer
  - blank is represented as `None`
- `Note`
  - optional text
  - blank is represented as `None`

## Returned Event Shape

Accepted event example:

```python
{
    "side": "opponent",
    "item": "focus-sash",
    "event_type": "item_activation_observed",
    "status": "user_confirmed",
    "source": "explicit_user_event_confirmation",
    "turn": 5,
    "note": "User saw Focus Sash activation text.",
}
```

`turn` and `note` keys are retained. Blank values are returned as `None`.

## Apply Behavior

Apply behavior:

- builds the current draft event
- adds metadata `status=user_confirmed`
- adds metadata `source=explicit_user_event_confirmation`
- validates the event through the explicit user item event helper
- stores a one-element result list for valid drafts
- accepts the dialog

The result remains an observed candidate only.

## Cancel Behavior

Cancel behavior:

- rejects the dialog
- leaves `item_event_confirmations` as `None`
- does not expose draft changes to the caller

Caller/session state preservation remains the caller's responsibility until
MainWindow wiring is implemented in a later phase.

## Reset Behavior

Reset behavior:

- clears the dialog-local draft
- does not accept the dialog by itself
- leaves `item_event_confirmations` as `None` until Apply
- Reset + Apply stores an empty list

This matches the v12.34 contract.

## Validation Rules

Required:

- `side`
- `item`
- `event_type`
- `status`
- `source`

Allowed:

- `side`: `self`, `opponent`
- `source`: `explicit_user_event_confirmation`
- `status`: `user_confirmed`
- `event_type`: observed event types only

Invalid drafts raise validation errors and do not save result events.

## Forbidden Fields

Dialog results do not include:

- `resolved_item_effect`
- `post_turn_item_state`
- `post_turn_hp_from_item`
- `exact_hp`
- `exact_damage`
- `item_damage_modifier_applied`
- `item_speed_modifier_applied`
- `rng_roll`
- `speed_order_override`
- `quick_claw_activated_by_rng`
- `focus_sash_post_hit_hp_1`
- `berry_recovered_exact_hp`

## No Payload Mapping Boundary

v12.35 does not implement:

- `item_event_context` payload mapping
- observed event prompt mapping
- `item_event_confirmations` inclusion in generated LLM payloads
- trusted item event claims in prompt text

## No Provider Call Boundary

The standalone dialog has no provider path. It does not request advice, call
Gemini, call Vertex AI, retry providers, or make network/provider calls.

## Tests

- `uv run pytest tests/test_item_event_dialog.py -q`: `13 passed`
- `uv run pytest tests/test_item_event_dialog_ui_contract.py -q`: `25 passed`

Related and full test results should be recorded before commit.

## Next Recommendation

v12.36 Explicit User Item Event Button Integration Tests.

The standalone dialog is implemented. The next safe step is to test-first lock
LLMAdvicePanel/MainWindow button behavior and session-local wiring before adding
the real button.

## No Actual Gemini Call

No actual Gemini call, retry, second provider call, Vertex AI call, or
network/provider call is part of v12.35.
