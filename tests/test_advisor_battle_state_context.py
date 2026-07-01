from __future__ import annotations

from llm.advisor_battle_state_context import (
    BATTLE_STATE_CONTEXT_FORBIDDEN_FIELDS,
    BATTLE_STATE_CONTEXT_UNSUPPORTED_BOUNDARIES,
    BATTLE_STATE_CONTEXT_UNKNOWN_FIELD,
    build_battle_state_context,
    build_battle_state_context_from_ui_selected_state,
)


def test_empty_input_returns_unknown_battle_state_context_without_inference() -> None:
    context = build_battle_state_context()

    assert context["kind"] == "battle_state_context"
    assert context["confidence"] == "unknown"
    assert context["self_active"] == _unknown_active_side()
    assert context["opponent_active"] == _unknown_active_side()
    assert context["field"] == _unknown_field_state()
    assert context["known_conditions"] == []
    _assert_required_unsupported_boundaries(context)
    _assert_required_safety_notes(context)
    _assert_no_forbidden_fields(context)


def test_visible_species_and_hp_produce_limited_context() -> None:
    context = build_battle_state_context(
        self_active={
            "species": {"source": "visible_ui", "name": "Garchomp"},
            "current_hp_percent": {"source": "visible_ui", "value": 100},
        },
        opponent_active={
            "species": {"source": "visible_ui", "name": "Charizard"},
            "current_hp_percent": {"source": "visible_ui", "value": 87},
        },
    )

    assert context["confidence"] == "limited"
    assert context["self_active"]["species"] == {"source": "visible_ui", "name": "Garchomp"}
    assert context["self_active"]["current_hp_percent"] == {"source": "visible_ui", "value": 100}
    assert context["opponent_active"]["species"] == {"source": "visible_ui", "name": "Charizard"}
    assert context["opponent_active"]["current_hp_percent"] == {"source": "visible_ui", "value": 87}
    assert context["self_active"]["status"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["self_active"]["boosts"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["self_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD


def test_active_and_field_sections_keep_required_keys() -> None:
    context = build_battle_state_context()

    assert set(context["self_active"]) == {"species", "current_hp_percent", "status", "boosts", "item"}
    assert set(context["opponent_active"]) == {"species", "current_hp_percent", "status", "boosts", "item"}
    assert set(context["field"]) == {"weather", "terrain", "screens", "hazards", "room"}


def test_missing_active_and_field_values_become_explicit_unknowns() -> None:
    context = build_battle_state_context(self_active={"species": {"source": "visible_ui"}})

    assert context["self_active"]["species"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["self_active"]["current_hp_percent"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["self_active"]["status"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["self_active"]["boosts"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["self_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["field"] == _unknown_field_state()


def test_explicit_and_user_confirmed_values_are_known_values() -> None:
    context = build_battle_state_context(
        self_active={
            "status": {"source": "explicit_input", "value": "burn"},
            "boosts": {"source": "explicit_input", "value": {"atk": 1}},
            "item": {"source": "user_confirmed", "value": "loaded-dice"},
        },
        field={
            "weather": {"source": "explicit_input", "value": "rain"},
            "terrain": {"source": "explicit_input", "value": "electric"},
            "screens": {"source": "explicit_input", "value": {"reflect": True}},
            "hazards": {"source": "explicit_input", "value": {"stealth_rock": True}},
            "room": {"source": "explicit_input", "value": {"trick_room": False}},
        },
        known_conditions=[
            {"source": "calculated_from_visible", "kind": "hp_band", "value": "opponent above half"}
        ],
    )

    assert context["confidence"] == "limited"
    assert context["self_active"]["status"] == {
        "known": True,
        "source": "explicit_input",
        "value": "burn",
    }
    assert context["self_active"]["boosts"] == {
        "known": True,
        "source": "explicit_input",
        "value": {"atk": 1},
    }
    assert context["self_active"]["item"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "loaded-dice",
    }
    assert context["field"]["weather"] == {
        "known": True,
        "source": "explicit_input",
        "value": "rain",
    }
    assert context["field"]["terrain"] == {
        "known": True,
        "source": "explicit_input",
        "value": "electric",
    }
    assert context["field"]["screens"] == {
        "known": True,
        "source": "explicit_input",
        "value": {"reflect": True},
    }
    assert context["field"]["hazards"] == {
        "known": True,
        "source": "explicit_input",
        "value": {"stealth_rock": True},
    }
    assert context["field"]["room"] == {
        "known": True,
        "source": "explicit_input",
        "value": {"trick_room": False},
    }
    assert context["known_conditions"] == [
        {"source": "calculated_from_visible", "kind": "hp_band", "value": "opponent above half"}
    ]


def test_forbidden_sources_become_unknown_or_are_omitted() -> None:
    context = build_battle_state_context(
        self_active={
            "species": {"source": "species_common_set", "name": "Garchomp"},
            "status": {"source": "usage_based_guess", "value": "burn"},
            "boosts": {"source": "meta_inferred", "value": {"atk": 1}},
            "item": {"source": "hidden_state_guess", "value": "choice-scarf"},
        },
        opponent_active={
            "current_hp_percent": {"source": "damage_reverse_inference", "value": 64},
        },
        field={
            "weather": {"source": "species_common_set", "value": "sun"},
            "terrain": {"source": "usage_based_guess", "value": "grassy"},
        },
        known_conditions=[
            {"source": "damage_reverse_inference", "kind": "item_guess", "value": "assault-vest"}
        ],
    )

    assert context["confidence"] == "unknown"
    assert context["self_active"] == _unknown_active_side()
    assert context["opponent_active"] == _unknown_active_side()
    assert context["field"] == _unknown_field_state()
    assert context["known_conditions"] == []
    _assert_no_forbidden_sources(context)
    _assert_no_forbidden_fields(context)


def test_confidence_never_becomes_partial_or_explicit() -> None:
    empty_context = build_battle_state_context()
    limited_context = build_battle_state_context(
        self_active={"species": {"source": "visible_ui", "name": "Garchomp"}}
    )

    assert empty_context["confidence"] == "unknown"
    assert limited_context["confidence"] == "limited"
    assert empty_context["confidence"] not in {"partial", "explicit"}
    assert limited_context["confidence"] not in {"partial", "explicit"}


def test_forbidden_fields_are_absent_recursively() -> None:
    context = build_battle_state_context(
        self_active={
            "status": {
                "source": "explicit_input",
                "value": {
                    "label": "burn",
                    "EVs": {"hp": 252},
                    "hidden_item": "choice-scarf",
                    "damage_reverse_inferred": True,
                },
            },
            "boosts": {
                "source": "explicit_input",
                "value": {
                    "atk": 1,
                    "post_turn_hp": 12,
                    "item_consumed": True,
                    "rng_resolved": True,
                },
            },
        },
        field={
            "room": {
                "source": "explicit_input",
                "value": {
                    "trick_room": False,
                    "speed_tie_resolved": True,
                    "quick_claw_activated": True,
                    "full_turn_result": "resolved",
                    "resolved_outcome": "win",
                },
            }
        },
    )

    _assert_no_forbidden_fields(context)


def test_damage_and_ko_context_are_not_used_for_hidden_state_inference() -> None:
    context = build_battle_state_context(
        known_conditions=[
            {
                "source": "damage_reverse_inference",
                "damage_estimate": {"rolls": [42, 45], "hidden_item": "choice-band"},
                "ko_context": {"summary": "possible 2HKO", "EVs": {"hp": 252}},
            }
        ]
    )

    assert context["confidence"] == "unknown"
    assert context["known_conditions"] == []
    assert context["self_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["opponent_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    _assert_no_forbidden_fields(context)


def test_species_common_set_or_meta_sources_do_not_generate_hidden_state() -> None:
    context = build_battle_state_context(
        opponent_active={
            "species": {"source": "visible_ui", "name": "Charizard"},
            "item": {"source": "meta_inferred", "value": "heavy-duty-boots"},
            "status": {"source": "usage_based_guess", "value": "healthy"},
            "boosts": {"source": "species_common_set", "value": {"spa": 1}},
        },
        field={
            "weather": {"source": "species_common_set", "value": "sun"},
            "terrain": {"source": "meta_inferred", "value": "psychic"},
        },
    )

    assert context["confidence"] == "limited"
    assert context["opponent_active"]["species"] == {"source": "visible_ui", "name": "Charizard"}
    assert context["opponent_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["opponent_active"]["status"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["opponent_active"]["boosts"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["field"]["weather"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["field"]["terrain"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD


def test_user_confirmed_items_are_known_for_self_and_opponent() -> None:
    context = build_battle_state_context(
        self_active={
            "species": {"source": "visible_ui", "name": "Garchomp"},
            "current_hp_percent": {"source": "visible_ui", "value": 100},
            "item": {"source": "user_confirmed", "value": "loaded-dice"},
        },
        opponent_active={
            "species": {"source": "visible_ui", "name": "Charizard"},
            "current_hp_percent": {"source": "visible_ui", "value": 87},
            "item": {"source": "user_confirmed", "value": "focus-sash"},
        },
    )

    assert context["confidence"] == "limited"
    assert context["self_active"]["item"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "loaded-dice",
    }
    assert context["opponent_active"]["item"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "focus-sash",
    }
    assert context["self_active"]["species"] == {"source": "visible_ui", "name": "Garchomp"}
    assert context["opponent_active"]["current_hp_percent"] == {"source": "visible_ui", "value": 87}
    _assert_no_forbidden_fields(context)
    _assert_no_item_resolution_fields(context)


def test_explicit_input_items_are_known_for_self_and_opponent() -> None:
    context = build_battle_state_context(
        self_active={"item": {"source": "explicit_input", "value": "leftovers"}},
        opponent_active={"item": {"source": "explicit_input", "value": "focus-band"}},
    )

    assert context["confidence"] == "limited"
    assert context["self_active"]["item"] == {
        "known": True,
        "source": "explicit_input",
        "value": "leftovers",
    }
    assert context["opponent_active"]["item"] == {
        "known": True,
        "source": "explicit_input",
        "value": "focus-band",
    }
    _assert_no_item_resolution_fields(context)


def test_item_sources_without_user_confirmation_remain_unknown() -> None:
    disallowed_sources = [
        "visible_ui",
        "calculated_from_visible",
        "species_common_set",
        "usage_based_guess",
        "meta_inferred",
        "hidden_state_guess",
        "damage_reverse_inference",
        "legality_gate_guess",
        "resist_berry_inferred",
        "context_derived",
    ]

    for source in disallowed_sources:
        context = build_battle_state_context(
            self_active={"item": {"source": source, "value": "choice-scarf"}},
            opponent_active={"item": {"source": source, "value": "focus-sash"}},
        )

        assert context["confidence"] == "unknown", source
        assert context["self_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD, source
        assert context["opponent_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD, source
        _assert_no_forbidden_sources(context)
        _assert_no_forbidden_fields(context)


def test_malformed_or_missing_item_values_remain_unknown() -> None:
    context = build_battle_state_context(
        self_active={
            "item": {"source": "user_confirmed"},
        },
        opponent_active={
            "item": {"source": "explicit_input", "value": None},
        },
    )

    assert context["confidence"] == "unknown"
    assert context["self_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["opponent_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD


def test_legality_gate_or_resist_berry_context_alone_does_not_create_known_item() -> None:
    context = build_battle_state_context(
        self_active={
            "item": {
                "source": "legality_gate_guess",
                "value": "yache-berry",
                "legal_status": "legal_modeled",
            }
        },
        opponent_active={
            "item": {
                "source": "resist_berry_inferred",
                "value": "yache-berry",
                "resist_effect": {"berry_type": "ice"},
            }
        },
        known_conditions=[
            {
                "source": "damage_reverse_inference",
                "kind": "resist_berry_context",
                "value": {"item": "yache-berry"},
            }
        ],
    )

    assert context["confidence"] == "unknown"
    assert context["self_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["opponent_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["known_conditions"] == []
    _assert_no_forbidden_sources(context)
    _assert_no_forbidden_fields(context)


def test_ui_selected_state_adapter_extracts_visible_species_and_hp_only() -> None:
    context = build_battle_state_context_from_ui_selected_state(
        {
            "pokemon": {
                "my_active": {
                    "name_en": "Garchomp",
                    "hp_percent": 76,
                    "item": {"source": "user_confirmed", "value": "loaded-dice"},
                },
                "opponent_active": {
                    "name_en": "Charizard",
                    "hp_percent": 42.5,
                    "status": {"source": "explicit_input", "value": "burn"},
                },
            },
            "item_profiles": {
                "my_active": {"status": "user_confirmed", "item_id": "loaded-dice"},
                "opponent_active": {"status": "user_confirmed", "item_id": "focus-sash"},
            },
            "damage_estimate": {"hidden_item": "choice-band"},
            "ko_context": {"EVs": {"hp": 252}},
        }
    )

    assert context["kind"] == "battle_state_context"
    assert context["confidence"] == "limited"
    assert context["self_active"]["species"] == {"source": "visible_ui", "name": "Garchomp"}
    assert context["self_active"]["current_hp_percent"] == {"source": "visible_ui", "value": 76}
    assert context["opponent_active"]["species"] == {"source": "visible_ui", "name": "Charizard"}
    assert context["opponent_active"]["current_hp_percent"] == {"source": "visible_ui", "value": 42.5}
    assert context["self_active"]["status"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["self_active"]["boosts"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["self_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["opponent_active"]["status"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["opponent_active"]["boosts"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["opponent_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert context["field"] == _unknown_field_state()
    assert context["known_conditions"] == []
    _assert_no_forbidden_fields(context)
    _assert_no_forbidden_sources(context)


def test_ui_selected_state_adapter_keeps_missing_sources_unknown() -> None:
    context = build_battle_state_context_from_ui_selected_state(
        {
            "pokemon": {
                "my_active": {"name_en": "", "hp_percent": None},
                "opponent_active": {"name_ko": "리자몽"},
            }
        }
    )

    assert context["confidence"] == "unknown"
    assert context["self_active"] == _unknown_active_side()
    assert context["opponent_active"] == _unknown_active_side()
    assert context["field"] == _unknown_field_state()
    assert context["known_conditions"] == []


def test_ui_selected_state_adapter_ignores_damage_and_ko_context_as_sources() -> None:
    context = build_battle_state_context_from_ui_selected_state(
        {
            "pokemon": {},
            "moves": {
                "my_selected_move": {
                    "damage_estimate": {
                        "status": "available_with_default_assumptions",
                        "damage_reverse_inferred": True,
                        "hidden_item": "choice-band",
                    },
                    "ko_context": {
                        "resolved_outcome": "ko",
                        "post_turn_hp": 0,
                    },
                }
            },
            "turn_pipeline": {"full_turn_result": "resolved"},
            "opponent_move_context": {"selected_opponent_move": {"status": "explicit", "move_id": "surf"}},
        }
    )

    assert context["confidence"] == "unknown"
    assert context["self_active"] == _unknown_active_side()
    assert context["opponent_active"] == _unknown_active_side()
    assert context["field"] == _unknown_field_state()
    _assert_no_forbidden_fields(context)


def test_unsupported_boundaries_and_safety_notes_are_included() -> None:
    context = build_battle_state_context()

    _assert_required_unsupported_boundaries(context)
    _assert_required_safety_notes(context)


def _unknown_active_side() -> dict:
    return {
        "species": dict(BATTLE_STATE_CONTEXT_UNKNOWN_FIELD),
        "current_hp_percent": dict(BATTLE_STATE_CONTEXT_UNKNOWN_FIELD),
        "status": dict(BATTLE_STATE_CONTEXT_UNKNOWN_FIELD),
        "boosts": dict(BATTLE_STATE_CONTEXT_UNKNOWN_FIELD),
        "item": dict(BATTLE_STATE_CONTEXT_UNKNOWN_FIELD),
    }


def _unknown_field_state() -> dict:
    return {
        "weather": dict(BATTLE_STATE_CONTEXT_UNKNOWN_FIELD),
        "terrain": dict(BATTLE_STATE_CONTEXT_UNKNOWN_FIELD),
        "screens": dict(BATTLE_STATE_CONTEXT_UNKNOWN_FIELD),
        "hazards": dict(BATTLE_STATE_CONTEXT_UNKNOWN_FIELD),
        "room": dict(BATTLE_STATE_CONTEXT_UNKNOWN_FIELD),
    }


def _assert_required_unsupported_boundaries(context: dict) -> None:
    assert set(BATTLE_STATE_CONTEXT_UNSUPPORTED_BOUNDARIES).issubset(set(context["unsupported"]))
    assert "hidden item inference" in context["unsupported"]
    assert "EV/IV/nature inference" in context["unsupported"]
    assert "damage reverse inference" in context["unsupported"]
    assert "RNG resolution" in context["unsupported"]
    assert "item consumption" in context["unsupported"]
    assert "post-turn HP resolution" in context["unsupported"]
    assert "full turn resolution" in context["unsupported"]


def _assert_required_safety_notes(context: dict) -> None:
    assert "Unknown battle state fields must remain unknown." in context["safety_notes"]
    assert (
        "Do not infer hidden state from species, common sets, damage estimates, or KO context."
        in context["safety_notes"]
    )
    assert "Battle state context is not a resolved turn simulation." in context["safety_notes"]


def _assert_no_forbidden_fields(value: object) -> None:
    if isinstance(value, dict):
        for key, child_value in value.items():
            assert key not in BATTLE_STATE_CONTEXT_FORBIDDEN_FIELDS
            _assert_no_forbidden_fields(child_value)
    elif isinstance(value, list):
        for child_value in value:
            _assert_no_forbidden_fields(child_value)


def _assert_no_forbidden_sources(value: object) -> None:
    forbidden_sources = {
        "context_derived",
        "legality_gate_guess",
        "resist_berry_inferred",
        "species_common_set",
        "usage_based_guess",
        "meta_inferred",
        "hidden_state_guess",
        "damage_reverse_inference",
    }
    if isinstance(value, dict):
        if "source" in value:
            assert value["source"] not in forbidden_sources
        for child_value in value.values():
            _assert_no_forbidden_sources(child_value)
    elif isinstance(value, list):
        for child_value in value:
            _assert_no_forbidden_sources(child_value)


def _assert_no_item_resolution_fields(value: object) -> None:
    forbidden_resolution_fields = {
        "item_consumed",
        "item_consumption",
        "post_turn_hp",
        "rng_resolved",
        "speed_tie_resolved",
        "quick_claw_activated",
        "full_turn_result",
        "resolved_outcome",
    }
    if isinstance(value, dict):
        for key, child_value in value.items():
            assert key not in forbidden_resolution_fields
            _assert_no_item_resolution_fields(child_value)
    elif isinstance(value, list):
        for child_value in value:
            _assert_no_item_resolution_fields(child_value)
