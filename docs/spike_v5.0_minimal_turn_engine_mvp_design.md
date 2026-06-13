# v5.0 Minimal Turn Engine MVP Design

## Purpose

The v4 TurnSnapshot phase is complete. The advisor now has a selected/pre-turn known-state snapshot that can be built from UI-selected `battle_input`, serialized into the optional top-level `turn_snapshot` payload field, smoke-verified without an actual Gemini call, and inspected through a local dry-run report.

v5.0 defines the next layer: a minimal turn-event planning model for PoChamps advisor use. This is not a full Showdown-equivalent engine. The goal is to create small, serializable contracts that can describe turn-stage candidates, known modifiers, and limitations before any item trigger resolution, HP mutation, or irreversible state update is implemented.

No production code was changed for v5.0. No actual Gemini call or Vertex AI call was run.

## v4 Input State Baseline

Existing v4 contracts remain the state foundation:

- `core.turn_state.PokemonBattleSlot`
- `core.turn_state.BattleState`
- `core.turn_state.TurnInput`
- `core.turn_state.TurnSnapshot`
- `normalize_turn_snapshot(...)`

Current data flow:

```text
UI-selected battle_input
  -> llm.advisor_turn_snapshot.build_turn_snapshot_from_battle_input(...)
  -> optional TurnSnapshot
  -> build_ui_advice_payload(..., turn_snapshot=...)
  -> top-level turn_snapshot
  -> selected/pre-turn snapshot limitations
```

The snapshot is input state only. It is not an engine result and does not imply that triggers, HP changes, move order, item consumption, or post-turn state have been resolved.

## Responsibilities

The Minimal Turn Engine MVP should eventually be responsible for:

- accepting `TurnSnapshot` as input state
- accepting selected move and target information through `TurnInput`
- referencing the existing `damage_estimate` primitive
- referencing the existing limited `ko_context` primitive
- separating turn-stage event candidates into a consistent stage model
- classifying item trigger candidates by stage
- representing known damage modifiers that are already reflected by `damage_estimate`
- producing a serializable turn pipeline summary that the LLM can explain with limitations

The MVP should prefer "candidate", "known modifier", and "not simulated" language over final outcome language.

## Non-responsibilities

The Minimal Turn Engine MVP must not attempt:

- full Showdown-equivalent simulation
- exact RNG resolution
- speed tie or random activation resolution
- irreversible item consumption mutation
- exact post-turn HP truth
- exact status or volatile condition resolution
- complete multi-hit event resolution
- final KO probability beyond existing `ko_context`
- final move order
- automatic replacement of existing item contexts

## Stage Model

Recommended stage names:

| Stage | Purpose | Example item/context mapping | v5.0 interpretation |
| --- | --- | --- | --- |
| `pre_turn` | Record input state before any action. | known HP, known item status, weather/terrain placeholders | snapshot context only |
| `pre_move` | Describe move-order and pre-action candidates. | Quick Claw, Choice Scarf speed influence | candidate or known speed modifier; no guaranteed order |
| `damage` | Reference calculated damage primitive. | Light Ball, type-boost items, direct applied damage modifiers | known modifier only when `damage_estimate.item_effects` says applied |
| `on_damage_before_ko` | Describe survival or mitigation candidates before fainting is finalized. | Focus Sash, Focus Band, resist berries, Chilan Berry | candidate/limited inference; no final survival truth |
| `on_hit_or_damage_dealt` | Describe effects after a hit or damage dealt. | Shell Bell | planning target; no HP update |
| `post_damage` | Describe threshold checks after damage. | Sitrus Berry, Oran Berry, healing berries | planning target; no item consumption or exact post-damage HP |
| `post_turn` | Describe end-of-turn candidates. | Leftovers, residual future hooks | planning target; no full end-turn sequencing |

Additional future stage families may be needed for `on_stat_drop`, `on_status_or_volatile`, and `form_state`, but v5.1 can represent them as trigger types without simulating them.

## Item Trigger Classification

| Item/context | Stage | Trigger type | MVP status |
| --- | --- | --- | --- |
| Choice Scarf | `pre_move` | speed_modifier | known modifier through existing `speed_context`; no final order |
| Quick Claw | `pre_move` | random_move_order_activation | candidate only; activation probability/order unresolved |
| Light Ball | `damage` | species_stat_damage_modifier | known modifier when already applied by `damage_estimate.item_effects` |
| Type-boost items | `damage` | type_damage_modifier | known modifier when already applied by `damage_estimate.item_effects` |
| Focus Sash | `on_damage_before_ko` | survival_item | candidate/limited survival context; no consumption |
| Focus Band | `on_damage_before_ko` | random_survival_item | candidate/limited survival context; no activation resolution |
| Resist berries | `on_damage_before_ko` | type_resist_mitigation | candidate/limited mitigation; raw rolls unchanged unless future integration chooses otherwise |
| Chilan Berry | `on_damage_before_ko` | normal_resist_mitigation | candidate/limited mitigation; raw rolls unchanged today |
| Shell Bell | `on_hit_or_damage_dealt` | recovery_from_damage_dealt | planning target; actual dealt damage and recovery not finalized |
| Oran/Sitrus/healing berries | `post_damage` | hp_threshold_recovery | planning target; threshold and consumption not finalized |
| Leftovers | `post_turn` | end_turn_recovery | planning target; exact end-turn sequencing not simulated |
| White Herb | `post_damage` or `on_stat_drop` | stat_drop_recovery | future hook; requires stat-stage event tracking |
| Mental Herb | `post_damage` or `on_status_or_volatile` | volatile_status_recovery | future hook; requires status/volatile event tracking |
| Loaded Dice | multi-hit event family | hit_count_modifier | future hook; requires multi-hit event model |
| Mega Stones | form/state family | form_state_change | deferred; requires form/state subsystem |

## TurnEvent Contract Candidate

Recommended fields:

```text
TurnEvent:
- stage: one of the stage model values
- source: "turn_snapshot" | "damage_estimate" | "ko_context" | "item_context" | "turn_planning"
- subject_side: "player" | "opponent" | None
- target_side: "player" | "opponent" | None
- item_id: optional item identifier
- trigger_type: concise trigger class
- status: "candidate" | "known_modifier" | "not_simulated" | "blocked" | "unavailable"
- certainty: "known" | "limited" | "candidate" | "unknown"
- summary: short human-readable explanation
- limitations: list of short limitation strings
- payload_key: optional pointer to the related payload surface
```

`TurnEvent` is not always a resolved result. It must be able to represent:

- a known modifier already applied by `damage_estimate`
- a candidate trigger that requires future turn simulation
- a blocked/unavailable trigger with debug-only reason
- a limited context that should not become final battle truth

Recommended validation for v5.1:

- stage must be known
- status must be known
- certainty must be known
- sides must be `player`, `opponent`, or `None`
- string fields should be plain, concise, and optional where uncertainty is expected

## TurnPipelineResult Contract Candidate

Recommended fields:

```text
TurnPipelineResult:
- input_snapshot: TurnSnapshot dict or reference
- selected_move_id: string | None
- damage_estimate_ref: optional payload reference
- ko_context_ref: optional payload reference
- events: list[TurnEvent]
- warnings: list[str]
- limitations: list[str]
- simulated: "not_simulated" | "planning_only" | "limited"
```

The default `simulated` value should be `planning_only` or `not_simulated`. The contract should not use names such as `final_result`, `engine_truth`, or `confirmed_turn_outcome`.

For v5.1, `TurnPipelineResult` should be fixture-serializable and testable without any advisor payload connection.

## Existing Context Connection

The existing calculator/context surfaces should remain intact:

- `damage_estimate` remains the primitive for damage ranges, rolls, type effectiveness, assumption profile, and applied item effects.
- `ko_context` remains limited damage-roll context only.
- item contexts remain additive advice surfaces.
- available/unavailable filtering behavior remains unchanged.
- `TurnEvent` should initially align and explain existing surfaces rather than replace them.

Progressive mapping path:

- Light Ball and type-boost items can map to `damage` / `known_modifier` because they are source-of-truth applied through `damage_estimate.item_effects`.
- Focus Band, Focus Sash, resist berries, and Chilan Berry can map to `on_damage_before_ko` / `candidate` or `not_simulated`.
- Quick Claw can map to `pre_move` / `candidate`.
- Sitrus Berry, Leftovers, Shell Bell, White Herb, Mental Herb, and Loaded Dice should remain planning targets until their required state/events exist.

## LLM Wording Expectations

Allowed:

- "The turn pipeline marks this as a candidate trigger."
- "This is a known modifier already reflected in the damage estimate."
- "This event is planning-only and does not resolve item consumption."
- "The existing ko_context remains limited damage-roll context."

Forbidden:

- "full turn simulation completed"
- "the item was consumed"
- "exact post-turn HP is known"
- "the move order is guaranteed"
- "the trigger definitely activates"
- "final KO probability includes all turn events"

## v5.1 Implementation MVP

Recommended next milestone:

```text
v5.1 Turn Event Contract Implementation
```

Scope:

- Add `core/turn_event.py` or `core/turn_pipeline.py`.
- Implement frozen dataclasses for `TurnEvent` and `TurnPipelineResult`.
- Add `to_dict()` / `from_dict(...)` helpers.
- Add minimal validation for stage, status, certainty, and sides.
- Add fixture-level tests for serialization, defaults, invalid values, and `planning_only` semantics.
- Do not connect to `advisor_client.py`.
- Do not insert turn pipeline output into LLM payload.
- Do not implement item trigger evaluation.
- Do not implement item consumption, HP updates, speed simulation, or post-turn mutation.

Recommended file choice:

- `core/turn_event.py` if v5.1 only defines events/results.
- `core/turn_pipeline.py` later if actual pipeline orchestration is added.

This keeps the first implementation contract-only and avoids implying that a full engine exists.

## Safety

v5.0 is design-only.

- No production code was changed.
- No actual Gemini call was run.
- No Vertex AI call was run.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update logic was implemented.
- No speed/order simulation was implemented.
- No damage formula changed.
- No raw damage rolls changed.
- No Q12 multiplier changed.
- No `ko_context` calculation changed.
- No payload filtering behavior changed.
