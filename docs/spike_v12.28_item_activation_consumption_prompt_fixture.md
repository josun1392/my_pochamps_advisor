# v12.28 Item Activation / Consumption Prompt Fixture

## Purpose

Verify offline that known user-confirmed items remain current context at the
prompt and mocked-response boundary, without being overclaimed as activation,
consumption, resolved item effects, or post-turn item state.

This step uses mocked provider responses only. No actual Gemini call, network
call, retry, second provider call, or Vertex AI call was made.

## Prompt Fixture

Primary test location:

- `tests/test_advisor_payload_contract.py`

New fixture:

- `test_item_activation_consumption_prompt_fixture_uses_mocked_provider_only`

The fixture builds prompts through `_build_ui_selected_prompt(...)`, captures the
serialized payload, routes provider calls through a monkeypatched
`advisor_client.call_gemini`, and logs usage through a monkeypatched
`advisor_client._log_advisor_call`.

Provider call count:

- mocked provider calls: 3
- actual Gemini calls: 0
- retry count: 0
- second provider calls: 0
- Vertex AI calls: 0

## Fixture Items

The fixture covers these item pairs:

- self `leftovers`, opponent `choice-scarf`
- self `focus-sash`, opponent `quick-claw`
- self `sitrus-berry`, opponent `yache-berry`

Together with the existing v12.27 contract tests, this covers the requested
Leftovers, Choice Scarf, Focus Sash, Berry, and Quick Claw boundaries.

Each item remains serialized as:

```json
{"known": true, "source": "user_confirmed", "value": "<item-id>"}
```

## Prompt Expectations

Allowed in generated prompt/payload:

- known item names
- `user_confirmed` item source
- current item context
- existing safety guard wording that says activation/consumption are not
  resolved
- field-state current context
- existing optional contexts when explicitly enabled

Forbidden in generated prompt/payload:

- `item_activated`
- `item_consumed`
- `resolved_item_effect`
- `post_turn_item_state`
- `post_turn_hp_from_item`
- `quick_claw_activated`
- `focus_sash_triggered`
- `berry_consumed`
- `recovery_applied`
- `damage_reduction_applied`
- `rng_roll`
- `speed_order_override`
- `post_hit_hp_1`

The prompt check targets positive overclaim phrases. Existing guard text may
still mention item consumption, post-turn HP, RNG, or Quick Claw activation as
things the model must not claim.

## Mocked Response Safety

Safe mocked response:

```text
Known items can matter strategically, but no item activation or consumption is
confirmed from the current context. Focus Sash and Quick Claw may matter if
their conditions occur, but their activation is not resolved here.
```

The response safety helper rejects these forbidden phrases:

- `Focus Sash activated`
- `Focus Sash was consumed`
- `Quick Claw activated`
- `Berry was consumed`
- `Leftovers recovered HP this turn`
- `post-turn HP is`
- `exact damage changed by item`

The safe mocked response passes because it uses non-resolved, current-context
wording.

## Coexistence Checks

The fixture enables and verifies coexistence with:

- user-confirmed item context
- `battle_state_context.field`
- `turn_pipeline`
- `turn_order_context`
- `opponent_move_context`

Boundary checks:

- field state does not become an item activation source
- turn-order context does not become a Quick Claw activation source
- opponent-move context does not become an item consumption source
- damage/KO context does not become a Focus Sash trigger source
- known item values serialize without item-event fields

## Tests

Executed:

- `uv run pytest tests/test_advisor_payload_contract.py -q`
- `uv run pytest tests/test_advisor_battle_state_context.py -q`
- `uv run pytest -q`

## Non-Goals

v12.28 does not implement:

- item activation
- item consumption
- resolved item effects
- post-turn item state
- post-turn HP calculation
- damage formula changes
- `damage_estimate` changes
- `ko_context` changes
- Q12 multiplier changes
- raw damage roll changes
- full Turn Engine
- resolved turn order
- RNG resolver
- speed tie resolver
- Quick Claw activation resolution
- hidden item inference
- opponent set/item inference
- prompt guard wording changes
- provider calls

## Next Recommendation

Recommended next:

- v12.29 Item Activation/Consumption Phase Closure

Reason:

- v12.26 documented the boundary
- v12.27 locked payload/battle-state contracts
- v12.28 locked prompt and mocked response behavior offline
- the item activation/consumption boundary phase is ready to close

Alternatives:

- v12.29 Item Event Source Inventory
- v12.29 Status/Condition Source Design
