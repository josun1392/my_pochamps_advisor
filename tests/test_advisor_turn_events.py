from __future__ import annotations

from llm.advisor_turn_events import (
    build_turn_events_from_advice_payload,
    build_turn_pipeline_result_from_advice_payload,
)


_FORBIDDEN_EVENT_WORDING = (
    "item was consumed",
    "exact trigger result",
    "exact post-turn HP",
    "guaranteed move order",
)


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
    assert "does not simulate item consumption" in event.limitations[0]


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
    assert "not resolved" in event.summary


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
    assert "not simulated" in event.summary


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
    assert "Item consumption" in event.limitations[0]


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
    assert "precise trigger outcome are not simulated" in event.summary


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


def test_available_context_with_unavailable_item_status_does_not_create_event() -> None:
    events = build_turn_events_from_advice_payload(
        {
            "speed_order_context": {
                "available": True,
                "attacker_side": "my_active",
                "item": {"item_id": "quick-claw", "status": "unavailable"},
            },
            "survival_context": {
                "available": True,
                "defender_side": "opponent_active",
                "item": {"item_id": "focus-band", "item_status": "blocked"},
            },
            "chilan_berry_context": {
                "available": True,
                "defender_side": "opponent_active",
                "item_id": "chilan-berry",
                "status": "deferred",
            },
        }
    )

    assert events == ()


def test_unknown_item_context_does_not_create_event() -> None:
    events = build_turn_events_from_advice_payload(
        {
            "survival_context": {
                "available": True,
                "defender_side": "opponent_active",
                "item": {"item_id": "leftovers", "status": "user_confirmed"},
            },
            "species_stat_item_context": {
                "available": True,
                "attacker_side": "my_active",
                "item": {"item_id": "thick-club", "status": "user_confirmed"},
            },
        }
    )

    assert events == ()


def test_malformed_optional_contexts_are_ignored() -> None:
    events = build_turn_events_from_advice_payload(
        {
            "species_stat_item_context": "not-a-context",
            "speed_order_context": None,
            "survival_context": ["not", "a", "context"],
            "chilan_berry_context": {
                "available": True,
                "defender_side": "opponent_active",
                "item": None,
            },
            "moves": {"my_available_moves": ["not-a-move", None]},
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
    assert [event.payload_key for event in events] == [
        "species_stat_item_context",
        "speed_order_context",
        "survival_context",
        "chilan_berry_context",
    ]


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


def test_event_summary_and_limitations_do_not_overstate_turn_results() -> None:
    events = build_turn_events_from_advice_payload(
        {
            "species_stat_item_context": {
                "available": True,
                "attacker_side": "my_active",
                "item": {"item_id": "light-ball"},
            },
            "speed_order_context": {
                "available": True,
                "attacker_side": "my_active",
                "item": {"item_id": "quick-claw"},
            },
            "survival_context": {
                "available": True,
                "defender_side": "opponent_active",
                "item": {"item_id": "focus-band"},
            },
            "chilan_berry_context": {
                "available": True,
                "defender_side": "opponent_active",
                "item": {"item_id": "chilan-berry"},
            },
        }
    )

    text = " ".join(
        part
        for event in events
        for part in (event.summary or "", *event.limitations)
    )
    lower_text = text.lower()

    for phrase in _FORBIDDEN_EVENT_WORDING:
        assert phrase.lower() not in lower_text
    assert "may affect" in lower_text
    assert "not resolved" in lower_text
    assert "not simulated" in lower_text


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


def test_turn_pipeline_result_from_payload_contains_stable_events() -> None:
    result = build_turn_pipeline_result_from_advice_payload(
        {
            "speed_order_context": {
                "available": True,
                "attacker_side": "my_active",
                "item": {"item_id": "quick-claw"},
            },
            "species_stat_item_context": {
                "available": True,
                "attacker_side": "my_active",
                "item": {"item_id": "light-ball"},
            },
            "survival_context": {
                "available": True,
                "defender_side": "opponent_active",
                "item": {"item_id": "focus-sash"},
            },
        },
        selected_move_id="thunderbolt",
        input_snapshot={"turn_input": {"acting_side": "player"}},
        damage_estimate_ref="moves.my_selected_move.damage_estimate",
        ko_context_ref="moves.my_selected_move.ko_context",
    )

    assert [event.item_id for event in result.events] == ["light-ball", "quick-claw", "focus-sash"]
    assert result.selected_move_id == "thunderbolt"
    assert result.damage_estimate_ref == "moves.my_selected_move.damage_estimate"
    assert result.ko_context_ref == "moves.my_selected_move.ko_context"
    assert result.simulated == "limited"
    assert result.simulated != "full"


def test_turn_pipeline_result_serializes_refs_and_limitations() -> None:
    result = build_turn_pipeline_result_from_advice_payload(
        {
            "chilan_berry_context": {
                "available": True,
                "defender_side": "opponent_active",
                "item": {"item_id": "chilan-berry"},
            }
        },
        selected_move_id="body-slam",
        damage_estimate_ref="damage_estimate",
        ko_context_ref="ko_context",
    )

    serialized = result.to_dict()

    assert serialized["selected_move_id"] == "body-slam"
    assert serialized["damage_estimate_ref"] == "damage_estimate"
    assert serialized["ko_context_ref"] == "ko_context"
    assert serialized["simulated"] == "limited"
    assert serialized["events"][0]["item_id"] == "chilan-berry"
    assert "not a full turn simulation" in " ".join(serialized["limitations"])
    assert "Item consumption is not simulated." in serialized["limitations"]
    assert "HP updates and exact post-turn state are not simulated." in serialized["limitations"]


def test_turn_pipeline_result_empty_payload_is_safe() -> None:
    result = build_turn_pipeline_result_from_advice_payload({})

    assert result.events == ()
    assert result.simulated == "limited"
    assert result.warnings == ("Unavailable, blocked, deferred, unknown, or malformed contexts do not create events.",)
    assert result.to_dict()["events"] == []


def test_turn_pipeline_result_helper_does_not_modify_payload_or_insert_llm_fields() -> None:
    payload = {
        "species_stat_item_context": {
            "available": True,
            "attacker_side": "my_active",
            "item": {"item_id": "light-ball"},
        }
    }
    before = {
        "species_stat_item_context": {
            "available": True,
            "attacker_side": "my_active",
            "item": {"item_id": "light-ball"},
        }
    }

    build_turn_pipeline_result_from_advice_payload(payload)

    assert payload == before
    assert "turn_pipeline" not in payload
    assert "turn_events" not in payload


def test_turn_pipeline_debug_fixture_output_shape() -> None:
    from scripts.spike_turn_pipeline_debug import build_turn_pipeline_debug_report

    report = build_turn_pipeline_debug_report()
    result = report["turn_pipeline_result"]

    assert report["actual_gemini_call_executed"] is False
    assert report["vertex_ai_call_executed"] is False
    assert report["is_full_turn_engine_result"] is False
    assert result["simulated"] == "limited"
    assert result["simulated"] != "full"
    assert [event["item_id"] for event in result["events"]] == [
        "light-ball",
        "quick-claw",
        "focus-sash",
        "chilan-berry",
    ]
    assert [event["stage"] for event in result["events"]] == [
        "damage",
        "pre_move",
        "on_damage_before_ko",
        "on_damage_before_ko",
    ]
    assert [event["status"] for event in result["events"]] == [
        "known_modifier",
        "candidate",
        "candidate",
        "candidate",
    ]
    assert [event["certainty"] for event in result["events"]] == [
        "known",
        "possible",
        "possible",
        "possible",
    ]
    limitations_text = " ".join(result["limitations"])
    assert "not a full turn simulation" in limitations_text
    assert "Item consumption is not simulated." in result["limitations"]
    assert "HP updates and exact post-turn state are not simulated." in result["limitations"]
