# v4.8 TurnSnapshot Dry-run Debug Sample

## Purpose

This document records a local dry-run report for the TurnSnapshot UI path.

No actual Gemini call was executed. No Vertex AI call was executed. This is not a full Turn Engine result.

## How to Reproduce

```bash
uv run python scripts/spike_turn_snapshot_debug.py
```

The script uses a deterministic fixture `battle_input`, builds a `TurnSnapshot`, attaches it through `build_ui_advice_payload(..., turn_snapshot=...)`, and checks that removing the optional snapshot section plus snapshot limitations returns the same payload as the absent snapshot path.

## Summary

```json
{
  "report_version": "v4.8",
  "actual_gemini_call_executed": false,
  "vertex_ai_call_executed": false,
  "is_full_turn_engine_result": false,
  "turn_snapshot_built": true,
  "summary": {
    "player_species": "charizard",
    "opponent_species": "garchomp",
    "player_hp_percent": 88,
    "opponent_hp_percent": 41,
    "player_item": {
      "item_id": "choice-scarf",
      "status": "user_confirmed"
    },
    "opponent_item": {
      "item_id": "focus-sash",
      "status": "user_confirmed"
    },
    "selected_move_id": "flamethrower"
  },
  "payload_checks": {
    "top_level_turn_snapshot_present": true,
    "turn_snapshot_absent_without_snapshot": true,
    "limitations_guard_present": true,
    "payload_matches_absent_after_removing_snapshot_fields": true,
    "fallback_helper_returns_none_for_invalid_hp": true
  },
  "non_goals": {
    "full_turn_engine": false,
    "item_trigger_evaluation": false,
    "item_consumption": false,
    "hp_update_logic": false,
    "speed_order_simulation": false
  }
}
```

## Normalized TurnSnapshot

```json
{
  "battle_state": {
    "active_player": {
      "side": "player",
      "slot_index": 0,
      "species_id": "charizard",
      "species_name": "Charizard",
      "current_hp_percent": 88,
      "known_item_id": "choice-scarf",
      "item_status": "user_confirmed",
      "stat_stages": {},
      "major_status": null,
      "volatile_conditions": []
    },
    "active_opponent": {
      "side": "opponent",
      "slot_index": 0,
      "species_id": "garchomp",
      "species_name": "Garchomp",
      "current_hp_percent": 41,
      "known_item_id": "focus-sash",
      "item_status": "user_confirmed",
      "stat_stages": {},
      "major_status": null,
      "volatile_conditions": []
    },
    "weather": null,
    "terrain": null,
    "field_conditions": {},
    "turn_number": null
  },
  "turn_input": {
    "selected_move_id": "flamethrower",
    "acting_side": "player",
    "target_side": "opponent"
  },
  "notes": [
    "Built from UI-selected battle_input."
  ],
  "limitations": [
    "No full turn simulation.",
    "No item trigger evaluation.",
    "No item consumption.",
    "No post-damage HP update.",
    "No speed/order simulation."
  ]
}
```

## Safety Notes

- `turn_snapshot` is selected/pre-turn known state only.
- The dry run does not call Gemini or Vertex AI.
- The dry run does not inspect environment variables, API keys, token logs, credentials, or billing details.
- Damage estimates, raw damage rolls, Q12 multipliers, `ko_context`, item contexts, and payload filtering are unchanged by the snapshot except for the optional top-level `turn_snapshot` section and snapshot limitations.
- Full Turn Engine behavior, item trigger evaluation, item consumption, HP updates, and speed/order simulation remain unimplemented.
