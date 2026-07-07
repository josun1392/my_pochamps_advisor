# v12.38 Item Event Payload Mapping Design

## Purpose

Design when and how `MainWindow._item_event_confirmations` should later enter
`battle_input` and LLM payloads as observed item-event context.

This phase is design-only. It does not implement `item_event_context`, prompt
serialization, response fixtures, parser/replay handling, Turn Engine behavior,
or provider calls.

## Current Implementation Status

Implemented:

- Standalone `ItemEventDialog`.
- `LLMAdvicePanel` `Item event` button.
- `MainWindow._item_event_confirmations` session-local state.
- Apply/Cancel/Reset behavior.
- Invalid item event storage rejection.
- Button click does not emit `advice_requested`.
- Button click does not call provider/Gemini paths.

Not implemented:

- `battle_input["item_event_confirmations"]` mapping.
- LLM payload `item_event_context` mapping.
- Prompt observed item event serialization.
- Response safety prompt fixture.
- Actual Gemini smoke.

## Future Mapping Path

Candidate path:

```text
MainWindow._item_event_confirmations
-> battle_input["item_event_confirmations"]  # future
-> include_user_confirmed_item_events gate   # future helper/client flag
-> item_event_context.observed_events
-> prompt serialization under limited context gate
```

This path is future-only in v12.38. Actual mapping should wait until v12.39
contract tests and a later approved implementation phase.

## Limited Context Gate Design

Use the existing limited context checkbox as the hard gate.

Checkbox off:

- `item_event_confirmations` may exist as UI session state or future
  `battle_input` input.
- LLM payload must omit `item_event_context`.
- Prompt must omit observed item event phrases.

Checkbox on:

- Valid `item_event_confirmations` may be normalized into
  `item_event_context.observed_events`.
- Invalid item events must be omitted or rejected.
- Resolved, post-turn, exact HP/damage, RNG, and Speed/order fields must stay
  absent.

Do not add a separate checkbox in this design. Field state, current known item
context, and observed user-confirmed item events are all user-confirmed limited
context, so they should share the existing gate.

## Future Payload Shape Candidate

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
      note: User saw Focus Sash activation text.
```

Required rules:

- Only `observed_events` is allowed initially.
- `resolved_effects` remains forbidden.
- `post_turn_item_state` remains forbidden.
- `exact_hp`, `exact_damage`, `rng_roll`, and `speed_order_override` remain
  forbidden.
- Source is limited to `explicit_user_event_confirmation`.
- Status is limited to `user_confirmed`.
- `event_type` is limited to v12.33 allowed observed event types.

## Allowed Observed Event Types

- `item_activation_observed`
- `item_consumption_observed`
- `item_recovery_observed`
- `item_prevention_observed`
- `item_reveal_observed`

## Forbidden Fields

The mapper and prompt payload must not emit:

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

## Observed vs Resolved Distinction

Observed item event:

- Means the user confirmed that an item event happened.
- Example: the user saw Focus Sash activation text.
- Means only that the event was observed.

Resolved item effect:

- Means a calculation engine applied the item event to an actual battle result.
- Example: Focus Sash caused survival at exactly 1 HP.
- Requires a future Turn Engine or resolver.
- Is not allowed by this mapping design.

## Known Item vs Observed Event Distinction

Known item:

- Means the current item is known.
- Example: the opponent is holding Focus Sash.
- Does not mean activation or consumption.

Observed event:

- Means the user confirmed that an item event occurred.
- Example: Focus Sash just activated.
- Does not mean post-turn item state or effect calculation.

## Item-Specific Examples

### Focus Sash

Input:

- `side=opponent`
- `item=focus-sash`
- `event_type=item_activation_observed`
- `source=explicit_user_event_confirmation`
- `status=user_confirmed`

Payload candidate:

- `item_event_context.observed_events[0]`

Allowed wording:

- User confirmed a Focus Sash activation event was observed.

Forbidden wording:

- Focus Sash caused exact HP 1.
- Focus Sash consumed and post-turn item state is empty.
- Damage was resolved by Focus Sash.

### Quick Claw

Allowed wording:

- User confirmed a Quick Claw activation event was observed.

Forbidden wording:

- Quick Claw RNG roll succeeded.
- Quick Claw changes resolved speed order.
- This guarantees future turn order.

### Berry

Allowed wording:

- User confirmed a Berry consumption/recovery event was observed.

Forbidden wording:

- Berry recovered exact HP.
- Berry changed exact damage.
- Post-turn HP is X.

### Leftovers

Allowed wording:

- User confirmed a Leftovers recovery event was observed.

Forbidden wording:

- Exact HP recovered was calculated.
- Post-turn HP is X.

### Choice Scarf

Allowed wording:

- User confirmed Choice Scarf was revealed.

Forbidden wording:

- Resolved speed order is guaranteed.
- Choice lock state is resolved unless separately observed or engine-resolved.

## Prompt Serialization Boundary

Prompt may mention:

- User-confirmed observed item event.
- Source `explicit_user_event_confirmation`.
- Confidence `observed`.
- No exact calculations.

Prompt must not mention:

- Resolved item effect.
- Post-turn item state.
- Exact HP.
- Exact damage.
- RNG roll.
- Resolved turn order.
- Hidden item inference.

## Response Safety Boundary

LLM may say:

- "The user confirmed an item event was observed."
- "This may affect strategic interpretation."
- "This does not by itself resolve exact HP/damage/order."

LLM must not say:

- "Focus Sash left the target at exactly 1 HP."
- "Quick Claw RNG succeeded and order is resolved."
- "Berry restored exactly X HP."
- "The item is consumed in the post-turn state."

## Validation Requirements

Required:

- `side`
- `item`
- `event_type`
- `status`
- `source`

Allowed:

- `source=explicit_user_event_confirmation`
- `status=user_confirmed`
- `event_type` in allowed observed event types

Optional:

- `turn`
- `note`

Normalization:

- Blank `turn` and `note` stay `None`.
- Mapper may add `confidence=observed`.
- Invalid event is omitted or rejected and never promoted.

Forbidden:

- Resolved fields.
- Post-turn fields.
- Exact HP/damage fields.
- RNG/order fields.

## Future Test Plan

v12.39 Item Event Payload Mapping Tests should lock:

- Checkbox off omits `item_event_context`.
- Checkbox on includes valid `observed_events`.
- Invalid events are omitted or rejected.
- `observed_events` carry source, status, and confidence.
- Resolved/post-turn/exact fields remain absent.
- Prompt includes safe observed wording only.
- Known item/current item behavior remains unchanged.
- Field state behavior remains unchanged.
- No actual Gemini call.

## Next Recommendation

Recommended next:

- v12.39 Item Event Payload Mapping Tests

Reason:

- Payload mapping affects LLM input directly. The limited context gate,
  source/status validation, and observed/resolved boundary should be locked by
  contract tests before implementation.

## No Actual Gemini Call

- No actual Gemini call was executed.
- No retry was executed.
- No second provider call was executed.
- No Vertex AI call was executed.
- No provider/network call was executed.
