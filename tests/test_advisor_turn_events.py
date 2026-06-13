from __future__ import annotations

from llm.advisor_turn_events import build_turn_events_from_advice_payload


def test_light_ball_context_maps_to_damage_known_modifier_event() -> None:
    events = build_turn_events_from_advice_payload(
        {
            "species_stat_item_context": {
                "available": True,
                "attacker_side": "my_active",
                "item": {"item_id": "light-ball", "status": "user_confirmed"},
            }
        }
    )

    assert len(events) == 1
    event = events[0]
    assert event.stage == "damage"
    assert event.status == "known_modifier"
    assert event.certainty == "known"
    assert event.item_id == "light-ball"
    assert event.trigger_type == "species_stat_modifier"
    assert event.subject_side == "player"
    assert event.payload_key == "species_stat_item_context"
    assert event.to_dict()["summary"] == "Light Ball is represented as a known Pikachu damage modifier in the advisor estimate."


def test_quick_claw_context_maps_to_pre_move_candidate_event() -> None:
    events = build_turn_events_from_advice_payload(
        {
            "speed_order_context": {
                "available": True,
                "attacker_side": "my_active",
                "item": {"item_id": "quick-claw", "status": "user_confirmed"},
            }
        }
    )

    assert len(events) == 1
    event = events[0]
    assert event.stage == "pre_move"
    assert event.status == "candidate"
    assert event.certainty == "possible"
    assert event.item_id == "quick-claw"
    assert event.trigger_type == "priority_or_move_order_chance"
    assert event.payload_key == "speed_order_context"


def test_focus_band_context_maps_to_survival_candidate_event() -> None:
    events = build_turn_events_from_advice_payload(
        {
            "survival_context": {
                "available": True,
                "defender_side": "opponent_active",
                "item": {"item_id": "focus-band", "status": "user_confirmed"},
            }
        }
    )

    assert len(events) == 1
    event = events[0]
    assert event.stage == "on_damage_before_ko"
    assert event.status == "candidate"
    assert event.certainty == "possible"
    assert event.item_id == "focus-band"
    assert event.trigger_type == "survival_before_ko"
    assert event.subject_side == "opponent"


def test_focus_sash_context_maps_to_survival_candidate_event() -> None:
    events = build_turn_events_from_advice_payload(
        {
            "survival_context": {
                "available": True,
                "defender_side": "opponent_active",
                "item": {"item_id": "focus-sash", "status": "user_confirmed"},
            }
        }
    )

    assert len(events) == 1
    event = events[0]
    assert event.stage == "on_damage_before_ko"
    assert event.status == "candidate"
    assert event.certainty == "possible"
    assert event.item_id == "focus-sash"
    assert event.trigger_type == "survival_before_ko"


def test_chilan_berry_context_maps_to_damage_reduction_candidate_event() -> None:
    events = build_turn_events_from_advice_payload(
        {
            "chilan_berry_context": {
                "available": True,
                "defender_side": "opponent_active",
                "item": {"item_id": "chilan-berry", "status": "user_confirmed"},
            }
        }
    )

    assert len(events) == 1
    event = events[0]
    assert event.stage == "on_damage_before_ko"
    assert event.status == "candidate"
    assert event.certainty == "possible"
    assert event.item_id == "chilan-berry"
    assert event.trigger_type == "normal_type_damage_reduction"
    assert "ko_context" in event.limitations[0]


def test_unavailable_context_does_not_create_event() -> None:
    events = build_turn_events_from_advice_payload(
        {
            "speed_order_context": {
                "available": False,
                "reason": "item_not_user_confirmed",
                "item": {"item_id": "quick-claw"},
            }
        }
    )

    assert events == ()


def test_blocked_or_deferred_context_does_not_create_event() -> None:
    events = build_turn_events_from_advice_payload(
        {
            "chilan_berry_context": {
                "available": False,
                "reason": "blocked_by_ruleset",
                "item": {"item_id": "chilan-berry"},
            },
            "species_stat_item_context": {
                "available": False,
                "reason": "deferred_until_damage_estimate",
                "item": {"item_id": "light-ball"},
            },
        }
    )

    assert events == ()


def test_multiple_contexts_return_events_in_stable_order() -> None:
    events = build_turn_events_from_advice_payload(
        {
            "survival_context": {
                "available": True,
                "defender_side": "opponent_active",
                "item": {"item_id": "focus-band"},
            },
            "species_stat_item_context": {
                "available": True,
                "attacker_side": "my_active",
                "item": {"item_id": "light-ball"},
            },
            "chilan_berry_context": {
                "available": True,
                "defender_side": "opponent_active",
                "item": {"item_id": "chilan-berry"},
            },
            "speed_order_context": {
                "available": True,
                "attacker_side": "my_active",
                "item": {"item_id": "quick-claw"},
            },
        }
    )

    assert [event.item_id for event in events] == ["light-ball", "quick-claw", "focus-band", "chilan-berry"]


def test_move_payload_under_advice_payload_maps_with_payload_paths() -> None:
    events = build_turn_events_from_advice_payload(
        {
            "moves": {
                "my_selected_move": {
                    "species_stat_item_context": {
                        "available": True,
                        "attacker_side": "my_active",
                        "item": {"item_id": "light-ball"},
                    }
                },
                "my_available_moves": [
                    {
                        "speed_order_context": {
                            "available": True,
                            "attacker_side": "my_active",
                            "item": {"item_id": "quick-claw"},
                        }
                    }
                ],
            }
        }
    )

    assert [event.payload_key for event in events] == [
        "moves.my_selected_move.species_stat_item_context",
        "moves.my_available_moves[0].speed_order_context",
    ]


def test_event_serialization_from_mapper_output() -> None:
    events = build_turn_events_from_advice_payload(
        {
            "speed_order_context": {
                "available": True,
                "attacker_side": "my_active",
                "item": {"item_name": "Quick Claw"},
            }
        }
    )

    assert events[0].to_dict()["item_id"] == "quick-claw"
    assert events[0].to_dict()["stage"] == "pre_move"


def test_mapper_does_not_modify_input_payload() -> None:
    payload = {
        "speed_order_context": {
            "available": True,
            "attacker_side": "my_active",
            "item": {"item_id": "quick-claw"},
        }
    }

    before = {
        "speed_order_context": {
            "available": True,
            "attacker_side": "my_active",
            "item": {"item_id": "quick-claw"},
        }
    }

    build_turn_events_from_advice_payload(payload)

    assert payload == before
    assert "turn_events" not in payload
