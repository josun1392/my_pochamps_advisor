# v9.2 Opponent Move UI Integration Offline E2E

## Purpose

Verify the existing limited-context UI checkbox path after `opponent_move_context` was connected to it in v9.1. This is an offline/mock-only E2E check from `LLMAdvicePanel` checkbox state through `run_ui_selected_advice(...)` prompt construction.

## Checkbox Off Behavior

- The checkbox defaults unchecked.
- `enable_turn_pipeline=False`.
- `enable_turn_order_context=False`.
- `enable_opponent_move_context=False`.
- The prompt payload omits `turn_pipeline`, `turn_order_context`, and `opponent_move_context`.
- The TurnPipeline, turn-order, and opponent-move prompt guards are absent.

## Checkbox On Behavior

- The existing checkbox state maps to all three limited contexts:
  - `enable_turn_pipeline=True`
  - `enable_turn_order_context=True`
  - `enable_opponent_move_context=True`
- When source data exists, one prompt/payload can contain `turn_pipeline`, `turn_order_context`, and `opponent_move_context` together.
- If no usable opponent move source exists, `opponent_move_context` is omitted rather than forced into an empty top-level field.

## Opponent Move Handling

- Visible UI opponent moves become `candidate_moves` with `source="visible_ui"`.
- Visible UI opponent moves do not become `known_opponent_moves`.
- Candidate moves remain `confirmed=False` and `selected=False`.
- `selected_opponent_move` remains `{"status": "unknown"}` because there is no explicit selected opponent move UI source.
- Champions movepool entries remain unconfirmed `champions_movepool` candidates.
- No hidden moveset, opponent set, selected move, species/common-set/meta move, EV/IV/nature, hidden item, weather, terrain, or boost inference is added.

## Prompt Guard

When `opponent_move_context` is present, the v8.4 opponent move guard is included. It keeps candidate moves from being treated as confirmed or selected moves and forbids hidden inference. When `opponent_move_context` is omitted, the guard is omitted.

## Provider No-Call Guarantee

The v9.2 tests monkeypatch `advisor_client.call_gemini` and `_log_advisor_call`. Checkbox toggles alone are verified to emit no advice request and make no provider call. The advice-flow checks use only mocked provider results.

## Tests

- `tests/test_ui_turn_pipeline_flag_flow.py`
- `tests/test_advisor_opponent_move_context.py`
- `tests/test_advisor_payload_contract.py`

## Next Recommendation

Proceed to v9.3 Opponent Move UI Copy / Tooltip Polish. The existing checkbox now covers multiple limited contexts, so its label, tooltip, and status copy should describe the combined behavior before any further smoke work.
