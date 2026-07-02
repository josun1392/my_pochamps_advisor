# v12.4 Field State Contract Tests

## Purpose

Lock the field-state source contract for `battle_state_context.field` before any helper expansion, UI integration, battle log parser, prompt fixture, or provider smoke work.

This milestone covers:

- default unknown field behavior
- allowed field source preservation
- forbidden field source normalization/rejection
- side-specific screens/hazards value behavior
- duration/expiration/post-turn guardrails
- damage/KO context non-mutation

## Contract Scope

Field keys under contract:

- `weather`
- `terrain`
- `screens`
- `hazards`
- `room`

Known field values are current context only. They do not imply duration, expiration, post-turn state, damage precision, turn order, item activation, item consumption, RNG resolution, Quick Claw activation, or full outcome.

## Helper Behavior

Helper layer behavior is locked in `tests/test_advisor_battle_state_context.py`:

- default field remains explicit unknown
- `user_confirmed` weather is preserved
- `explicit_input` weather is preserved
- `user_confirmed` terrain is preserved
- `explicit_input` terrain is preserved
- `user_confirmed` room is preserved
- `explicit_input` room is preserved
- `user_confirmed` screens/hazards values are preserved
- `explicit_input` screens/hazards values are preserved
- forbidden field sources normalize to unknown
- known field values do not create duration, expiration, or post-turn fields

## Payload Behavior

Payload adapter behavior is locked in `tests/test_advisor_payload_contract.py`:

- payload accepts `user_confirmed` field sources
- payload accepts `explicit_input` field sources
- payload accepts side-specific screens/hazards values inside the existing known envelope
- payload rejects forbidden field sources
- payload rejects `context_derived` field sources
- payload rejects `calculated_from_visible` field sources
- known fields do not mutate `damage_estimate`
- known fields do not mutate `ko_context`
- known fields do not create duration, expiration, or post-turn fields

## Allowed Field Sources

Allowed field sources in v12.4:

- `explicit_input`
- `user_confirmed`

This is intentionally narrower than the general battle-state source set. `visible_ui` remains future-only until a real field-state UI source exists.

## Forbidden Field Sources

Known field state must not be created from:

- `visible_ui`
- `calculated_from_visible`
- `context_derived`
- `damage_reverse`
- `damage_reverse_inference`
- `ko_context`
- `turn_order_context`
- `opponent_move_context`
- `species_common_meta`
- `species_common_set`
- `item_inferred_effect`
- `legality_gate`
- `legality_gate_guess`
- `resist_berry_context`
- `resist_berry_inferred`
- `hidden_guess`
- `hidden_state_guess`
- `model_guess`

Helper policy:

- forbidden field sources normalize to unknown

Payload policy:

- directly injected forbidden field sources are rejected

## Tested Field Keys

All field keys are covered:

- `weather`
- `terrain`
- `screens`
- `hazards`
- `room`

## Side-specific Screens/Hazards Behavior

v12.4 keeps the existing field shape:

```python
"screens": {
    "known": True,
    "source": "user_confirmed",
    "value": {"self": ["reflect"], "opponent": ["light_screen"]},
}
```

```python
"hazards": {
    "known": True,
    "source": "explicit_input",
    "value": {"self": [], "opponent": ["stealth_rock"]},
}
```

The tests intentionally preserve side-specific values inside the existing known-value envelope rather than changing the top-level field shape.

## Safety Boundary

Locked boundaries:

- known field is current context only
- known field does not create duration fields
- known field does not create expiration fields
- known field does not create post-turn outcome fields
- known field does not modify `damage_estimate`
- known field does not modify `ko_context`
- no field inference from damage or KO context
- no field inference from turn order or opponent move context
- no field inference from species/common/meta
- no field inference from item effects, legality gate, or resist berry context
- no hidden/model field guess

## Tests Added

Test locations:

- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`

Focused additions:

- helper field source preservation tests
- helper forbidden source normalization tests
- helper duration/expiration/post-turn guard test
- payload field source acceptance tests
- payload forbidden source rejection tests
- payload damage/KO non-mutation test
- field-specific source contract assertion helper

## No UI Integration

No UI field controls, checkbox changes, UI copy changes, or runtime UI mapping changes are added.

## No Actual Gemini Call

No actual Gemini, retry, second provider, Vertex AI, network, or provider call is executed in v12.4.

## Next Recommendation

Recommended next:

- v12.5 Field State Helper

Reason:

- The contract is now locked enough to extend field helper normalization in the next milestone without changing UI integration or provider behavior.

Alternatives:

- v12.5 Field State Prompt/Offline Fixture
- v12.5 Item Activation/Consumption Boundary Design
