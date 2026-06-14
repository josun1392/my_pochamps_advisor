# v7.2 Turn Order Context Payload Contract

## Purpose

v7.2 locks the Turn Order Context payload contract before implementing a helper or integrating it into the advice payload.

This is contract/test work. It does not implement a full Turn Engine, resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, or opponent set inference.

## Contract Placement

Recommended future payload key:

```text
turn_order_context
```

For v7.2, no runtime top-level key is added. The contract is locked with fixture/dict tests first so later implementation can adopt the shape without changing existing advice behavior.

## Contract Shape

Draft fixture shape:

```python
{
    "kind": "deterministic_turn_order_context",
    "confidence": "limited",
    "priority": {
        "own_move_priority": 0,
        "opponent_move_priority": "unknown",
        "priority_relation": "unknown"
    },
    "speed": {
        "basis": "base_species_stats_only",
        "own_base_speed": 100,
        "opponent_base_speed": 80,
        "speed_relation": "own_faster_by_base_speed",
        "final_speed_known": False
    },
    "order_hint": "own_likely_before_opponent_if_same_priority",
    "tie_or_unknown": False,
    "candidate_modifiers": [
        {
            "source": "Quick Claw",
            "effect": "may alter move order",
            "resolved": False
        }
    ],
    "unsupported": [
        "final EV/IV/nature speed",
        "speed tie resolution",
        "RNG item activation",
        "exact final order",
        "item consumption",
        "post-turn HP update"
    ]
}
```

## Allowed Values

`confidence`:

- `limited`
- `unknown`

`priority.priority_relation`:

- `own_higher_priority`
- `opponent_higher_priority`
- `same_priority`
- `unknown`

`speed.speed_relation`:

- `own_faster_by_base_speed`
- `opponent_faster_by_base_speed`
- `equal_base_speed_tie_candidate`
- `own_faster_by_confirmed_final_speed`
- `opponent_faster_by_confirmed_final_speed`
- `equal_confirmed_final_speed_tie_candidate`
- `unknown_due_to_missing_speed_data`
- `unknown_due_to_missing_priority_or_move`

`order_hint`:

- `own_likely_before_opponent_if_same_priority`
- `opponent_likely_before_own_if_same_priority`
- `priority_overrides_speed`
- `tie_or_unknown`
- `unknown`

The contract avoids final wording such as `will_move_first`, `guaranteed_first`, or `final_order_resolved`.

## Unsupported / Required Boundaries

The context must include unsupported boundaries when applicable. The v7.2 fixture requires:

- `speed tie resolution`
- `RNG item activation`
- `exact final order`
- `item consumption`
- `post-turn HP update`

Candidate modifiers must remain unresolved:

```python
{"resolved": False}
```

## Forbidden Fields

The contract must not include fields that imply resolved outcomes:

- `final_order_resolved`
- `item_consumed`
- `post_turn_hp`
- `speed_tie_resolved`
- `rng_item_activated`

These fields are forbidden at any nesting level in the fixture contract.

## Prompt Safety Wording

English draft:

```text
This turn order context is limited planning context, not a resolved move order.
Do not claim speed ties are resolved.
Do not claim RNG items activate.
Do not claim exact final order unless explicitly provided.
Do not infer item consumption or post-turn HP from this context.
```

Korean draft:

```text
이 턴 순서 정보는 확정 행동 순서가 아니라 제한적 판단 보조 정보입니다.
스피드 타이, RNG 아이템 발동, 정확한 최종 행동 순서, 아이템 소모, 턴 종료 후 HP를 확정하지 마세요.
```

## Tests Added

`tests/test_advisor_payload_contract.py` now includes fixture-level tests that verify:

- `kind == "deterministic_turn_order_context"`
- `confidence` uses allowed values
- `priority_relation` uses allowed values
- `speed_relation` uses allowed values
- `order_hint` uses non-final allowed values
- candidate modifiers require `resolved=False`
- unsupported boundaries include speed tie, RNG, exact final order, item consumption, and post-turn HP
- resolved-outcome fields such as `final_order_resolved`, `item_consumed`, and `post_turn_hp` are forbidden
- prompt safety copy preserves limited / not-resolved wording

## Next Recommendation

Recommended next step:

```text
v7.3 Deterministic Turn Order Context Helper
```

Scope for v7.3 should remain narrow:

- base Speed relation
- confirmed final Speed relation
- known priority relation
- unknown handling
- unresolved Quick Claw candidate modifier passthrough

Still forbidden:

- no exact final order
- no speed tie resolver
- no RNG resolver
- no item consumption
- no post-turn HP update
- no opponent set inference

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
