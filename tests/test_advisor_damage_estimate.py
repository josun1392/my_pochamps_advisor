from __future__ import annotations

from llm.advisor_damage_estimate import (
    attach_opponent_known_move_damage_estimates,
    attach_selected_move_damage_estimate,
    build_opponent_known_move_damage_estimate,
    build_selected_move_damage_estimate,
)
from llm.advisor_accuracy_context import build_accuracy_context
from llm.advisor_critical_context import build_critical_context
from llm.advisor_ko_context import build_ko_context
from llm.advisor_recovery_context import build_recovery_context


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
    assert estimate["type_effectiveness"] == {
        "multiplier": 0.5,
        "label": "not_very_effective",
    }
    assert len(estimate["rolls"]) == 16
    assert estimate["rolls"][0] == estimate["damage_range"]["min"]
    assert estimate["rolls"][-1] == estimate["damage_range"]["max"]
    _assert_default_assumption_profile(estimate)
    assert estimate["assumptions"]["level"] == 50
    assert estimate["assumptions"]["ivs"] == "31 all"
    assert estimate["assumptions"]["evs"] == "0 all"
    assert estimate["assumptions"]["item"] == "none"
    assert estimate["assumptions"]["ability_effects"] == "not_applied_unselected"
    assert estimate["item_effects"]["attacker_item"]["status"] == "system_default_none"
    assert estimate["item_effects"]["defender_item"]["status"] == "system_default_none"
    assert (
        "KO/OHKO/2HKO context, when present, is limited damage-roll context only and not final battle truth."
        in estimate["limitations"]
    )
    assert "ohko_chance" not in estimate
    assert "ko_chance" not in estimate


def test_type_effectiveness_metadata_marks_corviknight_resisting_dragon() -> None:
    payload = _battle_input(selected_move=_dragon_claw())
    payload["pokemon"]["opponent_active"] = _corviknight_payload()

    estimate = build_selected_move_damage_estimate(payload)

    assert estimate["status"] == "available_with_default_assumptions"
    assert estimate["selected_move_id"] == "dragon-claw"
    assert estimate["type_effectiveness"] == {
        "multiplier": 0.5,
        "label": "not_very_effective",
    }


def test_type_effectiveness_metadata_marks_ground_immunity() -> None:
    payload = _battle_input(selected_move=_earthquake())
    payload["pokemon"]["opponent_active"] = _corviknight_payload()

    estimate = build_selected_move_damage_estimate(payload)

    assert estimate["damage_range"] == {"min": 0, "max": 0}
    assert estimate["type_effectiveness"] == {
        "multiplier": 0.0,
        "label": "immune",
    }


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
    assert "Opponent ability, EV/IV/nature, boosts, and final stats may be missing or defaulted." in estimate[
        "limitations"
    ]
    assert (
        "KO/OHKO/2HKO context, when present, is limited damage-roll context only and not final battle truth."
        in estimate["limitations"]
    )
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
    assert "ko_context" not in candidate_move
    assert "survival_context" not in candidate_move
    assert "recovery_context" not in candidate_move
    assert "accuracy_context" not in candidate_move
    assert "critical_context" not in candidate_move
    assert "damage_estimate" not in payload["opponent_moves"]["known_moves"][0]


def test_ko_context_marks_guaranteed_ohko_from_rolls() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["pokemon"]["opponent_active"]["current_hp"] = 30
    payload["pokemon"]["opponent_active"]["max_hp"] = 100
    estimate = _ko_damage_estimate(rolls=[30, 31, 32, 33])

    context = build_ko_context(payload, estimate, defender_key="opponent_active", scope="selected_move_only")

    assert context["available"] is True
    assert context["ohko"]["possible"] is True
    assert context["ohko"]["guaranteed"] is True
    assert context["ohko"]["chance"] == 1.0
    assert context["ohko"]["successful_rolls"] == 4
    assert context["ohko"]["total_rolls"] == 4
    assert context["damage"]["roll_count"] == 4


def test_ko_context_marks_impossible_ohko_from_rolls() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["pokemon"]["opponent_active"]["current_hp"] = 50
    payload["pokemon"]["opponent_active"]["max_hp"] = 100
    estimate = _ko_damage_estimate(rolls=[30, 31, 32, 33])

    context = build_ko_context(payload, estimate, defender_key="opponent_active", scope="selected_move_only")

    assert context["ohko"]["possible"] is False
    assert context["ohko"]["guaranteed"] is False
    assert context["ohko"]["chance"] == 0.0
    assert context["ohko"]["successful_rolls"] == 0
    assert context["ohko"]["total_rolls"] == 4


def test_ko_context_marks_partial_ohko_chance_from_rolls() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["pokemon"]["opponent_active"]["current_hp"] = 32
    payload["pokemon"]["opponent_active"]["max_hp"] = 100
    estimate = _ko_damage_estimate(rolls=[30, 31, 32, 33])

    context = build_ko_context(payload, estimate, defender_key="opponent_active", scope="selected_move_only")

    assert context["ohko"]["possible"] is True
    assert context["ohko"]["guaranteed"] is False
    assert context["ohko"]["chance"] == 0.5
    assert context["ohko"]["successful_rolls"] == 2
    assert context["ohko"]["total_rolls"] == 4


def test_ko_context_no_roll_fallback_uses_min_max() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["pokemon"]["opponent_active"]["current_hp"] = 32
    payload["pokemon"]["opponent_active"]["max_hp"] = 100

    guaranteed = build_ko_context(
        payload,
        _ko_damage_estimate(min_damage=32, max_damage=40, rolls=None),
        defender_key="opponent_active",
        scope="selected_move_only",
    )
    possible = build_ko_context(
        payload,
        _ko_damage_estimate(min_damage=20, max_damage=40, rolls=None),
        defender_key="opponent_active",
        scope="selected_move_only",
    )
    impossible = build_ko_context(
        payload,
        _ko_damage_estimate(min_damage=20, max_damage=31, rolls=None),
        defender_key="opponent_active",
        scope="selected_move_only",
    )

    assert guaranteed["ohko"]["guaranteed"] is True
    assert guaranteed["ohko"]["possible"] is True
    assert guaranteed["ohko"]["chance"] is None
    assert possible["ohko"]["guaranteed"] is False
    assert possible["ohko"]["possible"] is True
    assert possible["ohko"]["chance"] is None
    assert impossible["ohko"]["guaranteed"] is False
    assert impossible["ohko"]["possible"] is False
    assert impossible["ohko"]["chance"] is None


def test_ko_context_requires_known_hp() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    del payload["pokemon"]["opponent_active"]["hp_percent"]

    context = build_ko_context(
        payload,
        _ko_damage_estimate(rolls=[30, 31, 32, 33]),
        defender_key="opponent_active",
        scope="selected_move_only",
    )

    assert context["available"] is False
    assert context["reason"] == "hp_unknown"


def test_ko_context_marks_two_hko_min_max_limited_outcomes() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["pokemon"]["opponent_active"]["current_hp"] = 80
    payload["pokemon"]["opponent_active"]["max_hp"] = 100

    guaranteed = build_ko_context(
        payload,
        _ko_damage_estimate(min_damage=40, max_damage=50, rolls=[40, 50]),
        defender_key="opponent_active",
        scope="selected_move_only",
    )
    possible = build_ko_context(
        payload,
        _ko_damage_estimate(min_damage=30, max_damage=40, rolls=[30, 40]),
        defender_key="opponent_active",
        scope="selected_move_only",
    )
    impossible = build_ko_context(
        payload,
        _ko_damage_estimate(min_damage=20, max_damage=39, rolls=[20, 39]),
        defender_key="opponent_active",
        scope="selected_move_only",
    )

    assert guaranteed["two_hko"]["guaranteed"] is True
    assert guaranteed["two_hko"]["possible"] is True
    assert guaranteed["two_hko"]["method"] == "limited_min_max"
    assert possible["two_hko"]["guaranteed"] is False
    assert possible["two_hko"]["possible"] is True
    assert impossible["two_hko"]["guaranteed"] is False
    assert impossible["two_hko"]["possible"] is False


def test_ko_context_attaches_to_my_move_without_changing_raw_damage() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["stat_profiles"] = {
        "my_active": _default_stat_profile(),
        "opponent_active": _user_final_stats(hp=35),
    }
    baseline = _battle_input(selected_move=_flamethrower())
    baseline["stat_profiles"] = payload["stat_profiles"]

    baseline_estimate = build_selected_move_damage_estimate(baseline)
    result = attach_selected_move_damage_estimate(payload)

    estimate = result["moves"]["my_selected_move"]["damage_estimate"]
    context = result["moves"]["my_selected_move"]["ko_context"]
    assert context["available"] is True
    assert context["scope"] == "selected_move_only"
    assert context["defender_side"] == "opponent_active"
    assert context["raw_damage_rolls_changed"] is False
    assert context["ohko"]["possible"] is True
    assert estimate["damage_range"] == baseline_estimate["damage_range"]
    assert estimate["rolls"] == baseline_estimate["rolls"]


def test_ko_context_attaches_to_opponent_known_move_and_excludes_candidates() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["stat_profiles"] = {
        "my_active": _user_final_stats(hp=45),
        "opponent_active": _default_stat_profile(),
    }
    payload["opponent_moves"] = {
        "known_moves": [{**_rock_slide(), "source": "user_confirmed"}],
        "candidate_moves": [{**_air_slash(), "source": "champions_movepool"}],
    }

    result = attach_opponent_known_move_damage_estimates(payload)

    known_move = result["opponent_moves"]["known_moves"][0]
    candidate_move = result["opponent_moves"]["candidate_moves"][0]
    assert known_move["ko_context"]["available"] is True
    assert known_move["ko_context"]["scope"] == "opponent_known_move_only"
    assert known_move["ko_context"]["defender_side"] == "my_active"
    assert "ko_context" not in candidate_move
    assert "critical_context" not in candidate_move


def test_ko_context_coexists_with_focus_sash_without_integrating_survival() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="focus-sash")
    payload["stat_profiles"] = {
        "my_active": _default_stat_profile(),
        "opponent_active": _user_final_stats(hp=35),
    }

    result = attach_selected_move_damage_estimate(payload)

    move = result["moves"]["my_selected_move"]
    assert move["survival_context"]["available"] is True
    assert move["ko_context"]["available"] is True
    assert move["ko_context"]["ohko"]["chance"] > 0
    assert "focus_sash" not in move["ko_context"]
    assert "survival_context" not in move["ko_context"]


def test_recovery_context_available_for_user_confirmed_sitrus_berry() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="sitrus-berry")
    payload["stat_profiles"] = {
        "my_active": _default_stat_profile(),
        "opponent_active": _user_final_stats(hp=183),
    }

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["recovery_context"]
    assert context["available"] is True
    assert context["mode"] == "limited_item_recovery_context"
    assert context["defender_side"] == "opponent_active"
    assert context["item"] == {"item_id": "sitrus-berry", "status": "user_confirmed"}
    assert context["recovery_effect"]["type"] == "sitrus_berry"
    assert context["recovery_effect"]["timing"] == "threshold_or_after_damage_limited"
    assert context["recovery_effect"]["estimated_recovery_hp"] == 45
    assert context["recovery_effect"]["formula_label"] == "floor(max_hp / 4)"
    assert context["recovery_effect"]["raw_damage_rolls_changed"] is False
    assert context["recovery_effect"]["ko_context_changed"] is False
    assert context["is_final_battle_truth"] is False


def test_recovery_context_available_for_user_confirmed_leftovers() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="leftovers")
    payload["stat_profiles"] = {
        "my_active": _default_stat_profile(),
        "opponent_active": _user_final_stats(hp=183),
    }

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["recovery_context"]
    assert context["available"] is True
    assert context["item"] == {"item_id": "leftovers", "status": "user_confirmed"}
    assert context["recovery_effect"]["type"] == "leftovers"
    assert context["recovery_effect"]["timing"] == "end_of_turn_limited"
    assert context["recovery_effect"]["estimated_recovery_hp"] == 11
    assert context["recovery_effect"]["formula_label"] == "floor(max_hp / 16)"
    assert "Limited end-of-turn recovery context only." in context["limitations"]


def test_recovery_context_requires_user_confirmed_item() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="sitrus-berry")
    payload["item_profiles"]["opponent_active"]["status"] = "unknown"

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["recovery_context"]
    assert context["available"] is False
    assert context["reason"] == "item_not_user_confirmed"


def test_recovery_context_unavailable_without_recovery_item() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item=None)

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["recovery_context"]
    assert context["available"] is False
    assert context["reason"] == "no_recovery_item"


def test_recovery_context_requires_max_hp() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="leftovers")
    estimate = {
        "status": "available_with_default_assumptions",
        "damage_range": {"min": 10, "max": 20},
    }

    context = build_recovery_context(
        payload,
        estimate,
        defender_key="opponent_active",
        scope="selected_move_only",
    )

    assert context["available"] is False
    assert context["reason"] == "defender_max_hp_missing"


def test_recovery_context_does_not_change_raw_damage_or_ko_context() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="sitrus-berry")
    payload["stat_profiles"] = {
        "my_active": _default_stat_profile(),
        "opponent_active": _user_final_stats(hp=35),
    }
    baseline = _battle_input(selected_move=_flamethrower())
    baseline["stat_profiles"] = payload["stat_profiles"]

    baseline_estimate = build_selected_move_damage_estimate(baseline)
    baseline_ko = build_ko_context(
        baseline,
        baseline_estimate,
        defender_key="opponent_active",
        scope="selected_move_only",
    )
    result = attach_selected_move_damage_estimate(payload)

    move = result["moves"]["my_selected_move"]
    assert move["recovery_context"]["available"] is True
    assert move["damage_estimate"]["damage_range"] == baseline_estimate["damage_range"]
    assert move["damage_estimate"]["rolls"] == baseline_estimate["rolls"]
    assert move["ko_context"]["ohko"] == baseline_ko["ohko"]
    assert move["ko_context"]["two_hko"] == baseline_ko["two_hko"]


def test_recovery_context_for_opponent_known_move_targets_my_active() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(my_item="leftovers")
    payload["stat_profiles"] = {
        "my_active": _user_final_stats(hp=160),
        "opponent_active": _default_stat_profile(),
    }
    payload["opponent_moves"] = {
        "known_moves": [{**_rock_slide(), "source": "user_confirmed"}],
        "candidate_moves": [{**_air_slash(), "source": "champions_movepool"}],
    }

    result = attach_opponent_known_move_damage_estimates(payload)

    known_move = result["opponent_moves"]["known_moves"][0]
    candidate_move = result["opponent_moves"]["candidate_moves"][0]
    context = known_move["recovery_context"]
    assert context["available"] is True
    assert context["scope"] == "opponent_known_move_only"
    assert context["defender_side"] == "my_active"
    assert context["recovery_effect"]["estimated_recovery_hp"] == 10
    assert "recovery_context" not in candidate_move
    assert "critical_context" not in candidate_move


def test_accuracy_context_available_for_user_confirmed_bright_powder() -> None:
    payload = _battle_input(selected_move=_air_slash())
    payload["item_profiles"] = _item_profiles(opponent_item="bright-powder")

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["accuracy_context"]
    assert context["available"] is True
    assert context["mode"] == "limited_accuracy_context"
    assert context["scope"] == "selected_move_only"
    assert context["defender_side"] == "opponent_active"
    assert context["item"] == {"item_id": "bright-powder", "status": "user_confirmed"}
    assert context["move_accuracy"] == {
        "base_accuracy": 95,
        "accuracy_source": "move_metadata",
        "accuracy_known": True,
    }
    assert context["accuracy_effect"]["type"] == "bright_powder"
    assert context["accuracy_effect"]["effect_label"] == "may_reduce_hit_reliability"
    assert context["accuracy_effect"]["formula_label"] == "bright_powder_limited_modifier"
    assert context["accuracy_effect"]["hit_probability_integrated"] is False
    assert context["accuracy_effect"]["raw_damage_rolls_changed"] is False
    assert context["accuracy_effect"]["ko_context_changed"] is False
    assert context["is_final_battle_truth"] is False


def test_accuracy_context_requires_user_confirmed_bright_powder() -> None:
    payload = _battle_input(selected_move=_air_slash())
    payload["item_profiles"] = _item_profiles(opponent_item="bright-powder")
    payload["item_profiles"]["opponent_active"]["status"] = "unknown"

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["accuracy_context"]
    assert context["available"] is False
    assert context["reason"] == "item_not_user_confirmed"


def test_accuracy_context_unavailable_without_bright_powder() -> None:
    payload = _battle_input(selected_move=_air_slash())
    payload["item_profiles"] = _item_profiles(opponent_item=None)

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["accuracy_context"]
    assert context["available"] is False
    assert context["reason"] == "no_bright_powder"


def test_accuracy_context_requires_move_accuracy_metadata() -> None:
    payload = _battle_input(selected_move={**_air_slash(), "accuracy": None})
    payload["item_profiles"] = _item_profiles(opponent_item="bright-powder")
    estimate = {
        "status": "available_with_default_assumptions",
        "damage_range": {"min": 10, "max": 20},
    }

    context = build_accuracy_context(
        payload,
        estimate,
        payload["moves"]["my_selected_move"],
        defender_key="opponent_active",
        scope="selected_move_only",
    )

    assert context["available"] is False
    assert context["reason"] == "move_accuracy_missing"


def test_accuracy_context_does_not_change_raw_damage_or_ko_context() -> None:
    payload = _battle_input(selected_move=_air_slash())
    payload["item_profiles"] = _item_profiles(opponent_item="bright-powder")
    payload["stat_profiles"] = {
        "my_active": _default_stat_profile(),
        "opponent_active": _user_final_stats(hp=35),
    }
    baseline = _battle_input(selected_move=_air_slash())
    baseline["stat_profiles"] = payload["stat_profiles"]

    baseline_estimate = build_selected_move_damage_estimate(baseline)
    baseline_ko = build_ko_context(
        baseline,
        baseline_estimate,
        defender_key="opponent_active",
        scope="selected_move_only",
    )
    result = attach_selected_move_damage_estimate(payload)

    move = result["moves"]["my_selected_move"]
    assert move["accuracy_context"]["available"] is True
    assert move["damage_estimate"]["damage_range"] == baseline_estimate["damage_range"]
    assert move["damage_estimate"]["rolls"] == baseline_estimate["rolls"]
    assert move["ko_context"]["ohko"] == baseline_ko["ohko"]
    assert move["ko_context"]["two_hko"] == baseline_ko["two_hko"]


def test_accuracy_context_for_opponent_known_move_targets_my_active_and_excludes_candidates() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(my_item="bright-powder")
    payload["opponent_moves"] = {
        "known_moves": [{**_rock_slide(), "source": "user_confirmed"}],
        "candidate_moves": [{**_air_slash(), "source": "champions_movepool"}],
    }

    result = attach_opponent_known_move_damage_estimates(payload)

    known_move = result["opponent_moves"]["known_moves"][0]
    candidate_move = result["opponent_moves"]["candidate_moves"][0]
    context = known_move["accuracy_context"]
    assert context["available"] is True
    assert context["scope"] == "opponent_known_move_only"
    assert context["defender_side"] == "my_active"
    assert context["move_accuracy"]["base_accuracy"] == 90
    assert "accuracy_context" not in candidate_move
    assert "critical_context" not in candidate_move


def test_critical_context_available_for_user_confirmed_scope_lens() -> None:
    payload = _battle_input(selected_move=_air_slash())
    payload["item_profiles"] = _item_profiles(my_item="scope-lens")

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["critical_context"]
    assert context["available"] is True
    assert context["mode"] == "limited_critical_context"
    assert context["scope"] == "selected_move_only"
    assert context["attacker_side"] == "my_active"
    assert context["item"] == {"item_id": "scope-lens", "status": "user_confirmed"}
    assert context["critical_effect"]["type"] == "scope_lens"
    assert context["critical_effect"]["effect_label"] == "may_increase_critical_hit_likelihood"
    assert context["critical_effect"]["formula_label"] == "scope_lens_limited_critical_modifier"
    assert context["critical_effect"]["crit_probability_integrated"] is False
    assert context["critical_effect"]["crit_adjusted_ko_integrated"] is False
    assert context["critical_effect"]["raw_damage_rolls_changed"] is False
    assert context["critical_effect"]["ko_context_changed"] is False
    assert context["is_final_battle_truth"] is False


def test_critical_context_requires_user_confirmed_scope_lens() -> None:
    payload = _battle_input(selected_move=_air_slash())
    payload["item_profiles"] = _item_profiles(my_item="scope-lens")
    payload["item_profiles"]["my_active"]["status"] = "unknown"

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["critical_context"]
    assert context["available"] is False
    assert context["reason"] == "item_not_user_confirmed"


def test_critical_context_unavailable_without_scope_lens() -> None:
    payload = _battle_input(selected_move=_air_slash())
    payload["item_profiles"] = _item_profiles(my_item=None)

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["critical_context"]
    assert context["available"] is False
    assert context["reason"] == "no_scope_lens"


def test_critical_context_requires_damage_estimate() -> None:
    payload = _battle_input(selected_move=_air_slash())
    payload["item_profiles"] = _item_profiles(my_item="scope-lens")

    context = build_critical_context(
        payload,
        {"status": "unavailable_status_move"},
        attacker_key="my_active",
        scope="selected_move_only",
    )

    assert context["available"] is False
    assert context["reason"] == "damage_estimate_missing"


def test_critical_context_does_not_change_raw_damage_or_ko_context() -> None:
    payload = _battle_input(selected_move=_air_slash())
    payload["item_profiles"] = _item_profiles(my_item="scope-lens")
    payload["stat_profiles"] = {
        "my_active": _default_stat_profile(),
        "opponent_active": _user_final_stats(hp=35),
    }
    baseline = _battle_input(selected_move=_air_slash())
    baseline["stat_profiles"] = payload["stat_profiles"]

    baseline_estimate = build_selected_move_damage_estimate(baseline)
    baseline_ko = build_ko_context(
        baseline,
        baseline_estimate,
        defender_key="opponent_active",
        scope="selected_move_only",
    )
    result = attach_selected_move_damage_estimate(payload)

    move = result["moves"]["my_selected_move"]
    assert move["critical_context"]["available"] is True
    assert move["damage_estimate"]["damage_range"] == baseline_estimate["damage_range"]
    assert move["damage_estimate"]["rolls"] == baseline_estimate["rolls"]
    assert move["ko_context"]["ohko"] == baseline_ko["ohko"]
    assert move["ko_context"]["two_hko"] == baseline_ko["two_hko"]


def test_critical_context_for_opponent_known_move_targets_opponent_active_and_excludes_candidates() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="scope-lens")
    payload["opponent_moves"] = {
        "known_moves": [{**_rock_slide(), "source": "user_confirmed"}],
        "candidate_moves": [{**_air_slash(), "source": "champions_movepool"}],
    }

    result = attach_opponent_known_move_damage_estimates(payload)

    known_move = result["opponent_moves"]["known_moves"][0]
    candidate_move = result["opponent_moves"]["candidate_moves"][0]
    context = known_move["critical_context"]
    assert context["available"] is True
    assert context["scope"] == "opponent_known_move_only"
    assert context["attacker_side"] == "opponent_active"
    assert "critical_context" not in candidate_move


def test_focus_sash_survival_context_for_my_move_when_full_hp_and_could_be_lethal() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="focus-sash")
    payload["stat_profiles"] = {
        "my_active": _default_stat_profile(),
        "opponent_active": _user_final_stats(hp=35),
    }
    baseline = _battle_input(selected_move=_flamethrower())
    baseline["stat_profiles"] = payload["stat_profiles"]

    baseline_estimate = build_selected_move_damage_estimate(baseline)
    result = attach_selected_move_damage_estimate(payload)

    estimate = result["moves"]["my_selected_move"]["damage_estimate"]
    context = result["moves"]["my_selected_move"]["survival_context"]
    assert estimate["damage_range"] == baseline_estimate["damage_range"]
    assert estimate["rolls"] == baseline_estimate["rolls"]
    assert context["available"] is True
    assert context["mode"] == "limited_item_survival_context"
    assert context["defender_side"] == "opponent_active"
    assert context["item"] == {"item_id": "focus-sash", "status": "user_confirmed"}
    assert context["current_hp_is_full"] is True
    assert context["incoming_damage"]["max"] >= 35
    assert context["incoming_damage"]["could_be_lethal_without_item"] is True
    assert context["incoming_damage"]["guaranteed_lethal_without_item"] is False
    assert context["survival_effect"]["may_survive_at_1_hp"] is True
    assert context["survival_effect"]["raw_damage_rolls_changed"] is False
    assert context["raw_damage_rolls_changed"] is False
    assert context["is_final_battle_truth"] is False


def test_focus_sash_survival_context_marks_guaranteed_lethal_without_item() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="focus-sash")
    payload["stat_profiles"] = {
        "my_active": _default_stat_profile(),
        "opponent_active": _user_final_stats(hp=31),
    }

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["survival_context"]
    assert context["available"] is True
    assert context["incoming_damage"]["could_be_lethal_without_item"] is True
    assert context["incoming_damage"]["guaranteed_lethal_without_item"] is True


def test_focus_sash_survival_context_requires_user_confirmed_item() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="focus-sash")
    payload["item_profiles"]["opponent_active"]["status"] = "unknown"
    payload["stat_profiles"] = {
        "my_active": _default_stat_profile(),
        "opponent_active": _user_final_stats(hp=31),
    }

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["survival_context"]
    assert context["available"] is False
    assert context["reason"] == "item_not_user_confirmed"


def test_focus_sash_survival_context_unavailable_without_focus_sash() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item=None)
    payload["stat_profiles"] = {
        "my_active": _default_stat_profile(),
        "opponent_active": _user_final_stats(hp=31),
    }

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["survival_context"]
    assert context["available"] is False
    assert context["reason"] == "no_focus_sash"


def test_focus_sash_survival_context_requires_full_hp() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="focus-sash")
    payload["pokemon"]["opponent_active"]["hp_percent"] = 50
    payload["stat_profiles"] = {
        "my_active": _default_stat_profile(),
        "opponent_active": _user_final_stats(hp=31),
    }

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["survival_context"]
    assert context["available"] is False
    assert context["reason"] == "hp_not_full"


def test_focus_sash_survival_context_requires_known_hp() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="focus-sash")
    del payload["pokemon"]["opponent_active"]["hp_percent"]

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["survival_context"]
    assert context["available"] is False
    assert context["reason"] == "hp_unknown"


def test_focus_sash_survival_context_unavailable_when_damage_not_lethal() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="focus-sash")
    payload["stat_profiles"] = {
        "my_active": _default_stat_profile(),
        "opponent_active": _user_final_stats(hp=999),
    }

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["survival_context"]
    assert context["available"] is False
    assert context["reason"] == "damage_not_lethal"


def test_focus_sash_survival_context_for_opponent_known_move_targets_my_active() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(my_item="focus-sash")
    payload["stat_profiles"] = {
        "my_active": _user_final_stats(hp=45),
        "opponent_active": _default_stat_profile(),
    }
    payload["opponent_moves"] = {
        "known_moves": [{**_rock_slide(), "source": "user_confirmed"}],
        "candidate_moves": [{**_air_slash(), "source": "champions_movepool"}],
    }

    result = attach_opponent_known_move_damage_estimates(payload)

    known_move = result["opponent_moves"]["known_moves"][0]
    candidate_move = result["opponent_moves"]["candidate_moves"][0]
    context = known_move["survival_context"]
    assert context["available"] is True
    assert context["scope"] == "opponent_known_move_only"
    assert context["defender_side"] == "my_active"
    assert context["survival_effect"]["may_survive_at_1_hp"] is True
    assert "survival_context" not in candidate_move
    assert "accuracy_context" not in candidate_move
    assert "critical_context" not in candidate_move


def test_focus_sash_survival_context_marks_multi_hit_unsupported() -> None:
    payload = _battle_input(selected_move={**_flamethrower(), "hit_count": 2})
    payload["item_profiles"] = _item_profiles(opponent_item="focus-sash")
    payload["stat_profiles"] = {
        "my_active": _default_stat_profile(),
        "opponent_active": _user_final_stats(hp=31),
    }

    result = attach_selected_move_damage_estimate(payload)

    context = result["moves"]["my_selected_move"]["survival_context"]
    assert context["available"] is False
    assert context["reason"] == "multi_hit_not_supported"
    assert "Multi-hit moves, hazards, residual damage, weather/status chip, and exact turn sequencing are not modeled." in context[
        "limitations"
    ]


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


def test_choice_band_applies_to_my_physical_move_only() -> None:
    physical_payload = _battle_input(selected_move=_dragon_claw())
    physical_payload["item_profiles"] = _item_profiles(my_item="choice-band")
    special_payload = _battle_input(selected_move=_flamethrower())
    special_payload["item_profiles"] = _item_profiles(my_item="choice-band")

    physical_default = build_selected_move_damage_estimate(_battle_input(selected_move=_dragon_claw()))
    physical_estimate = build_selected_move_damage_estimate(physical_payload)
    special_default = build_selected_move_damage_estimate(_battle_input(selected_move=_flamethrower()))
    special_estimate = build_selected_move_damage_estimate(special_payload)

    assert physical_estimate["damage_range"]["max"] > physical_default["damage_range"]["max"]
    assert physical_estimate["item_effects"]["attacker_item"] == {
        "item_id": "choice-band",
        "status": "applied",
        "applied_effects": ["damage_modifier"],
        "unapplied_effects": ["choice_lock"],
    }
    assert physical_estimate["assumption_profile"]["id"] == "default_level50_ivs31_evs0_neutral_with_damage_item"
    assert special_estimate["damage_range"] == special_default["damage_range"]
    assert special_estimate["item_effects"]["attacker_item"]["status"] == "not_applicable"
    assert "choice_lock" in special_estimate["item_effects"]["attacker_item"]["unapplied_effects"]


def test_choice_specs_applies_to_my_special_move_only() -> None:
    special_payload = _battle_input(selected_move=_flamethrower())
    special_payload["item_profiles"] = _item_profiles(my_item="choice-specs")
    physical_payload = _battle_input(selected_move=_dragon_claw())
    physical_payload["item_profiles"] = _item_profiles(my_item="choice-specs")

    special_default = build_selected_move_damage_estimate(_battle_input(selected_move=_flamethrower()))
    special_estimate = build_selected_move_damage_estimate(special_payload)
    physical_default = build_selected_move_damage_estimate(_battle_input(selected_move=_dragon_claw()))
    physical_estimate = build_selected_move_damage_estimate(physical_payload)

    assert special_estimate["damage_range"]["max"] > special_default["damage_range"]["max"]
    assert special_estimate["item_effects"]["attacker_item"]["status"] == "applied"
    assert special_estimate["item_effects"]["attacker_item"]["unapplied_effects"] == ["choice_lock"]
    assert physical_estimate["damage_range"] == physical_default["damage_range"]
    assert physical_estimate["item_effects"]["attacker_item"]["status"] == "not_applicable"


def test_life_orb_applies_damage_and_marks_recoil_unapplied() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(my_item="life-orb")

    default_estimate = build_selected_move_damage_estimate(_battle_input(selected_move=_flamethrower()))
    estimate = build_selected_move_damage_estimate(payload)

    assert estimate["damage_range"]["max"] > default_estimate["damage_range"]["max"]
    assert estimate["item_effects"]["attacker_item"] == {
        "item_id": "life-orb",
        "status": "applied",
        "applied_effects": ["damage_modifier"],
        "unapplied_effects": ["recoil"],
    }
    assert estimate["assumptions"]["item"] == "supported_attacker_damage_item_applied"
    assert estimate["is_final_battle_damage"] is False
    assert "ko_chance" not in estimate


def test_muscle_band_and_wise_glasses_apply_by_move_category() -> None:
    muscle_payload = _battle_input(selected_move=_dragon_claw())
    muscle_payload["item_profiles"] = _item_profiles(my_item="muscle-band")
    wise_payload = _battle_input(selected_move=_flamethrower())
    wise_payload["item_profiles"] = _item_profiles(my_item="wise-glasses")

    physical_default = build_selected_move_damage_estimate(_battle_input(selected_move=_dragon_claw()))
    special_default = build_selected_move_damage_estimate(_battle_input(selected_move=_flamethrower()))

    muscle_estimate = build_selected_move_damage_estimate(muscle_payload)
    wise_estimate = build_selected_move_damage_estimate(wise_payload)

    assert muscle_estimate["damage_range"]["max"] > physical_default["damage_range"]["max"]
    assert muscle_estimate["item_effects"]["attacker_item"]["status"] == "applied"
    assert wise_estimate["damage_range"]["max"] > special_default["damage_range"]["max"]
    assert wise_estimate["item_effects"]["attacker_item"]["status"] == "applied"


def test_legal_type_boosting_item_applies_when_move_type_matches() -> None:
    cases = [
        ("charcoal", "Charcoal", _flamethrower(), "fire"),
        ("mystic-water", "Mystic Water", _water_pulse(), "water"),
        ("black-belt", "Black Belt", _brick_break(), "fighting"),
        ("metal-coat", "Metal Coat", _iron_head(), "steel"),
        ("sharp-beak", "Sharp Beak", _air_slash(), "flying"),
    ]

    for item_id, name_en, move, boosted_type in cases:
        default_estimate = build_selected_move_damage_estimate(_battle_input(selected_move=move))
        payload = _battle_input(selected_move=move)
        payload["item_profiles"] = {
            "my_active": _legal_type_boosting_item_profile(item_id, name_en=name_en),
            "opponent_active": _item_profile(None),
        }

        estimate = build_selected_move_damage_estimate(payload)

        assert estimate["damage_range"]["max"] > default_estimate["damage_range"]["max"]
        assert estimate["item_effects"]["attacker_item"] == {
            "item_id": item_id,
            "name_en": name_en,
            "effect_type": "type_boosting_damage_modifier",
            "boosted_type": boosted_type,
            "modifier": 1.2,
            "status": "applied",
            "applied_effects": ["damage_modifier"],
            "unapplied_effects": [],
            "reason": "Move type matches item boosted type.",
        }
        assert estimate["assumptions"]["item"] == "supported_attacker_damage_item_applied"


def test_legal_type_boosting_item_mismatch_is_not_applicable_without_damage_change() -> None:
    default_estimate = build_selected_move_damage_estimate(_battle_input(selected_move=_air_slash()))
    payload = _battle_input(selected_move=_air_slash())
    payload["item_profiles"] = {
        "my_active": _legal_type_boosting_item_profile("charcoal", name_en="Charcoal"),
        "opponent_active": _item_profile(None),
    }

    estimate = build_selected_move_damage_estimate(payload)

    assert estimate["damage_range"] == default_estimate["damage_range"]
    assert estimate["item_effects"]["attacker_item"]["status"] == "not_applicable"
    assert estimate["item_effects"]["attacker_item"]["item_id"] == "charcoal"
    assert estimate["item_effects"]["attacker_item"]["name_en"] == "Charcoal"
    assert estimate["item_effects"]["attacker_item"]["effect_type"] == "type_boosting_damage_modifier"
    assert estimate["item_effects"]["attacker_item"]["boosted_type"] == "fire"
    assert estimate["item_effects"]["attacker_item"]["modifier"] == 1.2
    assert estimate["item_effects"]["attacker_item"]["reason"] == "Move type does not match item boosted type."
    _assert_default_assumption_profile(estimate)


def test_legal_type_boosting_item_applies_to_available_selected_and_opponent_known_moves() -> None:
    payload = _battle_input(
        selected_move=_flamethrower(),
        available_moves=[_flamethrower(), _air_slash()],
    )
    payload["item_profiles"] = {
        "my_active": _legal_type_boosting_item_profile("charcoal", name_en="Charcoal"),
        "opponent_active": _legal_type_boosting_item_profile("sharp-beak", name_en="Sharp Beak"),
    }
    payload["opponent_moves"] = {
        "known_moves": [{**_air_slash(), "source": "user_confirmed"}],
        "candidate_moves": [{**_air_slash(), "source": "champions_movepool"}],
    }

    with_my_estimates = attach_selected_move_damage_estimate(payload)
    result = attach_opponent_known_move_damage_estimates(with_my_estimates)

    available = result["moves"]["my_available_moves"]
    selected = result["moves"]["my_selected_move"]["damage_estimate"]
    known_move = result["opponent_moves"]["known_moves"][0]
    candidate_move = result["opponent_moves"]["candidate_moves"][0]
    assert available[0]["damage_estimate"]["item_effects"]["attacker_item"]["status"] == "applied"
    assert available[1]["damage_estimate"]["item_effects"]["attacker_item"]["status"] == "not_applicable"
    assert selected["item_effects"]["attacker_item"]["status"] == "applied"
    assert known_move["damage_estimate"]["item_effects"]["attacker_item"]["status"] == "applied"
    assert known_move["damage_estimate"]["item_effects"]["attacker_item"]["item_id"] == "sharp-beak"
    assert known_move["damage_estimate"]["target"] == "my_active"
    assert "damage_estimate" not in candidate_move
    assert "ko_context" not in candidate_move
    assert "recovery_context" not in candidate_move
    assert "accuracy_context" not in candidate_move
    assert "critical_context" not in candidate_move


def test_fairy_feather_remains_unsupported_without_catalog_damage_change() -> None:
    default_estimate = build_selected_move_damage_estimate(_battle_input(selected_move=_moonblast()))
    payload = _battle_input(selected_move=_moonblast())
    payload["item_profiles"] = {
        "my_active": _legal_type_boosting_item_profile(
            "fairy-feather",
            name_en="Fairy Feather",
            effect_support_status="legal_but_not_modeled",
            ui_status="recognized_not_modeled",
        ),
        "opponent_active": _item_profile(None),
    }

    estimate = build_selected_move_damage_estimate(payload)

    assert estimate["damage_range"] == default_estimate["damage_range"]
    assert estimate["item_effects"]["attacker_item"] == {
        "item_id": "fairy-feather",
        "name_en": "Fairy Feather",
        "status": "unsupported_item",
        "effect_type": "type_boosting_damage_modifier",
        "applied_effects": [],
        "unapplied_effects": ["unsupported_catalog_missing"],
        "reason": "No catalog-backed damage modifier is available yet.",
    }
    _assert_default_assumption_profile(estimate)


def test_unsupported_item_does_not_modify_damage() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(my_item="expert-belt")

    default_estimate = build_selected_move_damage_estimate(_battle_input(selected_move=_flamethrower()))
    estimate = build_selected_move_damage_estimate(payload)

    assert estimate["damage_range"] == default_estimate["damage_range"]
    assert estimate["item_effects"]["attacker_item"]["status"] == "unsupported_item"
    assert "item_damage_modifier_not_supported_in_v0.16" in estimate["item_effects"]["attacker_item"][
        "unapplied_effects"
    ]
    _assert_default_assumption_profile(estimate)


def test_unknown_and_none_items_do_not_modify_damage() -> None:
    unknown_payload = _battle_input(selected_move=_flamethrower())
    unknown_payload["item_profiles"] = {
        "my_active": {
            "status": "unknown",
            "source": "user_unconfirmed",
            "item_id": None,
            "name_en": None,
            "name_ko": None,
            "effects_scope": [],
            "damage_modifier_status": "not_applicable",
        },
        "opponent_active": _item_profile(None),
    }
    no_item_payload = _battle_input(selected_move=_flamethrower())
    no_item_payload["item_profiles"] = {
        "my_active": {
            "status": "none",
            "source": "user_confirmed",
            "item_id": None,
            "name_en": None,
            "name_ko": None,
            "effects_scope": [],
            "damage_modifier_status": "not_applicable",
        },
        "opponent_active": _item_profile(None),
    }

    default_estimate = build_selected_move_damage_estimate(_battle_input(selected_move=_flamethrower()))
    unknown_estimate = build_selected_move_damage_estimate(unknown_payload)
    no_item_estimate = build_selected_move_damage_estimate(no_item_payload)

    assert unknown_estimate["damage_range"] == default_estimate["damage_range"]
    assert no_item_estimate["damage_range"] == default_estimate["damage_range"]
    assert unknown_estimate["item_effects"]["attacker_item"]["status"] == "unknown"
    assert no_item_estimate["item_effects"]["attacker_item"]["status"] == "none"
    assert "ko_chance" not in unknown_estimate
    assert "ohko_chance" not in no_item_estimate


def test_legal_but_not_modeled_items_do_not_modify_damage() -> None:
    default_estimate = build_selected_move_damage_estimate(_battle_input(selected_move=_flamethrower()))

    for item_id in ("choice-scarf", "focus-sash", "leftovers"):
        payload = _battle_input(selected_move=_flamethrower())
        payload["item_profiles"] = {
            "my_active": _legal_but_not_modeled_item_profile(item_id),
            "opponent_active": _item_profile(None),
        }

        estimate = build_selected_move_damage_estimate(payload)

        assert estimate["damage_range"] == default_estimate["damage_range"]
        assert estimate["item_effects"]["attacker_item"]["item_id"] == item_id
        assert estimate["item_effects"]["attacker_item"]["status"] == "not_applied"
        assert "ko_chance" not in estimate


def test_opponent_known_move_uses_opponent_attacker_item() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="life-orb")

    default_estimate = build_opponent_known_move_damage_estimate(_battle_input(selected_move=_flamethrower()), _rock_slide())
    estimate = build_opponent_known_move_damage_estimate(payload, _rock_slide())

    assert estimate["damage_range"]["max"] > default_estimate["damage_range"]["max"]
    assert estimate["target"] == "my_active"
    assert estimate["item_effects"]["attacker_item"]["item_id"] == "life-orb"
    assert estimate["item_effects"]["attacker_item"]["status"] == "applied"
    assert estimate["item_effects"]["defender_item"]["status"] == "system_default_none"
    assert "ko_chance" not in estimate


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


def _item_profiles(my_item: str | None = None, opponent_item: str | None = None) -> dict:
    return {
        "my_active": _item_profile(my_item),
        "opponent_active": _item_profile(opponent_item),
    }


def _item_profile(item_id: str | None) -> dict:
    if item_id is None:
        return {
            "status": "system_default_none",
            "source": "system_default",
            "item_id": None,
            "name_en": None,
            "name_ko": None,
            "effects_scope": [],
            "damage_modifier_status": "not_applicable",
        }
    return {
        "status": "user_confirmed",
        "source": "user_input",
        "item_id": item_id,
        "name_en": item_id,
        "name_ko": None,
        "effects_scope": ["damage_modifier"],
        "damage_modifier_status": "not_applied",
    }


def _legal_but_not_modeled_item_profile(item_id: str) -> dict:
    return {
        "status": "user_confirmed",
        "source": "user_input",
        "item_id": item_id,
        "name_en": item_id,
        "name_ko": None,
        "effects_scope": [],
        "legality_status": "legal",
        "effect_support_status": "legal_but_not_modeled",
        "damage_modifier_status": "not_applied",
        "ui_status": "recognized_not_modeled",
        "notes": [],
    }


def _legal_type_boosting_item_profile(
    item_id: str,
    *,
    name_en: str,
    effect_support_status: str = "legal_and_damage_supported",
    ui_status: str = "recognized_modeled",
) -> dict:
    return {
        "status": "user_confirmed",
        "source": "user_input",
        "item_id": item_id,
        "name_en": name_en,
        "name_ko": None,
        "effects_scope": ["damage_modifier"],
        "category": "type_boosting_item",
        "legal": True,
        "legality_status": "legal",
        "effect_support_status": effect_support_status,
        "damage_modifier_status": "not_applied",
        "ui_status": ui_status,
        "notes": [],
    }


def _ko_damage_estimate(
    *,
    min_damage: int = 30,
    max_damage: int = 33,
    rolls: list[int] | None = None,
) -> dict:
    estimate = {
        "status": "available_with_default_assumptions",
        "scope": "selected_move_only",
        "damage_range": {
            "min": min_damage,
            "max": max_damage,
        },
        "derived_stats": {
            "defender": {
                "default_max_hp": 100,
            },
        },
    }
    if rolls is not None:
        estimate["rolls"] = rolls
        estimate["damage_range"] = {
            "min": min(rolls),
            "max": max(rolls),
        }
    return estimate


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


def _water_pulse() -> dict:
    return {
        "slot": 0,
        "move_id": "water-pulse",
        "name_en": "Water Pulse",
        "name_ko": "Water Pulse",
        "type": "water",
        "category": "special",
        "power": 60,
        "accuracy": 100,
        "pp": 20,
    }


def _brick_break() -> dict:
    return {
        "slot": 0,
        "move_id": "brick-break",
        "name_en": "Brick Break",
        "name_ko": "Brick Break",
        "type": "fighting",
        "category": "physical",
        "power": 75,
        "accuracy": 100,
        "pp": 15,
    }


def _iron_head() -> dict:
    return {
        "slot": 0,
        "move_id": "iron-head",
        "name_en": "Iron Head",
        "name_ko": "Iron Head",
        "type": "steel",
        "category": "physical",
        "power": 80,
        "accuracy": 100,
        "pp": 15,
    }


def _moonblast() -> dict:
    return {
        "slot": 0,
        "move_id": "moonblast",
        "name_en": "Moonblast",
        "name_ko": "Moonblast",
        "type": "fairy",
        "category": "special",
        "power": 95,
        "accuracy": 100,
        "pp": 15,
    }


def _dragon_claw() -> dict:
    return {
        "slot": 0,
        "move_id": "dragon-claw",
        "name_en": "Dragon Claw",
        "name_ko": "Dragon Claw",
        "type": "dragon",
        "category": "physical",
        "power": 80,
        "accuracy": 100,
        "pp": 15,
    }


def _corviknight_payload() -> dict:
    return {
        "slot_index": 0,
        "name_en": "corviknight",
        "name_ko": "Corviknight",
        "types": ["flying", "steel"],
        "types_ko": ["Flying", "Steel"],
        "base_stats": {
            "hp": 98,
            "attack": 87,
            "defense": 105,
            "special-attack": 53,
            "special-defense": 85,
            "speed": 67,
        },
        "abilities": ["pressure", "unnerve"],
        "abilities_ko": ["Pressure", "Unnerve"],
        "hp_percent": 100,
        "selected_move_index": None,
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
