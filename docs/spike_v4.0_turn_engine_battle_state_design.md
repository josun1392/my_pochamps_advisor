# v4.0 Turn Engine / Battle State Design

## Purpose

v3.2 closed the item context actual Gemini verification queue:

| Item / context | Final actual Gemini status |
|---|---|
| Focus Band / `survival_context` | PASS |
| Quick Claw / `speed_order_context` | PASS |
| Chilan Berry / `chilan_berry_context` | PASS |
| Light Ball / `species_stat_item_context` | PASS |

v3.4 then centralized item context guard metadata in `ADVICE_ITEM_CONTEXT_GUARD_METADATA` while preserving Light Ball, Chilan Berry, Choice Scarf, and unavailable-context filtering behavior.

The next broad step should not be another limited item context by default. Many remaining item candidates need turn timing, item consumption, HP updates, stat-stage updates, volatile conditions, and event order. This document proposes a minimum Turn Engine / Battle State design for PoChamps Advisor without implementing it yet.

This is design-only. No Gemini call, Vertex AI call, code implementation, new item implementation, payload filtering change, damage formula change, raw damage roll change, Q12 change, or `ko_context` change was made.

## Current Advisor State

The current advisor is centered on:

- selected active Pokemon
- selected move
- user-confirmed stat and item profiles
- damage estimates for confirmed moves
- limited additive `ko_context`
- item context helpers that explain specific available item effects
- prompt guard metadata for available item contexts

This is enough for limited advice contexts such as:

- Focus Band may sometimes affect survival.
- Quick Claw may occasionally affect move order.
- Chilan Berry is a Normal-type limited context.
- Light Ball is applied for user-confirmed Pikachu damage estimates.

It is not enough for full turn-state reasoning. The current payload does not own a durable battle state, event queue, item consumption ledger, post-damage HP update, stat-stage timeline, status/volatile timeline, or final turn-order result.

## Missing Battle State

The missing state is what blocks the next group of item mechanics:

- current HP before and after damage
- item status: held, consumed, disabled, revealed, unknown
- trigger timing inside a turn
- event order when multiple effects trigger
- post-damage recovery timing
- stat stage changes and restoration
- major status and volatile condition changes
- speed, priority, and activation effects that produce actual move order
- form and state changes

Without this state, adding more item contexts would keep producing limited explanatory notes rather than reliable battle-state conclusions.

## Minimum BattleState Candidate

Do not start by building a full Showdown-style engine. v4 should introduce only the state PoChamps Advisor needs to connect the existing selected-state UI to future trigger evaluation.

### `PokemonBattleSlot`

Candidate fields:

- `side`: `player` or `opponent`
- `species_id`
- `display_name`
- `level`
- `types`
- `current_hp_percent`
- `estimated_hp_range`
- `known_item`
- `item_status`: `unknown`, `held`, `consumed`, `none`, `disabled`
- `stat_stages`: attack, defense, special_attack, special_defense, speed, accuracy, evasion
- `major_status`: none, burn, paralysis, poison, toxic, sleep, freeze
- `volatile_conditions`: taunt, encore, confusion, flinch, trap, substitute, protect-like state, and similar known conditions
- `confirmed_final_stats`
- `source_notes`

### `BattleState`

Candidate fields:

- `active_player_pokemon`
- `active_opponent_pokemon`
- `field_state`
- `weather`
- `terrain`
- `room_effects`: Trick Room, Magic Room, Wonder Room
- `screens`
- `hazards`
- `turn_number`
- `last_turn_events`
- `known_battle_notes`

### `TurnInput`

Candidate fields:

- `actor_side`
- `selected_move`
- `target_side`
- `declared_item_context`
- `known_priority_context`
- `source`: UI selection, imported log, manual user confirmation

### `TurnSnapshot`

Candidate fields:

- `pre_turn_state`
- `turn_input`
- `order_context`
- `damage_estimate`
- `ko_context`
- `trigger_results`
- `post_damage_state_estimate`
- `consumption_results`
- `advice_payload_context`

The first implementation should prefer immutable snapshots over mutating a global battle object. That keeps the current advisor behavior easy to compare against pre-v4 outputs.

## Turn Engine Responsibilities

The Turn Engine should be split into narrow steps:

| Step | Responsibility | Initial scope |
|---|---|---|
| Pre-turn snapshot | Capture known HP, item, status, volatile, stat-stage, field, weather, terrain, and selected move state | schema only in v4.1 |
| Move choice input | Normalize selected move and target side | existing selected move can feed this |
| Speed/order context | Convert Speed, priority, Quick Claw, Choice Scarf, and field effects into an order context | keep limited; no final order in MVP |
| Damage estimate call | Reuse current damage estimate primitive | unchanged initially |
| Hit/KO context generation | Reuse current damage-roll-based `ko_context` | unchanged initially |
| Item trigger evaluation | Evaluate timing-specific triggers against the snapshot and damage result | design first, selective later |
| Post-damage update | Estimate HP after damage and after recovery triggers | not in v4.1 simulation |
| Item consumption update | Mark consumed items when a trigger result consumes them | schema first |
| Advisor payload generation | Add Turn Engine result to LLM payload without breaking existing item contexts | later staged integration |

The engine should produce structured results first. Natural-language advice should remain downstream of deterministic state and context outputs.

## Item Trigger Model

| Trigger family | Examples | Required state | Engine hook | Output | Existing context connection |
|---|---|---|---|---|---|
| Pre-move | Quick Claw, Choice Scarf speed influence | item status, Speed, priority, field/order effects | before move order resolution | order modifiers, activation candidates | `speed_context`, `speed_order_context` explain limited order uncertainty |
| On-damage-before-KO | Focus Sash, Focus Band, resist berries, Chilan Berry | pre-hit HP, incoming move type/category, item status, damage rolls, multi-hit state | after damage roll candidate, before KO finalization | survival or damage-reduction trigger result, possible consumption | `survival_context`, `resist_berry_context`, `chilan_berry_context` become trigger-result explanations |
| On-hit / on-damage-dealt | Shell Bell | actual damage dealt, post-hit HP, item status | after hit damage is applied | recovery amount and post-recovery HP estimate | `recovery_context` needs actual dealt damage instead of generic note |
| Post-damage HP threshold | Oran Berry, Sitrus Berry, other healing berries | post-damage HP percent/range, item status | after damage and before next event window | recovery trigger and consumption | `recovery_context` becomes threshold-trigger explanation |
| On-stat-drop | White Herb | stat-stage delta, item status, source of drop | after stat-stage lowering event | restored stages and consumption | needs stat-stage event tracking |
| On-status/volatile | Mental Herb | major/volatile condition event, item status | after volatile/status is applied or would be applied | cured/prevented condition and consumption | needs condition timeline |
| Form/state | Mega Stones | species/form eligibility, item status, turn timing | pre-action or battle-start form state depending on rules | form transition and updated stats/types/ability | needs form subsystem, not a limited item note |
| Multi-hit event | Loaded Dice, Focus Sash interactions | hit-count distribution, per-hit damage, item status, per-hit HP | during hit loop | hit-count result and per-hit trigger sequence | `multi_hit_context` needs event modeling |

## Existing Context Migration Path

The existing item context system should remain in place during v4 migration.

Recommended migration:

1. Keep damage estimate as the calculation primitive.
2. Keep `ko_context` as limited damage-roll context.
3. Keep current item contexts and default advice filtering.
4. Introduce Turn Engine snapshots beside the existing payload, not inside every helper immediately.
5. Let trigger results gradually become the source for contexts that currently have limited wording.
6. Keep prompt guard metadata registry-backed so new trigger-result contexts can reuse the same visible-available-context policy.

Future role changes:

- Focus Band / Focus Sash: from "may survive" note to explanation of an on-damage-before-KO trigger candidate or result.
- Quick Claw: from move-order note to explanation of pre-move activation/order uncertainty.
- Chilan Berry / resist berries: from limited item context to damage-reduction trigger result once consumption and hit timing exist.
- Shell Bell / healing berries: should wait for post-damage HP and item consumption.
- Light Ball: remains a damage-estimate item effect sibling explanation and does not require Turn Engine for the current scope.

## v4.1 MVP Recommendation

Recommended next milestone:

```text
v4.1 Turn State Snapshot Contract
```

Scope:

- Add a `BattleState` / `TurnSnapshot` contract or dataclass layer.
- Include item status, HP percent/range, stat stages, major status, volatile conditions, field/weather/terrain, turn number, and selected move input.
- Build tests that serialize the snapshot without changing current damage estimate behavior.
- Do not implement full turn simulation.
- Do not change raw damage rolls, `ko_context`, or item-context filtering.
- Keep current UI-selected payload behavior as the source feeding the first snapshot.

Why this MVP:

- It creates a stable state container before item triggers mutate behavior.
- It lets future Shell Bell / healing berry / White Herb / Mental Herb work share one source of truth.
- It avoids mixing stateful battle updates into current damage estimate helpers.
- It gives tests a contract boundary before adding trigger logic.

## v4.2+ Candidate Sequence

After v4.1:

1. `v4.2 Item Trigger Result Contract`
   - Define trigger result objects, timing windows, item consumption fields, and confidence/source labels.
2. `v4.3 Post-Damage HP Snapshot`
   - Connect damage rolls to estimated post-damage HP ranges without changing final battle truth.
3. `v4.4 Healing Berry / Shell Bell Design`
   - Use post-damage HP and damage-dealt state.
4. `v4.5 Stat Stage / Volatile Trigger Design`
   - Prepare White Herb and Mental Herb.
5. `v5.0 Turn Engine Simulation MVP`
   - Evaluate a narrow single-action turn sequence once contracts are stable.

## Risks and Open Questions

- HP percent precision may be too coarse for threshold berries unless the UI captures exact HP or a reliable range.
- Damage rolls are estimates, so trigger results may need `possible`, `guaranteed`, `not_possible`, and `unknown` states instead of a single boolean.
- Item consumption must not be committed as battle truth unless the triggering event is confirmed.
- Quick Claw and Focus Band include activation probability; current advice should not convert them into deterministic outcomes.
- Multi-hit moves need per-hit event ordering before Focus Sash, Focus Band, Loaded Dice, and berries can be fully modeled.
- Stat-stage and volatile condition names should be normalized before Mental Herb / White Herb implementation.
- Form/state changes need a separate identity/stat recalculation path and should not be bolted onto item context wording.

## Non-Goals

- No full Pokemon battle simulator in v4.1.
- No Showdown parity target in the first pass.
- No new item implementation in this design.
- No actual Gemini verification in this design.
- No Vertex AI call in this design.
- No damage formula, raw damage roll, Q12, `ko_context`, or payload filtering change in this design.
