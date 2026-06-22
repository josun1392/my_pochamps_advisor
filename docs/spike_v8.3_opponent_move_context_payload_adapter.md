# v8.3 Opponent Move Context Payload Adapter

## Purpose

v8.3 connects a prebuilt, valid `opponent_move_context` to the advice payload as an optional top-level field.

This is an adapter-only step:

- no prompt guard
- no prompt integration
- no UI checkbox behavior change
- no UI/source extraction
- no actual Gemini call
- no full Turn Engine

## Adapter Location

`llm/advisor_client.py`

`build_ui_advice_payload(...)` now accepts:

```python
opponent_move_context: dict | None = None
enable_opponent_move_context: bool = False
```

## Default-Off Behavior

Default remains off:

- omitted `opponent_move_context`: no top-level `opponent_move_context`
- `opponent_move_context` supplied but `enable_opponent_move_context=False`: no top-level `opponent_move_context`
- `enable_opponent_move_context=True` with `None`: no top-level `opponent_move_context`

This preserves the existing payload shape unless the caller explicitly enables the context and supplies valid non-empty context.

## Explicit-On Behavior

When `enable_opponent_move_context=True` and a valid non-empty context is supplied, the adapter inserts:

```python
payload["opponent_move_context"] = context
```

The inserted context is a deep copy of the supplied context.

## No-Context Behavior

The helper's empty context is valid but not useful for payload insertion:

```python
{
    "selected_opponent_move": {"status": "unknown"},
    "known_opponent_moves": [],
    "candidate_moves": [],
    "priority_move_candidates": [],
}
```

v8.3 omits this empty context instead of emitting a placeholder top-level payload field.

Invalid contexts raise `ValueError`, matching the existing turn-order adapter's validation style.

## Validation

The adapter validates:

- `kind == "opponent_move_context"`
- `confidence` is `limited` or `unknown`
- `selected_opponent_move.status` is `unknown` or `explicit`
- explicit selected move has trusted source, `move_id`, and `name`
- known moves have trusted source and `confirmed=True`
- candidate moves have allowed candidate source, `confirmed=False`, and `selected=False`
- priority candidates remain `confirmed=False` and `selected=False`
- unsupported boundaries include hidden moveset, opponent set, selected move, EV/IV/nature, hidden item, weather/terrain/boost, RNG, and full turn resolution
- safety notes include candidate-not-confirmed wording
- forbidden hidden-inference and resolved-outcome fields are absent recursively

## Coexistence

`opponent_move_context` is independent from existing optional contexts:

- `turn_pipeline`
- `turn_order_context`
- `turn_snapshot`
- existing damage / KO / item contexts

The adapter does not overwrite `turn_pipeline` or `turn_order_context`. Tests cover no optional contexts, each context alone, and all three optional contexts together.

## Safety Boundary

v8.3 does not infer or resolve:

- hidden movesets
- opponent sets
- selected opponent move
- species/common set/meta-based moves
- EV/IV/nature
- hidden item
- weather, terrain, or boosts
- speed tie
- RNG
- Quick Claw activation
- item consumption
- post-turn HP
- full turn result

## Tests

`tests/test_advisor_payload_contract.py` covers:

- default-off omission
- explicit-on top-level insertion
- no-context omission
- invalid value rejection
- forbidden field rejection
- candidate `confirmed=False` / `selected=False` preservation
- selected move unknown and explicit preservation
- coexistence with `turn_pipeline` and `turn_order_context`

Existing helper tests remain green.

## Next Recommendation

Recommended next:

- v8.4 Opponent Move Prompt Guard

Rationale:

- once the context can be present in payload JSON, prompt safety should be locked before UI/source extraction
- the guard should prevent the LLM from treating candidate moves as confirmed selected moves

Alternative:

- v8.4 Opponent Move UI/Source Integration Design
