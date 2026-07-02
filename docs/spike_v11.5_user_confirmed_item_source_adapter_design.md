# v11.5 User-confirmed Item Source Adapter Design

## Purpose

Design the future source-adapter boundary for passing user-confirmed or explicit
item values from the UI-selected `battle_input` into `battle_state_context`.
This is design-only. It does not change production code, connect UI item
profiles to battle state, alter checkbox behavior, change prompt guard wording,
or run an actual Gemini call.

## Current Item Contract Summary

v11.4 locked `battle_state_context.item` known-source behavior:

- allowed known item sources: `user_confirmed`, `explicit_input`
- forbidden item sources: `visible_ui`, `calculated_from_visible`,
  `species_common_set`, `usage_based_guess`, `meta_inferred`,
  `hidden_state_guess`, `damage_reverse_inference`,
  `legality_gate_guess`, `resist_berry_inferred`, `context_derived`
- helper behavior: forbidden-source item input becomes unknown
- payload adapter behavior: invalid prebuilt item contexts are rejected
- omitted self/opponent items remain `{"known": false, "value": "unknown"}`
- known item values do not create item consumption, activation, post-turn HP,
  RNG, speed tie, Quick Claw, or full outcome fields

The current UI-selected adapter still extracts only self/opponent species and HP
percent as `visible_ui`. It intentionally ignores `item_profiles`.

## Inspected Files

- `docs/spike_v11.4_user_confirmed_item_contract_tests.md`
- `docs/spike_v11.3_user_confirmed_item_boundary_design.md`
- `docs/advisor_payload_contract.md`
- `docs/PROGRESS.md`
- `docs/handoff_next_session_prompt_v1.9.md`
- `llm/advisor_battle_state_context.py`
- `llm/advisor_client.py`
- `ui/widgets/item_profile_dialog.py`
- `ui/main_window.py`
- `ui/widgets/llm_advice_panel.py`
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`

## Existing Item Profile/Dialog Findings

The existing UI item-profile surface already distinguishes sides and profile
status, but it is not yet connected to `battle_state_context.item`.

- `ItemProfileDialog` is opened with a role key: `my_active` or
  `opponent_active`.
- `MainWindow._build_llm_battle_input()` already includes
  `battle_input["item_profiles"]["my_active"]` and
  `battle_input["item_profiles"]["opponent_active"]`.
- The profile payload uses metadata such as `status`, `source`, `item_id`,
  display names, legality/effect support fields, and damage modifier status.
- User-selected legal item profiles are stored with `status:
  "user_confirmed"`, `source: "user_input"`, and canonical `item_id` values.
- Opponent default item profile is `unknown`; self default is a system default
  no-item profile.
- `unknown`, `none`, and `system_default_none` profiles must not be promoted to
  known `battle_state_context.item` values by the first adapter.
- Existing item profile metadata can distinguish user-confirmed selection from
  unknown/default states, but it should still be consumed through an explicit
  battle-state adapter opt-in.

## Adapter Input Design

The future implementation should preserve the existing species/HP-only adapter
by default. Recommended shape:

```python
build_battle_state_context_from_ui_selected_state(
    battle_input,
    include_user_confirmed_items=False,
)
```

Design rules:

- Default `include_user_confirmed_items=False` keeps current behavior unchanged.
- When false, `item_profiles` must not be read for `battle_state_context`.
- When true, the adapter may inspect `battle_input["item_profiles"]` only for
  `my_active` and `opponent_active`.
- The item adapter should be a small internal helper, for example
  `_item_entry_from_ui_item_profile(profile)`, that returns a helper input
  envelope or `None`.
- Missing profile metadata, unsupported status, missing `item_id`, or any
  non-user-confirmed source should return `None`, leaving helper output unknown.
- Future `explicit_input` item sources may be supported only if a separate UI
  source clearly records direct explicit input rather than recommendation,
  filter output, legality gate output, damage context, or inferred state.

An alternate standalone function is acceptable if implementation wants a
separate composition point:

```python
build_battle_state_context_item_sources_from_ui_selected_state(battle_input)
```

However, the final implementation should keep item inclusion opt-in so the
existing checkbox-on path does not silently change from species/HP-only behavior.

## Adapter Output/Envelope Proposal

The source adapter should pass helper input, not a final known-value envelope.
`build_battle_state_context(...)` remains responsible for creating the final
normalized context.

Self example:

```python
self_active = {
    "species": {"source": "visible_ui", "name": "Charizard"},
    "current_hp_percent": {"source": "visible_ui", "value": 100},
    "item": {"source": "user_confirmed", "value": "leftovers"},
}
```

Opponent example:

```python
opponent_active = {
    "species": {"source": "visible_ui", "name": "Garchomp"},
    "current_hp_percent": {"source": "visible_ui", "value": 100},
    "item": {"source": "user_confirmed", "value": "choice-scarf"},
}
```

Unknown items should usually be represented by omitting `item` from helper input
and letting the helper produce:

```python
{"known": False, "value": "unknown"}
```

If a future direct explicit-input surface exists, it may use:

```python
{"source": "explicit_input", "value": "<canonical-item-id>"}
```

The adapter should prefer canonical `item_id` values over localized display
names. Display names may remain in the original top-level `item_profiles`
payload, but `battle_state_context.item.value` should be stable enough for
contract tests.

## Self Item Rules

- Allow known self item only when profile metadata represents direct user
  confirmation or a future direct explicit-input source.
- Current item-profile candidate: `status == "user_confirmed"`,
  `source == "user_input"`, and non-empty string `item_id`.
- Map the current item-profile candidate to `source: "user_confirmed"`.
- Future direct explicit item entry may map to `source: "explicit_input"` only
  if it is not generated by recommendation, legality filtering, damage context,
  common-set data, or inference.
- If source metadata is missing, malformed, or ambiguous, keep self item
  unknown.
- `none` and `system_default_none` should remain out of
  `battle_state_context.item` for the first implementation unless a separate
  no-item semantics design decides otherwise.

## Opponent Item Rules

- Opponent item remains hidden/unknown by default.
- Allow known opponent item only when the user directly selected or confirmed it
  in a trusted UI source with the same explicit metadata requirements as self
  item.
- Current item-profile candidate: `status == "user_confirmed"`,
  `source == "user_input"`, and non-empty string `item_id`.
- Missing opponent profile metadata keeps item unknown.
- Hidden/default opponent items, species-common items, usage items, and
  battle-state guesses must never become known.
- Observed item activation from logs/parsers is a future source design, not part
  of v11.5.

## Legality Gate Relationship

- The legality gate may validate an already user-confirmed or explicit item.
- The legality gate must not create a known `battle_state_context.item` by
  itself.
- If legality validation rejects or blocks an item, the adapter should prevent
  known item insertion or keep the item unknown.
- The legality gate must not infer or substitute a replacement item.
- Legality or effect support metadata should not be copied into
  `battle_state_context.item`; the item field remains a narrow known-value
  envelope.

## Resist Berry Relationship

- Resist berry context may explain berry-related calculation context when its
  own user-confirmed item source is available.
- Resist berry context must not become the source of truth for
  `battle_state_context.item`.
- Damage, KO, or type-effectiveness signals must not reverse-infer a resist
  berry as a known item.
- A resist berry context existing in the payload is insufficient to create a
  known battle-state item.

## Forbidden Sources

The item source adapter must not create known items from:

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
- recommendation/filter output without direct user confirmation
- hidden opponent default item
- item consumption, activation, post-turn HP, RNG, speed tie, Quick Claw, or
  full turn outcome reasoning

## Behavior Preservation

- Existing limited-context checkbox behavior stays unchanged.
- Existing default unchecked behavior stays unchanged.
- Existing species/HP extraction stays unchanged.
- Existing prompt guard wording stays unchanged.
- Existing payload adapter contract stays unchanged.
- Current adapter remains species/HP-only unless a future implementation adds an
  explicit item opt-in.
- Missing, malformed, or ambiguous item profile metadata keeps item unknown.
- No hidden item inference is introduced.

## Test Plan

Future implementation should add tests before connecting item profiles:

- item adapter disabled -> existing species/HP-only behavior unchanged
- self item with `user_confirmed` metadata -> known item `user_confirmed`
- self item with `explicit_input` metadata -> known item `explicit_input`
- self item without metadata -> unknown
- self item from legality gate only -> unknown
- self item from recommendation/filter only -> unknown
- opponent item omitted -> unknown
- opponent item with `user_confirmed` metadata -> known item `user_confirmed`
- opponent item with `explicit_input` metadata -> known item `explicit_input`
- opponent item without metadata -> unknown
- opponent hidden/default item -> unknown
- resist berry context does not create known item
- damage/KO does not create known item
- known item coexists with species/HP
- known item does not imply consumption, activation, post-turn result, RNG,
  speed tie, Quick Claw activation, or full outcome

## Next Recommendation

Recommended next milestone: v11.6 User-confirmed Item Source Adapter.

Implementation should add the opt-in adapter extension and tests while keeping
the default UI-selected path species/HP-only unless item inclusion is explicitly
enabled. Actual Gemini calls remain out of scope.

## No Production Code Change

v11.5 is documentation/design only. It does not change production code, UI item
integration, UI source adapter wiring, checkbox behavior, payload adapter
contract, or prompt guard wording.

## No Actual Gemini Call

No actual Gemini, Vertex AI, provider, retry, second provider, or network call is
part of this design step.
