# v8.7 Controlled Opponent Move Gemini Smoke

## Purpose

v8.7 executes the v8.6 controlled smoke plan for `opponent_move_context`.

This smoke makes at most one actual Gemini call and verifies that Gemini keeps opponent move context within the explicitly known / visible boundary.

## Pre-Check Result

All pre-checks passed before the provider call:

- `opponent_move_context` payload present: passed
- opponent move prompt guard present: passed
- known move represented as known data, not selected move: passed
- candidate move `confirmed=False`: passed
- candidate move `selected=False`: passed
- `selected_opponent_move` is `unknown`: passed
- candidate-not-confirmed prompt anchor: passed
- candidate-not-selected prompt anchor: passed
- known-not-selected prompt anchor: passed
- hidden moveset inference guard: passed
- opponent set inference guard: passed
- selected move inference guard unless explicit: passed
- EV/IV/nature, hidden item, weather, terrain, boost inference guard: passed
- RNG, item consumption, post-turn HP inference guard: passed
- provider call count before smoke: `0`

## Actual Call

- actual Gemini call count: `1`
- retry count: `0`
- stop condition: none
- result classification: `PASS`
- model: `gemini-2.5-flash`

No repeated provider call was made.

## Response Safety Summary

The response passed the v8.6 safety criteria:

- `opponent_move_context` treated as explicitly known / visible context: yes
- known move treated as selected move: no
- candidate move treated as confirmed move: no
- candidate move treated as selected move: no
- selected opponent move inferred despite unknown: no
- hidden moveset inference: no
- opponent set inference: no
- EV/IV/nature inference: no
- hidden item inference: no
- weather/terrain/boosts inference: no
- RNG resolved claim: no
- item consumption claim: no
- post-turn HP claim: no
- full turn resolution claim: no

Safe paraphrase:

- Gemini recommended a one-turn action, described Thunderbolt as known move data, and did not claim that Thunderbolt or Quick Attack was the opponent's selected move.
- Quick Attack was not promoted from candidate context to confirmed or selected move.
- The response did not fill in hidden moveset, hidden item, EV/IV/nature, weather, terrain, boosts, RNG, item consumption, post-turn HP, or full turn resolution.

## Known / Candidate / Selected Wording Check

Observed behavior:

- known move data remained known context
- candidate move data remained unconfirmed and unselected
- `selected_opponent_move` remained unknown
- no `opponent will use X` claim
- no `opponent likely uses X` claim
- no candidate confirmed/selected claim

## Token / Cost Safe Summary

Safe usage fields returned by the provider wrapper:

- input tokens: `7931`
- output tokens: `73`
- cached tokens: `0`

No raw token log content, API key, credential, billing detail, or full raw response is recorded here.

`logs/token_usage.jsonl` was not committed or reset.

## Not Implemented

v8.7 does not add:

- UI/source extraction
- UI checkbox behavior change
- full Turn Engine behavior
- resolved turn order
- opponent set inference
- hidden moveset inference
- selected opponent move inference
- species/common-set/meta-based move generation
- EV/IV/nature inference
- hidden item inference
- weather/terrain/boost inference
- speed tie resolver
- RNG resolver
- Quick Claw activation resolution
- item consumption
- post-turn HP update
- damage formula changes
- raw damage roll changes
- Q12 multiplier changes
- `ko_context` changes
- payload filtering changes

## Tests

Pre-call:

- `uv run pytest tests/test_advisor_payload_contract.py -q`: `199 passed`
- `uv run pytest tests/test_advisor_opponent_move_context.py -q`: `18 passed`
- `uv run pytest tests/test_advisor_turn_order_context.py -q`: `10 passed`
- `uv run pytest tests/test_advisor_turn_events.py -q`: `27 passed`
- `uv run pytest tests/test_turn_event.py -q`: `15 passed`
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: `96 passed`
- `uv run pytest tests/test_damage_perf.py -q`: `4 passed`

Post-call:

- `uv run pytest tests/test_advisor_payload_contract.py -q`: `199 passed`
- `uv run pytest -q`: `1157 passed, 2 deselected`

## Next Recommendation

Recommended next:

- v8.8 Opponent Move Context Closure

Rationale:

- contract, helper, adapter, prompt guard, offline advice fixture, controlled smoke design, and controlled smoke PASS are complete
- no safety guard failure or wording polish need was observed in the one-call smoke

Alternatives:

- v8.8 Prompt Wording Polish, only if T2 wants extra cautious copy tightening
- v8.8 Opponent Move UI/Source Integration Design, if the next phase should move toward actual UI/cache source supply
