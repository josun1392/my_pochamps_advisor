# v9.1 Opponent Move UI Source Integration

## Purpose

v9.1 connects the existing default-off limited-context UI developer checkbox to `opponent_move_context` source generation.

This is an offline/test-only implementation milestone. It does not run Gemini, does not add a new checkbox, and does not change the checkbox default.

## Implementation Scope

Changed behavior:

- `run_ui_selected_advice(...)` now accepts `enable_opponent_move_context: bool = False`.
- `_build_ui_selected_prompt(...)` builds optional `opponent_move_context` only when that flag is true.
- `LLMAdviceWorker` stores and forwards `enable_opponent_move_context`.
- `MainWindow._start_llm_advice()` maps the existing checkbox to all three limited-context flags:
  - `enable_turn_pipeline`
  - `enable_turn_order_context`
  - `enable_opponent_move_context`

Unchanged behavior:

- the checkbox starts unchecked
- no saved auto-enable setting exists
- no new checkbox was added
- checkbox toggle alone does not call Gemini
- the existing advice button remains the only UI action that can start advice generation

## Source Mapping

The source is intentionally narrow:

- only existing `opponent_moves` data from the UI-selected advice payload is read
- UI-visible opponent move slots are converted into `visible_ui` candidate moves for `opponent_move_context`
- Champions movepool entries remain `champions_movepool` candidate moves
- no hidden moves are generated
- no species/common-set/meta moves are generated
- selected opponent move remains `{"status": "unknown"}`

The v9.1 runtime context does not promote UI-visible moves into `known_opponent_moves`. They remain candidates with:

```text
confirmed = False
selected = False
```

This keeps the opponent move context safe until a future explicit selected/confirmed source is designed.

## Checkbox Mapping

| Existing checkbox state | `enable_turn_pipeline` | `enable_turn_order_context` | `enable_opponent_move_context` |
| --- | --- | --- | --- |
| unchecked | `False` | `False` | `False` |
| checked | `True` | `True` | `True` |

## Payload Behavior

Unchecked:

- no top-level `turn_pipeline`
- no top-level `turn_order_context`
- no top-level `opponent_move_context`
- no opponent-move prompt guard

Checked with source:

- includes `turn_pipeline` when turn event context can be generated
- includes `turn_order_context` when valid source exists
- includes `opponent_move_context` when `opponent_moves` has visible or candidate source moves
- omits empty `opponent_move_context`

## Prompt Behavior

When top-level `opponent_move_context` is present, the v8.4 prompt guard is included. It keeps these boundaries explicit:

- candidate moves are not confirmed moves
- candidate moves are not confirmed selected moves
- known moves are not selected unless selected opponent move is explicit
- hidden movesets, opponent sets, selected moves, EV/IV/nature, hidden item, weather, terrain, boosts, RNG, item consumption, and post-turn HP must not be inferred

## Tests

Covered by:

- `tests/test_advisor_payload_contract.py`
- `tests/test_advisor_opponent_move_context.py`

Important checks:

- checkbox default remains unchecked
- checkbox toggle emits no advice request
- checkbox off omits `opponent_move_context`
- checkbox on forwards `enable_opponent_move_context=True`
- checked path includes `turn_pipeline`, `turn_order_context`, and `opponent_move_context` when sources exist
- UI-visible opponent moves become `visible_ui` candidate moves
- candidate moves remain `confirmed=False` and `selected=False`
- `selected_opponent_move` remains unknown
- prompt guard appears only when context is present
- provider calls are mocked in tests

## Next Recommendation

Recommended:

- v9.2 Opponent Move UI Integration Offline E2E

Safe alternatives:

- v9.2 Controlled UI Gemini Smoke Design
- v9.2 Opponent Move UI Copy / Tooltip Polish

Do not run an actual Gemini call in v9.2 unless T1 explicitly approves a separate controlled one-call smoke design and execution.

## Safety Statement

- No actual Gemini call was made.
- No Vertex AI call was made.
- No new checkbox was added.
- Checkbox default remains unchecked.
- Checkbox toggle alone does not call Gemini.
- No full Turn Engine was implemented.
- No resolved turn order was implemented.
- No hidden moveset, opponent set, selected opponent move, species/common-set/meta move, EV/IV/nature, hidden item, weather, terrain, boost, speed tie, RNG, Quick Claw activation, item consumption, or post-turn HP inference was implemented.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- No logs, `.env`, secrets, API keys, token-log contents, or `docs/handoff_capsule_v1.1.md` changes were made.
