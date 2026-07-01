# v11.3 User-confirmed Item Boundary Design

## Purpose

Design the boundary for adding self/opponent item facts to
`battle_state_context` without implementing item integration.

The goal is to make future item support explicit, source-bound, and safe:
known items must come only from direct user input or user confirmation, while
hidden, inferred, legality-derived, damage-derived, and meta-derived items
remain unknown.

This design step does not change production code, payload adapters, prompt
guards, source adapters, UI behavior, or tests, and it does not execute any
Gemini, Vertex AI, provider, or network call.

## Current Battle State Context Item Status

Current `battle_state_context` already has an `item` field on both active sides:

- `self_active.item`
- `opponent_active.item`

Current UI-selected adapter behavior:

- extracts only self/opponent species and HP percent as `visible_ui`
- intentionally ignores `item_profiles`
- keeps self/opponent item unknown
- keeps status, boosts, field state, and `known_conditions` unknown or `[]`

Current unknown item shape:

```python
{"known": False, "value": "unknown"}
```

Current helper known-value shape:

```python
{"known": True, "source": "user_confirmed", "value": "loaded-dice"}
```

The future item integration should use this existing helper style rather than
introducing a new shape.

## Inspected Files

- `docs/spike_v11.2_battle_state_context_actual_smoke_closure.md`
- `docs/spike_v10.12_battle_state_context_ui_phase_closure.md`
- `docs/spike_v10.6_battle_state_ui_source_inventory.md`
- `docs/spike_v10.7_battle_state_ui_integration_design.md`
- `docs/advisor_payload_contract.md`
- `docs/PROGRESS.md`
- `docs/handoff_next_session_prompt_v1.9.md`
- `llm/advisor_battle_state_context.py`
- `llm/advisor_client.py`
- `llm/advisor_resist_berry_context.py`
- `llm/advisor_item_legal_gate.py`
- `ui/widgets/item_profile_dialog.py`
- `ui/main_window.py`
- `ui/widgets/llm_advice_panel.py`
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`

## Self Item Boundary

Self item can be considered a future `battle_state_context.item` source only
when it is direct user input or user-confirmed UI state.

Allowed self item source candidates:

- item profile dialog selection with `status == "user_confirmed"` and
  `source == "user_input"`
- equivalent future explicit input with a trusted source tag
- explicit no-item input can remain a separate design decision; it should not be
  confused with unknown item

Not enough by itself:

- default `system_default_none`
- legal item repository membership
- legal item gate pass
- item context availability
- damage modifier support
- damage or KO output
- species-common or usage-based item assumptions

Recommended source tag:

- `user_confirmed` for item profile dialog selections saved as
  `status == "user_confirmed"`
- `explicit_input` only for future non-dialog explicit item entry surfaces that
  are intentionally designed and tested

Future adapter should require at minimum:

- profile is a mapping
- `status == "user_confirmed"` for `user_confirmed`
- `source == "user_input"` or another explicitly allowed direct-input source
- non-empty item identifier or display name
- no forbidden hidden/inferred source metadata

## Opponent Item Boundary

Opponent item is hidden by default and must remain unknown unless the user
explicitly confirms it.

Allowed opponent item source candidates:

- user directly selects or enters the opponent item in the item profile dialog
  and the saved profile has `status == "user_confirmed"`
- future explicit opponent item input with source `explicit_input`
- future battle-log/parser observation only after a separate design proves the
  observation is explicit, visible, and not inferred

Current stage decision:

- no battle-log/parser item-observation source is implemented
- no automatic "item activated" source is implemented
- opponent item defaults to unknown

Forbidden opponent item sources:

- hidden item guess
- common set item
- usage or meta assumption
- damage reverse inference
- resist berry inferred from damage pattern
- legality gate guess
- candidate item from opponent sample/profile metadata

## Existing Item Context Relationship

### Item Profile Dialog

`ui/widgets/item_profile_dialog.py` stores item profiles with status/source
metadata. User selections can produce:

- `unknown`
- `none`
- `system_default_none`
- `user_confirmed`

Only `user_confirmed` profiles are candidates for future known item insertion
into `battle_state_context`.

### Main Window Payload

`ui/main_window.py` already places `item_profiles` into `battle_input`.

That payload can be an input source for a future item adapter, but the current
`build_battle_state_context_from_ui_selected_state(...)` intentionally ignores
it. The current ignore behavior is covered by tests and should remain unchanged
until item contract tests are added.

### Legality Gate

`llm/advisor_item_legal_gate.py` is validation/filtering infrastructure. It is
not an item source.

Legality can answer whether a user-selected item is allowed for a context, but
it must not create or guess a known item.

### Resist Berry Context

`llm/advisor_resist_berry_context.py` builds a limited damage-context helper
from an existing user-confirmed item profile and current damage/move metadata.

It is not a source of truth for `battle_state_context.item`. A future adapter
should read the original explicit/user-confirmed item profile, not promote a
resist berry context into battle-state item knowledge.

### Other Item Contexts

Existing item contexts such as speed order, survival, accuracy, flinch,
multi-hit, type boost, recovery, Chilan Berry, and species-stat item contexts
are limited advice contexts. They may reference user-confirmed item profiles,
but they should not become the source of truth for `battle_state_context.item`.

## Allowed Sources

Allowed:

- user-confirmed self item
- explicit-input self item
- user-confirmed opponent item
- explicit-input opponent item

Conditionally allowed:

- item value that the user entered and the legality gate validates as possible
- item profile dialog value only if it represents direct user input, not inference

## Forbidden Sources

Not allowed:

- species common item
- usage-based item
- meta-inferred item
- damage reverse-inferred item
- resist berry inferred from damage
- legality gate guessed item
- opponent hidden item default
- item consumption or item-resolution result
- possible sample item
- opponent set inference
- hidden moveset inference

## Payload Shape Proposal

Use the current helper known-value envelope:

```python
"item": {
    "known": True,
    "source": "user_confirmed",
    "value": "leftovers",
}
```

For explicit non-dialog entry, if contract tests keep `explicit_input` allowed:

```python
"item": {
    "known": True,
    "source": "explicit_input",
    "value": "leftovers",
}
```

Unknown remains:

```python
"item": {"known": False, "value": "unknown"}
```

Recommended future normalization:

- use normalized item id as `value` when available
- optionally include display labels only after contract tests decide the stable
  key shape
- do not include legality, effect support, damage modifier, item consumption,
  or activation result inside `battle_state_context.item`

## Prompt and Guard Consideration

Current prompt guard already forbids hidden item inference.

Recommended v11.3 decision:

- no prompt guard wording change in this design step
- future item contract tests should prove that a known `user_confirmed` item can
  be treated as known
- if item is unknown, hidden item inference remains forbidden
- opponent item remains unknown unless explicitly user-confirmed
- known item must not imply item consumption, activation, final item state, or
  turn outcome

Future prompt tests should lock both branches:

- known `user_confirmed` item appears as known item context
- unknown item still triggers hidden item inference boundary

## Test Plan for Future Implementation

Future contract/helper tests:

- self item omitted -> unknown
- self `user_confirmed` item -> known item source `user_confirmed`
- self `explicit_input` item -> known item source `explicit_input`, if allowed by contract
- opponent item omitted -> unknown
- opponent `user_confirmed` item -> known item source `user_confirmed`
- opponent common/meta item guess rejected
- damage reverse-inferred item rejected
- legality gate alone does not create known item
- resist berry context alone does not create known item
- known item does not imply item consumption
- known item coexists with species/HP `visible_ui`
- known item appears in payload/prompt only when source is allowed
- hidden item inference guard remains active for unknown item

Future UI/source adapter tests:

- item profile dialog `user_confirmed` profile maps to helper input only when
  item integration flag/scope is explicitly implemented
- `unknown`, `none`, and `system_default_none` do not become hidden item facts
- opponent item profile defaults to unknown
- item profile legal validation does not invent a known item
- item contexts do not become source of truth for battle-state item

## Safety Boundary

This design forbids:

- hidden item inference
- EV/IV/nature inference
- status/boost/field inference
- damage reverse inference
- species/common-set/meta item generation
- opponent set inference
- hidden moveset inference
- selected opponent move inference
- item consumption resolution
- RNG, speed tie, or Quick Claw activation resolution
- post-turn HP calculation
- full turn outcome
- full Turn Engine behavior

## Next Recommendation

Recommended next: `v11.4 User-confirmed Item Contract Tests`.

Reason:

- The helper already supports source-bound known item envelopes.
- The current UI adapter intentionally ignores item profiles.
- Before source adapter implementation, contract/helper tests should lock
  allowed item sources and forbidden item sources.

Alternatives:

- `v11.4 User-confirmed Item Source Adapter Design`
- `v11.4 Field State Source Design`
