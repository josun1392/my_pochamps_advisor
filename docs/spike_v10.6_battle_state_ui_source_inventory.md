# v10.6 Battle State UI Source Inventory

## Purpose

Inventory the current UI and repo sources that can safely feed future
`battle_state_context` UI integration. This is design/inventory only:

- no production code change
- no UI/source integration
- no payload adapter change
- no prompt guard change
- no actual Gemini, Vertex AI, provider, or network call
- no hidden-state inference
- no full Turn Engine behavior

## Files Inspected

- `ui/main_window.py`
- `ui/widgets/pokemon_panel.py`
- `ui/widgets/llm_advice_panel.py`
- `ui/widgets/item_profile_dialog.py`
- `llm/advisor_client.py`
- `llm/advisor_battle_state_context.py`
- `tests/test_ui_turn_pipeline_flag_flow.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_advisor_battle_state_context.py`
- `docs/spike_v10.5_battle_state_context_offline_advice_fixture.md`
- `docs/spike_v10.4_battle_state_context_prompt_guard.md`
- `docs/spike_v10.3_battle_state_context_payload_adapter.md`
- `docs/spike_v10.2_battle_state_context_helper.md`
- `docs/advisor_payload_contract.md`
- `docs/PROGRESS.md`
- `docs/handoff_next_session_prompt_v1.9.md`

## Current UI Source Summary

`MainWindow._build_llm_battle_input(...)` already builds a selected UI
`battle_input` with:

- `pokemon.my_active` and `pokemon.opponent_active`
- `pokemon.*.name_en`, `name_ko`, type data, base stats, slot index, and
  `hp_percent`
- `item_profiles.my_active` and `item_profiles.opponent_active`
- optional user-confirmed final-stat profiles
- selected and available move data
- `opponent_moves`

`PokemonPanel` owns the direct UI state for selected Pokemon, HP percent, move
slots, optional final stats, and optional item profile. It does not expose UI
fields for major status, stat boosts, weather, terrain, screens, hazards, or
room effects.

`LLMAdvicePanel` has the existing limited-context checkbox. v10.6 does not
change its behavior and does not connect it to `battle_state_context`.

## self_active Inventory

| Field | Current source | Trust level | Classification | v10.7 note |
| --- | --- | --- | --- | --- |
| `species` | `pokemon.my_active.name_en` / selected `PokemonPanel.pokemon_view` | `visible_ui` | immediately usable | Normalize to `{"source": "visible_ui", "name": ...}`. Prefer canonical English id/name already present in payload. |
| `current_hp_percent` | `PokemonPanel.current_hp_percent` -> `pokemon.my_active.hp_percent` | `visible_ui` | immediately usable | Normalize to `{"source": "visible_ui", "value": ...}`. It is pre-turn visible UI state, not post-turn HP. |
| `status` | No current UI source | none | not currently available / must remain unknown | Emit `{"known": false, "value": "unknown"}` until explicit UI input exists. |
| `boosts` | No current UI source | none | not currently available / must remain unknown | Emit explicit unknown. Do not derive from final stats, species, damage, or common sets. |
| `item` | `item_profiles.my_active` can be `system_default_none`, `none`, `unknown`, or `user_confirmed` | `user_confirmed` only when status is `user_confirmed`; explicit absent when `none`; otherwise not safe | usable with normalization | User-confirmed held item can become a known item value. `system_default_none` should not be promoted to hidden truth without a design decision. `unknown` remains unknown. |

## opponent_active Inventory

| Field | Current source | Trust level | Classification | v10.7 note |
| --- | --- | --- | --- | --- |
| `species` | `pokemon.opponent_active.name_en` / selected enemy `PokemonPanel.pokemon_view` | `visible_ui` | immediately usable | Normalize to `{"source": "visible_ui", "name": ...}`. |
| `current_hp_percent` | `PokemonPanel.current_hp_percent` -> `pokemon.opponent_active.hp_percent` | `visible_ui` | immediately usable | Normalize to `{"source": "visible_ui", "value": ...}`. It is visible UI state only. |
| `status` | No current UI source | none | not currently available / must remain unknown | Emit explicit unknown until a trusted UI input exists. |
| `boosts` | No current UI source | none | not currently available / must remain unknown | Emit explicit unknown. Do not infer from species, sample, or damage. |
| `item` | `item_profiles.opponent_active` defaults to `unknown`; item dialog can produce `user_confirmed` or `none` | `user_confirmed` only when status is `user_confirmed`; explicit absent when `none`; otherwise hidden/unknown | usable with normalization | User-confirmed opponent item can become known. Default unknown must remain unknown. |

## Field Inventory

| Field | Current source | Trust level | Classification | v10.7 note |
| --- | --- | --- | --- | --- |
| `weather` | No current UI source in the advice flow | none | not currently available / must remain unknown | Do not infer from abilities, species, damage, or common sets. |
| `terrain` | No current UI source in the advice flow | none | not currently available / must remain unknown | Do not infer from abilities, species, damage, or common sets. |
| `screens` | No current UI source in the advice flow | none | not currently available / must remain unknown | Do not infer Reflect/Light Screen from damage or matchups. |
| `hazards` | No current UI source in the advice flow | none | not currently available / must remain unknown | Do not infer hazards from HP or KO context. |
| `room` | No current UI source in the advice flow | none | not currently available / must remain unknown | Trick Room/Tailwind-style order effects stay outside battle state until explicit source exists. |

The damage engine has internal field concepts, but the current UI-selected
advice flow does not expose explicit field-state controls. Those engine types
are not a safe UI source for v10.7 integration.

## known_conditions Inventory

No current UI component provides explicit battle conditions as a general list.

Existing contexts such as item context, `turn_pipeline`, `turn_order_context`,
and `opponent_move_context` should not be copied into `known_conditions` in
v10.7. They already have their own bounded surfaces and guards; moving them
into battle state risks duplicate meaning or accidental inference.

Recommended v10.7 behavior:

- Keep `known_conditions` as `[]`.
- Add only future explicit UI/user-confirmed condition input.
- Do not derive conditions from item contexts, damage estimates, KO context,
  turn events, opponent moves, species, or common sets.

## Immediately Usable Sources

These facts are already visible in UI-selected battle input and can safely be
used after a narrow source adapter is designed:

- self active species as `visible_ui`
- opponent active species as `visible_ui`
- self active HP percent as `visible_ui`
- opponent active HP percent as `visible_ui`

These are visible snapshot facts only. They must not be treated as post-turn
state or resolved battle outcomes.

## Sources Requiring Normalization

The following sources are safe only after explicit normalization into the
v10.2 helper input shape:

- `pokemon.*.name_en` -> `active.species.name`
- `pokemon.*.hp_percent` -> `active.current_hp_percent.value`
- `item_profiles.*.status == "user_confirmed"` -> `active.item` with
  `source == "user_confirmed"`
- `item_profiles.*.status == "none"` may be represented as explicit no item
  only if v10.7 design chooses a stable value convention
- `item_profiles.*.status in {"unknown", "user_unconfirmed"}` must remain
  unknown
- `item_profiles.my_active.status == "system_default_none"` should remain a
  default assumption, not hidden battle truth, unless a later design explicitly
  maps it as an explicit absent item boundary

## Not Currently Available

- self/opponent major status
- self/opponent stat boosts
- weather
- terrain
- screens
- hazards
- room effects
- general `known_conditions` UI input

## Must Remain Unknown

The following fields must remain `{"known": false, "value": "unknown"}` unless
a future explicit or visible UI source is added:

- unobserved status
- unobserved boosts
- default/unknown opponent item
- field weather
- field terrain
- screens
- hazards
- room
- known conditions list

## Unsafe / Forbidden Sources

The following must not feed `battle_state_context`:

- `species_common_set`
- `usage_based_guess`
- `meta_inferred`
- `hidden_state_guess`
- `damage_reverse_inference`
- opponent set inference
- hidden moveset inference
- selected move inference
- sample/common-set item assumptions
- damage estimate reverse inference
- KO context reverse inference
- TurnPipeline candidate events as resolved state
- TurnOrderContext hints as resolved order or RNG state
- OpponentMoveContext candidates as selected moves or hidden movesets

The following fields/meanings must not be emitted:

- hidden item
- EV/IV/nature
- inferred boosts
- inferred status
- inferred weather
- inferred terrain
- inferred hazards/screens
- RNG result
- speed tie result
- Quick Claw activation
- post-turn HP
- item consumption
- full turn outcome

## Recommended v10.7 Direction

Recommended next milestone:

```text
v10.7 Battle State UI Integration Design
```

Reason:

- The safe source set is narrow but real: selected species and HP percent for
  both active Pokemon are visible UI facts.
- Item profile integration needs a design decision before implementation,
  especially for `system_default_none`, explicit `none`, and opponent unknown
  handling.
- Status, boosts, field state, and known conditions are not currently available
  and should stay unknown.
- The existing limited-context checkbox already controls several contexts; any
  battle-state connection should be designed before implementation.

Implementation should not start directly from v10.6 unless T1/T2 explicitly
approve skipping the design step.

## Verification

Recommended tests for this docs-only inventory:

- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_ui_turn_pipeline_flag_flow.py`

No actual Gemini, Vertex AI, provider, or network call is needed.
