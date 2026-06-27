# v10.0 Battle State Context Design

## Purpose

Design a future `battle_state_context` before any implementation.

The context should give the LLM a bounded view of visible or explicit battle state while preventing hidden-state inference. It is a state-boundary context, not a turn simulator, damage calculator, or reverse-inference engine.

This milestone is design-only:

- no production code change
- no payload adapter
- no prompt guard implementation
- no UI behavior change
- no actual Gemini or Vertex AI call
- no full Turn Engine

## Problem

The current advisor payload can expose several partial contexts:

- `damage_estimate`: selected move damage under stated assumptions
- `ko_context`: limited KO probability/threshold context
- `turn_pipeline`: limited candidate turn events
- `turn_order_context`: limited turn-order helper context
- `opponent_move_context`: UI-visible or possible opponent move context

None of these is a unified battle-state snapshot. The LLM can see pieces of state, but there is no single explicit boundary for:

- current visible HP state
- known item state
- known status conditions
- known stat boosts
- weather, terrain, screens, hazards, and room effects
- what is explicit, visible, unknown, unsupported, or deliberately absent

`battle_state_context` should fill that gap without encouraging hidden state inference.

## Proposed Top-Level Shape

Initial contract proposal:

```python
battle_state_context = {
    "kind": "battle_state_context",
    "confidence": "limited",
    "self_active": {
        "species": {"known": True, "value": "charizard", "source": "visible_ui"},
        "current_hp_percent": {"known": True, "value": 100, "source": "visible_ui"},
        "status": {"known": False, "value": "unknown"},
        "boosts": {"known": False, "value": "unknown"},
        "item": {"known": False, "value": "unknown"},
    },
    "opponent_active": {
        "species": {"known": True, "value": "garchomp", "source": "visible_ui"},
        "current_hp_percent": {"known": True, "value": 100, "source": "visible_ui"},
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
        "Do not infer hidden state from species, common sets, usage, damage, or KO context.",
        "This context is a visible/explicit state snapshot, not a resolved turn simulation.",
    ],
}
```

Design notes:

- Field values should use a `{known, value, source}` envelope when known.
- Unknown fields should use `{"known": False, "value": "unknown"}`.
- The first contract should prefer omission or unknown over weak guesses.
- Do not include future-dated post-turn values.

## Confidence Policy

Recommended initial values:

- `unknown`: no usable visible or explicit battle state beyond baseline payload identity.
- `limited`: species and/or visible HP are available, or a small number of explicit state fields are available.

Deferred values:

- `partial`: possible future value when several explicit state fields are present but not enough for a complete battle state.
- `explicit`: possible future value only after a trusted UI/source path can provide most state fields explicitly.

Initial recommendation: implement only `unknown` and `limited` in v10.1. Avoid `explicit` until the source path is real and tested.

## Source Policy

Allowed sources:

- `visible_ui`: state directly visible in the current UI.
- `explicit_input`: state explicitly entered by the user.
- `user_confirmed`: state explicitly confirmed by the user.
- `calculated_from_visible`: deterministic normalization from visible UI state, such as percent formatting.

Context-only references, not hidden-state sources:

- `damage_estimate`
- `ko_context`
- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`

Forbidden sources:

- `species_common_set`
- `usage_based_guess`
- `meta_inferred`
- `hidden_state_guess`
- `damage_reverse_inference`

Rules:

- Do not infer hidden item, EVs, IVs, nature, defensive investment, boosts, weather, terrain, screens, hazards, room effects, or status from `damage_estimate`.
- Do not infer field state from species, common sets, or usage trends.
- Do not infer status or boosts from move choice, matchup, or KO context.
- Do not create battle-state facts from `turn_pipeline`, `turn_order_context`, or `opponent_move_context`.

## Field Categories

### `self_active`

Allowed:

- species from visible UI
- current HP percent from visible UI
- user-confirmed item/status/boosts if a future explicit source exists

Default when unknown:

- `{"known": False, "value": "unknown"}`

Forbidden inference:

- EV/IV/nature
- hidden item
- unobserved boosts
- unobserved status
- post-turn HP

Future extension:

- current HP absolute value if the UI has a trusted source
- explicit status selector
- explicit stat-stage/boost selector
- explicit item-confirmation path

### `opponent_active`

Allowed:

- species from visible UI
- current HP percent from visible UI
- explicit/user-confirmed item/status/boosts if future UI source exists

Default when unknown:

- `{"known": False, "value": "unknown"}`

Forbidden inference:

- hidden item from damage numbers
- defensive investment from damage rolls
- common-set item/status/boost inference
- selected move or hidden moveset inference

Future extension:

- explicit opponent status/boost/item controls
- explicit visible ability/item state if added to UI

### `field`

Allowed:

- weather, terrain, screens, hazards, and room effects only when visible or explicitly selected.

Default when unknown:

- `{"known": False, "value": "unknown"}`

Forbidden inference:

- weather from species, ability expectations, team archetype, or move damage.
- terrain from species/common team style.
- hazards/screens from matchup assumptions.
- Trick Room/Tailwind from speed relation alone.

Future extension:

- UI controls for weather, terrain, screens, hazards, room, Tailwind, and side conditions.

### `known_conditions`

Allowed:

- small list of normalized visible or explicit conditions that do not fit active Pokemon or field sections.

Default when unknown:

- empty list

Forbidden inference:

- any condition derived from meta assumptions, common sets, usage, or reverse damage inference.

Future extension:

- explicit source-tagged side conditions and volatile conditions.

### `unsupported`

Required boundaries:

- hidden item inference
- EV/IV/nature inference
- unobserved boosts inference
- unobserved status inference
- weather/terrain inference without explicit source
- hazards/screens inference without explicit source
- damage reverse inference
- RNG resolution
- item consumption
- post-turn HP resolution
- full turn resolution

### `safety_notes`

Required message:

- unknown fields remain unknown
- visible/explicit state only
- no hidden-state inference
- not a full turn simulation

## Relationship With Existing Contexts

### `damage_estimate`

`damage_estimate` remains a damage candidate under an `assumption_profile`. It is not a source for hidden item, EV/IV/nature, defensive investment, boosts, weather, terrain, screens, hazards, or status. `battle_state_context` must not reverse-engineer hidden battle state from damage.

### `ko_context`

`ko_context` remains limited damage-roll KO context. It is not final battle truth, not post-turn HP, and not a source for field state or hidden state.

### `turn_pipeline`

`turn_pipeline` remains candidate turn-event context. It is not a resolved event log and must not produce item consumption, RNG results, exact trigger outcomes, or post-turn HP for `battle_state_context`.

### `turn_order_context`

`turn_order_context` remains turn-order helper context. It is not a final move order, speed tie resolution, RNG item activation result, or field-state source.

### `opponent_move_context`

`opponent_move_context` remains opponent move fact/candidate context. It is not a selected move inference, hidden moveset inference, opponent set inference, or state source for item/status/boost/field assumptions.

### `battle_state_context`

`battle_state_context` should be a visible/explicit state snapshot. It should describe what is known and what is unknown. It should not resolve the turn, infer hidden state, or override the existing damage/KO/turn contexts.

## Future Prompt Guard Needs

A future prompt guard should say:

- Unknown state fields must remain unknown.
- Do not infer hidden item, EVs, IVs, nature, boosts, status, weather, terrain, hazards, screens, or room effects unless explicitly provided.
- Do not reverse-engineer hidden state from `damage_estimate` or `ko_context`.
- Do not treat `battle_state_context` as a resolved turn simulation.
- Do not claim post-turn HP, item consumption, RNG result, speed tie result, exact final order, or full turn outcome.
- If a state is unknown, mention it as unknown only when relevant; do not fill it with common-set or meta assumptions.

## Excluded Fields For Initial Contract

Do not include:

- final post-turn HP
- consumed item state
- resolved RNG results
- speed tie resolution
- exact final move order
- hidden items
- inferred EV/IV/nature
- inferred boosts or status
- inferred weather, terrain, hazards, screens, or room effects
- opponent set or hidden moveset
- selected opponent move inference
- full simulation output

## Implementation Plan

Recommended sequence:

1. v10.1 Battle State Context Payload Contract
   - Add fixture-level shape tests for a future optional top-level `battle_state_context`.
   - Validate allowed values, unknown envelopes, source policy, unsupported boundaries, and forbidden fields.
   - Do not add runtime adapter or UI extraction yet.

2. v10.2 Battle State Context Helper
   - Add a standalone helper that accepts explicit caller-provided state only.
   - Preserve unknown defaults.
   - Reject forbidden hidden/resolved fields.

3. v10.3 Payload Adapter
   - Add explicit/default-off `build_ui_advice_payload(..., battle_state_context=..., enable_battle_state_context=True)`.
   - Omit empty/unknown-only context if that matches the established optional-context policy.

4. v10.4 Prompt Guard
   - Add a guard only when top-level `battle_state_context` exists.

5. v10.5 UI/source design
   - Inventory what current UI can actually provide.
   - Avoid enabling state fields that do not have explicit source.

## Next Recommendation

Recommended:

- v10.1 Battle State Context Payload Contract

Fallback:

- v10.1 Battle State Context Source Inventory, if T2 determines that UI/source availability is too unclear for a contract-first step.

Alternative:

- v10.1 Battle State Prompt Guard Design

Conclusion:

- Start with a fixture-level contract if possible.
- Do not run an actual Gemini call.
- Do not implement `battle_state_context` runtime behavior yet.
