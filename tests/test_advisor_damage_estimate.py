from __future__ import annotations

from llm.advisor_damage_estimate import (
    attach_opponent_known_move_damage_estimates,
    attach_selected_move_damage_estimate,
    build_opponent_known_move_damage_estimate,
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
    _assert_default_assumption_profile(estimate)
    assert estimate["assumptions"]["level"] == 50
    assert estimate["assumptions"]["ivs"] == "31 all"
    assert estimate["assumptions"]["evs"] == "0 all"
    assert estimate["assumptions"]["ability_effects"] == "not_applied_unselected"
    assert "OHKO/2HKO/KO chance is not provided in v0.14." in estimate["limitations"]
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
    _assert_default_assumption_profile(estimate)
    assert "damage_range" not in estimate


def test_opponent_known_move_returns_damage_against_my_active() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    earthquake = _earthquake()

    estimate = build_opponent_known_move_damage_estimate(payload, earthquake)

    assert estimate["status"] == "available_with_default_assumptions"
    assert estimate["scope"] == "opponent_known_move_only"
    assert estimate["target"] == "my_active"
    assert estimate["is_final_battle_damage"] is False
    assert estimate["selected_move_id"] == "earthquake"
    assert estimate["damage_range"]["min"] >= 0
    assert estimate["damage_range"]["max"] >= estimate["damage_range"]["min"]
    assert estimate["percent_range"]["min"] >= 0
    assert estimate["percent_range"]["max"] >= estimate["percent_range"]["min"]
    assert estimate["percent_range"]["denominator"] == "default_defender_max_hp"
    assert len(estimate["rolls"]) == 16
    _assert_default_assumption_profile(estimate)
    assert "Opponent item, ability, EV/IV/nature, boosts, and final stats are not connected." in estimate[
        "limitations"
    ]
    assert "OHKO/2HKO/KO chance is not provided in v0.14." in estimate["limitations"]
    assert "ohko_chance" not in estimate
    assert "ko_chance" not in estimate


def test_opponent_status_known_move_returns_unavailable_with_target() -> None:
    payload = _battle_input(selected_move=_flamethrower())

    estimate = build_opponent_known_move_damage_estimate(payload, _will_o_wisp())

    assert estimate["status"] == "unavailable_status_move"
    assert estimate["target"] == "my_active"
    assert estimate["selected_move_id"] == "will-o-wisp"
    assert "damage_range" not in estimate


def test_attach_opponent_known_damage_skips_candidate_moves() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["opponent_moves"] = {
        "known_moves": [{**_earthquake(), "source": "user_confirmed"}],
        "candidate_moves": [{**_air_slash(), "source": "champions_movepool"}],
    }

    result = attach_opponent_known_move_damage_estimates(payload)

    known_move = result["opponent_moves"]["known_moves"][0]
    candidate_move = result["opponent_moves"]["candidate_moves"][0]
    assert known_move["damage_estimate"]["target"] == "my_active"
    assert known_move["damage_estimate"]["scope"] == "opponent_known_move_only"
    _assert_default_assumption_profile(known_move["damage_estimate"])
    assert "damage_estimate" not in candidate_move
    assert "damage_estimate" not in payload["opponent_moves"]["known_moves"][0]


def test_available_move_estimates_include_default_assumption_profile() -> None:
    payload = _battle_input(
        selected_move=_flamethrower(),
        available_moves=[_flamethrower(), _air_slash()],
    )

    result = attach_selected_move_damage_estimate(payload)

    for move in result["moves"]["my_available_moves"]:
        estimate = move["damage_estimate"]
        _assert_default_assumption_profile(estimate)
        assert estimate["is_final_battle_damage"] is False
        assert "assumptions" in estimate


def test_my_move_damage_uses_user_confirmed_final_stats() -> None:
    default_payload = _battle_input(selected_move=_flamethrower())
    final_stats_payload = _battle_input(selected_move=_flamethrower())
    final_stats_payload["stat_profiles"] = {
        "my_active": _user_final_stats(spa=300),
        "opponent_active": _default_stat_profile(),
    }

    default_estimate = build_selected_move_damage_estimate(default_payload)
    final_stats_estimate = build_selected_move_damage_estimate(final_stats_payload)

    assert final_stats_estimate["damage_range"]["max"] > default_estimate["damage_range"]["max"]
    _assert_user_final_stats_profile(
        final_stats_estimate,
        attacker="user_confirmed_final_stats",
        defender="default_assumption",
    )
    assert final_stats_estimate["is_final_battle_damage"] is False


def test_opponent_known_move_damage_uses_user_confirmed_final_stats() -> None:
    default_payload = _battle_input(selected_move=_flamethrower())
    final_stats_payload = _battle_input(selected_move=_flamethrower())
    final_stats_payload["stat_profiles"] = {
        "my_active": _user_final_stats(def_=50),
        "opponent_active": _user_final_stats(atk=300),
    }

    default_estimate = build_opponent_known_move_damage_estimate(default_payload, _rock_slide())
    final_stats_estimate = build_opponent_known_move_damage_estimate(final_stats_payload, _rock_slide())

    assert final_stats_estimate["damage_range"]["max"] > default_estimate["damage_range"]["max"]
    _assert_user_final_stats_profile(
        final_stats_estimate,
        attacker="user_confirmed_final_stats",
        defender="user_confirmed_final_stats",
    )
    assert "ko_chance" not in final_stats_estimate
    assert "ohko_chance" not in final_stats_estimate


def test_partial_final_stats_falls_back_to_default_profile() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["stat_profiles"] = {
        "my_active": {
            "status": "user_confirmed_final_stats",
            "final_stats": {"hp": 153, "atk": 104},
        },
        "opponent_active": _default_stat_profile(),
    }

    estimate = build_selected_move_damage_estimate(payload)

    _assert_default_assumption_profile(estimate)


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


def _assert_default_assumption_profile(estimate: dict) -> None:
    assert estimate["assumption_profile"] == {
        "id": "default_level50_ivs31_evs0_neutral_no_item",
        "label": "Default Level 50 / IV 31 / EV 0 / neutral nature / no item",
        "source": "system_default",
        "confidence": "rough_reference",
        "is_user_confirmed": False,
    }


def _assert_user_final_stats_profile(
    estimate: dict,
    *,
    attacker: str,
    defender: str,
) -> None:
    profile = estimate["assumption_profile"]
    assert profile["id"] == "user_confirmed_final_stats_level50"
    assert profile["source"] == "user_input"
    assert profile["confidence"] == "higher_confidence_reference"
    assert profile["is_user_confirmed"] is True
    assert profile["stats_used"] == {
        "attacker": attacker,
        "defender": defender,
    }


def _default_stat_profile() -> dict:
    return {
        "status": "default_assumption",
        "source": "system_default",
        "level": 50,
        "final_stats": None,
        "evs": None,
        "ivs": "31 all",
        "nature": "neutral",
        "item": None,
    }


def _user_final_stats(
    *,
    hp: int = 153,
    atk: int = 104,
    def_: int = 98,
    spa: int = 161,
    spd: int = 105,
    spe: int = 167,
) -> dict:
    return {
        "status": "user_confirmed_final_stats",
        "source": "user_input",
        "level": 50,
        "final_stats": {
            "hp": hp,
            "atk": atk,
            "def": def_,
            "spa": spa,
            "spd": spd,
            "spe": spe,
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


def _earthquake() -> dict:
    return {
        "slot": 0,
        "move_id": "earthquake",
        "name_en": "Earthquake",
        "name_ko": "Earthquake",
        "type": "ground",
        "category": "physical",
        "power": 100,
        "accuracy": 100,
        "pp": 10,
    }


def _rock_slide() -> dict:
    return {
        "slot": 0,
        "move_id": "rock-slide",
        "name_en": "Rock Slide",
        "name_ko": "Rock Slide",
        "type": "rock",
        "category": "physical",
        "power": 75,
        "accuracy": 90,
        "pp": 10,
    }
