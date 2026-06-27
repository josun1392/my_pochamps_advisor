# v9.3 Opponent Move UI Copy / Tooltip Polish

## Purpose

Clarify the existing limited-context checkbox copy after the checkbox became the single UI switch for `turn_pipeline`, `turn_order_context`, and `opponent_move_context`.

This milestone changes copy only. It does not change checkbox behavior, default state, payload generation, prompt generation, provider behavior, damage behavior, or inference boundaries.

## Final Copy

Label:

```text
제한 컨텍스트 포함
```

Tooltip:

```text
턴 이벤트 후보, 선후공 판단 보조, UI에 보이는 상대 기술 후보를 LLM 입력에 포함합니다.
이 정보는 확정 턴 결과가 아니며, 상대 기술 후보는 확정된 기술이 아닙니다. 숨겨진 기술배치, RNG 결과, 아이템 소모, 턴 후 HP를 추론하지 않습니다.
```

Status:

```text
제한 컨텍스트 켜짐: 후보 이벤트, 선후공 보조 정보, 상대 기술 후보 전달 | 확정 결과 아님
```

## What The Checkbox Includes

- Limited turn event candidates from `turn_pipeline`.
- Turn-order helper context from `turn_order_context`.
- UI-visible opponent move candidates from `opponent_move_context`.

## What The Checkbox Does Not Mean

- It does not mean final turn resolution.
- It does not mean confirmed final move order.
- It does not mean opponent move candidates are confirmed moves.
- It does not mean opponent move candidates are selected moves.
- It does not infer hidden movesets, opponent sets, selected opponent moves, RNG results, item consumption, or post-turn HP.
- It does not resolve Quick Claw activation.

## Tests

- `tests/test_ui_turn_pipeline_flag_flow.py` locks the UI copy anchors and forbidden phrases.
- `tests/test_advisor_payload_contract.py` keeps existing checkbox default/no-call behavior and static wiring checks aligned with the new copy.

## Provider Boundary

No actual Gemini call, Vertex AI call, retry, or provider/network call was made for v9.3.

## Next Recommendation

Proceed to v9.4 Opponent Move UI Integration Closure. The UI/source integration phase now has design, implementation, offline E2E coverage, and copy polish.
