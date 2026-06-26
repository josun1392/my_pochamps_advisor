# v9.0 Opponent Move UI / Source Integration Design

## Purpose

v9.0 designs how the existing UI-selected advice path should source and expose `opponent_move_context` in a future implementation.

This is design only:

- no production code implementation
- no UI checkbox behavior change
- no new checkbox
- no actual Gemini call
- no Vertex AI call
- no full Turn Engine
- no hidden opponent moveset, opponent set, selected opponent move, EV/IV/nature, hidden item, weather, terrain, boost, RNG, item consumption, or post-turn HP inference

## Current State

`opponent_move_context` is ready below the UI layer:

- v8.1 locked the fixture-level payload contract
- v8.2 added `build_opponent_move_context(...)`
- v8.3 added the explicit/default-off payload adapter
- v8.4 added prompt guard integration
- v8.5 verified mocked offline advice behavior
- v8.7 completed one controlled Gemini smoke with PASS
- v8.8 closed the phase and recommended UI/source integration design

The current UI-selected advice path already builds an `opponent_moves` section:

- `known_moves`: opponent move slots explicitly filled by the user
- `candidate_moves`: Champions movepool candidates, limited to possible/unconfirmed moves
- `candidate_source_status`: source availability metadata
- `limitations`: wording that candidates are not confirmed moves

`run_ui_selected_advice(...)` already accepts `opponent_move_context` and `enable_opponent_move_context`, but `ui/main_window.py` does not yet build or pass this context.

The existing UI developer checkbox currently controls:

- `enable_turn_pipeline`
- `enable_turn_order_context`

It starts unchecked, is not persisted, and toggling alone does not call Gemini.

## Source Policy

Future UI/source integration should use only the existing selected-battle input and explicit visible sources:

- user-filled opponent move slots may become `known_opponent_moves`
- Champions movepool candidates may become `candidate_moves`
- positive-priority candidate flags may be included only when trusted move metadata exposes priority
- `selected_opponent_move` remains unknown unless a future explicit selected-opponent-move UI source is added
- missing metadata becomes `unknown`, not inferred

The first implementation should not add a new data source.

## Selected Recommendation

Recommended v9.1 implementation path:

- add a narrow helper near the UI/advice boundary that converts existing `opponent_moves` payload data into `build_opponent_move_context(...)` inputs
- enable it only when an explicit UI/dev flag is checked
- reuse the existing limited-context developer checkbox for the first implementation
- keep default unchecked behavior unchanged
- keep checkbox toggle no-call behavior unchanged
- pass `enable_opponent_move_context=True` only when the advice button is pressed and the checkbox is checked
- omit `opponent_move_context` when the derived context is empty

Reason:

- this follows the v7 turn-order rollout pattern
- it avoids a second developer checkbox before manual QA proves the combined scope is too broad
- it keeps rollback simple
- it keeps source extraction tied to existing explicit/visible data

## Flag Mapping

Recommended first implementation mapping:

| Existing checkbox state | `enable_turn_pipeline` | `enable_turn_order_context` | `enable_opponent_move_context` |
| --- | --- | --- | --- |
| unchecked | `False` | `False` | `False` |
| checked | `True` | `True` | `True` |

This does not mean all contexts are always emitted. Each optional context should still be included only when its valid source context exists.

## Payload Behavior

When unchecked:

- no top-level `turn_pipeline`
- no top-level `turn_order_context`
- no top-level `opponent_move_context`
- no opponent-move prompt guard
- default/off prompt remains unchanged

When checked:

- include `turn_pipeline` when limited turn events can be generated
- include `turn_order_context` when valid source context exists
- include `opponent_move_context` when existing `opponent_moves` data can produce a non-empty valid context
- omit `opponent_move_context` when no known moves and no candidate moves are available
- keep known opponent moves user-confirmed only
- keep candidate moves unconfirmed and unselected
- keep selected opponent move unknown unless explicitly provided by a future trusted source

## UI Copy Direction

For the first implementation, keep visible UI churn minimal:

- do not add a new checkbox
- do not persist the enabled state
- keep the existing advice button as the only provider-call trigger
- update tooltip/status copy only if tests or manual QA need clearer wording

If copy is changed later, it should describe a combined limited planning context, not a full simulator.

## Test Plan For v9.1

Required implementation tests:

- checkbox default remains unchecked
- checkbox toggle emits no advice request and makes no Gemini call
- unchecked path passes `enable_opponent_move_context=False`
- checked path passes `enable_opponent_move_context=True`
- source-less checked path omits invalid empty `opponent_move_context`
- opponent user-confirmed move slots become `known_opponent_moves`
- Champions movepool candidates become unconfirmed/unselected `candidate_moves`
- candidate moves do not become selected moves
- prompt includes opponent-move guard only when top-level `opponent_move_context` is present
- default/off prompt remains unchanged
- coexistence with `turn_pipeline` and `turn_order_context` remains covered

Recommended targeted tests:

```text
tests/test_advisor_opponent_move_context.py
tests/test_advisor_payload_contract.py
UI/advice-flow tests that already cover the existing checkbox path
```

## Non-Goals

v9.0 and the recommended v9.1 path do not implement:

- selected opponent move inference
- hidden moveset inference
- opponent set inference
- species/common-set/meta-based move generation
- EV/IV/nature inference
- hidden item inference
- weather, terrain, screens, hazards, boosts, or room inference
- speed tie resolver
- RNG resolver
- Quick Claw activation resolution
- item consumption
- post-turn HP update
- full Turn Engine
- damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes

## Next Recommendation

Recommended:

- v9.1 Opponent Move UI Source Helper / Flag Integration

Safe alternatives:

- v9.1 Opponent Move UI Mock Fixture
- v9.1 Battle State Context Payload Contract

Do not run an actual Gemini call in v9.1. First connect the source path offline and verify default-off behavior.

## Safety Statement

- Documentation-only design.
- No production code was changed.
- No UI checkbox behavior was changed.
- No actual Gemini call was made.
- No Vertex AI call was made.
- No new checkbox was added.
- No saved setting auto-enable was added.
- No full Turn Engine was implemented.
- No hidden opponent information was inferred.
- No logs, `.env`, secrets, API keys, token-log contents, or `docs/handoff_capsule_v1.1.md` changes were made.
