# v11.7 User-confirmed Item Prompt/Offline Fixture

## Purpose

Verify offline that user-confirmed items can appear in `battle_state_context`
payload and prompt without becoming hidden item inference, item consumption, or
resolved turn simulation claims. This fixture uses a mocked provider only.

## Fixture Summary

The fixture builds a UI-selected battle-state context through the v11.6 opt-in
adapter:

```python
build_battle_state_context_from_ui_selected_state(
    battle_input,
    include_user_confirmed_items=True,
)
```

Fixture state:

- self: `Garchomp`, HP `100`
- opponent: `Charizard`, HP `87`
- `item_profiles.my_active`: `status=user_confirmed`,
  `source=user_input`, `item_id=leftovers`
- `item_profiles.opponent_active`: `status=user_confirmed`,
  `source=user_input`, `item_id=choice-scarf`

## Known Item Payload Behavior

The prompt payload preserves:

```python
self_active.item == {
    "known": True,
    "source": "user_confirmed",
    "value": "leftovers",
}

opponent_active.item == {
    "known": True,
    "source": "user_confirmed",
    "value": "choice-scarf",
}
```

Species and HP stay `visible_ui`. Field values remain unknown and
`known_conditions` remains `[]`.

## Prompt Behavior

The serialized prompt includes:

- top-level `battle_state_context`
- known self item with `source=user_confirmed`
- known opponent item with `source=user_confirmed`
- self/opponent species and HP percent as `visible_ui`

The prompt does not include item consumption, post-turn HP, RNG, speed tie,
Quick Claw activation, or full outcome fields.

## Guard Behavior

The existing v10.4 battle-state guard is reused unchanged. The prompt still
states:

- unknown battle state fields must remain unknown
- hidden items must not be inferred
- EV/IV/nature must not be inferred
- boosts/status/weather/terrain/hazards/screens/room must not be inferred unless
  explicit
- damage/KO context must not be used for reverse inference
- battle state is not a resolved turn simulation
- post-turn HP, item consumption, RNG result, speed tie result, Quick Claw
  activation, and full turn outcome must not be claimed

## Mocked Response Safety

The mocked response acknowledges known user-confirmed items as context only and
does not claim:

- item consumption
- item activation result
- post-turn HP
- RNG resolution
- speed tie resolution
- Quick Claw activation
- full turn outcome
- opponent selected move certainty
- hidden item inference

## No UI Integration

v11.7 does not connect `include_user_confirmed_items=True` to the existing UI
checkbox path. It does not change `MainWindow`, `LLMAdviceWorker`,
`run_ui_selected_advice(...)`, payload builder call flow, UI behavior, or UI
copy.

## No Actual Gemini Call

No actual Gemini, Vertex AI, provider retry, second provider call, or network
call was executed.

## Tests

- `tests/test_advisor_payload_contract.py`
  - `test_user_confirmed_item_battle_state_offline_prompt_fixture`

The fixture monkeypatches `call_gemini` and `_log_advisor_call`, captures the
prompt, verifies payload/prompt/guard boundaries, and checks mocked response
safety.

## Next Recommendation

Recommended next: v11.8 User-confirmed Item UI Mapping Design.

Before enabling item opt-in in the runtime UI-selected path, design when the
existing limited-context checkbox should pass `include_user_confirmed_items=True`
and which user-facing copy or guard coverage is needed.
