# v5.6 TurnPipeline Debug Report Sample

## Purpose

This document records a local dry-run report for the TurnEvent / TurnPipelineResult fixture path.

No actual Gemini call was executed. No Vertex AI call was executed. This is not a full Turn Engine result.

## How to Reproduce

```bash
uv run python scripts/spike_turn_pipeline_debug.py
```

The script builds a deterministic fixture advice payload, maps available item contexts to `TurnEvent` candidates, bundles those events into `TurnPipelineResult`, and prints JSON to stdout.

## Sample Fixture Summary

- selected move: `thunderbolt`
- damage estimate ref: `moves.my_selected_move.damage_estimate`
- ko context ref: `moves.my_selected_move.ko_context`
- included available contexts:
  - Light Ball `species_stat_item_context`
  - Quick Claw `speed_order_context`
  - Focus Sash `survival_context`
  - Chilan Berry `chilan_berry_context`
- included unavailable fixture context:
  - unavailable Quick Claw context under `moves.my_available_moves[0]`, which does not create an event

## Generated TurnPipelineResult Summary

```json
{
  "report_version": "v5.6",
  "actual_gemini_call_executed": false,
  "vertex_ai_call_executed": false,
  "is_full_turn_engine_result": false,
  "summary": {
    "event_count": 4,
    "event_items": [
      "light-ball",
      "quick-claw",
      "focus-sash",
      "chilan-berry"
    ],
    "event_stages": [
      "damage",
      "pre_move",
      "on_damage_before_ko",
      "on_damage_before_ko"
    ],
    "simulated": "limited"
  }
}
```

## Events

| stage | status | certainty | item_id | payload_key | summary |
|---|---|---|---|---|---|
| `damage` | `known_modifier` | `known` | `light-ball` | `moves.my_selected_move.species_stat_item_context` | Light Ball is represented as a known Pikachu damage modifier in the advisor estimate. |
| `pre_move` | `candidate` | `possible` | `quick-claw` | `moves.my_selected_move.speed_order_context` | Quick Claw may affect move order, but activation is not resolved by the Turn Engine yet. |
| `on_damage_before_ko` | `candidate` | `possible` | `focus-sash` | `moves.my_selected_move.survival_context` | Focus Sash may affect survival before KO, but the trigger result is not simulated. |
| `on_damage_before_ko` | `candidate` | `possible` | `chilan-berry` | `moves.my_selected_move.chilan_berry_context` | Chilan Berry can reduce Normal-type damage, but consumption and the precise trigger outcome are not simulated. |

## Limitations

- This result is a limited planning summary, not a full turn simulation.
- Item consumption is not simulated.
- HP updates and exact post-turn state are not simulated.

## Safety Notes

- `simulated` is `limited`, not `full`.
- `damage_estimate_ref` and `ko_context_ref` are references only.
- No item trigger evaluation is performed.
- No item consumption is performed.
- No HP update or post-turn state update is performed.
- No speed/order simulation is performed.
- The dry run does not call Gemini or Vertex AI.
- The dry run does not inspect environment variables, API keys, token logs, credentials, or billing details.
- The dry run does not connect to `advisor_client.py` and does not insert `TurnPipelineResult` into the LLM payload.
