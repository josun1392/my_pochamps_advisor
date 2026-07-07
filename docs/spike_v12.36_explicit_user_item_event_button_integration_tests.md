# v12.36 Explicit User Item Event Button Integration Tests

## Purpose

Lock the future Item Event Dialog button integration behavior before adding a
real LLMAdvicePanel button or MainWindow session-local wiring.

This phase is test-first only. It does not implement the real button, real
MainWindow `_item_event_confirmations`, `item_event_context` payload mapping, or
observed event prompt mapping.

## Test-First Integration Contract

New test file:

- `tests/test_item_event_button_integration_contract.py`

The tests model future integration behavior around the standalone v12.35
`ItemEventDialog` result contract and v12.33 validation helper.

## Test-Only Seam

The contract uses:

- `_FakeItemEventDialog`
- `_ItemEventButtonContractController`
- `_ProviderSpy`

The controller models the future candidate session-local state:

```text
MainWindow._item_event_confirmations: list[dict]
```

## Button/Open No-Advice Behavior

The future button/open action is locked as local UI behavior:

- opening Item Event Dialog does not emit advice request behavior in the test
  seam
- opening Item Event Dialog does not call a provider
- opening Item Event Dialog does not call Gemini

## Apply Behavior

Apply behavior is locked as:

- accepted dialog result is saved to session-local `_item_event_confirmations`
- stored event preserves `side`, `item`, `event_type`, `status`, `source`,
  `turn`, and `note`
- stored event remains an observed candidate only
- no resolved, post-turn, exact HP, exact damage, RNG, or Speed/order fields are
  added

## Cancel Behavior

Cancel behavior is locked as:

- existing `_item_event_confirmations` remain unchanged
- draft dialog result is discarded

## Reset Behavior

Reset behavior is locked as:

- Reset clears dialog-local draft to an empty event list
- Reset only persists if Apply is pressed
- Reset + Cancel preserves previous session state
- Reset + Apply stores an empty list

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

## Existing Field State Behavior Unchanged

Tests verify:

- no real `item_event_button` or `item_event_requested` signal exists yet
- existing `field_profile_button` still emits only `field_profile_requested`
- `advice_requested` is not emitted by field profile button behavior
- limited-context checkbox default remains off
- existing `field_profiles` still flow only through `battle_state_context.field`
  when the checkbox is enabled

## No Payload Mapping Behavior

Session-local item event confirmations are not included in generated LLM
payloads yet.

Tests verify:

- `_item_event_confirmations` is not added to battle input
- `item_event_confirmations` is absent from generated prompt payloads
- trusted `item_event_context` remains absent
- prompt text does not contain observed item event claims

## Recursive Forbidden Field Scan

Session state and prompt payloads are recursively checked for absence of:

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

v12.36 does not implement:

- real LLMAdvicePanel Item Event button
- real MainWindow `_item_event_confirmations` wiring
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

## Test Results

- `uv run pytest tests/test_item_event_button_integration_contract.py -q`: `21 passed`

Related and full test results should be recorded before commit.

## Next Recommendation

v12.37 Explicit User Item Event Button Integration.

The standalone dialog exists and the future button/session-local behavior is
now locked test-first, so the next safe step is adding the actual LLMAdvicePanel
button and MainWindow wiring.

## No Actual Gemini Call

No actual Gemini call, retry, second provider call, Vertex AI call, or
network/provider call is part of v12.36.
