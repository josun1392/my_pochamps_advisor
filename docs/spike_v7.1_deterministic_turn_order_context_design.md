# v7.1 Deterministic Turn Order Context Design

## Purpose

v7.1 designs a deterministic turn order context before any full Turn Engine work.

This context is not a final move-order resolver. It is a limited planning context that summarizes currently known priority and Speed information so the LLM can reason more carefully without claiming resolved turn order.

It must not:

- determine exact final move order
- resolve speed ties
- resolve RNG item activation
- consume items
- calculate post-turn state
- update HP
- infer opponent sets or hidden move choices

## Design Goal

Deterministic Turn Order Context should answer a narrower question:

```text
Given only known priority and known Speed information, what order pressure can be safely described?
```

It should support phrases like:

- "likely before if same priority"
- "unknown because opponent move priority is unknown"
- "tie candidate by known Speed"
- "priority may override Speed if known"

It should avoid phrases like:

- "will move first"
- "speed tie is resolved"
- "Quick Claw activates"
- "final order is guaranteed"

## Inputs

Potential input sources:

- selected own Pokemon
- selected opponent Pokemon
- selected own move
- selected opponent move, only when explicitly known
- move priority, only when available from trusted move metadata
- base species Speed, as weak context only
- user-confirmed final Speed from `stat_profiles`
- existing top-level `speed_context`
- existing move-level `speed_order_context` for Quick Claw candidate pressure
- existing `turn_snapshot`, only as selected/pre-turn known state
- existing `turn_pipeline` candidate events, only as non-resolved context

Input fallback policy:

- If EV/IV/nature/final stats are unknown, mark final Speed unknown.
- If opponent selected move is unknown, mark opponent move priority unknown.
- If move priority metadata is unavailable, mark priority unknown.
- If both known priority values differ, priority relation may produce a stronger order hint.
- If priority is tied or unknown, Speed relation may be described only according to its basis.
- If only base Speed is available, the output must say base Speed is not final Speed.
- Quick Claw and other RNG items may appear only as candidate modifiers and must not resolve order.

## Output Schema Draft

The future context can be represented as an optional top-level payload section or as a nested turn-planning context after contract review. The draft shape is intentionally explicit about confidence and unsupported boundaries:

```python
{
    "kind": "deterministic_turn_order_context",
    "schema_version": "turn_order_context_v0.1",
    "confidence": "limited",
    "priority": {
        "own_move_priority": 0,
        "opponent_move_priority": "unknown",
        "priority_relation": "unknown_due_to_missing_opponent_move_priority",
        "priority_basis": "own_selected_move_only"
    },
    "speed": {
        "basis": "base_species_stats_only",
        "own_base_speed": 100,
        "opponent_base_speed": 80,
        "own_final_speed": "unknown",
        "opponent_final_speed": "unknown",
        "final_speed_known": False,
        "speed_relation": "own_faster_by_base_speed"
    },
    "order_hint": {
        "value": "own_likely_before_opponent_if_same_priority",
        "is_resolved_order": False,
        "reason": "Own base Speed is higher, but final Speed and opponent priority are not fully known."
    },
    "tie_or_unknown": {
        "is_tie_candidate": False,
        "has_unknown_priority": True,
        "has_unknown_final_speed": True
    },
    "candidate_modifiers": [
        {
            "source": "Quick Claw",
            "effect": "may alter move order",
            "resolved": False
        }
    ],
    "unsupported": [
        "final EV/IV/nature speed when not user-confirmed",
        "speed tie resolution",
        "RNG item activation",
        "exact final order",
        "post-turn state"
    ]
}
```

The schema should prefer explicit `unknown` fields over omitted data when omission could be misread as certainty.

## Classification Values

Recommended priority relation values:

- `own_priority_higher`
- `opponent_priority_higher`
- `same_priority`
- `priority_unknown`
- `unknown_due_to_missing_own_move_priority`
- `unknown_due_to_missing_opponent_move_priority`
- `unknown_due_to_missing_both_move_priorities`

Recommended speed relation values:

- `own_faster_by_confirmed_final_speed`
- `opponent_faster_by_confirmed_final_speed`
- `equal_confirmed_final_speed_tie_candidate`
- `own_faster_by_base_speed`
- `opponent_faster_by_base_speed`
- `equal_base_speed_tie_candidate`
- `unknown_due_to_missing_speed_data`
- `unknown_due_to_unconfirmed_final_speed`

Recommended order hint values:

- `own_likely_before_opponent_if_same_priority`
- `opponent_likely_before_own_if_same_priority`
- `own_before_by_known_priority`
- `opponent_before_by_known_priority`
- `tie_candidate_if_same_priority`
- `unknown_due_to_priority`
- `unknown_due_to_speed`
- `unknown_due_to_priority_and_speed`

Important wording rule:

- `own_before_by_known_priority` and `opponent_before_by_known_priority` are still context hints, not a complete final-order claim, because unsupported effects such as Trick Room, abilities, field conditions, and RNG items may remain outside scope.

## Prompt Safety Wording

English guard draft:

```text
turn_order_context, when present, is limited deterministic planning context only. It is not resolved final move order. Do not claim speed ties are resolved. Do not claim RNG items activate. Do not claim exact final order unless an explicit resolved engine result is provided. Treat priority and Speed relations as limited context, and mention unknown priority or Speed data when relevant.
```

Korean UI / documentation copy draft:

```text
턴 순서 힌트는 확정 행동 순서가 아니라 제한적 판단 보조입니다. 스피드 타이, RNG 아이템 발동, 정확한 최종 순서, 턴 종료 후 상태를 확정하지 않습니다. 우선도와 스피드 정보가 부족하면 unknown으로 표시합니다.
```

Short status/help copy:

```text
턴 순서 힌트: 확정 순서 아님
```

The LLM may say:

- "현재 알려진 우선도 기준"
- "동일 우선도라면 더 빠를 가능성"
- "상대 기술 우선도가 unknown이라 확정 불가"
- "스피드 타이 후보"
- "Quick Claw는 순서에 영향을 줄 수 있지만 발동은 확정되지 않음"

The LLM must not say:

- "반드시 먼저 행동"
- "스피드 타이 결과 확정"
- "Quick Claw가 발동함"
- "최종 행동 순서"
- "턴 종료 후 HP"

## Unsupported Boundaries

The deterministic turn order context must explicitly remain outside these behaviors:

- full Turn Engine
- resolved final move order
- speed tie result
- RNG item activation
- Quick Claw activation
- item consumption
- post-turn HP update
- fainted-state update
- opponent set inference
- hidden opponent move inference
- Trick Room, Tailwind, paralysis, boosts, ability speed effects, weather, terrain, or field-condition sequencing unless a later scoped milestone explicitly adds them

## v7.2 Options

### Option A: v7.2 Deterministic Turn Order Context Helper

Implement a small helper that produces the draft context.

Scope:

- base Speed relation
- confirmed final Speed relation when available
- known move priority relation when available
- unknown handling
- candidate modifier passthrough for Quick Claw only as unresolved

Forbidden:

- no RNG resolution
- no exact order
- no speed tie resolver
- no item consumption
- no HP update

Pros:

- Makes the design tangible quickly.
- Can be tested with small fixtures.

Cons:

- Risks turning schema design into runtime behavior before the contract is stable.

### Option B: v7.2 Turn Order Context Payload Contract

Write schema/contract tests first and defer helper implementation.

Scope:

- define allowed classification values
- define required limitations
- reject resolved-order claims
- add prompt guard copy anchors
- preserve current advice behavior when absent

Pros:

- Safest path.
- Keeps implementation from overreaching.
- Matches the prior TurnPipeline pattern of contract before runtime exposure.

Cons:

- Slower to produce a visible feature.

### Option C: v7.2 Battle State / Opponent Move Context Design

Strengthen known opponent move and battle-state inputs before turn order context.

Pros:

- Better input quality may reduce unknown cases.

Cons:

- Does not directly advance Stage 1.
- May require broader UI/input decisions.

## Recommendation

Recommended safest next step:

```text
v7.2 Turn Order Context Payload Contract
```

Faster alternative:

```text
v7.2 Deterministic Turn Order Context Helper
```

If T1/T2 prefer maximum safety, start with the contract. If they prefer implementation momentum, implement only a helper with base Speed / confirmed Speed / priority / unknown relation handling and no resolved-order semantics.

## Safety Statement

- No production code was implemented in v7.1.
- No actual Gemini call was executed.
- No Vertex AI call was executed.
- No full Turn Engine was implemented.
- No resolved turn order was implemented.
- No speed tie resolver was implemented.
- No RNG resolver was implemented.
- No item consumption was implemented.
- No HP update was implemented.
- No opponent set inference was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- `logs/token_usage.jsonl` was not committed or reset.
