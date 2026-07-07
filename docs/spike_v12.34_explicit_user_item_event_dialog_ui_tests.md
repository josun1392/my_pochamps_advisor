# v12.34 Explicit User Item Event Dialog UI Tests

## Purpose

Lock the future Item Event Dialog behavior with UI contract tests before any
real dialog, button, MainWindow wiring, or payload mapping implementation.

The tests define how explicit user item event confirmations should behave as
session-local observed candidates only.

## Test-First UI Contract

v12.34 adds a test-only seam:

- `_FakeItemEventDialog`
- `_ItemEventDialogContractController`
- `_ProviderSpy`

This seam models the future dialog owner behavior without adding production UI.
It validates events through the v12.33 helper-level validator and keeps the
runtime prompt payload unmapped.

## Apply Behavior

Apply behavior is locked as:

- accepted dialog results save to the session-local event list candidate
- stored events preserve `side`, `item`, `event_type`, `status`, `source`,
  `turn`, and `note`
- allowed observed event types remain observed candidates only
- no resolved, post-turn, exact HP, exact damage, RNG, or Speed/order fields are
  added
- opening/applying the dialog does not call a provider

Covered observed event types:

- `item_activation_observed`
- `item_consumption_observed`
- `item_recovery_observed`
- `item_prevention_observed`
- `item_reveal_observed`

## Cancel Behavior

Cancel behavior is locked as:

- existing session-local event confirmations remain unchanged
- draft dialog results are discarded
- no provider call occurs

## Reset Behavior

Reset behavior is locked as:

- Reset clears the dialog-local draft to an empty event list
- Reset + Cancel preserves previous session state
- Reset + Apply stores an empty session-local event list

## Invalid Event Behavior

Invalid event candidates are rejected and are not stored.

Covered invalid cases:

- missing `side`
- missing `item`
- missing `event_type`
- missing `status`
- missing `source`
- `source != explicit_user_event_confirmation`
- `status != user_confirmed`
- `event_type=resolved_item_effect`
- `event_type=post_turn_item_state`
- event includes `exact_hp`
- event includes `exact_damage`
- event includes `rng_roll`
- event includes `speed_order_override`

## No Advice/Provider Call Behavior

The future item event dialog open action is locked to be a local UI action:

- opening the dialog does not emit advice request behavior in the test seam
- opening the dialog does not call a provider
- opening the dialog does not call Gemini

The current `LLMAdvicePanel` is also checked to ensure v12.34 does not add a
real item event button or signal.

## No Payload Mapping Behavior

Stored test-only `item_event_confirmations` are not sent into generated LLM
payloads yet.

Checks verify:

- `item_event_confirmations` is absent from generated prompt payloads
- trusted `item_event_context` is absent
- observed item event claims are absent from prompt text
- existing limited-context checkbox behavior remains unchanged
- existing field profile mapping still goes only through
  `battle_state_context.field` when the checkbox is enabled

## Recursive Forbidden Field Scan

Stored events and prompt payloads are recursively checked for absence of:

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

## Safety Boundary

v12.34 does not implement:

- real Item Event Dialog
- real button
- real `MainWindow._item_event_confirmations` wiring
- `item_event_context` payload mapping
- observed event prompt mapping
- battle log parser
- replay parser
- Turn Engine
- item activation
- item consumption
- resolved item effect
- post-turn item state
- exact HP calculation
- exact damage calculation
- RNG resolver
- Speed/order resolver

Explicit user item event confirmations remain observed candidates only.

## Test Results

- `uv run pytest tests/test_item_event_dialog_ui_contract.py -q`: `25 passed`

Related and full test results should be recorded before commit.

## Next Recommendation

v12.35 Explicit User Item Event Dialog Implementation.

The behavior is now locked test-first, so the next safe step is implementing the
real dialog against this contract.

## No Actual Gemini Call

No actual Gemini call, retry, second provider call, Vertex AI call, or
network/provider call is part of v12.34.
