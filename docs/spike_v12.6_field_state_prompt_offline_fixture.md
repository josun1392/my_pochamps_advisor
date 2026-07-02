# v12.6 Field State Prompt/Offline Fixture

## Purpose

Verify that known `battle_state_context.field` values serialize into the advisor prompt safely through a mocked offline fixture. This milestone does not add UI integration, battle log/parser input, prompt guard wording changes, payload builder call-flow changes, or provider calls.

Known field values remain current context only. They do not imply duration, expiration, post-turn state, damage precision, turn order, item activation, item consumption, RNG resolution, speed tie resolution, Quick Claw activation, or full outcome.

## Fixture Summary

The fixture in `tests/test_advisor_payload_contract.py` uses:

- self: `Garchomp`, HP `100`, item `leftovers`
- opponent: `Charizard`, HP `87`, item `choice-scarf`
- weather: `rain`, `source=user_confirmed`
- terrain: `electric_terrain`, `source=explicit_input`
- room: `trick_room`, `source=user_confirmed`
- screens: `{"self": ["reflect"], "opponent": ["light_screen"]}`, `source=user_confirmed`
- hazards: `{"self": [], "opponent": ["stealth_rock"]}`, `source=explicit_input`

The fixture also covers an unknown-field battle-state context and a coexistence path with:

- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`
- `battle_state_context`

## Payload Behavior

Verified payload behavior:

- `battle_state_context` is present when explicitly enabled
- self species/HP remain `visible_ui`
- opponent species/HP remain `visible_ui`
- known weather envelope is preserved
- known terrain envelope is preserved
- known room envelope is preserved
- known screens side-specific envelope is preserved
- known hazards side-specific envelope is preserved
- `known_conditions` remains `[]`
- unknown field fixture keeps all field entries unknown

## Prompt Behavior

Verified prompt behavior:

- serialized `battle_state_context` appears
- known weather appears in serialized prompt
- known terrain appears in serialized prompt
- known room appears in serialized prompt
- known screens appear in serialized prompt
- known hazards appear in serialized prompt
- existing `battle_state_context` guard appears
- existing limited context guards remain present in the coexistence path

No prompt guard wording change was made.

## Mocked Response Safety

The mocked response is constrained to safe language:

```text
Known field entries are current context only. They do not by themselves resolve duration, expiration, post-turn state, damage precision, RNG, speed ties, item activation, or the full turn outcome.
```

The fixture rejects mocked response wording that would imply:

- known remaining duration
- this-turn expiration
- definite post-turn field state
- precise hazard damage calculation
- guaranteed damage
- known full turn outcome
- damage-derived field inference
- hidden field state

## Duration/Expiration/Post-turn Guard

The fixture verifies known field values do not create:

- `duration`
- `duration_turns`
- `expires`
- `expiration`
- `post_turn_expiration`
- `post_turn_field`
- `post_turn_outcome`
- `resolved_outcome`

## Damage Estimate / KO Context

The fixture compares the prompt payload against the baseline payload and verifies known field context does not change:

- `moves.my_selected_move.damage_estimate`
- `moves.my_selected_move.ko_context`

## Coexistence With Existing Contexts

The coexistence path verifies known field context can appear alongside:

- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`
- `battle_state_context`

Each existing guard remains present where applicable, and none of those contexts turns field state into resolved battle truth.

## No UI Integration

No UI field controls, source adapter connections, checkbox changes, UI default changes, UI behavior changes, or UI copy changes are added.

## No Actual Gemini Call

No actual Gemini, retry, second provider, Vertex AI, network, or provider call is executed in v12.6. The provider call is monkeypatched.

## Tests

Updated test file:

- `tests/test_advisor_payload_contract.py`

Primary test:

- `test_field_state_battle_state_offline_prompt_fixture`

Supporting regression suites:

- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_ui_turn_pipeline_flag_flow.py`

## Next Recommendation

Recommended next:

- v12.7 Field State UI Source Inventory

Reason:

- Helper, contract, and prompt serialization are now covered. The next safe step is to inspect whether the current UI has any explicit or user-confirmed field source surface before designing mapping.

Alternatives:

- v12.7 Field State UI Mapping Design
- v12.7 Item Activation/Consumption Boundary Design
