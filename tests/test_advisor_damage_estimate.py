from __future__ import annotations

from llm.advisor_damage_estimate import (
    attach_selected_move_damage_estimate,
    build_selected_move_damage_estimate,
)


def test_selected_move_missing_returns_unavailable() -> None:
    payload = _battle_input(selected_move=None)

    estimate = build_selected_move_damage_estimate(payload)

    assert estimate["status"] == "unavailable_no_selected_move"
    assert estimate["is_final_battle_damage"] is False
    assert "damage_range" not in estimate


def test_status_move_returns_unavailable() -> None:
    payload = _battle_input(
        selected_move={
            "slot": 0,
            "move_id": "will-o-wisp",
            "name_en": "Will-O-Wisp",
            "name_ko": "Will-O-Wisp",
            "type": "fire",
            "category": "status",
            "power": None,
            "accuracy": 85,
            "pp": 15,
        }
    )

    estimate = build_selected_move_damage_estimate(payload)

    assert estimate["status"] == "unavailable_status_move"
    assert estimate["selected_move_id"] == "will-o-wisp"
    assert "damage_range" not in estimate


def test_missing_power_returns_unavailable() -> None:
    payload = _battle_input(
        selected_move={
            "slot": 0,
            "move_id": "dragon-rage",
            "name_en": "Dragon Rage",
            "name_ko": "Dragon Rage",
            "type": "dragon",
            "category": "special",
            "power": None,
            "accuracy": 100,
            "pp": 10,
        }
    )

    estimate = build_selected_move_damage_estimate(payload)

    assert estimate["status"] == "unavailable_missing_power"
    assert "damage_range" not in estimate


def test_damaging_selected_move_returns_default_assumption_range() -> None:
    payload = _battle_input(selected_move=_flamethrower())

    estimate = build_selected_move_damage_estimate(payload)

    assert estimate["status"] == "available_with_default_assumptions"
    assert estimate["scope"] == "selected_move_only"
    assert estimate["is_final_battle_damage"] is False
    assert estimate["selected_move_id"] == "flamethrower"
    assert estimate["damage_range"]["min"] > 0
    assert estimate["damage_range"]["max"] >= estimate["damage_range"]["min"]
    assert estimate["percent_range"]["min"] > 0
    assert estimate["percent_range"]["max"] >= estimate["percent_range"]["min"]
    assert estimate["percent_range"]["denominator"] == "default_defender_max_hp"
    assert len(estimate["rolls"]) == 16
    assert estimate["rolls"][0] == estimate["damage_range"]["min"]
    assert estimate["rolls"][-1] == estimate["damage_range"]["max"]
    assert estimate["assumptions"]["level"] == 50
    assert estimate["assumptions"]["ivs"] == "31 all"
    assert estimate["assumptions"]["evs"] == "0 all"
    assert estimate["assumptions"]["ability_effects"] == "not_applied_unselected"
    assert "OHKO/2HKO/KO chance is not provided in v0.11.2." in estimate["limitations"]
    assert "ohko_chance" not in estimate
    assert "ko_chance" not in estimate


def test_attach_places_estimate_under_my_selected_move() -> None:
    payload = _battle_input(selected_move=_flamethrower())

    result = attach_selected_move_damage_estimate(payload)

    estimate = result["moves"]["my_selected_move"]["damage_estimate"]
    assert estimate["status"] == "available_with_default_assumptions"
    assert result["moves"]["my_selected_move"]["move_id"] == "flamethrower"
    assert "damage_estimate" not in payload["moves"]["my_selected_move"]


def test_attach_places_estimates_under_available_moves() -> None:
    payload = _battle_input(
        selected_move=_flamethrower(),
        available_moves=[_flamethrower(), _air_slash(), _will_o_wisp()],
    )

    result = attach_selected_move_damage_estimate(payload)

    estimates = [move["damage_estimate"] for move in result["moves"]["my_available_moves"]]
    assert [estimate["scope"] for estimate in estimates] == [
        "available_move_comparison",
        "available_move_comparison",
        "available_move_comparison",
    ]
    assert estimates[0]["status"] == "available_with_default_assumptions"
    assert estimates[1]["status"] == "available_with_default_assumptions"
    assert estimates[2]["status"] == "unavailable_status_move"
    assert "damage_range" in estimates[0]
    assert "percent_range" in estimates[1]
    assert "damage_range" not in estimates[2]
    assert "ko_chance" not in estimates[0]
    assert "ohko_chance" not in estimates[0]
    assert "damage_estimate" not in payload["moves"]["my_available_moves"][0]


def test_attach_handles_no_selected_move_with_unavailable_schema() -> None:
    payload = _battle_input(selected_move=None)

    result = attach_selected_move_damage_estimate(payload)

    estimate = result["moves"]["my_selected_move"]["damage_estimate"]
    assert estimate["status"] == "unavailable_no_selected_move"
    assert "damage_range" not in estimate


def _battle_input(selected_move: dict | None, available_moves: list[dict] | None = None) -> dict:
    if available_moves is None:
        available_moves = [_flamethrower()] if selected_move else []
    return {
        "scenario": {
            "mode": "ui-selected-pokemon-v0.11",
            "known_limitations": [],
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
                "hp_percent": 100,
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
                "hp_percent": 100,
                "selected_move_index": None,
            },
        },
        "moves": {
            "my_selected_move_index": 0,
            "my_available_moves": available_moves,
            "my_selected_move": selected_move,
            "opponent_available_moves": [],
            "opponent_selected_move": None,
            "opponent_selected_move_index": None,
            "move_data_status": "four_move_damage_comparison_v0.10",
            "notes": [],
        },
    }


def _flamethrower() -> dict:
    return {
        "slot": 0,
        "move_id": "flamethrower",
        "name_en": "Flamethrower",
        "name_ko": "Flamethrower",
        "type": "fire",
        "category": "special",
        "power": 90,
        "accuracy": 100,
        "pp": 15,
    }


def _air_slash() -> dict:
    return {
        "slot": 1,
        "move_id": "air-slash",
        "name_en": "Air Slash",
        "name_ko": "Air Slash",
        "type": "flying",
        "category": "special",
        "power": 75,
        "accuracy": 95,
        "pp": 15,
    }


def _will_o_wisp() -> dict:
    return {
        "slot": 2,
        "move_id": "will-o-wisp",
        "name_en": "Will-O-Wisp",
        "name_ko": "Will-O-Wisp",
        "type": "fire",
        "category": "status",
        "power": None,
        "accuracy": 85,
        "pp": 15,
    }
