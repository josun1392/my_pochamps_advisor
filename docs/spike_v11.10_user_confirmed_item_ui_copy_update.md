# v11.10 User-confirmed Item UI Copy Update

## Purpose

Update the existing limited-context UI copy so it safely reflects that the checked path can include user-confirmed item context. This is a copy-only UI update.

## Copy Location

- `ui/widgets/llm_advice_panel.py`
  - `TURN_PIPELINE_HELP_TEXT`
  - `TURN_PIPELINE_STATUS_TEXT`
  - existing `turn_pipeline_checkbox` label

## Label

The checkbox label remains unchanged:

```text
제한 컨텍스트 포함
```

No new checkbox was added.

## Tooltip/Status/Help Copy

The help text now says the limited context can include:

- candidate events
- turn order helper information
- UI-visible opponent move candidates
- current Pokemon/HP snapshot
- user-confirmed items

The status text now summarizes:

```text
제한 컨텍스트 켜짐: 후보 이벤트, 선후공 보조 정보, 상대 기술 후보, 현재 포켓몬/HP 스냅샷, 사용자 확인 아이템 전달 | 확정 결과 아님
```

## Included Meanings

- User-confirmed item values may be passed when the existing limited-context checkbox is enabled and the metadata is allowed.
- The item wording is limited to user-confirmed context.
- Candidate events, turn-order helper information, opponent move candidates, Pokemon/HP snapshot, and user-confirmed item context remain limited advice context.

## Forbidden Meanings Guarded

The copy and tests avoid wording that implies:

- hidden opponent item inference
- inferred item, recommended item, or automatically detected item
- damage-based item inference
- item activation certainty
- item consumption certainty
- post-turn HP certainty
- RNG, speed tie, Quick Claw, or full outcome certainty
- selected opponent move certainty

## Checkbox Behavior Preservation

- Checkbox default remains off.
- Checkbox toggle alone still does not call Gemini/provider code.
- Checkbox off still omits `battle_state_context` and item payload/prompt content.
- Checkbox on behavior is unchanged from v11.9.
- No payload builder call flow changed.

## Tests Added

Updated `tests/test_ui_turn_pipeline_flag_flow.py` to verify:

- the checkbox label remains unchanged
- the copy mentions candidate events
- the copy mentions turn-order helper information
- the copy mentions opponent move candidates
- the copy mentions current Pokemon/HP snapshot
- the copy mentions user-confirmed item context
- the copy says the context is not a confirmed result
- forbidden hidden/inferred/recommended item and resolved-outcome wording is absent
- checkbox default and toggle no-call behavior remain unchanged

## No Prompt Guard Change

The battle-state prompt guard wording was not changed in v11.10.

## No Actual Gemini Call

No actual Gemini, Vertex AI, provider, or network call was made.

## Next Recommendation

Recommended next:

- v11.11 User-confirmed Item UI Offline Smoke

Alternatives:

- v11.11 User-confirmed Item Phase Closure
- v11.11 Field State Source Design
