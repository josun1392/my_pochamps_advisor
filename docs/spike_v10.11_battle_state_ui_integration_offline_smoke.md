# v10.11 Battle State UI Integration Offline Smoke

## Purpose

Verify the UI-selected limited-context checkbox flow with a mocked provider after
`battle_state_context` was connected to the existing checkbox and copy was updated.

The smoke confirms payload and prompt preservation without any actual Gemini,
Vertex AI, provider, or network call.

## Checkbox Off Smoke

The default unchecked path verifies:

- `turn_pipeline` is omitted.
- `turn_order_context` is omitted.
- `opponent_move_context` is omitted.
- `battle_state_context` is omitted.
- serialized `battle_state_context` is absent from the prompt.
- the battle-state prompt guard is absent from the prompt.

This preserves the default-off behavior.

## Checkbox On Smoke

The checked path verifies:

- `turn_pipeline` is present.
- `turn_order_context` is present.
- `opponent_move_context` is present when valid source data exists.
- `battle_state_context` is present.
- serialized `battle_state_context` appears in the prompt.
- the v10.4 battle-state prompt guard appears in the prompt.

## Payload Preservation

The smoke captures the provider prompt and parses the final prompt payload. When
the checkbox is on, `battle_state_context` remains a top-level context and does
not overwrite the other limited contexts.

## Prompt Guard Preservation

The prompt contains the existing guard anchors:

- unknown battle-state fields must remain unknown
- hidden item inference is forbidden
- EV/IV/nature inference is forbidden
- boosts/status/weather/terrain/hazards/screens/room inference is forbidden unless explicit
- damage estimate / KO context reverse inference is forbidden
- `battle_state_context` is not a resolved turn simulation
- post-turn HP, item consumption, RNG result, speed tie result, Quick Claw activation,
  and full turn outcome claims are forbidden

No prompt guard wording was changed.

## Species / HP Visible UI Verification

The smoke verifies:

- self species source is `visible_ui`
- self HP percent source is `visible_ui`
- opponent species source is `visible_ui`
- opponent HP percent source is `visible_ui`

## Unknown Field Verification

The smoke verifies:

- self status, boosts, and item remain unknown
- opponent status, boosts, and item remain unknown
- field weather, terrain, screens, hazards, and room remain unknown
- `known_conditions` remains `[]`

## Coexistence

The checked path confirms `battle_state_context` coexists with:

- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`

The battle-state context is not generated from those other contexts.

## Provider No-Call Guarantee

The smoke monkeypatches:

- `call_gemini`
- `_log_advisor_call`

Only the mocked `call_gemini` is used. The test does not perform an actual
Gemini call, Vertex AI call, provider call, or network call.

## Mocked Response Safety

The mocked response avoids hidden-state certainty and resolved-outcome claims,
including hidden item certainty, EV/IV/nature guesses, post-turn HP certainty,
item consumption certainty, RNG resolution, speed tie resolution, Quick Claw
activation certainty, and full turn outcome certainty.

## Tests

Updated coverage:

- `tests/test_ui_turn_pipeline_flag_flow.py`
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`

## Safety Boundary

v10.11 does not add a checkbox, change checkbox defaults, change UI behavior,
change UI copy, change payload flow behavior, change prompt guard wording, change
payload adapter contract, change the battle-state source adapter, call providers,
infer hidden state, reverse-infer from damage or KO context, or implement full
Turn Engine behavior.

## Next Recommendation

Recommended next milestone:

```text
v10.12 Battle State Context UI Phase Closure
```

Reason:

- The battle-state core, UI source adapter, checkbox mapping, copy, and offline
  UI-selected smoke are now covered without provider calls.
