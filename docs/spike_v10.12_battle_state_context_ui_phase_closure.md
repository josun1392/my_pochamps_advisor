# v10.12 Battle State Context UI Phase Closure

## Purpose

Close the `battle_state_context` UI phase after design, contract, helper,
payload adapter, prompt guard, offline fixtures, UI source inventory, checkbox
mapping, copy update, and offline UI-selected smoke coverage.

This closure records what is supported now, what remains unknown by design, and
what must stay out of scope until a future explicit design or controlled smoke.

## Phase Summary

The v10 phase made `battle_state_context` a limited visible/explicit snapshot
context. It is available from the existing limited-context checkbox path, but it
does not resolve battle outcomes or infer hidden state.

Completed milestones:

| Milestone | Result |
| --- | --- |
| v10.0 Battle State Context Design | Designed a visible/explicit battle-state snapshot with unknown-safe boundaries. |
| v10.1 Battle State Context Payload Contract | Locked optional top-level shape and confidence/source/forbidden-field rules in contract tests. |
| v10.2 Battle State Context Helper | Added `build_battle_state_context(...)` for safe visible/explicit input normalization. |
| v10.3 Battle State Context Payload Adapter | Added default-off payload insertion for valid non-empty contexts. |
| v10.4 Battle State Context Prompt Guard | Added guard wording for unknown fields, hidden-state inference, reverse inference, and resolved simulation boundaries. |
| v10.5 Battle State Context Offline Advice Fixture | Verified mocked advice flow preserves context and guard without provider calls. |
| v10.6 Battle State UI Source Inventory | Identified UI-safe sources as self/opponent species and HP percent only. |
| v10.7 Battle State UI Integration Design | Designed checkbox integration using only species/HP and leaving other fields unknown. |
| v10.8 Battle State UI Source Adapter | Added `build_battle_state_context_from_ui_selected_state(...)` for species/HP extraction. |
| v10.9 Battle State UI Checkbox Mapping | Connected the existing limited-context checkbox to `enable_battle_state_context`. |
| v10.10 Battle State UI Copy Update | Updated checkbox copy to mention current Pokemon/HP snapshot without implying resolved state. |
| v10.11 Battle State UI Integration Offline Smoke | Verified checkbox off/on payload, prompt, guard, and mocked provider behavior. |

## Current Runtime Behavior

- The existing limited-context checkbox remains default off.
- Checkbox off omits `battle_state_context`.
- Checkbox on enables `battle_state_context` together with the other limited contexts.
- `enable_battle_state_context = enable_turn_pipeline`.
- The source adapter uses the UI-selected `battle_input` shape.
- The source adapter extracts species and HP percent only.
- The existing v10.4 prompt guard is reused when `battle_state_context` appears.
- No actual Gemini call was executed in this phase.

## Current UI Checkbox Behavior

Unchecked:

```text
enable_turn_pipeline = False
enable_turn_order_context = False
enable_opponent_move_context = False
enable_battle_state_context = False
battle_state_context omitted
```

Checked:

```text
enable_turn_pipeline = True
enable_turn_order_context = True
enable_opponent_move_context = True
enable_battle_state_context = True
battle_state_context built from visible species/HP source when available
```

No new checkbox was added. The checkbox default, toggle behavior, and advice
button flow remain unchanged.

## Current Supported Sources

`self_active.species`:

- source: `visible_ui`
- from UI-selected own Pokemon name

`self_active.current_hp_percent`:

- source: `visible_ui`
- from UI-selected own Pokemon HP percent

`opponent_active.species`:

- source: `visible_ui`
- from UI-selected opponent Pokemon name

`opponent_active.current_hp_percent`:

- source: `visible_ui`
- from UI-selected opponent Pokemon HP percent

## Unknown Fields Policy

The current UI path leaves these fields unknown:

- `self_active.status`: unknown
- `self_active.boosts`: unknown
- `self_active.item`: unknown
- `opponent_active.status`: unknown
- `opponent_active.boosts`: unknown
- `opponent_active.item`: unknown
- `field.weather`: unknown
- `field.terrain`: unknown
- `field.screens`: unknown
- `field.hazards`: unknown
- `field.room`: unknown
- `known_conditions`: `[]`

Unknown fields are represented with the existing contract value:

```python
{"known": False, "value": "unknown"}
```

## Payload Behavior

- `battle_state_context` is optional and top-level.
- Default/off paths preserve the existing payload shape.
- Explicit enabled UI paths add `battle_state_context` only when a valid non-empty context exists.
- The payload adapter validates kind, confidence, source policy, required shape, and forbidden fields.
- `battle_state_context` coexists with `turn_pipeline`, `turn_order_context`, and `opponent_move_context`.
- `battle_state_context` is not generated from damage estimates, KO context, turn events, turn order, or opponent move candidates.

## Prompt Guard Behavior

When `battle_state_context` is present, the prompt guard says:

- unknown battle-state fields must remain unknown
- hidden items must not be inferred
- EVs, IVs, and nature must not be inferred
- boosts, status, weather, terrain, hazards, screens, or room must not be inferred unless explicitly provided
- damage estimates and KO context must not be used to reverse-engineer hidden state
- `battle_state_context` is not a resolved turn simulation
- post-turn HP, item consumption, RNG result, speed tie result, Quick Claw activation, and full turn outcome must not be claimed

When `battle_state_context` is absent, the serialized block and guard are absent.

## UI Copy Summary

Label:

```text
제한 컨텍스트 포함
```

Enabled status/help:

```text
제한 컨텍스트 켜짐: 후보 이벤트, 선후공 보조 정보, 상대 기술 후보, 현재 포켓몬/HP 스냅샷 전달 | 확정 결과 아님
```

The tooltip explains candidate events, turn-order helper information,
UI-visible opponent move candidates, and the current Pokemon/HP snapshot. It
also avoids hidden item/status/boost/field inference and resolved-outcome
certainty.

## Tests / Offline Verification Summary

Covered tests include:

- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_ui_turn_pipeline_flag_flow.py`

Verification currently covers:

- contract shape and forbidden fields
- helper normalization
- payload adapter default-off and explicit-on behavior
- prompt guard presence/absence and wording anchors
- mocked advice fixture preservation
- UI source adapter species/HP extraction
- checkbox off/on payload and prompt behavior
- checkbox toggle no-call behavior
- mocked provider only, with no actual Gemini/Vertex/network call

## Known Limitations

- No actual Gemini smoke has been run for the `battle_state_context` UI path.
- `battle_state_context` currently carries only species/HP snapshot data.
- status, boosts, item, and field state remain unknown.
- user-confirmed item boundary is not designed yet.
- field state UI source is not available.
- `known_conditions` source is not available.
- no resolved simulation is implemented.

## Safety Boundary

The current phase does not implement:

- hidden item inference
- EV/IV/nature inference
- status/boost/field inference
- damage reverse inference
- species/common set/meta state generation
- opponent set inference
- hidden moveset inference
- selected opponent move inference
- post-turn HP calculation
- item consumption resolution
- RNG resolver
- speed tie resolver
- Quick Claw activation resolution
- full turn outcome
- full Turn Engine

## Next Recommendations

Option A:

```text
v11.0 Controlled Battle State UI Gemini Smoke Design
```

Goal:

```text
Design controlled smoke conditions, fixture, abort criteria, and expected output boundaries before any actual Gemini call.
```

Option B:

```text
v11.0 User-confirmed Item Boundary Design
```

Goal:

```text
Design the user_confirmed boundary for adding self/opponent item fields to battle_state_context.
```

Option C:

```text
v11.0 Field State Source Design
```

Goal:

```text
Design safe UI sources for weather, terrain, screens, hazards, and room.
```

T2 recommendation:

- If v10.12 is green, move to v11.0 Controlled Battle State UI Gemini Smoke Design.
- Do not run an actual call yet.
- First document T1 approval conditions, one-call limit, abort criteria, and expected safety boundaries.

## Closure

The `battle_state_context` UI phase is closed for offline/mocked coverage. The
current implementation is safe for visible species/HP snapshot context and keeps
unknown/hidden battle state out of the payload and prompt unless a future
explicit source boundary is designed.
