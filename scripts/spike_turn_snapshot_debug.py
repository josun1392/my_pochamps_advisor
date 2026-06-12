"""Local TurnSnapshot dry-run report.

This script builds a deterministic fixture battle_input, converts it to a
TurnSnapshot, and verifies the optional advice payload adapter without making
any Gemini or Vertex AI call.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm.advisor_client import build_ui_advice_payload  # noqa: E402
from llm.advisor_damage_estimate import attach_selected_move_damage_estimate  # noqa: E402
from llm.advisor_payload_contract import TURN_SNAPSHOT_KNOWN_LIMITATIONS  # noqa: E402
from llm.advisor_turn_snapshot import (  # noqa: E402
    build_turn_snapshot_from_battle_input,
    try_build_turn_snapshot_from_battle_input,
)


def build_fixture_battle_input() -> dict[str, Any]:
    return {
        "scenario": {
            "mode": "ui-selected-pokemon-v0.18",
            "known_limitations": [
                "Move damage estimates, when present, use default assumptions and are not final battle damage.",
                "ko_context, when present, is limited damage-roll context only and is not final battle truth.",
            ],
        },
        "pokemon": {
            "my_active": {
                "slot_index": 0,
                "name_en": "charizard",
                "name_ko": "Charizard",
                "types": ["fire", "flying"],
                "types_ko": ["Fire", "Flying"],
                "base_stats": {
                    "hp": 78,
                    "attack": 84,
                    "defense": 78,
                    "special-attack": 109,
                    "special-defense": 85,
                    "speed": 100,
                },
                "abilities": ["blaze", "solar-power"],
                "abilities_ko": ["Blaze", "Solar Power"],
                "hp_percent": 88,
                "selected_move_index": 0,
            },
            "opponent_active": {
                "slot_index": 0,
                "name_en": "garchomp",
                "name_ko": "Garchomp",
                "types": ["dragon", "ground"],
                "types_ko": ["Dragon", "Ground"],
                "base_stats": {
                    "hp": 108,
                    "attack": 130,
                    "defense": 95,
                    "special-attack": 80,
                    "special-defense": 85,
                    "speed": 102,
                },
                "abilities": ["sand-veil", "rough-skin"],
                "abilities_ko": ["Sand Veil", "Rough Skin"],
                "hp_percent": 41,
                "selected_move_index": None,
            },
        },
        "item_profiles": {
            "my_active": {
                "status": "user_confirmed",
                "source": "user_input",
                "item_id": "choice-scarf",
                "name_en": "Choice Scarf",
                "name_ko": None,
                "effects_scope": ["speed_modifier"],
                "damage_modifier_status": "not_applied",
            },
            "opponent_active": {
                "status": "user_confirmed",
                "source": "user_input",
                "item_id": "focus-sash",
                "name_en": "Focus Sash",
                "name_ko": None,
                "effects_scope": ["survival"],
                "damage_modifier_status": "not_applicable",
            },
        },
        "moves": {
            "my_selected_move_index": 0,
            "my_available_moves": [_flamethrower()],
            "my_selected_move": _flamethrower(),
            "opponent_available_moves": [],
            "opponent_selected_move": None,
            "opponent_selected_move_index": None,
            "move_data_status": "turn_snapshot_debug_fixture_v4.8",
            "notes": [],
        },
    }


def build_turn_snapshot_debug_report() -> dict[str, Any]:
    battle_input = attach_selected_move_damage_estimate(build_fixture_battle_input())
    snapshot = build_turn_snapshot_from_battle_input(battle_input)
    payload_without_snapshot = build_ui_advice_payload(battle_input)
    payload_with_snapshot = build_ui_advice_payload(battle_input, turn_snapshot=snapshot)

    snapshot_payload_without_optional_fields = deepcopy(payload_with_snapshot)
    snapshot_payload_without_optional_fields.pop("turn_snapshot")
    for limitation in TURN_SNAPSHOT_KNOWN_LIMITATIONS:
        snapshot_payload_without_optional_fields["scenario"]["known_limitations"].remove(limitation)

    invalid_battle_input = deepcopy(battle_input)
    invalid_battle_input["pokemon"]["my_active"]["hp_percent"] = 120

    snapshot_dict = snapshot.to_dict()
    return {
        "report_version": "v4.8",
        "actual_gemini_call_executed": False,
        "vertex_ai_call_executed": False,
        "is_full_turn_engine_result": False,
        "turn_snapshot_built": True,
        "turn_snapshot": snapshot_dict,
        "summary": {
            "player_species": snapshot_dict["battle_state"]["active_player"]["species_id"],
            "opponent_species": snapshot_dict["battle_state"]["active_opponent"]["species_id"],
            "player_hp_percent": snapshot_dict["battle_state"]["active_player"]["current_hp_percent"],
            "opponent_hp_percent": snapshot_dict["battle_state"]["active_opponent"]["current_hp_percent"],
            "player_item": {
                "item_id": snapshot_dict["battle_state"]["active_player"]["known_item_id"],
                "status": snapshot_dict["battle_state"]["active_player"]["item_status"],
            },
            "opponent_item": {
                "item_id": snapshot_dict["battle_state"]["active_opponent"]["known_item_id"],
                "status": snapshot_dict["battle_state"]["active_opponent"]["item_status"],
            },
            "selected_move_id": snapshot_dict["turn_input"]["selected_move_id"],
        },
        "payload_checks": {
            "top_level_turn_snapshot_present": "turn_snapshot" in payload_with_snapshot,
            "turn_snapshot_absent_without_snapshot": "turn_snapshot" not in payload_without_snapshot,
            "limitations_guard_present": all(
                limitation in payload_with_snapshot["scenario"]["known_limitations"]
                for limitation in TURN_SNAPSHOT_KNOWN_LIMITATIONS
            ),
            "payload_matches_absent_after_removing_snapshot_fields": (
                snapshot_payload_without_optional_fields == payload_without_snapshot
            ),
            "fallback_helper_returns_none_for_invalid_hp": (
                try_build_turn_snapshot_from_battle_input(invalid_battle_input) is None
            ),
        },
        "non_goals": {
            "full_turn_engine": False,
            "item_trigger_evaluation": False,
            "item_consumption": False,
            "hp_update_logic": False,
            "speed_order_simulation": False,
        },
    }


def _flamethrower() -> dict[str, Any]:
    return {
        "slot": 0,
        "move_id": "flamethrower",
        "name_en": "Flamethrower",
        "name_ko": "Flamethrower",
        "type": "fire",
        "category": "special",
        "power": 90,
        "accuracy": 100,
        "source": "user_selected",
    }


def main() -> None:
    print(json.dumps(build_turn_snapshot_debug_report(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
