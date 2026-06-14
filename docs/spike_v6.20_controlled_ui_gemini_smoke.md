# v6.20 Controlled UI Gemini Smoke

## Purpose

v6.20 verifies the TurnPipeline dev flag path with one controlled actual Gemini call.

This smoke checks whether the UI-enabled `turn_pipeline` path still keeps Gemini from treating candidate TurnPipeline events as full simulation results.

## UI Flag State

The smoke used the v6.18 UI dev flag state:

- `LLMAdvicePanel` instantiated offscreen
- checkbox default verified unchecked
- checkbox toggled on
- toggle alone emitted no `advice_requested`
- enabled status text remained `턴 이벤트 후보 포함됨 | 확정 시뮬레이션 아님`
- `run_ui_selected_advice(..., enable_turn_pipeline=True)` was executed explicitly from that checked state

## Call Policy

- actual Gemini call count: 1
- retry: none
- automatic retry: none
- Vertex AI call: none
- stop condition: none

The call path was wrapped with a local counter that would fail on a second Gemini call. The prompt was checked before the call to contain top-level `turn_pipeline`, `simulated="limited"`, and the candidate / not-resolved guard.

## Fixture

The fixture was the existing explicit TurnPipeline advice-flow payload used by offline tests:

- Light Ball known modifier
- Quick Claw candidate move-order context
- Focus Sash candidate survival context
- Chilan Berry candidate limited damage context
- existing `damage_estimate` and `ko_context`
- existing item contexts preserved

## Result Classification

```text
PASS
```

## Response Safety Summary

Gemini treated the TurnPipeline context as limited / candidate context rather than full simulation.

Observed safe behavior:

- Quick Claw was described with possibility wording: it may occasionally affect move order
- final move order was explicitly not modeled
- Focus Sash was described as a possible survival context, not guaranteed consumption
- no full turn simulation claim was found
- no item consumption claim was found
- no exact post-turn HP claim was found
- no speed tie / RNG / exact trigger resolution claim was found
- damage and KO wording stayed tied to the existing damage estimate range

Short response excerpts used for classification:

- Quick Claw: "may occasionally affect move order, but final move order is not modeled"
- Focus Sash: "may allow survival at 1 HP from a lethal hit while at full HP"
- Damage / KO: "31-37 damage (16.9-20.2% HP) and cannot OHKO or 2HKO"

The response did not include forbidden phrases such as:

- `Quick Claw will activate`
- `Focus Sash will be consumed`
- `post-turn HP will be`
- `full turn simulation shows`
- `speed tie is resolved`

## Test Notes

Pre-call tests:

- `tests/test_advisor_payload_contract.py`: passed
- `tests/test_advisor_turn_events.py`: passed
- `tests/test_turn_event.py`: passed
- `tests/test_advisor_damage_estimate.py`: passed
- `tests/test_damage_perf.py`: one known timing-sensitive failure before the call, then isolated target passed 3/3

Post-call tests:

- `tests/test_advisor_payload_contract.py`: passed
- `tests/test_advisor_turn_events.py`: passed
- `tests/test_damage_perf.py`: passed after isolated target checks
- full pytest: first two full runs hit the known timing-sensitive perf failure, final full run passed

The perf failure was `test_item_damage_calculation_under_point_12ms_average` with median `0.125000ms` over threshold `0.120000ms`. Thresholds, skips, and xfails were not changed.

## Token / Cost Policy

Token usage was handled through the existing advisor token logger path. The raw token log was not printed, copied, committed, or reset.

No API key, access token, ADC credential, service account JSON, billing details, or token-log contents were recorded in this document.

## Next Step

Recommended next step:

```text
v6.21 TurnPipeline UI Phase Closure
```

If later UI wording feels too strong or visually awkward, a small UI Copy Polish can happen separately without another Gemini call.

## Safety Statement

- Actual Gemini call count was exactly 1.
- No retry was used.
- No Vertex AI call was executed.
- Checkbox toggle alone did not call Gemini.
- No saved setting or persisted auto-enable was implemented.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No speed/order simulation was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- `logs/token_usage.jsonl` was not committed or reset.
- Secrets, API keys, access tokens, ADC credentials, service-account JSON, billing details, and token-log contents were not printed or recorded.
