# v12.29 Item Activation / Consumption Phase Closure

## Purpose

Close the item activation/consumption boundary phase after design, contract
tests, and offline prompt fixture coverage.

This closure records the final boundary for known user-confirmed items:
`known_item` remains current context only and must not be promoted to item
activation, item consumption, resolved item effects, post-turn item state, exact
damage, post-turn HP, or resolved Speed/order effects.

No actual Gemini call was made for this closure.

## Phase Scope

Closed phase:

```text
v12.26 Item Activation/Consumption Boundary Design
-> v12.27 Item Activation/Consumption Contract Tests
-> v12.28 Item Activation/Consumption Prompt Fixture
-> v12.29 Item Activation/Consumption Phase Closure
```

Scope:

- define known item versus activation/consumption boundary
- lock payload and battle-state contract behavior
- lock prompt payload and mocked response safety behavior offline
- document allowed, future, and forbidden item sources
- document remaining future-only item event work

## Completed Milestones

v12.26 Item Activation/Consumption Boundary Design:

- defined known item as user-confirmed/current context only
- documented the item state model
- documented allowed and forbidden sources
- documented Leftovers, Choice Scarf, Focus Sash, Berry, and Quick Claw
  boundaries
- documented current payload, prompt, and response boundaries
- recommended contract tests before any implementation

v12.27 Item Activation/Consumption Contract Tests:

- added contract tests for known item versus item-event separation
- kept valid known item behavior unchanged
- expanded malformed `battle_state_context` forbidden-field validation for
  item-event and resolved-effect fields
- verified Focus Sash, Quick Claw, Berry, Leftovers, and Choice Scarf stay
  current/candidate context only
- verified forbidden inference sources do not become known items or item events

v12.28 Item Activation/Consumption Prompt Fixture:

- added an offline mocked prompt fixture using `_build_ui_selected_prompt(...)`
- covered Leftovers, Choice Scarf, Focus Sash, Quick Claw, and Sitrus/Yache
  Berry
- verified known items serialize only as `known=true`,
  `source=user_confirmed`, and current item `value`
- verified prompt payloads omit activation, consumption, resolved-effect, and
  post-turn item fields
- verified safe mocked response wording stays strategic/current-context only
- verified coexistence with `battle_state_context.field`, `turn_pipeline`,
  `turn_order_context`, and `opponent_move_context`

## Known Item Boundary

Final boundary:

- known item means user-confirmed/current context only
- known item does not imply item activation
- known item does not imply item consumption
- known item does not imply resolved item effect
- known item does not imply post-turn item state
- known item does not imply post-turn HP
- known item does not imply exact damage modifier applied
- known item does not imply Speed/order override applied
- known item does not imply hidden item inference
- known item does not imply opponent set/item inference

Known items may support strategic context. They do not create observed events or
resolved outcomes.

## Item State Model

State model:

- `unknown_item`
- `known_item`
- `candidate_activation`
- `observed_activation`
- `observed_consumption`
- `resolved_item_effect`

Implemented or verified in this phase:

- `unknown_item`
- `known_item`
- `candidate_activation` wording boundary

Future-only:

- `observed_activation`
- `observed_consumption`
- `resolved_item_effect`
- post-turn item state

## Allowed / Future / Forbidden Sources

Allowed current source:

- `user_confirmed_current_item` -> `known_item` only

Future allowed source candidates:

- `explicit_user_confirmation`
- `battle_log_observed`
- `parser_observed`
- `imported_replay_observed`
- `future_turn_engine_resolved`

Forbidden sources:

- species/common/meta inference
- damage reverse inference
- HP percentage inference
- move/context inference
- opponent_move_context inference
- turn_order_context inference
- field_state inference
- legality gate inference
- resist berry context inference
- LLM/model guess
- hidden item guess

These forbidden sources cannot create known items, observed activation,
observed consumption, or resolved item effects.

## Payload Safety Result

Payload/battle-state safety result: PASS.

Locked behavior:

- known item metadata is allowed
- `user_confirmed` source is allowed for known current item
- activation/consumption/resolved/post-turn fields are recursively forbidden
- malformed `battle_state_context` forbidden-field validation set is expanded
- tests verify no `item_activated`, `item_consumed`,
  `resolved_item_effect`, `post_turn_item_state`,
  `post_turn_hp_from_item`, `quick_claw_activated`,
  `focus_sash_triggered`, `berry_consumed`, `recovery_applied`,
  `damage_reduction_applied`, `rng_roll`, `speed_order_override`, or
  `post_hit_hp_1`
- tests verify Focus Sash, Quick Claw, and Berry stay candidate/current context
  only

The valid known-item path remains unchanged.

## Prompt / Response Safety Result

Prompt/response safety result: PASS.

Locked behavior:

- prompt fixture verifies known item serialized as `known=true`,
  `source=user_confirmed`, and current item `value` only
- prompt fixture verifies no activation/consumption/resolved/post-turn item
  fields are serialized
- prompt fixture targets positive overclaim phrases while allowing existing
  safety guard wording that states boundaries
- mocked safe response passes strategic/current-context wording

Forbidden response phrases checked:

- Focus Sash activated/consumed
- Quick Claw activated
- Berry consumed
- post-turn HP
- exact damage changed by item

## Coexistence Result

Coexistence result: PASS.

Verified coexistence with:

- `battle_state_context.field`
- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`

Boundary:

- field state is not an item activation source
- turn_order_context is not a Quick Claw activation source
- opponent_move_context is not an item consumption source
- damage/KO context is not a Focus Sash trigger source

## Remaining Limitations

Still not implemented:

- item activation
- item consumption
- resolved item effect
- post-turn item state
- post-turn HP from item
- Quick Claw RNG/resolution
- Focus Sash trigger resolution
- Berry consumption/recovery/reduction resolution
- Choice lock state resolution unless observed/user-confirmed
- item event source inventory
- battle log/parser/imported replay item event handling
- full Turn Engine integration

## Final Phase Status

Final status:

```text
CLOSED - PASS
```

The item activation/consumption boundary is closed for the current known-item
path. Future observed activation, observed consumption, resolved item effects,
and post-turn item state require separate source inventory, design, contract
tests, prompt tests, and explicit approval.

## Next Recommendation

Recommended next:

- v12.30 Item Event Source Inventory

Reason:

- known item boundary is closed
- the next safe step is to inventory sources that could eventually support
  observed activation or observed consumption

Alternatives:

- v12.30 Status/Condition Source Design
- v12.30 Damage Calculator Integration Design

## No Actual Gemini Call

No actual Gemini call, retry, second provider call, Vertex AI call, or
network/provider call was made for v12.29.
