from __future__ import annotations

import pytest

from core.turn_event import (
    TurnEvent,
    TurnPipelineResult,
    normalize_turn_event,
    normalize_turn_pipeline_result,
)


def test_turn_event_serializes_contract_fields() -> None:
    event = TurnEvent(
        stage="on_damage_before_ko",
        source="item_context",
        subject_side="player",
        target_side="opponent",
        item_id="focus-band",
        trigger_type="random_survival_item",
        status="candidate",
        certainty="possible",
        summary="Focus Band may occasionally survive a lethal hit.",
        limitations=["activation is not resolved", "item consumption is not simulated"],
        payload_key="moves.my_selected_move.survival_context",
    )

    assert event.to_dict() == {
        "stage": "on_damage_before_ko",
        "source": "item_context",
        "subject_side": "player",
        "target_side": "opponent",
        "item_id": "focus-band",
        "trigger_type": "random_survival_item",
        "status": "candidate",
        "certainty": "possible",
        "summary": "Focus Band may occasionally survive a lethal hit.",
        "limitations": ["activation is not resolved", "item consumption is not simulated"],
        "payload_key": "moves.my_selected_move.survival_context",
    }


def test_turn_event_from_dict_round_trips_unknown_values() -> None:
    event = TurnEvent.from_dict(
        {
            "stage": "pre_move",
            "source": None,
            "subject_side": "unknown",
            "target_side": None,
            "item_id": None,
            "trigger_type": None,
            "status": "not_simulated",
            "certainty": "unknown",
            "summary": None,
            "limitations": [],
            "payload_key": None,
        }
    )

    assert event.subject_side == "unknown"
    assert event.target_side is None
    assert event.limitations == ()
    assert event.to_dict()["certainty"] == "unknown"


def test_turn_event_invalid_stage_raises() -> None:
    with pytest.raises(ValueError):
        TurnEvent(stage="pre_damage", status="candidate", certainty="possible")


def test_turn_event_invalid_status_raises() -> None:
    with pytest.raises(ValueError):
        TurnEvent(stage="damage", status="resolved", certainty="known")


def test_turn_event_invalid_certainty_raises() -> None:
    with pytest.raises(ValueError):
        TurnEvent(stage="damage", status="known_modifier", certainty="guaranteed")


def test_turn_event_invalid_side_raises() -> None:
    with pytest.raises(ValueError):
        TurnEvent(stage="pre_move", status="candidate", certainty="possible", subject_side="bench")

    with pytest.raises(ValueError):
        TurnEvent(stage="pre_move", status="candidate", certainty="possible", target_side="bench")


def test_turn_event_normalizes_limitations_list_to_tuple() -> None:
    event = TurnEvent(
        stage="post_damage",
        status="not_simulated",
        certainty="not_simulated",
        limitations=["no hp update"],
    )

    assert event.limitations == ("no hp update",)


def test_turn_pipeline_result_serializes_defaults_without_full_simulation() -> None:
    result = TurnPipelineResult()

    assert result.to_dict() == {
        "input_snapshot": None,
        "selected_move_id": None,
        "damage_estimate_ref": None,
        "ko_context_ref": None,
        "events": [],
        "warnings": [],
        "limitations": [],
        "simulated": "none",
    }
    assert result.simulated != "full"


def test_turn_pipeline_result_from_dict_normalizes_event_dicts() -> None:
    result = TurnPipelineResult.from_dict(
        {
            "input_snapshot": {"turn_input": {"selected_move_id": "tackle"}},
            "selected_move_id": "tackle",
            "damage_estimate_ref": "moves.my_selected_move.damage_estimate",
            "ko_context_ref": "moves.my_selected_move.ko_context",
            "events": [
                {
                    "stage": "damage",
                    "source": "damage_estimate",
                    "subject_side": "player",
                    "target_side": "opponent",
                    "item_id": "light-ball",
                    "trigger_type": "species_stat_damage_modifier",
                    "status": "known_modifier",
                    "certainty": "known",
                    "summary": "Light Ball is already reflected in the estimate.",
                    "limitations": ["not final KO truth"],
                    "payload_key": "moves.my_selected_move.damage_estimate.item_effects",
                }
            ],
            "warnings": ["planning only"],
            "limitations": ["no item consumption"],
            "simulated": "limited",
        }
    )

    assert result.events[0].stage == "damage"
    assert result.events[0].status == "known_modifier"
    assert result.warnings == ("planning only",)
    assert result.limitations == ("no item consumption",)
    assert result.to_dict()["events"][0]["item_id"] == "light-ball"


def test_turn_pipeline_result_accepts_turn_event_instances() -> None:
    event = TurnEvent(stage="pre_move", status="candidate", certainty="possible", item_id="quick-claw")
    result = TurnPipelineResult(events=[event])

    assert result.events == (event,)
    assert result.to_dict()["events"][0]["item_id"] == "quick-claw"


def test_turn_pipeline_result_invalid_event_type_raises() -> None:
    with pytest.raises(ValueError):
        TurnPipelineResult(events=["not-an-event"])  # type: ignore[list-item]


def test_turn_pipeline_result_invalid_simulated_raises() -> None:
    with pytest.raises(ValueError):
        TurnPipelineResult(simulated="engine_truth")


def test_warnings_and_limitations_normalize_to_tuples() -> None:
    result = TurnPipelineResult(warnings=["planning only"], limitations=["no hp mutation"])

    assert result.warnings == ("planning only",)
    assert result.limitations == ("no hp mutation",)


def test_normalizers_accept_mapping_or_instances() -> None:
    event = TurnEvent(stage="damage", status="known_modifier", certainty="known")
    result = TurnPipelineResult(events=[event], simulated="limited")

    assert normalize_turn_event(event) is event
    assert normalize_turn_event(event.to_dict()).to_dict() == event.to_dict()
    assert normalize_turn_pipeline_result(result) is result
    assert normalize_turn_pipeline_result(result.to_dict()).to_dict() == result.to_dict()
    assert normalize_turn_pipeline_result().simulated == "none"


def test_contract_does_not_mutate_hp_or_consume_items() -> None:
    snapshot = {
        "battle_state": {
            "active_player": {
                "side": "player",
                "current_hp_percent": 25,
                "known_item_id": "sitrus-berry",
                "item_status": "user_confirmed",
            }
        }
    }
    event = TurnEvent(
        stage="post_damage",
        item_id="sitrus-berry",
        trigger_type="hp_threshold_recovery",
        status="candidate",
        certainty="possible",
        limitations=["item consumption is not simulated", "post-damage HP is not updated"],
    )
    result = TurnPipelineResult(input_snapshot=snapshot, events=[event])

    assert result.input_snapshot["battle_state"]["active_player"]["current_hp_percent"] == 25
    assert result.input_snapshot["battle_state"]["active_player"]["item_status"] == "user_confirmed"
    assert "current_hp_percent" not in event.to_dict()
    assert "consumed" not in event.to_dict()
