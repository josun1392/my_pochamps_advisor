# v12.5 Field State Helper

## Purpose

Extend `battle_state_context.field` helper normalization to match the v12.4 contract tests without adding UI integration, battle log/parser support, prompt guard wording changes, payload builder call-flow changes, or provider calls.

This milestone keeps field state as current context only. Known weather, terrain, screens, hazards, or room values do not imply duration, expiration, post-turn state, damage precision, turn order, item activation, item consumption, RNG resolution, Quick Claw activation, or full outcome.

## Helper Changes

`llm/advisor_battle_state_context.py` now normalizes field entries by field key:

- `weather`
- `terrain`
- `screens`
- `hazards`
- `room`

The helper preserves known field envelopes only when the field source is allowed and the value shape is valid for the field key. Otherwise, the field entry normalizes to:

```python
{"known": False, "value": "unknown"}
```

## Allowed Field Sources

Known field source allowlist:

- `explicit_input`
- `user_confirmed`

Known field envelope:

```python
{"known": True, "source": "user_confirmed", "value": "<field-state>"}
```

or:

```python
{"known": True, "source": "explicit_input", "value": "<field-state>"}
```

## Forbidden Field Sources

The helper does not preserve known field values from:

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

Forbidden source policy:

- helper layer: normalize to unknown
- direct payload layer: reject as invalid battle-state context

## Malformed Input Behavior

Malformed helper inputs normalize to unknown. Covered malformed cases include:

- non-mapping field entry
- `known=False` with a non-unknown value
- missing source
- missing value
- empty or invalid scalar field values
- forbidden source
- malformed screens/hazards side-specific values
- screens/hazards with no known side-specific condition

Direct payload validation rejects malformed known field envelopes rather than accepting them.

## Screens/Hazards Behavior

`screens` and `hazards` keep the existing known envelope and store side-specific state inside `value`:

```python
{
    "known": True,
    "source": "user_confirmed",
    "value": {"self": ["reflect"], "opponent": "unknown"},
}
```

```python
{
    "known": True,
    "source": "explicit_input",
    "value": {"self": "unknown", "opponent": ["stealth_rock"]},
}
```

Allowed side keys:

- `self`
- `opponent`

Allowed side values:

- list of non-empty condition strings
- `"unknown"`

At least one side must contain a known condition string for the field to remain known.

## Preserved Behavior

Unchanged behavior:

- default field state remains unknown
- species/HP `visible_ui` behavior remains unchanged
- user-confirmed item behavior remains unchanged
- limited-context checkbox behavior remains unchanged
- payload builder call flow remains unchanged
- prompt guard wording remains unchanged
- UI behavior/copy/default remain unchanged
- no battle log/parser source is added

## Safety Boundary

Known field context remains limited:

- known field is current context only
- known field does not imply duration accuracy
- known field does not imply expiration timing
- known field does not imply post-turn state
- known field does not imply damage precision
- known field does not mutate `damage_estimate`
- known field does not mutate `ko_context`
- no field inference from damage or KO context
- no field inference from turn order or opponent move context
- no field inference from species/common/meta
- no field inference from item effects, legality gate, or resist berry context
- no hidden/model field guess

## Tests

Updated tests:

- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`

Coverage:

- helper preserves `user_confirmed` and `explicit_input` weather
- helper preserves `user_confirmed` and `explicit_input` terrain
- helper preserves `user_confirmed` and `explicit_input` room
- helper preserves side-specific screens/hazards values
- helper preserves side-specific unknown markers
- helper normalizes forbidden field sources to unknown
- helper normalizes malformed field values to unknown
- payload adapter rejects malformed direct known field values
- known fields do not create duration, expiration, or post-turn fields
- known fields do not change `damage_estimate` or `ko_context`

## No UI Integration

No UI field controls, checkbox changes, UI copy changes, source adapter connections, or runtime UI mapping changes are added.

## No Actual Gemini Call

No actual Gemini, retry, second provider, Vertex AI, network, or provider call is executed in v12.5.

## Next Recommendation

Recommended next:

- v12.6 Field State Prompt/Offline Fixture

Reason:

- Helper and contract normalization are now aligned. The next safe step is a mocked prompt fixture proving known field context serializes safely without implying duration, expiration, post-turn outcomes, damage precision, or resolved battle state.

Alternatives:

- v12.6 Field State UI Source Inventory
- v12.6 Item Activation/Consumption Boundary Design
