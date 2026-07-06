# v12.31 Item Event Source Contract Tests

## Purpose

Lock the v12.30 item event source inventory with contract tests so future item
event fields cannot enter the current payload as trusted facts without a
trusted observed or resolved source implementation.

This step is contract-test focused. It does not implement item activation,
item consumption, resolved item effects, post-turn item state, battle log
parsing, replay parsing, Turn Engine behavior, damage changes, prompt guard
wording changes, or provider calls.

No actual Gemini call was made.

## Contract Tests

Primary test location:

- `tests/test_advisor_payload_contract.py`

New coverage:

- current known item source path remains known-item context only
- future item event fields are rejected before they can reach prompt payloads
- forbidden sources cannot create item events
- future trusted source names are still future-only and are rejected by current validation
- generated prompt payloads omit future item event fields
- generated prompt text avoids positive observed/resolved item-event claims

## Current Known Source Boundary

The current runtime representation remains:

```json
{"known": true, "source": "user_confirmed", "value": "<item-id>"}
```

This corresponds to the v12.30 conceptual source boundary:

```text
user_confirmed_current_item -> known_item only
```

The new contract fixture uses:

- self item: `focus-sash`
- opponent item: `quick-claw`
- source path: user-confirmed current item metadata

Expected result:

- known item context is present
- `observed_activation` is absent
- `observed_consumption` is absent
- `resolved_item_effect` is absent
- `post_turn_item_state` is absent
- no item event context reaches the prompt payload

## Future Event Field Behavior

Future-only fields are rejected by the current `battle_state_context` contract:

- `item_event_context`
- `observed_events`
- `resolved_effects`
- `post_turn_item_state`
- `observed_activation`
- `observed_consumption`
- `resolved_item_effect`
- `item_event_type`
- `event_source`
- `event_confidence`
- `event_turn`
- `event_provenance`

These fields remain schema candidates only. They are not runtime payload fields
until a future source contract and implementation are approved.

## Forbidden Source Behavior

The test coverage confirms forbidden sources do not upgrade items into known
items or item events:

- `species_common_set`
- `damage_reverse_inference`
- `hp_percent_inference`
- `opponent_move_context`
- `turn_order_context`
- `field_state_inference`
- `legality_gate`
- `legality_gate_guess`
- `resist_berry_context`
- `resist_berry_inferred`
- `llm_guess`
- `model_guess`
- `hidden_item_guess`
- `hidden_state_guess`

Expected result:

- source is not trusted
- item remains unknown/omitted where appropriate
- no observed activation is created
- no observed consumption is created
- no resolved item effect is created
- no post-turn item state is created

## Future Trusted Source Name Behavior

The v12.30 future trusted source names remain future-only:

- `explicit_user_event_confirmation`
- `battle_log_observed`
- `parser_observed`
- `imported_replay_observed`
- `future_turn_engine_resolved`

Current behavior:

- source name alone is not enough
- these names are rejected by current validation
- no observed activation, observed consumption, resolved item effect, or post-turn item state is generated

This preserves the future-only boundary until a dedicated source schema,
validation contract, and implementation are approved.

## Recursive Forbidden Field Scan

The existing recursive item activation boundary field scan now also covers
future item event source fields:

- `item_event_context`
- `observed_events`
- `resolved_effects`
- `post_turn_item_state`
- `observed_activation`
- `observed_consumption`
- `resolved_item_effect`
- `item_activated`
- `item_consumed`
- `quick_claw_activated`
- `focus_sash_triggered`
- `berry_consumed`
- `post_turn_hp_from_item`
- `item_damage_modifier_applied`
- `item_speed_modifier_applied`
- `rng_roll`
- `speed_order_override`

## Prompt Forbidden Phrase Checks

The prompt-level fixture checks that generated prompt text does not include
positive observed/resolved event claims such as:

- observed activation
- observed consumption
- resolved item effect
- post-turn item state
- item was consumed
- item activated
- Focus Sash activated
- Quick Claw activated
- Berry was consumed
- resolved by Turn Engine

Existing safety guard wording may still describe boundaries and unsupported
claims. The check targets positive item-event claims in generated prompt
content.

## Contract Surface Change

The valid known-item path is unchanged.

The malformed/forbidden `battle_state_context` validation set is expanded to
reject v12.30 future item-event source fields and future source names. This is
contract hardening only. It does not add:

- item activation
- item consumption
- resolved item effects
- post-turn item state
- battle log parser
- replay parser
- Turn Engine
- damage changes
- prompt guard wording changes

## Tests

Executed:

- `uv run pytest tests/test_advisor_payload_contract.py -q`
- `uv run pytest tests/test_advisor_battle_state_context.py -q`
- `uv run pytest -q`

## Non-Goals

v12.31 does not implement:

- battle log parser
- replay parser
- Turn Engine
- item activation
- item consumption
- resolved item effect
- post-turn item state
- post-turn HP from item
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

- v12.32 Explicit User Item Event Confirmation Design

Reason:

- the source inventory and contract boundary are now locked
- the smallest future trusted observed source is explicit user confirmation that an item just activated or was consumed

Alternatives:

- v12.32 Battle Log Parser Spike
- v12.32 Item Event Source Phase Closure
