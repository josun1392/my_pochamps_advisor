# v12.40 Item Event Payload Mapping Implementation

## Purpose

Implement the v12.39 mapping contract so session-local explicit user item event
confirmations reach LLM payloads only through the existing limited context gate.

## Checkbox Off Behavior

- `MainWindow._item_event_confirmations` remains session-local.
- `MainWindow` does not add `item_event_confirmations` to `battle_input`.
- The LLM payload omits `item_event_context`.
- The LLM payload omits `observed_events`.
- No observed item event prompt wording is added.

## Checkbox On Behavior

- `MainWindow` copies session-local confirmations into
  `battle_input["item_event_confirmations"]`.
- The client removes that raw UI input from the provider payload.
- The client normalizes valid entries into:

```yaml
item_event_context:
  observed_events:
    - side: opponent
      item: focus-sash
      event_type: item_activation_observed
      status: user_confirmed
      source: explicit_user_event_confirmation
      confidence: observed
      turn: 5
      note: User saw Focus Sash activation text.
```

- The existing limited context checkbox is the only gate; no new checkbox was
  added.

## MainWindow to Payload Path

```text
MainWindow._item_event_confirmations
-> _build_llm_battle_input(include_item_event_confirmations=True)
-> battle_input["item_event_confirmations"]
-> build_item_event_context_from_confirmations(...)
-> item_event_context.observed_events
-> structured prompt payload
```

When the checkbox is off, the first `battle_input` mapping step is skipped.

## Payload Normalization

- `build_item_event_context_from_confirmations(...)` reuses the explicit user
  item event validator.
- Only observed event types are retained.
- Valid events preserve `side`, `item`, `event_type`, `status`, `source`,
  `turn`, and `note`.
- `confidence=observed` is added.
- Raw `item_event_confirmations` is always removed before provider payload
  serialization.

## Invalid Event Handling

- Invalid individual confirmations are omitted.
- If all confirmations are invalid, `item_event_context` is omitted.
- Invalid entries do not reach `observed_events` or the prompt payload.

## Forbidden Field Handling

The existing validator rejects or strips resolved/post-turn/exact calculation
claims. The normalized context cannot contain:

- resolved item effects
- post-turn item state or HP
- exact HP or damage
- RNG results
- Speed/order overrides

## Known Item and Field State Invariants

- Known current items remain separate user-confirmed current context.
- Known items are not promoted to observed events.
- Existing field state mapping and the limited-context field gate are unchanged.
- `field_profiles` do not become an item event source.

## Prompt Wording

No new natural-language prompt guard or wording fixture was added. The current
prompt builder serializes the normalized structured payload only. Positive
resolved/exact claims were not added.

## Tests

- `uv run pytest tests/test_item_event_payload_mapping_contract.py -q`
- `uv run pytest tests/test_advisor_payload_contract.py -q`
- `uv run pytest tests/test_item_event_button_integration_contract.py -q`
- `uv run pytest tests/test_ui_turn_pipeline_flag_flow.py -q`
- `uv run pytest tests/test_advisor_battle_state_context.py -q`
- `uv run pytest -q`

## Next Recommendation

Recommended next:

- v12.41 Item Event Prompt Fixture

Reason:

- Mapping is now active under the limited context gate. An offline prompt and
  response safety fixture should lock observed-only wording before any actual
  provider smoke work.

## No Actual Gemini Call

- No actual Gemini call was executed.
- No retry was executed.
- No second provider call was executed.
- No Vertex AI call was executed.
- No provider/network call was executed.
