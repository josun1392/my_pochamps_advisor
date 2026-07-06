# v12.33 Explicit User Item Event Contract Tests

## Purpose

Lock the v12.32 explicit user item event confirmation design with contract
tests before any UI, payload mapping, parser, replay, or Turn Engine
implementation.

The contract allows a user-confirmed item event shape to be validated as an
observed candidate only. It must not become a resolved item effect, post-turn
item state, exact HP result, exact damage result, RNG result, or Speed/order
override.

## Current Phase Status

- v12.30 inventoried future item event sources.
- v12.31 locked future item event fields and source names out of the current
  payload without trusted implementation.
- v12.32 designed explicit user item event confirmation as the smallest future
  trusted observed source.
- v12.33 adds helper-level contract tests for the explicit source candidate.

No runtime item-event payload mapping is added in v12.33.

## Explicit Event Candidate Shape

Valid candidate example:

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

Required fields:

- `side`
- `item`
- `event_type`
- `status`
- `source`

Optional fields:

- `turn`
- `note`

## Valid Values

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

These event types are observed candidates only. They are not calculated
effects.

## Valid Candidate Behavior

Contract tests verify that a valid explicit user event candidate:

- is accepted by the helper-level validator
- keeps `source=explicit_user_event_confirmation`
- keeps `status=user_confirmed`
- keeps an observed `event_type`
- does not create `resolved_item_effect`
- does not create `post_turn_item_state`
- does not create exact HP
- does not create exact damage
- does not create an RNG roll
- does not create a Speed/order override

## Invalid Source Behavior

Invalid source tests cover:

- `battle_log_observed`
- `parser_observed`
- `imported_replay_observed`
- `future_turn_engine_resolved`
- `llm_guess`
- `hidden_item_guess`
- `damage_reverse_inference`
- `field_state_inference`

These sources are rejected by the explicit user event validator. They do not
promote the candidate to an observed event or resolved effect.

## Invalid Status Behavior

Invalid status tests cover:

- `inferred`
- `model_guessed`
- `calculated`
- `observed_by_context`

Only `user_confirmed` is accepted for the explicit user event source.

## Invalid Event Type Behavior

Invalid event type tests cover:

- `resolved_item_effect`
- `post_turn_item_state`
- `item_damage_modifier_applied`
- `item_speed_modifier_applied`
- `quick_claw_rng_roll`
- `focus_sash_post_hit_hp_1`
- `berry_recovered_exact_hp`

These are rejected because they imply resolved, post-turn, exact HP, exact
damage, RNG, or Speed/order behavior.

## Missing Required Fields

Tests reject candidates missing any required field:

- `side`
- `item`
- `event_type`
- `status`
- `source`

## Recursive Forbidden Field Scan

The helper result and generated prompt payload are checked for absence of:

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

## Prompt/Payload Checks

Generated prompt payload checks confirm:

- the validated explicit user event candidate is not mapped into the prompt
  payload yet
- no trusted `item_event_context` reaches the prompt
- no resolved item effect claim appears
- no post-turn state claim appears
- no exact HP claim appears
- no exact damage claim appears
- no RNG/order resolution claim appears

This preserves the v12.31 boundary that current runtime payloads reject future
item-event facts until a dedicated mapping phase is approved.

## Safety Boundary

`explicit_user_event_confirmation` may validate a future observed event
candidate. It must not directly create:

- item activation implementation
- item consumption implementation
- resolved item effect
- post-turn item state
- exact HP
- exact damage
- RNG result
- Speed/order result
- hidden item inference
- opponent set/item inference

## Test Results

- `uv run pytest tests/test_advisor_payload_contract.py -q`: `500 passed`
- `uv run pytest tests/test_advisor_battle_state_context.py -q`: `39 passed`

Full pytest should remain the final verification before commit.

## Non-Goals

- No UI implementation.
- No dialog or button implementation.
- No battle log parser.
- No replay parser.
- No Turn Engine.
- No item activation or consumption implementation.
- No resolved item effect implementation.
- No post-turn item state calculation.
- No exact HP or damage calculation.
- No actual Gemini call.

## Next Recommendation

v12.34 Explicit User Item Event Dialog UI Tests.

The helper-level source contract is now locked, so the next safe step is to
write UI tests for an Item Event Dialog before implementing the dialog.
