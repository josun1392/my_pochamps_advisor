"""Local TurnPipelineResult dry-run report.

This script builds a deterministic fixture advice payload, maps available item
contexts to TurnEvent candidates, and bundles them into a TurnPipelineResult
without making any Gemini or Vertex AI call.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm.advisor_turn_events import build_turn_pipeline_result_from_advice_payload  # noqa: E402


def build_fixture_advice_payload() -> dict[str, Any]:
    return {
        "moves": {
            "my_selected_move": {
                "move_id": "thunderbolt",
                "species_stat_item_context": {
                    "available": True,
                    "attacker_side": "my_active",
                    "item": {"item_id": "light-ball", "status": "user_confirmed"},
                },
                "speed_order_context": {
                    "available": True,
                    "attacker_side": "my_active",
                    "item": {"item_id": "quick-claw", "status": "user_confirmed"},
                },
                "survival_context": {
                    "available": True,
                    "defender_side": "opponent_active",
                    "item": {"item_id": "focus-sash", "status": "user_confirmed"},
                },
                "chilan_berry_context": {
                    "available": True,
                    "defender_side": "opponent_active",
                    "item": {"item_id": "chilan-berry", "status": "user_confirmed"},
                },
            },
            "my_available_moves": [
                {
                    "move_id": "quick-attack",
                    "speed_order_context": {
                        "available": False,
                        "reason": "item_not_user_confirmed",
                        "item": {"item_id": "quick-claw"},
                    },
                }
            ],
        }
    }


def build_turn_pipeline_debug_report() -> dict[str, Any]:
    result = build_turn_pipeline_result_from_advice_payload(
        build_fixture_advice_payload(),
        selected_move_id="thunderbolt",
        input_snapshot={"source": "fixture", "turn_input": {"acting_side": "player"}},
        damage_estimate_ref="moves.my_selected_move.damage_estimate",
        ko_context_ref="moves.my_selected_move.ko_context",
    )
    result_dict = result.to_dict()
    return {
        "report_version": "v5.6",
        "actual_gemini_call_executed": False,
        "vertex_ai_call_executed": False,
        "is_full_turn_engine_result": False,
        "turn_pipeline_result": result_dict,
        "summary": {
            "event_count": len(result.events),
            "event_items": [event.item_id for event in result.events],
            "event_stages": [event.stage for event in result.events],
            "simulated": result.simulated,
            "limitations": list(result.limitations),
        },
        "non_goals": {
            "advisor_client_connection": False,
            "llm_payload_connection": False,
            "full_turn_engine": False,
            "item_trigger_evaluation": False,
            "item_consumption": False,
            "hp_update_logic": False,
            "speed_order_simulation": False,
        },
    }


def main() -> None:
    print(json.dumps(build_turn_pipeline_debug_report(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
