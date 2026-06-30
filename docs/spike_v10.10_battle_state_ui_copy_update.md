# v10.10 Battle State UI Copy Update

## Purpose

Update the existing limited-context checkbox copy so it matches the v10.9 behavior:
the checkbox now enables `turn_pipeline`, `turn_order_context`, `opponent_move_context`,
and `battle_state_context` together.

## Previous Copy

Label:

```text
제한 컨텍스트 포함
```

Tooltip/status previously described:

- candidate turn events
- turn-order helper context
- UI-visible opponent move candidates
- non-final result boundary

It did not yet mention the visible Pokemon/HP battle-state snapshot added through v10.9.

## New Copy

Label:

```text
제한 컨텍스트 포함
```

Tooltip:

```text
후보 이벤트, 선후공 보조 정보, UI에 보이는 상대 기술 후보, 현재 포켓몬/HP 스냅샷을 LLM 입력에 포함합니다.
이 정보는 확정 결과가 아니며, 상대의 실제 선택 기술이나 숨겨진 아이템/상태/랭크/필드를 추론하지 않습니다. 턴 후 HP, 아이템 소모, RNG, 스피드 타이, Quick Claw 발동, 전체 턴 결과를 확정하지 않습니다.
```

Enabled status/help:

```text
제한 컨텍스트 켜짐: 후보 이벤트, 선후공 보조 정보, 상대 기술 후보, 현재 포켓몬/HP 스냅샷 전달 | 확정 결과 아님
```

## Included Context Meanings

- `turn_pipeline`: candidate events only, not confirmed turn results.
- `turn_order_context`: turn-order helper information only, not final/resolved order.
- `opponent_move_context`: UI-visible opponent move candidates only, not selected moves or hidden movesets.
- `battle_state_context`: current visible Pokemon/HP snapshot only.

## Forbidden Wording

The copy must not imply:

- confirmed battle result
- actual opponent selected move
- hidden item inference
- status, boost, or field inference
- post-turn HP resolution
- item consumption resolution
- RNG result resolution
- speed tie resolution
- Quick Claw activation resolution
- full turn outcome resolution

## Behavior Unchanged

v10.10 changes only UI copy and copy-lock tests.

No new checkbox was added. The existing checkbox remains default unchecked.
The checkbox behavior, payload flow, payload adapter contract, source adapter,
and prompt guard wording are unchanged.

## Tests

Updated tests lock:

- label text
- tooltip/status copy anchors
- visible Pokemon/HP snapshot meaning
- non-final result wording
- forbidden certainty/inference wording absence
- default unchecked behavior
- checkbox toggle no-call behavior

## Safety Boundary

v10.10 does not implement actual Gemini calls, Vertex AI calls, retries, network calls,
full Turn Engine behavior, resolved turn order, post-turn HP calculation, item consumption,
RNG or speed tie resolution, Quick Claw activation resolution, hidden item inference,
EV/IV/nature inference, weather/terrain/boost/status/hazard/screen inference, damage reverse
inference, species/common-set/meta-based state generation, opponent set inference, hidden
moveset inference, selected opponent move inference, damage formula changes, raw roll changes,
Q12 multiplier changes, `ko_context` changes, or payload filtering changes.

## Next Recommendation

Recommended next milestone:

```text
v10.11 Battle State UI Integration Offline Smoke
```

Reason:

- After copy and checkbox mapping are aligned, the next safe step is an offline mocked
  UI-selected path smoke that verifies the limited-context checkbox on/off flow and
  battle-state prompt preservation without an actual provider call.
