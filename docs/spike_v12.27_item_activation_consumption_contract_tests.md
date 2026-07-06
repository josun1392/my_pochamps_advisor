# v12.27 Item Activation / Consumption Contract Tests

## Purpose

Lock the v12.26 boundary with contract tests so `known_item` cannot be promoted
to activation, consumption, resolved item effects, or post-turn item state.

This step is test/contract focused. It does not implement item activation,
consumption, resolved item effects, post-turn item state, Turn Engine behavior,
damage changes, prompt guard wording changes, or provider calls.

No actual Gemini call was made.

## Contract Tests

Primary test location:

- `tests/test_advisor_payload_contract.py`

The tests extend the existing battle-state and UI-selected prompt contract
coverage. No new runtime feature path is added.

New coverage:

- known user-confirmed item context remains present as known current item
- known item context does not emit activation fields
- known item context does not emit consumption fields
- known item context does not emit resolved item effect fields
- known item context does not emit post-turn item state fields
- malformed battle-state contexts with item event fields are rejected
- forbidden item-profile sources do not upgrade to known items or item events
- prompt payloads for known item fixtures do not serialize item-event fields
- prompt text does not include positive overclaim phrases such as activated,
  consumed, triggered, exact damage change, or Quick Claw moving first

## Known Item Boundary

The locked fixture uses user-confirmed current items:

- self item: `leftovers`
- opponent item: `choice-scarf`

Expected behavior:

- both items serialize only as known current item context
- item source remains `user_confirmed`
- no activation/consumption/resolved/post-turn fields appear recursively
- the battle-state contract remains valid

## Forbidden Payload Fields

The v12.27 contract rejects or forbids these fields when they appear anywhere in
`battle_state_context`:

- `activation_turn`
- `berry_consumed`
- `consumed_turn`
- `damage_reduction_applied`
- `focus_sash_triggered`
- `item_activated`
- `item_consumed`
- `item_damage_modifier_applied`
- `item_speed_modifier_applied`
- `post_hit_hp_1`
- `post_turn_hp_from_item`
- `post_turn_item_state`
- `quick_claw_activated`
- `recovery_applied`
- `resolved_item_effect`
- `rng_roll`
- `speed_order_override`

The existing forbidden fields remain in force, including hidden item, inferred
item, damage reverse fields, post-turn HP, RNG resolved, speed tie resolved,
full turn result, and resolved outcome.

## Focus Sash Boundary

The Focus Sash fixture uses:

- item: `focus-sash`
- source: `user_confirmed`
- HP percent: `100`

Expected behavior:

- Focus Sash remains a known current item
- candidate/survival discussion may remain limited elsewhere
- `focus_sash_triggered` is absent
- `item_consumed` is absent
- `post_hit_hp_1` is absent
- exact survival result is absent

## Quick Claw Boundary

The Quick Claw fixture uses:

- item: `quick-claw`
- source: `user_confirmed`

Expected behavior:

- Quick Claw remains a known current item
- candidate move-order discussion may remain limited elsewhere
- `quick_claw_activated` is absent
- `rng_roll` is absent
- `speed_order_override` is absent
- resolved turn order remains absent

## Berry Boundary

The Berry fixture uses:

- item: `sitrus-berry`
- source: `user_confirmed`

Expected behavior:

- Berry remains a known current item
- trigger/recovery/reduction may be discussed only as limited candidate context
  where existing contracts allow it
- `berry_consumed` is absent
- `recovery_applied` is absent
- `damage_reduction_applied` is absent
- exact activation timing is absent

## Forbidden Source Behavior

The tests verify that these item-profile sources do not produce known item
context or item events through the UI-selected adapter:

- `damage_reverse_inference`
- `species_common_set`
- `model_guess`
- `hidden_state_guess`
- `turn_order_context`
- `opponent_move_context`
- `legality_gate_guess`
- `resist_berry_inferred`

These sources remain unknown/omitted for item context. They do not become
observed activation, observed consumption, or resolved item effects.

## Prompt Forbidden Phrase Checks

The prompt fixture checks avoid positive overclaims such as:

- `activated this turn`
- `was consumed`
- `triggered this turn`
- `recovered HP this turn`
- `changed the exact damage`
- `moves first because of Quick Claw`
- `Focus Sash activated`
- `Berry was consumed`
- `post-turn HP is`

Existing guard wording can still mention boundaries such as item consumption,
post-turn HP, RNG, or Quick Claw activation as things the model must not claim.
The v12.27 checks therefore target positive overclaim phrases and serialized
payload fields, not safety guard prohibitions.

## Contract Surface Change

The valid known-item path is unchanged.

The malformed/forbidden `battle_state_context` validation set is expanded to
reject the v12.26 item-event fields. This is a contract hardening change only:
it does not add item activation, item consumption, resolved item effects,
post-turn item state, payload filtering changes, prompt wording changes, damage
changes, or Turn Engine behavior.

## Tests

Executed:

- `uv run pytest tests/test_advisor_payload_contract.py -q`
- `uv run pytest tests/test_advisor_battle_state_context.py -q`
- `uv run pytest -q`

## Non-Goals

v12.27 does not implement:

- item activation
- item consumption
- observed item events
- resolved item effects
- post-turn item state
- post-turn HP calculation
- damage formula changes
- `damage_estimate` changes
- `ko_context` changes
- Q12 multiplier changes
- raw damage roll changes
- full Turn Engine
- resolved turn order
- RNG resolver
- speed tie resolver
- Quick Claw activation resolution
- hidden item inference
- opponent set/item inference
- prompt guard wording changes
- provider calls

## Next Recommendation

Recommended next:

- v12.28 Item Activation/Consumption Prompt Fixture

Reason:

- payload/battle-state contracts now block known-item promotion to item events
- the next useful check is an offline prompt/response fixture that verifies
  known item context is not overclaimed at the LLM-facing text boundary

Alternatives:

- v12.28 Item Event Source Inventory
- v12.28 Status/Condition Source Design
