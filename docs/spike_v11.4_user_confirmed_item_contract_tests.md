# v11.4 User-confirmed Item Contract Tests

## Purpose

Lock the `battle_state_context.item` contract/helper boundary before any UI item
integration.

This step adds tests and minimal helper/adapter validation so known item facts
can only come from direct `user_confirmed` or explicitly allowed
`explicit_input` sources. It does not connect item profiles to the UI-selected
`battle_state_context` adapter.

## Allowed Item Sources

Known `battle_state_context.item` values are allowed only for:

- `user_confirmed`
- `explicit_input`

The known item shape remains:

```python
{"known": True, "source": "user_confirmed", "value": "<item-id>"}
```

or:

```python
{"known": True, "source": "explicit_input", "value": "<item-id>"}
```

Unknown item shape remains:

```python
{"known": False, "value": "unknown"}
```

## Forbidden Item Sources

The helper and contract tests prevent the following from becoming known item
facts:

- `visible_ui`
- `calculated_from_visible`
- `species_common_set`
- `usage_based_guess`
- `meta_inferred`
- `hidden_state_guess`
- `damage_reverse_inference`
- `legality_gate_guess`
- `resist_berry_inferred`
- `context_derived`

This keeps item stricter than species/HP. Species/HP may use `visible_ui`, but
item still requires user confirmation or explicit input.

## Helper Behavior

`build_battle_state_context(...)` now uses item-specific source validation for
active-side item fields.

- omitted self item -> unknown
- omitted opponent item -> unknown
- `user_confirmed` item -> known
- `explicit_input` item -> known
- malformed or missing item value -> unknown
- forbidden item source -> unknown
- legality gate or resist berry context alone -> unknown
- known item does not add item consumption, post-turn HP, RNG, speed tie, Quick
  Claw activation, or full outcome fields

The UI-selected adapter still extracts only species/HP and intentionally ignores
`item_profiles`.

## Payload Contract Behavior

Payload contract tests now lock item-specific source policy:

- prebuilt `battle_state_context` with `user_confirmed` item is accepted
- prebuilt `battle_state_context` with `explicit_input` item is accepted
- prebuilt `battle_state_context` with `visible_ui`, `calculated_from_visible`,
  or `context_derived` item source is rejected by the payload adapter
- unknown item shape is preserved
- forbidden hidden/resolved fields remain rejected recursively

## Tests Added

Added/strengthened tests in:

- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`

Coverage includes:

- self/opponent `user_confirmed` known items
- self/opponent `explicit_input` known items
- forbidden item sources becoming unknown in helper output
- malformed item values becoming unknown
- legality gate or resist berry context alone not creating known item
- known item coexisting with species/HP `visible_ui`
- no item consumption or post-turn result fields from known item
- payload adapter preserving allowed known items
- payload adapter rejecting item sources without user confirmation

## No UI Integration

No UI item integration was implemented.

Specifically unchanged:

- `build_battle_state_context_from_ui_selected_state(...)` still ignores
  `item_profiles`
- limited-context checkbox flow is unchanged
- UI copy is unchanged
- prompt guard wording is unchanged

## No Actual Gemini Call

No actual Gemini, retry, Vertex AI, provider, or network call was executed in
v11.4.

## Next Recommendation

Recommended next: `v11.5 User-confirmed Item Source Adapter Design`.

Reason:

- Contract/helper boundaries now identify allowed and forbidden item sources.
- The next safe step is to design how UI item profile data should be converted
  into helper input without connecting it directly yet.

Alternatives:

- `v11.5 User-confirmed Item Prompt/Offline Fixture`
- `v11.5 Field State Source Design`
