# v12.7 Field State UI Source Inventory

## Purpose

Inventory the current UI-selected path to determine whether weather, terrain, screens, hazards, or room state can be sourced safely for `battle_state_context.field`.

This is documentation-only. v12.7 does not implement field UI, field mapping, battle log parsing, payload builder changes, prompt guard wording changes, provider calls, or damage/KO behavior changes.

## Inspected Files

- `docs/spike_v12.6_field_state_prompt_offline_fixture.md`
- `docs/spike_v12.5_field_state_helper.md`
- `docs/spike_v12.4_field_state_contract_tests.md`
- `docs/spike_v12.3_field_state_source_design.md`
- `docs/advisor_payload_contract.md`
- `docs/PROGRESS.md`
- `docs/handoff_next_session_prompt_v1.9.md`
- `llm/advisor_battle_state_context.py`
- `llm/advisor_client.py`
- `llm/advisor_turn_snapshot.py`
- `core/turn_state.py`
- `ui/main_window.py`
- `ui/widgets/llm_advice_panel.py`
- `ui/widgets/pokemon_panel.py`
- `ui/widgets/item_profile_dialog.py`
- `tests/test_ui_turn_pipeline_flag_flow.py`
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`

## Current UI Source Inventory

Current UI controls and safe sources:

- Pokemon slot selection
- Pokemon identity display
- HP percent spinbox/progress display
- selected move slots
- final stat profile dialog
- held item profile dialog
- existing limited-context checkbox

Current field-state UI source status:

| Field key | Current UI input/display source | Decision |
| --- | --- | --- |
| `weather` | None found | No immediate UI source |
| `terrain` | None found | No immediate UI source |
| `screens` | None found | No immediate UI source |
| `hazards` | None found | No immediate UI source |
| `room` | None found | No immediate UI source |

The existing limited-context checkbox only gates whether optional contexts are included. It is not a field-state source.

## Current Battle Input / Payload Source Inventory

`MainWindow._build_llm_battle_input()` currently builds:

- `scenario`
- `pokemon`
- `stat_profiles`
- `item_profiles`
- `opponent_assumptions`
- `speed_context`
- `moves`
- `opponent_moves`

No current `battle_input` key carries:

- `field_profiles`
- `weather`
- `terrain`
- `screens`
- `hazards`
- `room`
- `field_conditions`

`build_battle_state_context_from_ui_selected_state(...)` currently reads:

- `battle_input["pokemon"].my_active/opponent_active` for visible species and HP
- `battle_input["item_profiles"].my_active/opponent_active` only when `include_user_confirmed_items=True`

It does not read field state. It explicitly remains species/HP plus optional user-confirmed item metadata only.

`build_turn_snapshot_from_battle_input(...)` creates a `BattleState` with:

- `weather=None`
- `terrain=None`
- `field_conditions={}`

The `core.turn_state.BattleState` contract can represent field-like data, but the current UI-selected adapter does not source field state from UI.

## Existing Metadata Pattern

The item profile pattern is the safest existing model:

```python
{
    "status": "user_confirmed",
    "source": "user_input",
    "item_id": "leftovers",
}
```

This pattern can be reused for future field profiles with field-specific `value` instead of `item_id`.

Recommended metadata interpretation:

- `source=user_input` means the UI surface was directly edited by the user.
- `status=user_confirmed` means the user confirmed the field state as current context.
- Adapter output should map trusted `status=user_confirmed` + `source=user_input` metadata to `source=user_confirmed`.
- `explicit_input` should be reserved for direct non-UI fixture/manual API input or a future explicit input surface that intentionally emits `explicit_input`.

## Immediate Usable Sources

Immediate usable UI sources for `battle_state_context.field`:

- none

Reason:

- no current UI widget captures field state
- no current UI display shows field state
- no current `battle_input` key carries trusted field metadata
- current `turn_snapshot` field values are defaults, not observed or user-confirmed sources

## Future Source Candidates

Future source candidates:

- Field Profile Dialog
- Battle State Panel
- manual explicit input surface
- battle log observed source
- parser observed source
- imported replay/source with parser contract

Candidate source policy:

- `user_confirmed`: direct user-confirmed UI field profile
- `explicit_input`: explicit fixture/manual API input surface
- `visible_ui`: only after a UI source visibly displays field state as a source of truth
- `battle_log_observed`: future only, requires parser/source tests
- `parser_observed`: future only, requires parser/source tests

## Not Allowed Sources

The following must not create known field state:

- damage reverse inference
- KO context inference
- turn order context inference
- opponent move context inference
- turn pipeline candidate events
- species/common/meta inference
- item inferred effects
- legality gate result
- resist berry context
- LLM/model guess
- hidden field guess
- `context_derived`
- `calculated_from_visible`

## Future Field Profiles Shape Proposal

Future `battle_input` shape candidate:

```python
"field_profiles": {
    "weather": {
        "status": "user_confirmed",
        "source": "user_input",
        "value": "rain",
    },
    "terrain": {
        "status": "user_confirmed",
        "source": "user_input",
        "value": "electric_terrain",
    },
    "room": {
        "status": "user_confirmed",
        "source": "user_input",
        "value": "trick_room",
    },
    "screens": {
        "status": "user_confirmed",
        "source": "user_input",
        "value": {
            "self": ["reflect"],
            "opponent": ["light_screen"],
        },
    },
    "hazards": {
        "status": "user_confirmed",
        "source": "user_input",
        "value": {
            "self": [],
            "opponent": ["stealth_rock"],
        },
    },
}
```

Adapter output candidate:

```python
"weather": {"known": True, "source": "user_confirmed", "value": "rain"}
```

```python
"hazards": {
    "known": True,
    "source": "user_confirmed",
    "value": {"self": [], "opponent": ["stealth_rock"]},
}
```

Malformed, missing, unconfirmed, or forbidden metadata should keep the field entry unknown.

## Future Mapping Considerations

First mapping candidate:

- reuse the existing limited-context checkbox as the hard gate
- checkbox off omits `battle_state_context`, therefore field is omitted
- checkbox on may include known field state only from valid `field_profiles`
- malformed or forbidden `field_profiles` normalize to unknown

Open design choices:

- whether a separate field profile opt-in flag is needed inside the adapter
- whether `include_user_confirmed_fields=enable_battle_state_context` is enough
- whether field UI should live in a Field Profile Dialog or a broader Battle State Panel
- whether future field copy should mention "user-confirmed field state"

Recommended next design stance:

- design a Field Profile Dialog before runtime mapping
- keep current checkbox default off
- avoid a new checkbox until an actual UI source exists and test coverage is locked
- do not connect parser/log sources without separate source contracts

## UI Copy Considerations

No UI copy changes are made in v12.7.

Future copy may need to add wording such as:

- user-confirmed field state
- current weather/terrain/screens/hazards/room snapshot
- not duration/expiration/post-turn result
- not damage precision
- not full outcome

Avoid copy that implies:

- inferred field state
- hidden field guessing
- field duration certainty
- post-turn field certainty
- hazard damage precision
- resolved battle outcome

## Safety Boundary

- no field source from damage reverse inference
- no field source from KO context
- no field source from turn order context
- no field source from opponent move context
- no field source from species/common/meta
- no field source from item inferred effects
- no field source from LLM/model guess
- no hidden field guessing
- known field is current context only
- known field does not imply duration
- known field does not imply expiration
- known field does not imply post-turn outcome
- known field does not imply damage precision
- unknown field remains unknown

## No Production Code Change

No production code, UI behavior, checkbox flow, payload builder call flow, prompt guard wording, damage engine, `damage_estimate`, or `ko_context` behavior is changed in v12.7.

## No Actual Gemini Call

No actual Gemini, retry, second provider, Vertex AI, network, or provider call is executed in v12.7.

## Next Recommendation

Recommended next:

- v12.8 Field Profile Dialog Design

Reason:

- The current UI has no immediate safe field source. A user-confirmed field input surface should be designed before field UI mapping.

Alternatives:

- v12.8 Field State UI Mapping Design
- v12.8 Item Activation/Consumption Boundary Design
