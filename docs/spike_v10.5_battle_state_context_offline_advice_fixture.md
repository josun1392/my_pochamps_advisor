# v10.5 Battle State Context Offline Advice Fixture

## Purpose

Verify that `battle_state_context` payload and prompt guard survive an offline mocked advice flow without any actual provider, Vertex AI, or network call.

This milestone adds only offline fixture coverage:

- no UI/source integration
- no UI checkbox behavior change
- no actual Gemini call
- no hidden-state inference
- no full Turn Engine

## Provider No-Call Guarantee

The fixture monkeypatches:

- `advisor_client.call_gemini`
- `advisor_client._log_advisor_call`

The test calls only the mocked provider function and records captured prompts in memory. No real Gemini, Vertex AI, network, token log, billing, or credential path is used.

## Payload Preservation

The fixture builds `battle_state_context` through `build_battle_state_context(...)` using allowed sources:

- `visible_ui`
- `explicit_input`
- `user_confirmed`
- `calculated_from_visible`

The captured prompt payload verifies:

- top-level `battle_state_context` is present when explicitly enabled
- helper output shape is preserved
- `confidence == "limited"`
- unknown fields remain explicit unknowns
- forbidden fields are absent recursively
- forbidden sources are absent recursively

## Prompt Guard Preservation

The captured prompt verifies:

- serialized `battle_state_context` appears
- `If battle_state_context is present` guard appears
- `Unknown battle state fields must remain unknown.`
- hidden item inference is forbidden
- EV/IV/nature inference is forbidden
- boosts/status/weather/terrain/hazards/screens/room inference is forbidden unless explicit
- damage/KO reverse inference is forbidden
- `battle_state_context` is not a resolved turn simulation
- post-turn HP, item consumption, RNG result, speed tie result, Quick Claw activation, and full turn outcome claims are forbidden

## Coexistence

The fixture also verifies coexistence with:

- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`
- `battle_state_context`

All guards remain present only when their corresponding top-level context is present.

## Mocked Response Safety

The mocked response says the battle state context is visible or explicit snapshot context only, keeps unknown fields unknown, and avoids claims about:

- hidden item certainty
- EV/IV/nature certainty
- post-turn HP certainty
- item consumption
- RNG resolution
- speed tie resolution
- Quick Claw activation
- full turn outcome

## Tests

Implemented in `tests/test_advisor_payload_contract.py`:

- default prompt omits `battle_state_context`
- explicit prompt includes top-level `battle_state_context`
- helper output shape is preserved in the captured prompt payload
- guard anchors are present
- forbidden fields and sources are absent recursively
- mocked provider and logger are the only called provider/log paths
- coexistence with `turn_pipeline`, `turn_order_context`, and `opponent_move_context`
- mocked response avoids hidden-state and resolved-outcome claims

## Next Recommendation

Recommended:

- v10.6 Battle State UI Source Inventory

Reason:

- Before UI integration, the next safe step is listing which self/opponent species, HP percent, status, boosts, item, and field sources are actually available and trustworthy from current UI/repo state.

Alternatives:

- v10.6 Battle State UI Integration Design
- v10.6 Battle State Context Closure

Do not run an actual Gemini call yet.
