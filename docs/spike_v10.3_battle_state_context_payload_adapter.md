# v10.3 Battle State Context Payload Adapter

## Purpose

Connect a caller-provided, already-normalized `battle_state_context` to the UI advice payload as an optional top-level context.

This milestone adds only the payload adapter:

- no prompt guard
- no UI/source integration
- no automatic battle-state generation
- no actual Gemini or Vertex AI call
- no hidden-state inference
- no full Turn Engine

## Adapter Location

`llm/advisor_client.py`

`build_ui_advice_payload(...)` now accepts:

```python
battle_state_context: dict | None = None
enable_battle_state_context: bool = False
```

The adapter does not call `build_battle_state_context(...)` itself. Callers must pass an explicit context.

## Default-Off Behavior

The payload omits `battle_state_context` when:

- `enable_battle_state_context=False`
- `battle_state_context=None`
- `battle_state_context={}`
- the helper output contains no accepted visible or explicit source data

Default payload shape remains unchanged.

## Explicit-On Behavior

The payload includes top-level `battle_state_context` only when:

- `enable_battle_state_context=True`
- a valid non-empty `battle_state_context` is provided

The inserted context is a deep copy of the caller-provided helper output and preserves the helper shape.

## Valid / Invalid Handling

Valid contexts must include:

- `kind == "battle_state_context"`
- `confidence` in `unknown` / `limited`
- `self_active`
- `opponent_active`
- `field`
- `known_conditions`
- `unsupported`
- `safety_notes`

Invalid contexts are rejected with `ValueError` following existing optional-context adapter style.

Rejected examples:

- wrong `kind`
- unsupported confidence such as `partial` or `explicit`
- missing required top-level shape
- forbidden source
- forbidden hidden or resolved fields

## Coexistence

The adapter coexists with:

- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`
- `battle_state_context`

The adapter does not overwrite existing optional contexts.

## Forbidden Fields

The adapter rejects forbidden fields recursively, including:

- `EVs`
- `IVs`
- `nature`
- `hidden_item`
- inferred, predicted, or likely item/boost/status/weather/terrain
- `damage_reverse_inferred`
- `post_turn_hp`
- `item_consumed`
- `rng_resolved`
- `speed_tie_resolved`
- `quick_claw_activated`
- `full_turn_result`
- `resolved_outcome`

## Relationship Boundaries

The adapter does not generate `battle_state_context` from:

- `damage_estimate`
- `ko_context`
- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`

These contexts remain independent and do not create hidden battle state or resolved outcomes.

## Tests

Implemented in `tests/test_advisor_payload_contract.py`:

- default payload omits `battle_state_context`
- disabled flag omits context even when provided
- explicit-on inserts valid context
- helper output shape is preserved
- `None`, `{}`, and empty helper contexts are omitted
- wrong kind and unsupported confidence are rejected
- forbidden sources are rejected
- forbidden fields are rejected recursively
- coexistence with `turn_pipeline`, `turn_order_context`, and `opponent_move_context`
- adapter does not call provider
- adapter does not infer hidden item, EV/IV/nature, or state from damage/KO context

## Next Recommendation

Recommended:

- v10.4 Battle State Context Prompt Guard

Reason:

- The payload can now carry `battle_state_context`, so the next safe step is guard wording that keeps unknown fields unknown and blocks hidden-state or full-simulation inference.

Alternatives:

- v10.4 Battle State Context Payload Adapter Offline Fixture
- v10.4 Battle State Source Inventory

Do not run an actual Gemini call yet.
