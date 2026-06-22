# v8.4 Opponent Move Prompt Guard

## Purpose

v8.4 adds prompt safety wording for `opponent_move_context` so the LLM does not treat candidate moves as confirmed known moves or selected opponent moves.

This step does not add:

- UI/source extraction
- UI checkbox behavior changes
- actual Gemini calls
- hidden moveset inference
- selected opponent move inference
- full Turn Engine behavior

## Guard Location

`llm/advisor_client.py`

Helper:

```python
_build_opponent_move_context_prompt_guard(payload)
```

Behavior:

- returns `""` when top-level `opponent_move_context` is absent
- returns safety wording when top-level `opponent_move_context` is present

## Prompt Placement

The guard is inserted in the optional-context guard area:

1. `turn_snapshot` guard
2. `turn_pipeline` guard
3. `turn_order_context` guard
4. `opponent_move_context` guard

## Safety Wording

Guard meaning:

- `opponent_move_context` is based only on explicitly known or visible opponent move data
- known opponent moves are not necessarily the selected opponent move this turn unless `selected_opponent_move` is explicit
- candidate moves are not confirmed moves
- candidate moves are not confirmed selected moves
- do not infer hidden movesets
- do not infer opponent sets
- do not infer selected opponent move unless explicitly provided
- do not infer EVs, IVs, nature, hidden item, weather, terrain, boosts, RNG results, item consumption, or post-turn HP unless explicitly provided
- treat unsupported entries as boundaries, not facts to fill in

Korean documentation meaning:

```text
상대 기술 정보는 명시적으로 알려진 정보 또는 UI에 보이는 정보에 한정한다.
known move도 이번 턴 선택 기술이라는 뜻은 아니다.
candidate move는 확정 기술이 아니다.
candidate move는 확정 선택 기술이 아니다.
상대 hidden moveset, opponent set, selected move를 추론하지 않는다.
EV/IV/nature, 숨겨진 아이템, 날씨, 필드, 랭크 보정, RNG 결과, 아이템 소모, 턴 후 HP를 명시 정보 없이 추정하지 않는다.
unsupported 항목은 채워 넣을 사실이 아니라 경계 조건이다.
```

## Default-Off Behavior

When `opponent_move_context` is absent:

- no opponent move guard is emitted
- existing prompt wording remains unchanged
- no top-level `opponent_move_context` appears in serialized prompt payload

## Explicit-On Behavior

When a caller supplies valid `opponent_move_context` with `enable_opponent_move_context=True`:

- payload includes top-level `opponent_move_context`
- prompt includes the opponent move guard
- serialized payload JSON includes the context

## Coexistence

The guard coexists with:

- `turn_pipeline` guard
- `turn_order_context` guard
- both guards together

No existing optional guard is replaced.

## Forbidden Positive Wording

Tests avoid treating negative instructions as positive claims. The guard must not positively state:

- opponent will use a candidate move
- opponent likely uses a candidate move
- candidate move is confirmed
- candidate move is selected
- opponent has a hidden moveset
- opponent item is inferred
- post-turn HP will be known
- RNG is resolved

## Tests

`tests/test_advisor_payload_contract.py` covers:

- no context means guard absent
- context present means guard present
- guard includes known/visible data limitation
- guard distinguishes known moves from selected move
- guard marks candidate moves as not confirmed and not selected
- guard forbids hidden moveset, opponent set, selected move, EV/IV/nature, hidden item, weather/terrain/boost, RNG, item consumption, and post-turn HP inference
- guard coexists with `turn_pipeline` and `turn_order_context`
- prompt default-off stays unchanged
- explicit prompt includes guard and serialized context

## Next Recommendation

Recommended next:

- v8.5 Opponent Move Offline Advice Fixture

Rationale:

- before any actual Gemini call or UI/source integration, verify the payload -> prompt -> mocked advice path
- mocked response checks should ensure candidate/known/selected move wording stays non-inferential

Alternative:

- v8.5 Opponent Move UI/Source Integration Design
