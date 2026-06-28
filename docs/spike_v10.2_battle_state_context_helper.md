# v10.2 Battle State Context Helper

## Purpose

Add a standalone helper that normalizes visible or explicit battle-state facts into the v10.1 `battle_state_context` contract shape.

This milestone adds only the helper and tests:

- no payload adapter
- no prompt guard implementation
- no UI/source integration
- no actual Gemini or Vertex AI call
- no hidden-state inference
- no full Turn Engine

## Helper Location

`llm/advisor_battle_state_context.py`

Primary API:

```python
build_battle_state_context(
    self_active=None,
    opponent_active=None,
    field=None,
    known_conditions=None,
)
```

## Input

The helper accepts caller-provided source-tagged dictionaries:

```python
self_active = {
    "species": {"source": "visible_ui", "name": "Garchomp"},
    "current_hp_percent": {"source": "visible_ui", "value": 100},
    "status": {"source": "explicit_input", "value": "burn"},
    "boosts": {"source": "explicit_input", "value": {"atk": 1}},
    "item": {"source": "user_confirmed", "value": "loaded-dice"},
}
```

```python
field = {
    "weather": {"source": "explicit_input", "value": "rain"},
    "terrain": {"source": "explicit_input", "value": "electric"},
    "screens": {"source": "explicit_input", "value": {"reflect": True}},
    "hazards": {"source": "explicit_input", "value": {"stealth_rock": True}},
    "room": {"source": "explicit_input", "value": {"trick_room": False}},
}
```

Inputs are not inferred from species, damage, KO context, common sets, or meta usage.

## Output

The helper returns:

- `kind == "battle_state_context"`
- `confidence`
- `self_active`
- `opponent_active`
- `field`
- `known_conditions`
- `unsupported`
- `safety_notes`

Missing or rejected values use:

```python
{"known": False, "value": "unknown"}
```

Known non-species values use:

```python
{"known": True, "source": "explicit_input", "value": "..."}
```

`species` and `current_hp_percent` keep the v10.1 source-tagged shape when present:

```python
{"source": "visible_ui", "name": "Garchomp"}
{"source": "visible_ui", "value": 100}
```

## Confidence Policy

- no accepted visible or explicit source: `unknown`
- at least one accepted visible or explicit source: `limited`
- never emits `partial`
- never emits `explicit`

## Source Policy

Allowed sources:

- `visible_ui`
- `explicit_input`
- `user_confirmed`
- `calculated_from_visible`

Forbidden sources become unknown or are omitted:

- `species_common_set`
- `usage_based_guess`
- `meta_inferred`
- `hidden_state_guess`
- `damage_reverse_inference`

## Active Fields

Both `self_active` and `opponent_active` always contain:

- `species`
- `current_hp_percent`
- `status`
- `boosts`
- `item`

Absent or rejected values stay explicit unknowns.

## Field Fields

`field` always contains:

- `weather`
- `terrain`
- `screens`
- `hazards`
- `room`

Absent or rejected values stay explicit unknowns.

## Forbidden Fields

The helper never outputs hidden or resolved fields such as:

- `EVs`
- `IVs`
- `nature`
- `hidden_item`
- inferred, predicted, or likely item/boost/status/weather/terrain
- `damage_reverse_inferred`
- `post_turn_hp`
- `item_consumed`
- `rng_resolved`
- `speed_tie_resolved`
- `quick_claw_activated`
- `full_turn_result`
- `resolved_outcome`

## Relationship Boundaries

The helper does not use these contexts as hidden-state sources:

- `damage_estimate`
- `ko_context`
- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`

They remain independent context surfaces and do not create hidden item, EV/IV/nature, status, boosts, field state, RNG, item consumption, post-turn HP, or resolved outcomes.

## Tests

Implemented in `tests/test_advisor_battle_state_context.py`:

- empty input returns `confidence == "unknown"`
- visible species and HP return `confidence == "limited"`
- required active and field keys are always present
- missing active and field values become explicit unknowns
- explicit status, boosts, item, weather, terrain, screens, hazards, and room are represented as known values
- forbidden sources become unknown or are omitted
- confidence never becomes `partial` or `explicit`
- forbidden fields are absent recursively
- damage and KO context are not used for hidden-state inference
- species/common set or meta sources do not generate hidden state
- unsupported boundaries and safety notes are included

## Next Recommendation

Recommended:

- v10.3 Battle State Context Payload Adapter

Alternative:

- v10.3 Battle State Prompt Guard

Fallback:

- v10.3 Battle State Source Inventory, if the helper input shape needs tighter alignment with real UI/source availability before adapter work.

Do not run an actual Gemini call yet.
