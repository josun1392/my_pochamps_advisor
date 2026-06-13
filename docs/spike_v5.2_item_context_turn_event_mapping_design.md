# v5.2 Item Context to TurnEvent Mapping Design

## Purpose

v5.1 added the standalone `core.turn_event` contract with `TurnEvent`, `TurnPipelineResult`, serialization, normalization, and validation. v5.2 designs how existing advisor payload surfaces can be mapped into `TurnEvent` candidates without changing runtime advice behavior.

This is design-only. No production code was changed. No actual Gemini call or Vertex AI call was run.

## Current Contract State

`TurnEvent` can represent:

- `candidate`
- `known_modifier`
- `not_simulated`
- `blocked`
- `unavailable`

Allowed stages:

- `pre_turn`
- `pre_move`
- `damage`
- `on_damage_before_ko`
- `on_hit_or_damage_dealt`
- `post_damage`
- `post_turn`

Allowed certainty values:

- `known`
- `likely`
- `possible`
- `unknown`
- `not_simulated`

`TurnPipelineResult` groups event candidates with optional references to existing primitives such as `damage_estimate` and `ko_context`. Its default `simulated` value is `none`.

## Mapping Principles

TurnEvent mapping should begin as a debug/planning layer:

- Do not replace existing item contexts.
- Do not connect to `advisor_client.py`.
- Do not insert events into the LLM payload.
- Do not change default advice filtering.
- Do not evaluate item triggers.
- Do not consume items or mutate HP.
- Do not simulate final move order.
- Preserve `damage_estimate` and `ko_context` as primitives.

The first mapper should read already-built payload/context dictionaries and emit `TurnEvent` candidates that summarize what the existing surfaces already say.

## Status and Certainty Policy

| Status | Meaning | Certainty guidance | Examples |
| --- | --- | --- | --- |
| `known_modifier` | The effect is already represented by a primitive calculation or deterministic context. | usually `known` | Light Ball applied in `damage_estimate.item_effects`, matching type-boost item already applied |
| `candidate` | Conditions suggest a possible trigger, but actual activation/result/consumption is unresolved. | usually `possible` or `likely` | Focus Band, Focus Sash, Quick Claw, Chilan Berry, resist berries |
| `not_simulated` | The context needs state/event machinery that does not exist yet. | `not_simulated` | Shell Bell, White Herb, Mental Herb, Loaded Dice full event modeling |
| `blocked` | Ruleset/legal/missing-engine gate prevents user-facing availability. | `unknown` or `not_simulated` | Champions legal gate, turn-engine-required gate |
| `unavailable` | Context is not present or `available=false`. | `unknown` | no matching item, item not confirmed, missing metadata |

`known_modifier` should be used sparingly. It is appropriate when the source-of-truth primitive already marks the modifier as applied. It should not mean final battle truth.

## Existing Context Inventory

| Surface | Current payload position | Related item/effect | Availability today | TurnEvent stage | Status | Certainty | Limitations | v5.3 mapping |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `damage_estimate` | move-level `damage_estimate` | damage rolls, type effectiveness, applied damage item effects | user-confirmed damaging move with sufficient stats | `damage` | `known_modifier` only for applied item effects; otherwise reference primitive | `known` for applied modifier | not final battle truth; no full turn effects | yes, reference source for known modifiers |
| `ko_context` | move-level `ko_context` | limited damage-roll KO context | damage rolls and target HP available | `damage` | reference primitive, not item trigger | `known` for roll math, not final outcome | no accuracy, speed, recovery, survival, hazards, turn sequencing | yes, ref only |
| `speed_context` | top-level `speed_context` | raw/effective Speed, Choice Scarf support | final Speed known; Choice Scarf only if supported/user-confirmed | `pre_move` | `known_modifier` for supported effective Speed, otherwise context ref | `known` for computed comparison | not final move order; no priority, Trick Room, ties, random activation | yes, ref/known modifier |
| `speed_order_context` | move-level item context | Quick Claw | user-confirmed legal Quick Claw | `pre_move` | `candidate` | `possible` | activation probability and final order not calculated | yes, early mapper target |
| `species_stat_item_context` | move-level item context | Light Ball on Pikachu | user-confirmed legal Light Ball, holder Pikachu, metadata, applied item_effects | `damage` | `known_modifier` | `known` | not exact final stats; not final KO truth | yes, early mapper target |
| `type_boost_context` | move-level item context | type-boosting damage items | user-confirmed legal item, matching move type, applied item_effects | `damage` | `known_modifier` when item_effects applied | `known` | context is explanatory; no new formula path | possible after early mapper |
| `survival_context` | move-level item context | Focus Sash / Focus Band | defender user-confirmed item, lethal context checks | `on_damage_before_ko` | `candidate` | `possible` | no activation probability, consumption, multi-hit, hazards, chip, sequencing | yes, Focus Band early mapper target; Focus Sash can follow |
| `resist_berry_context` | move-level item context | standard type-resist berries | defender user-confirmed legal berry, incoming type matches, super-effective hit | `on_damage_before_ko` | `candidate` | `possible` | raw damage and KO do not include berry reduction; no consumption | possible after early mapper |
| `chilan_berry_context` | move-level item context | Chilan Berry Normal-type special case | defender user-confirmed legal Chilan, Normal damaging move | `on_damage_before_ko` | `candidate` | `likely` | deterministic item rule, but actual trigger/consumption and adjusted damage are not simulated | yes, early mapper target |
| `recovery_context` | move-level item context | Sitrus Berry / Leftovers | defender user-confirmed item, max HP available | `post_damage` for Sitrus, `post_turn` for Leftovers | `candidate` or `not_simulated` | `possible` / `not_simulated` | exact threshold timing, consumption, sequencing, post-turn HP not modeled | later mapper |
| `accuracy_context` | move-level item context | Bright Powder | defender user-confirmed Bright Powder and move accuracy metadata | `pre_move` or `damage` boundary | `candidate` | `possible` | hit probability not integrated; accuracy/evasion stages not modeled | later mapper |
| `critical_context` | move-level item context | Scope Lens | attacker user-confirmed Scope Lens | `damage` | `candidate` | `possible` | crit probability and crit-adjusted KO not integrated | later mapper |
| `flinch_context` | move-level item context | King's Rock | attacker user-confirmed King's Rock | `on_hit_or_damage_dealt` | `candidate` | `possible` | final flinch probability, speed order, target action state not modeled | later mapper |
| `multi_hit_context` | move-level item context | Loaded Dice | helper exists; user-facing modeled context blocked until legal coverage | `on_hit_or_damage_dealt` | `not_simulated` or `blocked` | `not_simulated` | multi-hit count probability and adjusted KO not integrated | later mapper |

## Stage Mapping

### `pre_turn`

Source candidates:

- `turn_snapshot`
- selected known HP/item state

v5.3 should not focus here unless it needs an input event marker. This stage is mostly state context rather than item context.

### `pre_move`

Mappings:

- `speed_context` Choice Scarf effective Speed: `known_modifier`, `known`
- `speed_order_context` Quick Claw: `candidate`, `possible`
- `accuracy_context` Bright Powder: `candidate`, `possible`

Reasoning:

These surfaces influence pre-action reliability or order but do not prove final move order. Quick Claw must never become guaranteed order.

### `damage`

Mappings:

- `damage_estimate.item_effects` applied attacker item: `known_modifier`, `known`
- `species_stat_item_context` Light Ball: `known_modifier`, `known`
- `type_boost_context`: `known_modifier`, `known` when tied to applied item effects
- `critical_context` Scope Lens: `candidate`, `possible`
- `ko_context`: primitive reference, not a trigger result

Reasoning:

Light Ball is the clearest `known_modifier` because v3.1 aligned the context with applied `damage_estimate.item_effects`. Critical-hit context is not a known modifier because crit chance is not integrated.

### `on_damage_before_ko`

Mappings:

- `survival_context` Focus Sash: `candidate`, `possible`
- `survival_context` Focus Band: `candidate`, `possible`
- `resist_berry_context`: `candidate`, `possible`
- `chilan_berry_context`: `candidate`, `likely`

Reasoning:

These contexts are about survival or damage mitigation before fainting is finalized. They can be user-confirmed and rules-valid, but current payload does not simulate consumption, multi-hit interactions, chip, or adjusted final KO truth.

Chilan Berry should not be `known_modifier` in v5.3 because current raw rolls and `ko_context` explicitly do not include Chilan reduction. It can be `candidate` / `likely`: the item rule is deterministic for a matching Normal-type hit, but the pipeline does not yet execute the trigger or mutate item state.

### `on_hit_or_damage_dealt`

Mappings:

- Shell Bell future recovery: `not_simulated`, `not_simulated`
- `flinch_context` King's Rock: `candidate`, `possible`
- `multi_hit_context` Loaded Dice: `not_simulated` or `blocked`, `not_simulated`

Reasoning:

This stage requires hit result, damage dealt, target action state, and sometimes multi-hit event ordering. v5.3 can classify but should not resolve.

### `post_damage`

Mappings:

- Sitrus Berry / Oran-like healing berry: `candidate` or `not_simulated`, `possible` / `not_simulated`
- White Herb: `not_simulated`, `not_simulated`

Reasoning:

Threshold recovery and stat-drop correction require post-damage or stat-stage event state. v5.3 can point at existing `recovery_context` but should not calculate exact post-damage HP or consumption.

### `post_turn`

Mappings:

- Leftovers: `candidate`, `possible`
- residual/status/weather future hooks: `not_simulated`, `not_simulated`

Reasoning:

End-of-turn sequencing is not modeled. A TurnEvent can mark the stage but should not claim exact recovery timing or final HP.

## Early v5.3 Mapping Targets

Recommended first implementation targets:

1. Light Ball / `species_stat_item_context`
   - stage: `damage`
   - status: `known_modifier`
   - certainty: `known`
   - source: `item_context`
   - payload key: selected move `species_stat_item_context`

2. Quick Claw / `speed_order_context`
   - stage: `pre_move`
   - status: `candidate`
   - certainty: `possible`
   - source: `item_context`
   - payload key: selected move `speed_order_context`

3. Focus Band / `survival_context`
   - stage: `on_damage_before_ko`
   - status: `candidate`
   - certainty: `possible`
   - source: `item_context`
   - payload key: selected move `survival_context`

4. Chilan Berry / `chilan_berry_context`
   - stage: `on_damage_before_ko`
   - status: `candidate`
   - certainty: `likely`
   - source: `item_context`
   - payload key: selected move `chilan_berry_context`

These four are good first targets because they match the closed actual verification queue and represent the main event families: known damage modifier, move-order candidate, survival candidate, and mitigation candidate.

## Migration Path

v5.3 should add mapper tests without changing the advisor runtime:

```text
existing enriched/default payload or selected move context dict
  -> mapper helper
  -> tuple[TurnEvent, ...]
  -> fixture/test assertions only
```

Rules:

- Existing item context payloads remain unchanged.
- `TurnEvent` is additive debug/planning metadata.
- `advisor_client.py` remains disconnected.
- LLM payload remains unchanged.
- Unavailable/debug reasons remain debug-only and should map only in explicit debug/planning tests.
- User-facing exposure should be a separate v5.4+ decision.

## v5.3 MVP Recommendation

Recommended next milestone:

```text
v5.3 Item Context TurnEvent Mapper Implementation
```

Suggested implementation scope:

- Add `llm/advisor_turn_events.py`.
- Input: an already-built move/context dictionary or advice payload fragment.
- Output: `tuple[TurnEvent, ...]`.
- Map only available contexts for the first pass:
  - `species_stat_item_context` Light Ball
  - `speed_order_context` Quick Claw
  - `survival_context` Focus Band / Focus Sash
  - `chilan_berry_context` Chilan Berry
- Add fixture-level tests only.
- Do not connect to `advisor_client.py`.
- Do not add events to LLM payload.
- Do not implement full Turn Engine behavior.
- Do not evaluate triggers, consume items, mutate HP, simulate speed order, or change damage/KO calculations.

`llm/advisor_turn_events.py` is preferred over `core.turn_event_mapper` for v5.3 because the mapper reads advisor payload/context dictionary shapes, while `core.turn_event` should remain a UI/LLM-agnostic contract module.

## Safety

v5.2 is design-only.

- No production code was changed.
- No actual Gemini call was run.
- No Vertex AI call was run.
- No `advisor_client.py` connection was added.
- No LLM payload connection was added.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update logic was implemented.
- No speed/order simulation was implemented.
- No damage formula changed.
- No raw damage rolls changed.
- No Q12 multiplier changed.
- No `ko_context` calculation changed.
- No payload filtering behavior changed.
