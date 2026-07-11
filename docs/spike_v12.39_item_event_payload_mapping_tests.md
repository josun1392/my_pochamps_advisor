# v12.39 Item Event Payload Mapping Tests

## Purpose

Lock the v12.38 item event payload mapping design test-first before any runtime
`battle_input` mapping, `item_event_context` payload mapping, or observed event
prompt serialization.

## Test-First Payload Mapping Contract

New test file:

- `tests/test_item_event_payload_mapping_contract.py`

The tests use a test-only future mapper seam. Production UI, payload, and prompt
paths remain unchanged.

## Checkbox Off Behavior

- The limited context gate returns no future item event context candidate when
  disabled.
- `item_event_context` is absent.
- `observed_events` is absent.
- Observed item event prompt wording is absent.

## Checkbox On Behavior

- When enabled, valid explicit user event confirmations normalize into a
  future `item_event_context.observed_events` candidate.
- The test-only mapper uses the existing explicit user event validator.
- Empty event lists produce no context candidate.
- This behavior is not wired into the current runtime payload path.

## Valid Observed Event Behavior

The contract covers all allowed observed event types:

- `item_activation_observed`
- `item_consumption_observed`
- `item_recovery_observed`
- `item_prevention_observed`
- `item_reveal_observed`

Normalized candidates preserve:

- `side`
- `item`
- `event_type`
- `status=user_confirmed`
- `source=explicit_user_event_confirmation`
- optional `turn`
- optional `note`

The mapper candidate adds:

- `confidence=observed`

## Invalid Event Behavior

The test-only mapper rejects:

- missing required fields
- invalid source
- invalid status
- resolved or post-turn event types
- exact HP fields
- exact damage fields
- RNG fields
- Speed/order fields

Invalid events do not reach `observed_events` or prompt candidates.

## Recursive Forbidden Field Scan

Helper candidates and current prompt payloads are recursively checked for:

- `resolved_item_effect`
- `resolved_effects`
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

## Known Item Behavior Unchanged

- User-confirmed current items remain known item context only.
- Known items do not become observed events.
- Known items do not become activation, consumption, resolved effect, or
  post-turn state.

## Field State Behavior Unchanged

- Existing `battle_state_context.field` normalization remains unchanged.
- Existing limited context field gate remains unchanged.
- `field_profiles` do not become an item event source.

## Prompt Wording Boundary

The test-only safe serialization candidate allows:

- `User confirmed an observed item event.`
- `source: explicit_user_event_confirmation`
- `confidence: observed`
- `This does not resolve exact HP, damage, RNG, or turn order.`

It rejects positive claims about exact HP, resolved damage, successful RNG,
post-turn consumption state, or resolved Speed/order.

Current generated prompts still omit item event context because runtime mapping
is not implemented.

## Current Runtime Boundary

- `MainWindow._item_event_confirmations` remains session-local UI state.
- Current `battle_input` does not include `item_event_confirmations`.
- Current prompt payloads omit `item_event_context` for checkbox off and on.
- No production mapping or prompt serialization was added in v12.39.

## No Actual Gemini Call

- No actual Gemini call was executed.
- No retry was executed.
- No second provider call was executed.
- No Vertex AI call was executed.
- No provider/network call was executed.

## Next Recommendation

Recommended next:

- v12.40 Item Event Payload Mapping Implementation

Reason:

- v12.38 defined the mapping design and v12.39 locked the gate, validation,
  observed-only, coexistence, and prompt safety boundaries. Runtime mapping can
  now be implemented against these tests in a separately approved phase.
