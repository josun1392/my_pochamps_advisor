# v8.5 Opponent Move Offline Advice Fixture

## Purpose

v8.5 verifies the `opponent_move_context` payload and prompt guard through a mocked offline advice path.

The goal is to confirm, without provider calls, that:

- valid `opponent_move_context` reaches the prompt payload
- the opponent move prompt guard is present
- candidate moves remain unconfirmed and unselected
- known moves are not treated as selected moves when `selected_opponent_move` is unknown
- mocked advice wording does not infer hidden movesets, selected moves, hidden items, EV/IV/nature, RNG, item consumption, or post-turn HP

## Mock / No-Call Guarantee

The fixture monkeypatches:

- `advisor_client.call_gemini`
- `advisor_client._log_advisor_call`

No actual Gemini call, Vertex AI call, network call, billing lookup, credential access, or token log read is performed.

## Fixture Coverage

Test:

```text
test_opponent_move_context_offline_advice_fixture_covers_prompt_and_mocked_response
```

The fixture runs three mocked paths:

- default path: no `opponent_move_context`
- explicit path: `opponent_move_context` only
- coexistence path: `turn_pipeline` + `turn_order_context` + `opponent_move_context`

## Payload Coverage

The explicit payload includes:

- `kind: opponent_move_context`
- `selected_opponent_move: {"status": "unknown"}`
- known Thunderbolt with `confirmed=True`
- candidate Quick Attack with `confirmed=False`, `selected=False`
- priority candidate Quick Attack with `confirmed=False`
- unsupported boundaries for hidden moveset, opponent set, selected move, EV/IV/nature, hidden item, weather/terrain/boost, RNG, and full turn resolution
- candidate-not-confirmed safety notes

## Prompt Guard Coverage

The prompt asserts:

- opponent move context is explicitly known / visible data only
- known moves are not necessarily selected this turn
- candidate moves are not confirmed moves
- candidate moves are not confirmed selected moves
- hidden movesets must not be inferred
- opponent sets must not be inferred
- selected opponent move must not be inferred unless explicit
- EV/IV/nature, hidden item, weather, terrain, boosts, RNG, item consumption, and post-turn HP must not be inferred

## Mocked Response Safety

The mocked response uses safe wording:

- Thunderbolt is user-confirmed known move data
- selected move is unknown
- Quick Attack is only a candidate
- Quick Attack is not confirmed or selected
- no hidden set, hidden item, EV, IV, nature, RNG, item consumption, or post-turn HP is inferred

The response avoids:

- `opponent will use`
- `likely uses`
- `Quick Attack is selected`
- `Quick Attack is confirmed`
- hidden moveset assertions
- hidden item assertions
- EV/IV/nature assertions
- post-turn HP assertions
- RNG resolution assertions

## Coexistence

The coexistence path confirms all optional guards can appear together:

- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`

This remains an offline mocked path only.

## Not Implemented

v8.5 does not add:

- UI/source extraction
- UI checkbox behavior changes
- actual Gemini calls
- Vertex AI calls
- controlled smoke execution
- hidden moveset inference
- selected opponent move inference
- species/common set/meta-based move generation
- full Turn Engine behavior

## Next Recommendation

Recommended next:

- v8.6 Controlled Gemini Smoke Design

Rationale:

- before any actual Gemini call, define call count, stop conditions, PASS/PARTIAL/FAIL/BLOCKED criteria, and response safety checks

Alternative:

- v8.6 Opponent Move UI/Source Integration Design
