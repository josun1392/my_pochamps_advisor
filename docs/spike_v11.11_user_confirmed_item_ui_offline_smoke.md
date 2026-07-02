# v11.11 User-confirmed Item UI Offline Smoke

## Purpose

Verify the UI-selected limited-context path for user-confirmed battle-state items with a mocked provider only. This smoke covers checkbox off/on behavior, prompt serialization, guard preservation, malformed/forbidden item metadata handling, and coexistence with the existing optional contexts.

## Fixture Summary

The smoke uses the UI-selected advice flow fixture with:

- self: `Garchomp`, HP `100`
- opponent: `Charizard`, HP `87`
- self item profile: `status=user_confirmed`, `source=user_input`, `item_id=leftovers`
- opponent item profile: `status=user_confirmed`, `source=user_input`, `item_id=choice-scarf`
- limited-context checkbox off and on cases
- mocked `call_gemini` and mocked token logging

## Checkbox Off Behavior

PASS:

- `battle_state_context` is omitted from payload.
- serialized `battle_state_context` is omitted from prompt.
- battle-state known item envelopes for `leftovers` and `choice-scarf` are absent.
- the battle-state prompt guard is absent.
- toggling the checkbox alone does not call the provider.

## Checkbox On Behavior

PASS:

- `battle_state_context` is included in payload and prompt.
- self species/HP are preserved as `visible_ui`.
- opponent species/HP are preserved as `visible_ui`.
- self item is preserved as `{"known": True, "source": "user_confirmed", "value": "leftovers"}`.
- opponent item is preserved as `{"known": True, "source": "user_confirmed", "value": "choice-scarf"}`.
- known item values appear in the serialized prompt.
- field values remain unknown.
- `known_conditions` remains `[]`.

## Malformed/Forbidden Item Behavior

PASS:

- checkbox on still includes `battle_state_context`.
- species/HP `visible_ui` values remain present.
- missing `item_id` keeps self item unknown.
- forbidden `context_derived` source keeps opponent item unknown.
- known item value envelopes are absent from the prompt.

## Prompt Behavior

PASS:

- serialized `battle_state_context` appears only when the checkbox is on.
- known user-confirmed item envelopes appear only for valid metadata.
- known item context does not create post-turn, item consumption, RNG, speed tie, Quick Claw, full result, or resolved outcome fields.

## Guard Behavior

PASS:

- the existing `battle_state_context` guard appears when context is present.
- the smoke keeps the existing guard wording unchanged.
- the guard continues to forbid post-turn HP, item consumption, RNG result, speed tie result, Quick Claw activation, and full turn outcome claims.

## Mocked Response Safety

PASS:

- mocked response uses safe wording that treats user-confirmed items as known context only.
- mocked response avoids item activation certainty, item consumption certainty, post-turn HP certainty, RNG resolution, speed tie resolution, Quick Claw activation certainty, selected opponent move certainty, hidden item inference, and full outcome certainty.

## Coexistence With Existing Contexts

PASS:

- `turn_pipeline` remains included in the checkbox-on path.
- `turn_order_context` remains included in the checkbox-on path.
- `opponent_move_context` remains included in the checkbox-on path.
- existing optional-context coexistence remains green.

## No Actual Gemini Call

No actual Gemini, Vertex AI, provider, or network call was made. The provider path was fully monkeypatched.

## Tests

Updated `tests/test_ui_turn_pipeline_flag_flow.py`:

- `test_user_confirmed_item_ui_offline_smoke_covers_checkbox_matrix`

The test covers:

- checkbox off + user-confirmed item profiles
- checkbox on + user-confirmed item profiles
- checkbox on + malformed/forbidden item profiles
- mocked provider only
- guard and prompt boundaries
- existing context coexistence

## Next Recommendation

Recommended next:

- v11.12 User-confirmed Item Phase Closure

Alternatives:

- v11.12 Controlled User-confirmed Item Gemini Smoke Design
- v11.12 Field State Source Design
