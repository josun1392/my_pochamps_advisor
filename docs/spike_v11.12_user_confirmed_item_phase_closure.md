# v11.12 User-confirmed Item Phase Closure

## Purpose

Close the user-confirmed item phase for `battle_state_context`. This closure summarizes the boundary, contract/helper tests, source adapter, prompt/offline fixture, UI mapping, UI copy, and UI-selected offline smoke completed from v11.3 through v11.11.

## Phase Summary

The phase safely extended `battle_state_context.item` from always-unknown UI behavior to a limited user-confirmed item path:

- item values remain unknown by default
- self/opponent item can become known only from trusted user-confirmed metadata
- checkbox off remains a hard gate
- checkbox on can include known user-confirmed item context with existing limited contexts
- known item context does not imply item activation, consumption, post-turn state, RNG, move order resolution, or full turn outcome

## Completed Milestones v11.3-v11.11

- v11.3 User-confirmed Item Boundary Design: defined `user_confirmed` / `explicit_input` item boundaries and rejected hidden, inferred, legality-derived, context-derived, and damage-derived item sources.
- v11.4 User-confirmed Item Contract Tests: locked helper and payload validation so known item sources are limited to `user_confirmed` and `explicit_input`; forbidden item sources remain unknown or are rejected.
- v11.5 User-confirmed Item Source Adapter Design: designed an explicit opt-in adapter path for trusted UI item profile metadata.
- v11.6 User-confirmed Item Source Adapter: added `include_user_confirmed_items=False` default behavior and opt-in parsing of valid `item_profiles`.
- v11.7 User-confirmed Item Prompt/Offline Fixture: verified known user-confirmed items in payload and prompt with mocked provider only.
- v11.8 User-confirmed Item UI Mapping Design: designed checkbox-gated runtime mapping.
- v11.9 User-confirmed Item UI Mapping: connected `include_user_confirmed_items=enable_battle_state_context` in the UI-selected prompt path.
- v11.10 User-confirmed Item UI Copy Update: updated limited-context copy to mention user-confirmed items without hidden/inferred/resolved wording.
- v11.11 User-confirmed Item UI Offline Smoke: verified checkbox off/on, malformed/forbidden metadata, prompt guard, mocked response safety, and coexistence with existing contexts.

## Current Runtime Behavior

- limited context checkbox default off
- checkbox off: `battle_state_context` omitted, therefore item omitted
- checkbox on: `battle_state_context` enabled with other limited contexts
- checkbox on: `include_user_confirmed_items=enable_battle_state_context`
- checkbox on + valid user-confirmed `item_profiles`: known item included
- checkbox on + missing/malformed/forbidden `item_profiles`: item unknown
- species/HP remain `visible_ui`
- field remains unknown
- `known_conditions` remains `[]`

## Current UI Behavior

- the existing checkbox label remains `제한 컨텍스트 포함`
- no new checkbox was added
- checkbox default remains off
- checkbox toggle alone does not call the provider
- enabled copy mentions candidate events, turn-order helper information, opponent move candidates, current Pokemon/HP snapshot, user-confirmed items, and not-confirmed-result semantics

## Current Payload Behavior

Known item envelope:

```json
{"known": true, "source": "user_confirmed", "value": "<item-id>"}
```

Unknown item envelope:

```json
{"known": false, "value": "unknown"}
```

Known item appears only when:

- limited context checkbox is on
- `battle_state_context` is enabled
- item profile metadata is allowed
- `status=user_confirmed`
- `source=user_input`
- `item_id` is non-empty

## Current Prompt Behavior

- checkbox off omits serialized `battle_state_context` and its guard
- checkbox on includes serialized `battle_state_context` and existing guard
- known user-confirmed item envelopes may appear in the serialized prompt
- malformed/forbidden item metadata remains unknown and does not serialize known item envelopes
- prompt guard wording remains unchanged in this phase after v10.4

## Allowed Item Sources

- `user_confirmed`
- `explicit_input` at helper/contract level
- UI mapping currently creates `user_confirmed` from `status=user_confirmed` + `source=user_input` + non-empty `item_id`

## Forbidden Item Sources

- hidden opponent default item
- inferred item
- recommended item
- common/meta/usage item
- damage reverse-inferred item
- legality gate guessed item
- resist berry inferred item
- context-derived item
- `visible_ui` item source
- `calculated_from_visible` item source

## Safety Boundary

- known item is user-confirmed context only
- known item does not imply activation
- known item does not imply consumption
- known item does not imply post-turn HP
- known item does not imply RNG result
- known item does not imply speed tie result
- known item does not imply Quick Claw activation
- known item does not imply full turn outcome
- known item does not imply selected opponent move
- unknown opponent item remains hidden/unknown
- no hidden item inference
- no damage reverse inference

## Verification Summary

- v11.4 contract/helper tests lock allowed/forbidden item sources and unknown behavior.
- v11.6 source adapter tests lock default species/HP-only behavior and explicit opt-in item parsing.
- v11.7 prompt/offline fixture verifies known user-confirmed item payload/prompt safety with mocked provider only.
- v11.9 UI mapping tests verify checkbox off omission and checkbox on known/unknown item behavior.
- v11.10 UI copy tests verify user-confirmed item copy and forbidden hidden/inferred/resolved wording absence.
- v11.11 UI offline smoke verifies checkbox off/on E2E prompt behavior with mocked provider only.
- Latest full pytest result before closure: `1305 passed, 2 deselected`.

## Known Limitations

- no additional actual Gemini item smoke yet
- one actual smoke was for `battle_state_context` before item UI mapping
- item source depends on existing `item_profiles` metadata
- no battle log/parser observed item source
- no item activation/consumption engine
- no field/status/boost integration
- user-confirmed item does not prove future model behavior for all cases

## Final Status

User-confirmed item support for `battle_state_context` is closed as PASS for design, contract/helper tests, source adapter, prompt/offline fixture, UI mapping, UI copy, and mocked UI-selected offline smoke.

The phase does not claim broad actual Gemini behavior for user-confirmed item prompts. Future actual Gemini work requires a separate controlled smoke design and explicit T1 approval before any provider call.

## Next Recommendations

Recommended next:

- v12.0 Controlled User-confirmed Item Gemini Smoke Design

Alternatives:

- v12.0 Field State Source Design
- v12.0 Item Activation/Consumption Boundary Design
