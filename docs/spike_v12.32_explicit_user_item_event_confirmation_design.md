# v12.32 Explicit User Item Event Confirmation Design

## Purpose

Design the smallest trusted observed item-event source: explicit user
confirmation that an item event just happened.

This design answers how a user could later tell the app "Focus Sash just
activated" or "Berry was just consumed" without confusing that event with
current known item context or resolved engine output.

This is design-only. No production code, tests, UI, dialog, button, payload
mapping, parser, replay importer, Turn Engine behavior, prompt guard wording,
damage calculation, dependency file, or provider behavior is changed.

No actual Gemini call was made.

## Current Phase Status

Current supported behavior:

- `unknown_item`
- `known_item`
- `candidate_activation` wording boundary only
- known user-confirmed item context in prompt payloads
- malformed/future item event fields rejected by contract

Still future-only:

- `observed_activation`
- `observed_consumption`
- `resolved_item_effect`
- `post_turn_item_state`
- battle log parser
- replay parser
- Turn Engine
- item event payload mapping

v12.31 currently rejects future item event fields and future source names until
a trusted source implementation exists.

## Known Item vs Explicit User Event Confirmation

Known item:

- the user confirms the current item
- example: the opponent has Focus Sash
- meaning: `known_item` only
- allowed as current context
- does not imply activation, consumption, resolved effect, or post-turn state

Explicit user item event confirmation:

- the user confirms that an item event just happened
- example: Focus Sash just activated
- meaning: future `observed_activation` or `observed_consumption` candidate
- source candidate: `explicit_user_event_confirmation`
- requires a separate contract and implementation before entering runtime
  payloads

Resolved item effect:

- a calculation engine or approved resolver applies the effect to battle state
- example: Focus Sash caused survival at exactly 1 HP
- meaning: future `future_turn_engine_resolved` output
- not implemented or allowed in this design

The boundary is:

```text
known_item
!= explicit_user_event_confirmation
!= resolved_item_effect
```

## Observed vs Resolved Distinction

Observed event:

- user confirms that an event text or visible event occurred
- can support future observed item event candidates
- does not calculate a final battle result
- does not prove exact post-turn HP, exact damage, RNG, or final order

Resolved effect:

- an approved engine applies mechanics and records assumptions
- may compute exact effect outcomes only when the resolver supports them
- future-only

Explicit user event confirmation can create observed candidates in a future
phase. It must not directly create resolved item effects.

## Event Type Candidates

Allowed future observed event candidates:

- `item_activation_observed`
- `item_consumption_observed`
- `item_recovery_observed`
- `item_prevention_observed`
- `item_reveal_observed`

Meaning:

- observed event means "the user saw or confirmed this event"
- observed event is not a calculated result
- observed event alone does not fully resolve post-turn state

## Item-Specific Examples

### Focus Sash

Known:

- user confirms opponent has Focus Sash
- state: `known_item`

Explicit event confirmation:

- user confirms Focus Sash activated
- future state candidate: `observed_activation`
- user confirms Focus Sash was consumed
- future state candidate: `observed_consumption`

Not allowed by this source alone:

- exact post-hit HP calculation
- exact damage calculation
- full post-turn state
- survival result beyond the observed event text

### Quick Claw

Known:

- user confirms opponent has Quick Claw
- state: `known_item`

Explicit event confirmation:

- user confirms Quick Claw activated
- future state candidate: `observed_activation`

Not allowed by this source alone:

- RNG roll value
- complete Speed/order resolver result
- future turn order prediction
- speed tie resolution

### Berry

Known:

- user confirms opponent has Berry
- state: `known_item`

Explicit event confirmation:

- user confirms Berry was consumed
- future state candidate: `observed_consumption`
- user confirms recovery text appeared
- future state candidate: `item_recovery_observed`

Not allowed by this source alone:

- exact recovered HP unless the user explicitly provides updated HP or an
  approved engine computes it
- exact damage reduction calculation unless engine-resolved
- post-turn item state beyond the observed event

### Leftovers

Known:

- user confirms Leftovers
- state: `known_item`

Explicit event confirmation:

- user confirms Leftovers recovery occurred
- future state candidate: `item_recovery_observed`

Not allowed by this source alone:

- exact end-turn HP unless user explicitly provides updated HP or an approved
  engine computes it
- complete post-turn state

### Choice Scarf

Known:

- user confirms Choice Scarf
- state: `known_item`

Explicit event confirmation:

- user confirms item was revealed
- future state candidate: `item_reveal_observed`

Not allowed by this source alone:

- exact Speed/order resolution
- Choice lock state unless observed from repeated move/context or future engine
- future turn order prediction

## UI / UX Options

### Option A: Item Event Dialog

Candidate flow:

- add an `Item event` button to `LLMAdvicePanel`
- dialog captures side, item, event type, optional turn, and optional note
- dialog supports Apply, Cancel, and Reset
- `MainWindow` stores session-local event confirmations

Pros:

- clear event-specific entry point
- similar to the existing `FieldProfileDialog` ownership pattern
- easier to separate source/status/value metadata
- easier to validate required fields before payload mapping
- scales naturally into v12.33 contract tests and v12.34 implementation

Cons:

- requires UI work
- user must enter event data directly
- more clicks than inline chips

### Option B: Inline Confirmation Chips

Candidate flow:

- show quick chips near known item UI such as `activated`, `consumed`, or
  `recovered`
- clicking a chip records an observed event

Pros:

- fast during a turn
- easier for common events

Cons:

- event metadata can be thin
- accidental clicks are more likely
- side, turn, item, note, and event provenance may be unclear
- harder to enforce explicit confirmation semantics

## Recommended UI Option

Recommended:

- Option A: Item Event Dialog

Reason:

- it follows the existing FieldProfileDialog-style pattern
- it keeps event metadata explicit
- it separates current item confirmation from event confirmation
- it gives contract tests a stable shape before runtime implementation

## Session-Local State Candidate

Candidate owner:

```text
MainWindow._item_event_confirmations: list[dict]
```

Candidate event shape:

```json
{
  "side": "self",
  "item": "focus-sash",
  "event_type": "item_activation_observed",
  "status": "user_confirmed",
  "source": "explicit_user_event_confirmation",
  "turn": null,
  "note": null
}
```

Notes:

- not implemented in v12.32
- session-local only should be considered first
- persistence should remain out of scope until the event contract is stable
- Apply stores the list, Cancel preserves previous state, Reset returns to an
  empty list

## Future Payload Shape Candidate

Future-only candidate:

```yaml
item_event_context:
  observed_events:
    - side: opponent
      item: focus-sash
      event_type: item_activation_observed
      status: user_confirmed
      source: explicit_user_event_confirmation
      turn: 5
      confidence: observed
      note: null
```

Warnings:

- v12.32 does not connect this to payloads
- v12.31 contract currently rejects this field without trusted implementation
- mapping must wait for separate contract tests
- observed event mapping must not create resolved effects or post-turn state

## Validation Rules

Required fields:

- `side`
- `item`
- `event_type`
- `status`
- `source`

Allowed source:

- `explicit_user_event_confirmation`

Allowed status:

- `user_confirmed`

Allowed event types:

- `item_activation_observed`
- `item_consumption_observed`
- `item_recovery_observed`
- `item_prevention_observed`
- `item_reveal_observed`

Optional fields:

- `turn`
- `note`

Invalid cases:

- `source != explicit_user_event_confirmation`
- `status != user_confirmed`
- unknown `event_type`
- missing side, item, event_type, status, or source
- event claims resolved effect
- event claims post-turn state
- event claims exact damage
- event claims RNG roll
- event claims resolved Speed/order
- event infers hidden item

## Safety Boundary

Explicit user event confirmation may create future observed item event
candidates.

It must not directly create:

- `resolved_item_effect`
- `post_turn_item_state`
- exact damage
- exact HP
- resolved Speed/order
- RNG result
- hidden item inference
- opponent set/item inference
- full turn outcome

It must also not replace current known item semantics. A known item remains
current context only unless a separate explicit event is confirmed.

## Future Implementation Path

Recommended path:

```text
v12.33 Explicit User Item Event Contract Tests
v12.34 Explicit User Item Event Dialog Implementation
v12.35 Item Event Payload Mapping Tests
v12.36 Item Event Payload Mapping Implementation
v12.37 Item Event Prompt Fixture
v12.38 Controlled Item Event Gemini Smoke Design
v12.39 Controlled Item Event Gemini Smoke
v12.40 Item Event Source Phase Closure
```

## Test Recommendations

Recommended next tests:

- valid explicit user event confirmation shape is accepted by fixture-level
  contract only
- invalid source/status/event type is rejected
- missing required fields are rejected
- observed event candidates do not create `resolved_item_effect`
- observed event candidates do not create `post_turn_item_state`
- observed event candidates do not calculate exact HP, exact damage, RNG, or
  resolved order
- known item context remains separate from item event confirmation
- future payload mapping remains blocked until explicit mapping is implemented

## Non-Goals

v12.32 does not implement:

- UI
- dialog/button
- item event payload
- observed activation
- observed consumption
- resolved item effect
- post-turn item state
- item activation
- item consumption
- battle log parser
- replay parser
- Turn Engine
- damage formula changes
- `damage_estimate` changes
- `ko_context` changes
- Q12 multiplier changes
- raw damage roll changes
- RNG resolver
- speed tie resolver
- Quick Claw activation resolution
- hidden item inference
- opponent set/item inference
- prompt guard wording changes
- provider calls

## Next Recommendation

Recommended next:

- v12.33 Explicit User Item Event Contract Tests

Reason:

- the explicit user event source design is now documented
- contract tests should lock observed-only behavior before any dialog or
  payload implementation

Alternatives:

- v12.33 Explicit User Item Event Dialog UI Tests
- v12.33 Item Event Source Phase Closure
