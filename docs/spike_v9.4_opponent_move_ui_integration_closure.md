# v9.4 Opponent Move UI Integration Closure

## Purpose

Close the v9.0-v9.3 Opponent Move UI Integration phase and fix the current implementation boundary before moving to the next design phase.

This is documentation-only closure. It does not change production code, UI behavior, payload behavior, prompt behavior, tests, damage logic, provider behavior, or credentials.

## Phase Summary

### v9.0 Design

- Designed how the UI-selected advice path should expose `opponent_move_context`.
- Chose the existing default-off limited-context checkbox as the initial switch.
- Restricted source extraction to existing explicit or visible `opponent_moves` data.
- Required empty context omission and no hidden inference.

### v9.1 Implementation

- Connected the existing checkbox to three flags:
  - `enable_turn_pipeline`
  - `enable_turn_order_context`
  - `enable_opponent_move_context`
- Checkbox off maps all three flags to `False`.
- Checkbox on maps all three flags to `True`.
- Runtime source extraction reads existing `opponent_moves` only.
- UI-visible opponent moves are converted to `visible_ui` candidate moves.
- UI-visible moves are not promoted to `known_opponent_moves`.
- Candidate moves remain `confirmed=False` and `selected=False`.
- `selected_opponent_move` remains `{"status": "unknown"}`.
- The v8.4 opponent move prompt guard appears when `opponent_move_context` exists.

### v9.2 Offline E2E

- Added focused UI/offline E2E coverage.
- Verified checkbox default unchecked.
- Verified checkbox toggle alone does not call the provider.
- Verified checkbox off omits `turn_pipeline`, `turn_order_context`, `opponent_move_context`, and related guards.
- Verified checkbox on can include all three limited contexts in one mocked advice prompt/payload.
- Verified empty opponent source omits `opponent_move_context`.
- Verified mocked provider-only advice flow.

### v9.3 Copy / Tooltip Polish

- Updated the checkbox label to `제한 컨텍스트 포함`.
- Updated tooltip/status copy to describe the combined limited context.
- Clarified that this is not a final turn result.
- Clarified that opponent move candidates are not actual selected moves.
- Clarified that hidden movesets, RNG results, item consumption, and post-turn HP are not inferred.

## Current Behavior

- The existing limited-context checkbox defaults unchecked.
- Checkbox off:
  - no top-level `turn_pipeline`
  - no top-level `turn_order_context`
  - no top-level `opponent_move_context`
  - no TurnPipeline, turn-order, or opponent-move prompt guard
- Checkbox on:
  - enables `turn_pipeline`
  - enables `turn_order_context`
  - enables `opponent_move_context`
  - each context is still emitted only when valid source data exists
- UI-visible opponent moves are converted to `visible_ui` candidate moves.
- Candidate moves remain `confirmed=False` and `selected=False`.
- `known_opponent_moves` are not created from UI-visible moves in the v9.1 runtime path.
- `selected_opponent_move` remains unknown unless a future explicit trusted UI/source path is added.
- The opponent move prompt guard is included only when `opponent_move_context` exists.

## UI Copy

Label:

```text
제한 컨텍스트 포함
```

Tooltip/status meaning:

- Includes candidate turn events.
- Includes turn-order helper context.
- Includes UI-visible opponent move candidates.
- Does not mean a final turn result.
- Does not mean the opponent's actual selected move.
- Does not infer hidden movesets, RNG results, item consumption, or post-turn HP.

Status:

```text
제한 컨텍스트 켜짐: 후보 이벤트, 선후공 보조 정보, 상대 기술 후보 전달 | 확정 결과 아님
```

## Safety Boundary

The closed v9 UI/source integration phase does not implement:

- hidden moveset inference
- opponent set inference
- selected opponent move inference
- species/common-set/meta-based move generation
- EV/IV/nature inference
- hidden item inference
- weather/terrain/boost inference
- RNG resolution
- Quick Claw activation resolution
- item consumption
- post-turn HP update
- resolved turn order
- full Turn Engine
- `battle_state_context`
- damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes

## Test Coverage

Covered by targeted tests:

- `tests/test_ui_turn_pipeline_flag_flow.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_advisor_opponent_move_context.py`
- `tests/test_advisor_turn_order_context.py`
- `tests/test_advisor_turn_events.py`
- `tests/test_turn_event.py`
- `tests/test_advisor_damage_estimate.py`
- `tests/test_damage_perf.py`

v9.3 reported full pytest green:

```text
1162 passed, 2 deselected
```

## Known Limitations

- UI-visible opponent moves are candidate context only.
- There is no explicit selected opponent move source yet.
- There is no opponent hidden moveset inference.
- There is no opponent set, meta, or common-set expansion.
- There is no actual UI-path Gemini smoke for this combined context path yet.
- There is no `battle_state_context` yet.
- There is no full turn simulation.

## Next Recommendation

Recommended:

- v10.0 Battle State Context Design

Reason:

- The opponent move UI path is sufficiently closed for offline integration.
- The next major missing context is battle state: known HP state, field state, boosts, weather, terrain, screens, hazards, room effects, and how to represent them safely without implying full turn simulation.
- This should be designed before any implementation or provider smoke.

Alternatives:

- v9.5 Controlled UI Gemini Smoke Design
- v9.5 Opponent Move UI Path Controlled Gemini Smoke

Conclusion:

- Do not run an actual Gemini call yet.
- Move to v10.0 Battle State Context Design.
