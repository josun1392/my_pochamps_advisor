# v6.10 Controlled Gemini Smoke Execution

## Purpose

v6.10 executes one controlled actual Gemini smoke for the explicit-on TurnPipeline payload path.

The smoke checks whether Gemini treats `turn_pipeline` as limited planning/debug context rather than full turn simulation or resolved battle truth.

## Fixture Summary

Fixture:

- explicit-on `turn_pipeline` payload fixture
- `turn_pipeline.simulated == "limited"`
- event candidates include:
  - Light Ball known modifier context
  - Quick Claw candidate move-order context
  - Focus Sash candidate survival-before-KO context
  - Chilan Berry candidate Normal-type damage reduction context
- existing `damage_estimate` and `ko_context` remain present
- existing item contexts remain present

This is a synthetic smoke fixture. It is used only to test guard interpretation and is not a user-facing battle scenario.

## Call Policy

- actual Gemini calls executed: 1
- automatic retries: none
- Vertex AI calls: none
- additional fixtures: none

No stop condition occurred.

Stop conditions that would have halted without retry:

- HTTP 429
- `RESOURCE_EXHAUSTED`
- API key / auth error
- billing / prepay / credit blocker
- provider routing error
- timeout
- unexpected exception

## Result Classification

```text
PASS
```

## Response Safety Summary

The response recommended Flamethrower and treated the damage estimate as default-assumption, non-final battle damage.

TurnPipeline-related safety behavior:

- Quick Claw was phrased as something that may affect move order, not guaranteed activation.
- Focus Sash was phrased as possible survival, not guaranteed consumption or resolved survival.
- Chilan Berry was described as conditional and not relevant to the selected Fire-type move.
- The response did not claim full turn simulation.
- The response did not claim item consumption.
- The response did not claim exact post-turn HP.
- The response did not claim RNG, speed tie, or exact trigger resolution.
- The response did not treat `turn_pipeline` as stronger than `damage_estimate` or `ko_context`.

Short safe excerpts:

- "may occasionally affect move order"
- "may survive a lethal hit"
- "damage estimate uses default assumptions"
- "is not final battle damage"

## Notes

The response mentioned the synthetic Light Ball context as a Charizard-held item and stated its effect was not applied in the Charizard damage estimate. This did not create a TurnPipeline safety failure because the response did not treat Light Ball as a resolved TurnPipeline outcome or override the damage estimate.

Future fixture design should consider using a species/item combination that avoids this synthetic-context awkwardness if another actual smoke is approved.

## Safe Usage Summary

Safe usage fields observed:

- input tokens: 9615
- output tokens: 200
- cached tokens: 0
- total calls in session summary: 1
- pricing status: `free_tier_zero_cost`

No API key, credential, billing detail, or token log content is recorded here.

## Tests

Pre-call:

- `uv run pytest tests/test_advisor_payload_contract.py -q`: 78 passed
- `uv run pytest tests/test_advisor_turn_events.py -q`: 27 passed
- `uv run pytest tests/test_turn_event.py -q`: 15 passed
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed

Post-call:

- `uv run pytest tests/test_advisor_payload_contract.py -q`: 78 passed
- `uv run pytest tests/test_advisor_turn_events.py -q`: 27 passed
- `uv run pytest -q`: 1008 passed, 2 deselected

## Safety Statement

- Actual Gemini call count was exactly 1.
- No automatic retry was performed.
- No Vertex AI call was executed.
- No UI checkbox was implemented.
- No user-facing advice button automatic connection was added.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No speed/order simulation was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- `logs/token_usage.jsonl` was not committed or reset.
- Secrets, API keys, access tokens, ADC credentials, service-account JSON, billing details, and token-log contents were not printed or recorded.

## Next Candidate

Recommended next step:

```text
v6.11 Controlled Gemini Smoke Closure / Next UI Exposure Design
```

The next step should close the controlled smoke result and decide whether to remain dev-only, design a UI exposure surface, or add one more offline fixture improvement before any UI checkbox.
