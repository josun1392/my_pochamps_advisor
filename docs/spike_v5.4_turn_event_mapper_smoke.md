# v5.4 TurnEvent Mapper Smoke / Fixture Coverage Expansion

## Purpose

v5.4 expands smoke and fixture coverage for the v5.3 item-context-to-`TurnEvent` mapper before any runtime payload exposure. The mapper remains a local planning/debug helper only.

## Coverage Added

The mapper tests now cover:

- Light Ball `species_stat_item_context` -> `damage` / `known_modifier` / `known`
- Quick Claw `speed_order_context` -> `pre_move` / `candidate` / `possible`
- Focus Band `survival_context` -> `on_damage_before_ko` / `candidate` / `possible`
- Focus Sash `survival_context` -> `on_damage_before_ko` / `candidate` / `possible`
- Chilan Berry `chilan_berry_context` -> `on_damage_before_ko` / `candidate` / `possible`

## Negative Cases

No event is created for:

- `available=false`
- item/status `unavailable`
- item/status `blocked`
- item/status `deferred`
- unknown item ids
- malformed optional context shapes

## Ordering

Event order remains stable:

1. `species_stat_item_context`
2. `speed_order_context`
3. `survival_context`
4. `chilan_berry_context`

## Safety Wording

Fixture checks verify that event summaries and limitations do not claim:

- item consumption happened
- exact post-turn HP
- guaranteed move order
- full turn simulation

Events remain phrased as candidates, known modifiers, or not-resolved planning notes.

## Boundaries

v5.4 does not:

- connect to `advisor_client.py`
- add events to the LLM payload
- create or connect `TurnPipelineResult`
- implement full Turn Engine behavior
- evaluate item triggers
- consume items
- update HP
- simulate speed/order
- change damage formula, raw damage rolls, Q12 multipliers, `ko_context`, or payload filtering
- run actual Gemini or Vertex AI calls

