# v4.9 TurnSnapshot Phase Closure / v5.0 Prep

## Purpose

The v4 TurnSnapshot phase prepared a selected/pre-turn state foundation before building any full Turn Engine behavior.

The goal was not to simulate turns. The goal was to make current UI-selected state visible as a validated, optional, serializable snapshot that can later become input to a minimal turn-event pipeline.

## Completed v4 Scope

### v4.1 TurnSnapshot Contract

Implemented in `core/turn_state.py`:

- `PokemonBattleSlot`
- `BattleState`
- `TurnInput`
- `TurnSnapshot`
- `to_dict()` / `from_dict(...)`
- `normalize_turn_snapshot(...)`
- validation for side, item status, HP percent, stat stages, turn number, and string tuple fields

### v4.3 Optional Payload Adapter

Implemented in `llm/advisor_client.py`:

- `build_ui_advice_payload(..., turn_snapshot=None)`
- optional top-level `turn_snapshot`
- snapshot normalization and serialization
- selected/pre-turn snapshot limitations in `scenario.known_limitations`
- prompt guard that prevents full Turn Engine claims

Snapshot absent behavior remains unchanged.

### v4.5 UI-selected Builder

Implemented in `llm/advisor_turn_snapshot.py`:

- strict `build_turn_snapshot_from_battle_input(...)`
- fallback `try_build_turn_snapshot_from_battle_input(...)`
- mapping from UI-selected `battle_input` to `TurnSnapshot`

Currently mapped:

- player/opponent species
- slot index
- HP percent
- known item id
- item status
- selected player move id

Not-yet-connected fields stay empty or `None`:

- stat stages
- major status
- volatile conditions
- weather
- terrain
- field conditions
- turn number

### v4.6 Smoke Verification

Verified without actual Gemini calls:

- snapshot present path
- snapshot absent/fallback path
- limitations guard presence
- no damage estimate / `ko_context` / item-context regression

### v4.7 Flow Handoff

Documented the complete TurnSnapshot UI flow in:

```text
docs/handoff_turn_snapshot_flow_v4.7.md
```

### v4.8 Local Dry-run / Debug Report

Added:

```text
scripts/spike_turn_snapshot_debug.py
docs/debug_turn_snapshot_sample_v4.8.md
```

The dry-run report confirms:

- fixture `battle_input` builds a `TurnSnapshot`
- top-level `turn_snapshot` is present when supplied
- snapshot limitations are present
- absent path omits `turn_snapshot`
- removing snapshot fields returns the absent-payload shape
- invalid HP falls back to `None`
- no Gemini or Vertex AI call is made

v4.8.1 perf recheck later passed:

- isolated target 3/3 passed
- perf file rerun passed
- full pytest passed

## Current Data Flow

```text
UI selected state
  -> MainWindow._build_llm_battle_input()
  -> attach_selected_move_damage_estimate(...)
  -> run_ui_selected_advice(...)
  -> try_build_turn_snapshot_from_battle_input(battle_input)
  -> _build_ui_selected_prompt(..., turn_snapshot=...)
  -> build_ui_advice_payload(..., turn_snapshot=...)
  -> optional top-level turn_snapshot
  -> selected/pre-turn snapshot limitations in prompt
```

The snapshot is additive context. It does not alter the calculator path.

## Still Not Implemented

The v4 phase deliberately does not implement:

- full Turn Engine
- item trigger evaluation
- item consumption
- HP update logic
- post-turn state mutation
- speed/order simulation
- exact status or volatile condition resolution
- multi-hit event engine
- irreversible battle state mutation
- Showdown-equivalent mechanics

## v5.0 Design Criteria

v5.0 should begin as design work, not implementation.

Recommended principles:

- Use `TurnSnapshot` as input state, not as an engine result.
- Keep `damage_estimate` as the damage primitive.
- Keep `ko_context` as limited damage-roll context.
- Treat existing item contexts as advice surfaces that can later explain deterministic trigger results.
- Build a minimal turn-event pipeline rather than a full battle engine.
- Keep event contracts serializable and testable before connecting them to UI or Gemini advice.

## v5.0 Minimal Turn Engine MVP Candidate

Recommended v5.0 scope:

- design `TurnEvent`
- design `TurnPipelineResult`
- separate event stages:
  - pre-damage
  - damage
  - on-damage-before-KO
  - post-damage
  - post-turn
- classify item trigger planning by stage
- keep output as planning/debug contract first

Initial planning targets:

- Focus Sash / Focus Band: on-damage-before-KO planning
- resist berries / Chilan Berry: on-damage-before-KO damage mitigation planning
- Shell Bell: on-hit / on-damage-dealt recovery planning
- healing berries / Oran Berry: post-damage HP-threshold planning
- White Herb: on-stat-drop planning
- Mental Herb: on-status/volatile planning
- Quick Claw: pre-move move-order planning
- Loaded Dice: multi-hit event planning

## v5.0 Non-goals

Do not implement in v5.0 design:

- real full simulation
- exact item trigger probability resolution
- irreversible item consumption state mutation
- exact post-turn HP truth
- guaranteed speed tie or random activation outcomes
- exact multi-hit event resolution
- Showdown-equivalent engine behavior
- Gemini actual verification

## Safety

v4.9 is documentation/handoff cleanup only.

No production code was changed. No actual Gemini call or Vertex AI call was run. Damage formula, raw damage rolls, Q12 multipliers, `ko_context`, item contexts, and payload filtering remain unchanged.
