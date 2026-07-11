# v12.42 Item Event Payload Mapping Phase Closure

## Purpose

Close the Item Event Payload Mapping phase covering v12.38 through v12.41.

## Phase Scope

- v12.38 Item Event Payload Mapping Design
- v12.39 Item Event Payload Mapping Tests
- v12.40 Item Event Payload Mapping Implementation
- v12.41 Observed Item Event Prompt Fixture

## Completed Milestones

### v12.38 Design

- Defined the future path from session-local confirmations through limited
  context gating to `item_event_context.observed_events`.
- Defined observed-only source, status, event type, forbidden field, semantic,
  prompt, and response boundaries.

### v12.39 Contract Tests

- Locked checkbox off/on, valid normalization, invalid handling, forbidden
  fields, known-item separation, field-state coexistence, and safe wording
  candidates with test-first contracts.

### v12.40 Implementation

- Connected `MainWindow._item_event_confirmations` to battle input only when
  the existing limited context checkbox is enabled.
- Normalized valid events into `item_event_context.observed_events`.
- Removed raw `item_event_confirmations` before provider payload serialization.
- Omitted invalid individual events and omitted item event context when no valid
  events remain.

### v12.41 Prompt Fixture

- Added a minimal prompt guard only when `item_event_context` is present.
- Verified the production advice prompt path offline with mocked `call_gemini`
  and mocked token logging.
- Covered all allowed observed event types, gate behavior, optional fields,
  known-item separation, invalid raw event omission, and forbidden claims.

## UI and Session-Local Source

`MainWindow._item_event_confirmations` is the session-local source.

- ItemEventDialog Apply stores validated event candidates.
- Cancel preserves previous session state.
- Reset + Apply stores an empty list.
- Invalid dialog output does not replace stored state.
- The Item event button emits its local request signal only; it does not request
  advice or call a provider itself.

## Limited Context Hard Gate

Checkbox off:

- `item_event_confirmations` is absent from battle input.
- `item_event_context` is absent from the LLM payload.
- `observed_events` is absent.
- The item-event prompt guard is absent.
- Event item and event type wording are absent.

Checkbox on:

- Valid explicit user-confirmed events may enter battle input.
- The client removes the raw UI list before provider serialization.
- Valid entries appear only as `item_event_context.observed_events`.

## Trusted Event Contract

Allowed metadata:

- `source=explicit_user_event_confirmation`
- `status=user_confirmed`
- `confidence=observed`

Allowed event types:

- `item_activation_observed`
- `item_consumption_observed`
- `item_recovery_observed`
- `item_prevention_observed`
- `item_reveal_observed`

Required fields:

- `side`
- `item`
- `event_type`
- `status`
- `source`

Optional fields:

- `turn`
- `note`

## Invalid Event Handling

The following are rejected by validation or omitted before payload mapping:

- missing required fields
- wrong source or status
- unsupported event type
- `resolved_item_effect`
- `post_turn_item_state`
- exact HP, exact damage, RNG, or Speed/order data

Individual invalid events are omitted. If every event is invalid,
`item_event_context` is omitted.

## Semantic Boundary

```text
known item = user-confirmed/current context only

known item != observed event
observed event != resolved effect
observed event != post-turn state
observed event != exact HP
observed event != exact damage
observed event != speed order result
observed event != RNG result
```

An item event is only a user-explicitly-confirmed observation. This phase does
not calculate or confirm actual recovery, prevented damage, Focus Sash HP,
Quick Claw RNG, final action order, item modifier application, or post-turn HP.

## Prompt Boundary

- The production prompt path is covered by offline fixtures.
- The observed-only guard appears only when `item_event_context` exists.
- Checkbox off and no-event cases have no item-event guard.
- Known item context and observed item event context serialize in separate
  sections.
- Positive resolved, exact, post-turn, RNG, and order claims are forbidden.
- Fixture provider calls use monkeypatches only; no actual provider call occurs.

## Unchanged Behavior

The phase did not change:

- known item/current item semantics
- field state mapping
- FieldProfileDialog behavior
- ItemEventDialog behavior
- Item event button Apply/Cancel/Reset behavior
- limited context field gate
- `damage_estimate`
- `ko_context`
- Q12 multipliers
- raw damage rolls
- provider retry behavior

## Remaining Limitations

- No actual provider smoke has been run for observed item events.
- No response safety enforcement beyond offline fixture assertions exists.
- No item event UI summary, edit/delete lifecycle, duplicate handling, ordering,
  or new-battle reset policy is implemented.
- No battle log, parser, replay, or Turn Engine event source is integrated.
- No resolved item effects, post-turn item state, exact HP/damage, RNG, or
  action order calculation exists.

## Final Phase Status

`CLOSED - PASS`

## Next Recommendation

v12.43 Item Event Phase Follow-up Inventory

Compare, without implementation, the next candidates:

- item event UI summary/readback
- event edit/delete lifecycle
- duplicate event handling
- event ordering/display policy
- session reset/new battle boundary
- future battle log/parser/replay integration prerequisites

## No Actual Gemini Call

- No actual Gemini call was executed.
- No retry was executed.
- No second provider call was executed.
- No Vertex AI call was executed.
- No provider/network call was executed.
