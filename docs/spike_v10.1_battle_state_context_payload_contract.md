# v10.1 Battle State Context Payload Contract

## Purpose

Lock the future optional top-level `battle_state_context` shape at fixture/test level before any helper, adapter, prompt guard, or UI/source integration exists.

This milestone is contract-only:

- no production helper
- no payload adapter
- no prompt guard implementation
- no UI/source integration
- no actual Gemini or Vertex AI call
- no hidden-state inference
- no full Turn Engine

## Contract Shape

The fixture-level contract uses:

```python
battle_state_context = {
    "kind": "battle_state_context",
    "confidence": "limited",
    "self_active": {
        "species": {"source": "visible_ui", "name": "Garchomp"},
        "current_hp_percent": {"source": "visible_ui", "value": 100},
        "status": {"known": False, "value": "unknown"},
        "boosts": {"known": False, "value": "unknown"},
        "item": {"known": False, "value": "unknown"},
    },
    "opponent_active": {
        "species": {"source": "visible_ui", "name": "Charizard"},
        "current_hp_percent": {"source": "visible_ui", "value": 100},
        "status": {"known": False, "value": "unknown"},
        "boosts": {"known": False, "value": "unknown"},
        "item": {"known": False, "value": "unknown"},
    },
    "field": {
        "weather": {"known": False, "value": "unknown"},
        "terrain": {"known": False, "value": "unknown"},
        "screens": {"known": False, "value": "unknown"},
        "hazards": {"known": False, "value": "unknown"},
        "room": {"known": False, "value": "unknown"},
    },
    "known_conditions": [],
    "unsupported": [
        "hidden item inference",
        "EV/IV/nature inference",
        "unobserved boosts inference",
        "unobserved status inference",
        "weather/terrain inference without explicit source",
        "hazards/screens inference without explicit source",
        "damage reverse inference",
        "RNG resolution",
        "item consumption",
        "post-turn HP resolution",
        "full turn resolution",
    ],
    "safety_notes": [
        "Unknown battle state fields must remain unknown.",
        "Do not infer hidden state from species, common sets, damage estimates, or KO context.",
        "Battle state context is not a resolved turn simulation.",
    ],
}
```

## Confidence Policy

Allowed in v10.1:

- `unknown`
- `limited`

Rejected in v10.1:

- `partial`
- `explicit`
- resolved or certainty-style values

`partial` and `explicit` remain future candidates only after trusted source paths exist.

## Source Policy

Allowed sources:

- `visible_ui`
- `explicit_input`
- `user_confirmed`
- `calculated_from_visible`

Forbidden sources:

- `species_common_set`
- `usage_based_guess`
- `meta_inferred`
- `hidden_state_guess`
- `damage_reverse_inference`

## Unknown Field Representation

Unknown fields must be explicit:

```python
{"known": False, "value": "unknown"}
```

The contract rejects missing active fields and missing field-state entries. Unknown fields are not replaced with default battle assumptions.

## Forbidden Fields

The contract rejects forbidden hidden or resolved fields recursively, including:

- `EVs`
- `IVs`
- `nature`
- `hidden_item`
- inferred/predicted/likely item, boosts, status, weather, or terrain
- `damage_reverse_inferred`
- `post_turn_hp`
- `item_consumed`
- `rng_resolved`
- `speed_tie_resolved`
- `quick_claw_activated`
- `full_turn_result`
- `resolved_outcome`

## Relationship Boundaries

The fixture tests lock these boundaries:

- `damage_estimate is not a hidden state inference source`
- `ko_context is not a final truth source`
- `turn_pipeline is not a resolved result source`
- `turn_order_context is not a speed tie/RNG/final order source`
- `opponent_move_context is not a selected move/hidden moveset source`
- `battle_state_context is not a resolved turn simulation`

## Tests

Implemented in `tests/test_advisor_payload_contract.py`:

- fixture top-level shape
- `kind == "battle_state_context"`
- confidence allow/reject policy
- required active side fields
- required field-state entries
- unknown field representation
- allowed source handling
- forbidden source rejection
- recursive forbidden field rejection
- required unsupported boundaries
- required safety notes
- relationship boundary anchors

## Next Recommendation

Recommended:

- v10.2 Battle State Context Helper

Fallback:

- v10.2 Battle State Context Source Inventory, if T2 decides current UI/source availability needs a stricter inventory before helper work.

Alternative:

- v10.2 Battle State Prompt Guard Design

Do not run an actual Gemini call yet.
