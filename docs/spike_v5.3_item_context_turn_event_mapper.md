# v5.3 Item Context TurnEvent Mapper

## Purpose

v5.3 adds a helper-level bridge from existing advisor item context dictionaries to `TurnEvent` candidates. This is a planning/debug layer only. It does not replace existing item contexts, does not connect to `advisor_client.py`, and does not add `turn_events` to the LLM payload.

## Added Module

- `llm/advisor_turn_events.py`
- Public helper: `build_turn_events_from_advice_payload(payload)`
- Output: `tuple[TurnEvent, ...]`

The helper accepts either a move/context dictionary or an advice payload fragment containing `moves.my_selected_move` and `moves.my_available_moves[*]`.

## First Mapping Scope

| Context | Item | Stage | Status | Certainty | Trigger type |
|---|---|---|---|---|---|
| `species_stat_item_context` | Light Ball | `damage` | `known_modifier` | `known` | `species_stat_modifier` |
| `speed_order_context` | Quick Claw | `pre_move` | `candidate` | `possible` | `priority_or_move_order_chance` |
| `survival_context` | Focus Band | `on_damage_before_ko` | `candidate` | `possible` | `survival_before_ko` |
| `survival_context` | Focus Sash | `on_damage_before_ko` | `candidate` | `possible` | `survival_before_ko` |
| `chilan_berry_context` | Chilan Berry | `on_damage_before_ko` | `candidate` | `possible` | `normal_type_damage_reduction` |

Focus Sash remains `candidate` in v5.3 because exact HP, hit result, multi-hit handling, item consumption, and post-damage state are not simulated.

## Availability Policy

Only `available=true` contexts create events. Unavailable, blocked, or deferred contexts create no event in v5.3. This keeps the mapper aligned with the existing default advice payload policy and avoids surfacing debug-only item context reasons as user-facing planning events.

## Event Ordering

Events are emitted in stable context order:

1. `species_stat_item_context`
2. `speed_order_context`
3. `survival_context`
4. `chilan_berry_context`

When the helper reads nested move payloads, `payload_key` preserves the source path, such as `moves.my_selected_move.species_stat_item_context`.

## Boundaries

v5.3 does not:

- connect events to `advisor_client.py`
- insert events into the LLM payload
- create or connect `TurnPipelineResult`
- evaluate item triggers
- consume items
- update HP
- simulate speed order
- modify damage formula, raw damage rolls, Q12 multipliers, `ko_context`, or payload filtering
- run actual Gemini or Vertex AI calls

## Verification

Fixture tests cover available Light Ball, Quick Claw, Focus Band, Focus Sash, and Chilan Berry mapping; unavailable/blocked/deferred omission; stable ordering; nested payload keys; serialization; and input immutability.

