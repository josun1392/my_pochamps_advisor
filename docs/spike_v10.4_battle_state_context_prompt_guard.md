# v10.4 Battle State Context Prompt Guard

## Purpose

Add prompt guard wording for payloads that include top-level `battle_state_context`.

The guard keeps `battle_state_context` limited to visible or explicit state snapshot context and prevents hidden-state inference, damage/KO reverse inference, and resolved turn simulation claims.

This milestone adds only prompt guard integration:

- no UI/source integration
- no UI checkbox behavior change
- no actual Gemini or Vertex AI call
- no hidden-state inference
- no full Turn Engine

## Absent Behavior

When `battle_state_context` is absent from the advice payload:

- no `battle_state_context` serialized block appears in the prompt
- no `battle_state_context` prompt guard appears
- existing prompt behavior is preserved

## Present Behavior

When a valid non-empty `battle_state_context` is explicitly inserted into the payload:

- serialized `battle_state_context` appears in the prompt JSON
- `_build_battle_state_context_prompt_guard(...)` adds guard wording
- unknown fields must remain unknown
- hidden-state inference is forbidden
- damage/KO reverse inference is forbidden
- resolved turn simulation claims are forbidden

## Placement

The prompt guard follows existing optional context guard order:

1. `turn_snapshot`
2. `turn_pipeline`
3. `turn_order_context`
4. `opponent_move_context`
5. `battle_state_context`

## Guard Wording

The guard anchors:

- `If battle_state_context is present`
- `Unknown battle state fields must remain unknown.`
- `Do not infer hidden items.`
- `Do not infer EVs, IVs, or nature.`
- `Do not infer boosts, status, weather, terrain, hazards, screens, or room unless explicitly provided.`
- `Do not reverse-engineer hidden state from damage estimates or KO context.`
- `not a resolved turn simulation`
- `Do not claim post-turn HP, item consumption, RNG result, speed tie result, Quick Claw activation, or full turn outcome`

## Hidden Inference Boundary

The guard forbids inferring:

- hidden items
- EVs
- IVs
- nature
- boosts
- status
- weather
- terrain
- hazards
- screens
- room

unless explicitly provided in `battle_state_context`.

## Reverse Inference Boundary

`damage_estimate` and `ko_context` remain limited calculation contexts. They must not be used to reverse-engineer hidden item, EV/IV/nature, boosts, status, field state, or other hidden battle state.

## Resolved Simulation Boundary

`battle_state_context` is not a resolved turn simulation. The guard forbids claiming:

- post-turn HP
- item consumption
- RNG result
- speed tie result
- Quick Claw activation
- full turn outcome

## Coexistence

The guard coexists with:

- `turn_pipeline` guard
- `turn_order_context` guard
- `opponent_move_context` guard

Each guard remains independently default-off and present only when the related top-level context is present.

## Tests

Implemented in `tests/test_advisor_payload_contract.py`:

- absent payload has no `battle_state_context` guard
- present payload serializes `battle_state_context`
- present payload includes guard wording
- unknown field guard anchor
- hidden item / EV / IV / nature guard anchors
- boost/status/weather/terrain/hazards/screens/room guard anchor
- damage/KO reverse inference guard anchor
- resolved simulation guard anchor
- post-turn HP / item consumption / RNG / speed tie / Quick Claw / full outcome guard anchor
- forbidden positive phrase absence
- coexistence with `turn_pipeline`, `turn_order_context`, and `opponent_move_context`
- prompt guard creation does not call provider

## Next Recommendation

Recommended:

- v10.5 Battle State Context Offline Advice Fixture

Reason:

- The next safe step is verifying mocked advice flow preserves `battle_state_context` payload and prompt guard without provider calls.

Alternatives:

- v10.5 Battle State UI Source Inventory
- v10.5 Battle State UI Integration Design

Do not run an actual Gemini call yet.
