# v7.3 Deterministic Turn Order Context Helper

## Purpose

v7.3 implements the minimal helper for the v7.2 `turn_order_context` contract.

The helper builds deterministic, non-resolved turn-order context from known priority and Speed inputs. It is not a full Turn Engine and does not resolve final move order.

## Helper Location

```text
llm/advisor_turn_order_context.py
```

Primary helper:

```python
build_deterministic_turn_order_context(...)
```

The helper is standalone. It is not connected to `build_ui_advice_payload(...)`, `run_ui_selected_advice(...)`, Gemini prompt generation, or the UI dev flag in v7.3.

## Inputs

The helper accepts:

- `own_move_priority: int | None`
- `opponent_move_priority: int | None`
- `own_base_speed: int | None`
- `opponent_base_speed: int | None`
- `own_confirmed_final_speed: int | None = None`
- `opponent_confirmed_final_speed: int | None = None`
- `candidate_modifiers: Sequence[Mapping[str, Any]] | None = None`

Unknown priority or Speed values are represented as `unknown` in the output instead of being guessed.

## Output

The helper returns the v7.2 contract shape:

- `kind`
- `confidence`
- `priority`
- `speed`
- `order_hint`
- `tie_or_unknown`
- `candidate_modifiers`
- `unsupported`

It never emits resolved-outcome fields such as:

- `final_order_resolved`
- `item_consumed`
- `post_turn_hp`
- `speed_tie_resolved`
- `rng_item_activated`

## Relation Logic

Priority:

- both priorities known and own > opponent -> `own_higher_priority`
- both priorities known and own < opponent -> `opponent_higher_priority`
- both priorities known and equal -> `same_priority`
- otherwise -> `unknown`

Speed:

- if both confirmed final Speed values are known, they take precedence over base Speed
- if confirmed final Speed is unavailable but both base Speed values are known, use base Speed relation
- if neither basis is complete, use `unknown_due_to_missing_speed_data`

Order hint:

- different known priority -> `priority_overrides_speed`
- unknown priority -> `unknown`
- same priority + own faster -> `own_likely_before_opponent_if_same_priority`
- same priority + opponent faster -> `opponent_likely_before_own_if_same_priority`
- tie candidate or unknown Speed -> `tie_or_unknown`

The helper does not emit "will move first" or any exact final order field.

## Candidate Modifiers

Candidate modifiers are normalized to:

```python
{
    "source": "...",
    "effect": "...",
    "resolved": False,
}
```

If a caller supplies `resolved=True` or `activated=True`, the helper does not pass those resolved fields through. Quick Claw and similar order modifiers remain candidate-only.

## Unsupported Boundaries

The helper always includes:

- `final EV/IV/nature speed`
- `speed tie resolution`
- `RNG item activation`
- `exact final order`
- `item consumption`
- `post-turn HP update`

## Tests

`tests/test_advisor_turn_order_context.py` covers:

- own faster by base Speed
- opponent faster by base Speed
- equal base Speed as tie candidate
- confirmed final Speed taking precedence over base Speed
- known priority relation
- unknown priority behavior
- missing Speed behavior
- Quick Claw candidate modifier normalization to `resolved=False`
- forbidden fields absence
- required unsupported boundaries

Existing v7.2 contract tests in `tests/test_advisor_payload_contract.py` remain unchanged and continue to pass.

## Next Recommendation

Recommended next step:

```text
v7.4 Turn Order Context Payload Adapter
```

Scope should remain:

- optional / explicit-only
- default-off
- no prompt integration unless separately designed or guarded
- no exact final order
- no speed tie resolver
- no RNG resolver
- no item consumption
- no post-turn HP update

Safe alternative:

```text
v7.4 Prompt Integration Design
```

## Safety Statement

- No actual Gemini call was executed.
- No Vertex AI call was executed.
- No full Turn Engine was implemented.
- No resolved turn order was implemented.
- No speed tie resolver was implemented.
- No RNG resolver was implemented.
- No item consumption was implemented.
- No post-turn HP update was implemented.
- No opponent set inference was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- `logs/token_usage.jsonl` was not committed or reset.
