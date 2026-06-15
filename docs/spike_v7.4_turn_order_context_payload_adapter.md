# v7.4 Turn Order Context Payload Adapter

## Purpose

v7.4 connects the deterministic turn order context helper to the advisor payload as an optional, explicit-only adapter path.

This is still limited planning context. It is not prompt integration, not UI integration, not a Gemini smoke, and not a full Turn Engine.

## Adapter Scope

Adapter location:

- `llm.advisor_client.build_ui_advice_payload(...)`
- validation constants remain in `llm.advisor_turn_order_context`
- helper remains `llm.advisor_turn_order_context.build_deterministic_turn_order_context(...)`

Enable flag:

- `enable_turn_order_context: bool = False`
- omitted or `False` preserves the previous payload shape
- `True` only adds context when the caller explicitly supplies `turn_order_context`

Payload location:

- top-level `turn_order_context`

## Default-Off Behavior

Default/off paths must not include top-level `turn_order_context`.

These cases preserve the existing advice payload shape:

- `enable_turn_order_context` omitted
- `enable_turn_order_context=False`
- `enable_turn_order_context=True` with `turn_order_context=None`

The existing `turn_pipeline` default-off behavior is unchanged.

## Explicit-On Behavior

When `enable_turn_order_context=True` and a valid context is supplied, the payload includes top-level `turn_order_context`.

The adapter validates the supplied context before insertion:

- `kind == deterministic_turn_order_context`
- `confidence` uses allowed contract values
- `priority.priority_relation` uses allowed contract values
- `speed.speed_relation` uses allowed contract values
- `order_hint` uses allowed contract values
- `candidate_modifiers[*].resolved` must be `False`
- `unsupported` must include speed tie, RNG item activation, exact final order, item consumption, and post-turn HP boundaries
- forbidden resolved-outcome fields are rejected recursively

Forbidden resolved-outcome fields include:

- `final_order_resolved`
- `item_consumed`
- `post_turn_hp`
- `speed_tie_resolved`
- `rng_item_activated`

## TurnPipeline Coexistence

`turn_pipeline` and `turn_order_context` are independent optional top-level sections.

Tests cover:

- both disabled
- `turn_pipeline` enabled only
- `turn_order_context` enabled only
- both enabled

Neither optional context overwrites the other.

## Unsupported Boundaries

v7.4 does not implement:

- prompt integration
- UI checkbox auto-connection
- saved setting auto-enable
- full Turn Engine
- resolved turn order
- speed tie resolver
- RNG resolver
- item consumption
- post-turn HP update
- opponent set inference

Damage formula, raw rolls, Q12 multiplier, `ko_context`, and payload filtering behavior are unchanged.

## Tests

Added payload contract tests for:

- default-off omission
- explicit top-level insertion
- allowed value validation
- forbidden field rejection
- resolved candidate modifier rejection
- coexistence with `turn_pipeline`

## Next Recommendation

Recommended next:

- v7.5 Turn Order Context Prompt Integration Design

Safe alternative:

- v7.5 Turn Order Context Prompt Contract Tests

Do not go directly to Gemini smoke. Prompt safety wording should be designed or locked first.
