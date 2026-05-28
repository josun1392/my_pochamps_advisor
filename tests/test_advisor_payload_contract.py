from __future__ import annotations

from types import MethodType, SimpleNamespace

from core.cache_manager import CacheManager
from core.champions_item_repository import ChampionsItemRepository
from core.champions_move_pool import ChampionsMovePoolRepository
from core.ko_mapping_loader import KoMappingLoader
from core.move_repository import MoveView
from core.move_repository import MoveRepository
from core.pokemon_repository import PokemonView
from core.pokemon_stat_sample_repository import PokemonStatSampleRepository
from llm.advisor_client import _build_ui_selected_prompt
from llm.advisor_payload_contract import ADVISOR_KNOWN_LIMITATIONS, ADVISOR_PAYLOAD_MODE
from ui.main_window import MainWindow
from ui.widgets.item_profile_dialog import item_profile_from_option, legal_item_options_from_repository


def test_ui_payload_uses_advisor_contract_guardrails() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()

    assert payload["scenario"]["mode"] == ADVISOR_PAYLOAD_MODE
    assert payload["scenario"]["known_limitations"] == ADVISOR_KNOWN_LIMITATIONS
    assert "Move damage estimates, when present, use default assumptions and are not final battle damage." in payload[
        "scenario"
    ]["known_limitations"]
    assert "Opponent candidate moves are possible Champions moves, not confirmed moves." in payload["scenario"][
        "known_limitations"
    ]
    assert "Candidate moves may be mentioned as possible threats only when labeled as unconfirmed." in payload[
        "scenario"
    ]["known_limitations"]
    assert (
        "Opponent known move damage estimates, when present, are default-assumption reference values only."
        in payload["scenario"]["known_limitations"]
    )
    assert (
        "Every damage estimate includes an assumption_profile that identifies the stat model used."
        in payload["scenario"]["known_limitations"]
    )
    assert "User-confirmed final stats may be used when stat_profiles provides all six stats." in payload["scenario"][
        "known_limitations"
    ]
    assert "item_profiles distinguishes unknown, none, system_default_none, and user_confirmed item state." in payload[
        "scenario"
    ]["known_limitations"]
    assert (
        "speed_context, when present, is raw/effective Speed comparison only and is not final turn order."
        in payload["scenario"]["known_limitations"]
    )
    assert (
        "Raw/effective Speed comparison is available only when both active Pokemon have user-confirmed final Speed in v0.30."
        in payload["scenario"]["known_limitations"]
    )
    assert "Default Speed fallback is not used in v0.30." in payload["scenario"]["known_limitations"]
    assert "Only item effects marked as applied in damage_estimate.item_effects are included in damage numbers." in payload[
        "scenario"
    ]["known_limitations"]
    assert "Type matchup descriptions must use damage_estimate.type_effectiveness when present." in payload[
        "scenario"
    ]["known_limitations"]
    assert "Opponent candidate move damage is not calculated in v0.18." in payload["scenario"]["known_limitations"]
    assert (
        "opponent_assumptions, when present, contains possible opponent profiles, not confirmed sets."
        in payload["scenario"]["known_limitations"]
    )
    assert (
        "opponent_assumptions.calculation_usage context_only means samples are not used directly for damage or speed calculations."
        in payload["scenario"]["known_limitations"]
    )
    assert (
        "When opponent_assumptions.available is true and possible_samples exist, briefly mention that possible sample context exists when relevant."
        in payload["scenario"]["known_limitations"]
    )
    assert (
        "When possible sample context is mentioned, keep it to at most one short limitation sentence."
        in payload["scenario"]["known_limitations"]
    )
    assert (
        "Do not dump sample_id, full stats, source metadata, update_policy, coverage_probability, or full Top-K sample lists into the response."
        in payload["scenario"]["known_limitations"]
    )
    assert (
        "When opponent_assumptions.available is false, do not invent samples or force a sample limitation."
        in payload["scenario"]["known_limitations"]
    )
    assert "Use my_available_moves damage_estimates to compare the user's own move options." in payload["scenario"][
        "known_limitations"
    ]
    assert "Terastallization is banned in PoChamps and must not be considered." in payload["scenario"][
        "known_limitations"
    ]


def test_manual_move_payload_includes_only_user_confirmed_moves() -> None:
    panel = _panel(
        "charizard",
        selected_move_index=2,
        selected_moves=[None, _move("air-slash"), _move("flamethrower"), None],
    )

    available_moves = MainWindow._panel_moves_payload(panel)
    selected_move = MainWindow._selected_move_payload(panel)

    assert [move["move_id"] for move in available_moves] == ["air-slash", "flamethrower"]
    assert [move["slot"] for move in available_moves] == [1, 2]
    assert selected_move is not None
    assert selected_move["move_id"] == "flamethrower"
    assert selected_move["slot"] == 2


def test_ui_payload_attaches_selected_move_damage_estimate() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()
    estimate = payload["moves"]["my_selected_move"]["damage_estimate"]

    assert estimate["status"] == "available_with_default_assumptions"
    assert estimate["is_final_battle_damage"] is False
    _assert_default_assumption_profile(estimate)
    assert "damage_range" in estimate
    assert "percent_range" in estimate
    assert "type_effectiveness" in estimate
    assert "assumptions" in estimate
    assert "limitations" in estimate
    assert "ko_chance" not in estimate
    assert "ohko_chance" not in estimate


def test_ui_payload_attaches_available_move_damage_estimates() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower"), _move("air-slash")])
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()
    estimates = [move["damage_estimate"] for move in payload["moves"]["my_available_moves"]]

    assert payload["moves"]["move_data_status"] == "four_move_damage_comparison_v0.10"
    assert len(estimates) == 2
    assert {estimate["scope"] for estimate in estimates} == {"available_move_comparison"}
    assert all(estimate["status"] == "available_with_default_assumptions" for estimate in estimates)
    assert all(
        estimate["assumption_profile"]["id"] == "default_level50_ivs31_evs0_neutral_no_item"
        for estimate in estimates
    )
    assert all("damage_range" in estimate for estimate in estimates)
    assert all("percent_range" in estimate for estimate in estimates)
    assert all("ko_chance" not in estimate for estimate in estimates)
    assert all("item_effects" in estimate for estimate in estimates)


def test_ui_payload_includes_default_stat_profiles() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()

    assert payload["stat_profiles"]["my_active"]["status"] == "default_assumption"
    assert payload["stat_profiles"]["my_active"]["source"] == "system_default"
    assert payload["stat_profiles"]["my_active"]["final_stats"] is None
    assert payload["stat_profiles"]["opponent_active"]["status"] == "default_assumption"
    assert payload["stat_profiles"]["opponent_active"]["source"] == "system_default"
    assert payload["stat_profiles"]["opponent_active"]["final_stats"] is None
    assert payload["speed_context"]["available"] is False
    assert payload["speed_context"]["reason"] == "insufficient_confirmed_final_stats"
    assert payload["speed_context"]["is_final_turn_order"] is False
    assert "Default Speed fallback is not used in v0.30." in payload["speed_context"]["limitations"]


def test_ui_payload_includes_opponent_assumptions_for_species_with_samples() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()
    assumptions = payload["opponent_assumptions"]

    assert assumptions["mode"] == "multi_sample_assumption_v0.38"
    assert assumptions["available"] is True
    assert assumptions["scope"] == "opponent_active"
    assert assumptions["is_confirmed_information"] is False
    assert assumptions["calculation_usage"] == "context_only"
    opponent = assumptions["opponent_active"]
    assert opponent["species_id"] == "garchomp"
    assert opponent["known_status"] == "not_confirmed"
    assert opponent["is_user_confirmed"] is False
    assert opponent["user_confirmed_fields"] == {}
    assert opponent["observation_history"] == []
    assert opponent["update_policy"]["mode"] == "static"
    assert opponent["samples_meta"]["default_top_k"] == 3
    assert opponent["samples_meta"]["included_top_k"] == 2
    sample = opponent["possible_samples"][0]
    assert sample["sample_id"] == "garchomp_fast_physical_01"
    assert sample["is_user_confirmed"] is False
    assert sample["prior_probability"] is None
    assert sample["prior_probability_type"] == "not_available"
    assert "possible_stats" not in sample
    assert "stats" not in sample
    assert "sp_distribution" not in sample


def test_opponent_assumptions_do_not_feed_damage_or_speed_context() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()

    assert payload["opponent_assumptions"]["available"] is True
    assert "possible_stats" not in payload["opponent_assumptions"]["opponent_active"]["possible_samples"][0]
    assert payload["stat_profiles"]["opponent_active"]["status"] == "default_assumption"
    assert payload["stat_profiles"]["opponent_active"]["final_stats"] is None
    assert payload["moves"]["my_selected_move"]["damage_estimate"]["assumption_profile"]["id"] == (
        "default_level50_ivs31_evs0_neutral_no_item"
    )
    assert payload["speed_context"]["available"] is False
    assert payload["speed_context"]["reason"] == "insufficient_confirmed_final_stats"


def test_ui_payload_includes_default_item_profiles() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()

    my_item = payload["item_profiles"]["my_active"]
    opponent_item = payload["item_profiles"]["opponent_active"]
    assert my_item["status"] == "system_default_none"
    assert my_item["source"] == "system_default"
    assert my_item["item_id"] is None
    assert my_item["damage_modifier_status"] == "not_applicable"
    assert opponent_item["status"] == "unknown"
    assert opponent_item["source"] == "user_unconfirmed"
    assert opponent_item["item_id"] is None


def test_ui_payload_includes_user_selected_item_profiles() -> None:
    item_options = legal_item_options_from_repository(ChampionsItemRepository())
    my_panel = _panel(
        "garchomp",
        selected_move_index=0,
        selected_moves=[_move("earthquake")],
        item_profile=item_profile_from_option("choice-scarf", item_options=item_options),
    )
    opponent_panel = _panel(
        "corviknight",
        selected_move_index=0,
        selected_moves=[_move("drill-peck")],
        item_profile=item_profile_from_option("focus-sash", role_key="opponent_active", item_options=item_options),
    )
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()

    assert payload["item_profiles"]["my_active"]["item_id"] == "choice-scarf"
    assert payload["item_profiles"]["my_active"]["status"] == "user_confirmed"
    assert payload["item_profiles"]["my_active"]["effect_support_status"] == "legal_but_not_modeled"
    assert payload["item_profiles"]["my_active"]["damage_modifier_status"] == "not_applied"
    assert payload["item_profiles"]["opponent_active"]["item_id"] == "focus-sash"
    assert payload["item_profiles"]["opponent_active"]["status"] == "user_confirmed"
    my_estimate = payload["moves"]["my_available_moves"][0]["damage_estimate"]
    opponent_estimate = payload["opponent_moves"]["known_moves"][0]["damage_estimate"]
    assert my_estimate["item_effects"]["attacker_item"]["status"] == "not_applied"
    assert opponent_estimate["item_effects"]["attacker_item"]["status"] == "not_applied"


def test_ui_payload_applies_legal_type_boosting_item_to_matching_move() -> None:
    item_options = legal_item_options_from_repository(ChampionsItemRepository())
    my_panel = _panel(
        "charizard",
        selected_move_index=0,
        selected_moves=[_move("flamethrower"), _move("air-slash")],
        item_profile=item_profile_from_option("charcoal", item_options=item_options),
    )
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()

    selected_estimate = payload["moves"]["my_selected_move"]["damage_estimate"]
    available_estimates = [move["damage_estimate"] for move in payload["moves"]["my_available_moves"]]
    assert payload["item_profiles"]["my_active"]["item_id"] == "charcoal"
    assert payload["item_profiles"]["my_active"]["effect_support_status"] == "legal_and_damage_supported"
    assert selected_estimate["item_effects"]["attacker_item"]["status"] == "applied"
    assert selected_estimate["item_effects"]["attacker_item"]["effect_type"] == "type_boosting_damage_modifier"
    assert selected_estimate["item_effects"]["attacker_item"]["boosted_type"] == "fire"
    assert selected_estimate["item_effects"]["attacker_item"]["modifier"] == 1.2
    assert available_estimates[0]["item_effects"]["attacker_item"]["status"] == "applied"
    assert available_estimates[1]["item_effects"]["attacker_item"]["status"] == "not_applicable"


def test_ui_payload_distinguishes_unknown_and_no_item() -> None:
    my_panel = _panel(
        "charizard",
        selected_move_index=0,
        selected_moves=[_move("flamethrower")],
        item_profile=item_profile_from_option("none"),
    )
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()

    assert payload["item_profiles"]["my_active"]["status"] == "none"
    assert payload["item_profiles"]["opponent_active"]["status"] == "unknown"


def test_ui_payload_includes_user_confirmed_final_stats() -> None:
    my_panel = _panel(
        "charizard",
        selected_move_index=0,
        selected_moves=[_move("flamethrower")],
        final_stats=_final_stats(spa=300),
    )
    opponent_panel = _panel(
        "garchomp",
        selected_move_index=0,
        selected_moves=[_move("earthquake")],
        final_stats=_final_stats(atk=300),
    )
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()

    assert payload["stat_profiles"]["my_active"]["status"] == "user_confirmed_final_stats"
    assert payload["stat_profiles"]["my_active"]["source"] == "user_input"
    assert payload["stat_profiles"]["my_active"]["final_stats"]["spa"] == 300
    assert payload["stat_profiles"]["opponent_active"]["status"] == "user_confirmed_final_stats"
    assert payload["stat_profiles"]["opponent_active"]["final_stats"]["atk"] == 300
    my_estimate = payload["moves"]["my_available_moves"][0]["damage_estimate"]
    opponent_estimate = payload["opponent_moves"]["known_moves"][0]["damage_estimate"]
    assert my_estimate["assumption_profile"]["id"] == "user_confirmed_final_stats_level50"
    assert my_estimate["assumption_profile"]["is_user_confirmed"] is True
    assert opponent_estimate["assumption_profile"]["id"] == "user_confirmed_final_stats_level50"
    assert opponent_estimate["is_final_battle_damage"] is False
    speed_context = payload["speed_context"]
    assert speed_context["available"] is True
    assert speed_context["my_active"]["raw_speed"] == 167
    assert speed_context["my_active"]["source"] == "user_confirmed_final_stats"
    assert speed_context["opponent_active"]["raw_speed"] == 167
    assert speed_context["my_active"]["effective_speed"] == 167
    assert speed_context["my_active"]["speed_modifiers"] == []
    assert speed_context["opponent_active"]["effective_speed"] == 167
    assert speed_context["opponent_active"]["speed_modifiers"] == []
    assert speed_context["comparison"]["raw_speed_relation"] == "speed_tie"
    assert speed_context["comparison"]["raw_speed_margin"] == 0
    assert speed_context["comparison"]["raw_speed_tie"] is True
    assert speed_context["comparison"]["effective_speed_relation"] == "speed_tie"
    assert speed_context["comparison"]["effective_speed_margin"] == 0
    assert speed_context["comparison"]["effective_speed_tie"] is True
    assert speed_context["comparison"]["speed_margin"] == 0
    assert speed_context["comparison"]["speed_tie"] is True
    assert speed_context["is_final_turn_order"] is False
    assert "Effective Speed includes only supported speed modifiers." in speed_context["limitations"]
    assert "Choice Scarf speed is modeled only when the item is user-confirmed." in speed_context["limitations"]
    assert "Choice lock is not modeled." in speed_context["limitations"]


def test_speed_context_my_active_faster_with_confirmed_final_stats() -> None:
    my_panel = _panel(
        "garchomp",
        selected_move_index=0,
        selected_moves=[_move("earthquake")],
        final_stats=_final_stats(spe=169),
    )
    opponent_panel = _panel(
        "corviknight",
        selected_move_index=0,
        selected_moves=[_move("drill-peck")],
        final_stats=_final_stats(spe=101),
    )
    window = _window(my_panel, opponent_panel)

    speed_context = window._build_llm_battle_input()["speed_context"]

    assert speed_context["available"] is True
    assert speed_context["comparison"]["raw_speed_relation"] == "my_active_faster"
    assert speed_context["comparison"]["effective_speed_relation"] == "my_active_faster"
    assert speed_context["comparison"]["raw_speed_margin"] == 68
    assert speed_context["comparison"]["effective_speed_margin"] == 68
    assert speed_context["comparison"]["speed_margin"] == 68
    assert speed_context["comparison"]["speed_tie"] is False
    assert speed_context["comparison"]["effective_speed_tie"] is False
    assert speed_context["is_final_turn_order"] is False


def test_speed_context_opponent_active_faster_with_confirmed_final_stats() -> None:
    my_panel = _panel(
        "garchomp",
        selected_move_index=0,
        selected_moves=[_move("earthquake")],
        final_stats=_final_stats(spe=90),
    )
    opponent_panel = _panel(
        "corviknight",
        selected_move_index=0,
        selected_moves=[_move("drill-peck")],
        final_stats=_final_stats(spe=134),
    )
    window = _window(my_panel, opponent_panel)

    speed_context = window._build_llm_battle_input()["speed_context"]

    assert speed_context["available"] is True
    assert speed_context["comparison"]["raw_speed_relation"] == "opponent_active_faster"
    assert speed_context["comparison"]["effective_speed_relation"] == "opponent_active_faster"
    assert speed_context["comparison"]["raw_speed_margin"] == 44
    assert speed_context["comparison"]["effective_speed_margin"] == 44
    assert speed_context["comparison"]["speed_margin"] == 44
    assert speed_context["comparison"]["speed_tie"] is False


def test_speed_context_requires_both_sides_user_confirmed_final_stats() -> None:
    my_panel = _panel(
        "garchomp",
        selected_move_index=0,
        selected_moves=[_move("earthquake")],
        final_stats=_final_stats(spe=169),
    )
    opponent_panel = _panel("corviknight", selected_move_index=0, selected_moves=[_move("drill-peck")])
    window = _window(my_panel, opponent_panel)

    speed_context = window._build_llm_battle_input()["speed_context"]

    assert speed_context["available"] is False
    assert speed_context["reason"] == "insufficient_confirmed_final_stats"
    assert "Default Speed fallback is not used in v0.30." in speed_context["limitations"]
    assert "my_active" not in speed_context
    assert "opponent_active" not in speed_context


def test_speed_context_applies_user_confirmed_choice_scarf_speed() -> None:
    item_options = legal_item_options_from_repository(ChampionsItemRepository())
    my_panel = _panel(
        "garchomp",
        selected_move_index=0,
        selected_moves=[_move("earthquake")],
        final_stats=_final_stats(spe=100),
        item_profile=item_profile_from_option("choice-scarf", item_options=item_options),
    )
    opponent_panel = _panel(
        "corviknight",
        selected_move_index=0,
        selected_moves=[_move("drill-peck")],
        final_stats=_final_stats(spe=120),
    )
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()
    speed_context = payload["speed_context"]

    assert payload["item_profiles"]["my_active"]["item_id"] == "choice-scarf"
    assert payload["item_profiles"]["my_active"]["effect_support_status"] == "legal_but_not_modeled"
    assert speed_context["my_active"]["raw_speed"] == 100
    assert speed_context["my_active"]["effective_speed"] == 150
    assert speed_context["my_active"]["speed_modifiers"] == [
        {
            "source": "item",
            "item_id": "choice-scarf",
            "name_en": "Choice Scarf",
            "modifier": 1.5,
            "applied": True,
            "unsupported_effects": ["choice_lock"],
        }
    ]
    assert speed_context["opponent_active"]["effective_speed"] == 120
    assert speed_context["comparison"]["raw_speed_relation"] == "opponent_active_faster"
    assert speed_context["comparison"]["effective_speed_relation"] == "my_active_faster"
    assert speed_context["comparison"]["raw_speed_margin"] == 20
    assert speed_context["comparison"]["effective_speed_margin"] == 30
    assert "Choice Scarf speed is modeled only when the item is user-confirmed." in speed_context["limitations"]
    assert "Choice lock is not modeled." in speed_context["limitations"]
    assert speed_context["is_final_turn_order"] is False


def test_speed_context_applies_opponent_user_confirmed_choice_scarf_speed() -> None:
    item_options = legal_item_options_from_repository(ChampionsItemRepository())
    my_panel = _panel(
        "garchomp",
        selected_move_index=0,
        selected_moves=[_move("earthquake")],
        final_stats=_final_stats(spe=160),
    )
    opponent_panel = _panel(
        "corviknight",
        selected_move_index=0,
        selected_moves=[_move("drill-peck")],
        final_stats=_final_stats(spe=120),
        item_profile=item_profile_from_option("choice-scarf", role_key="opponent_active", item_options=item_options),
    )
    window = _window(my_panel, opponent_panel)

    speed_context = window._build_llm_battle_input()["speed_context"]

    assert speed_context["my_active"]["effective_speed"] == 160
    assert speed_context["opponent_active"]["raw_speed"] == 120
    assert speed_context["opponent_active"]["effective_speed"] == 180
    assert speed_context["opponent_active"]["speed_modifiers"][0]["item_id"] == "choice-scarf"
    assert speed_context["comparison"]["raw_speed_relation"] == "my_active_faster"
    assert speed_context["comparison"]["effective_speed_relation"] == "opponent_active_faster"


def test_speed_context_ignores_unconfirmed_unknown_and_no_item_choice_scarf() -> None:
    cases = [
        {"status": "unknown", "source": "user_unconfirmed", "item_id": "choice-scarf", "name_en": "Choice Scarf"},
        item_profile_from_option("unknown"),
        item_profile_from_option("none"),
    ]

    for item_profile in cases:
        my_panel = _panel(
            "garchomp",
            selected_move_index=0,
            selected_moves=[_move("earthquake")],
            final_stats=_final_stats(spe=100),
            item_profile=item_profile,
        )
        opponent_panel = _panel(
            "corviknight",
            selected_move_index=0,
            selected_moves=[_move("drill-peck")],
            final_stats=_final_stats(spe=120),
        )
        window = _window(my_panel, opponent_panel)

        speed_context = window._build_llm_battle_input()["speed_context"]

        assert speed_context["my_active"]["effective_speed"] == 100
        assert speed_context["my_active"]["speed_modifiers"] == []
        assert speed_context["comparison"]["effective_speed_relation"] == "opponent_active_faster"


def test_partial_final_stats_remain_default_assumption() -> None:
    my_panel = _panel(
        "charizard",
        selected_move_index=0,
        selected_moves=[_move("flamethrower")],
        final_stats={"hp": 153, "atk": 104},
    )
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()

    assert payload["stat_profiles"]["my_active"]["status"] == "default_assumption"
    assert payload["stat_profiles"]["my_active"]["final_stats"] is None


def test_ui_payload_includes_opponent_moves_section() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()
    opponent_moves = payload["opponent_moves"]

    assert opponent_moves["status"] == "candidates_only"
    assert opponent_moves["known_moves"] == []
    assert len(opponent_moves["candidate_moves"]) == 24
    assert opponent_moves["candidate_moves_limit"] == 24
    assert opponent_moves["candidate_source_status"]["status"] == "available"
    assert all(candidate["source"] == "champions_movepool" for candidate in opponent_moves["candidate_moves"])
    assert all(
        candidate["confidence"] == "possible_not_confirmed"
        for candidate in opponent_moves["candidate_moves"]
    )


def test_opponent_selected_moves_become_known_moves() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    opponent_panel = _panel("garchomp", selected_move_index=0, selected_moves=[_move("earthquake")])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()
    opponent_moves = payload["opponent_moves"]

    assert opponent_moves["status"] == "known_and_candidates"
    known_move = opponent_moves["known_moves"][0]
    assert len(opponent_moves["known_moves"]) == 1
    assert known_move["slot"] == 0
    assert known_move["move_id"] == "earthquake"
    assert known_move["source"] == "user_confirmed"
    assert known_move["damage_estimate"]["status"] == "available_with_default_assumptions"
    assert known_move["damage_estimate"]["scope"] == "opponent_known_move_only"
    assert known_move["damage_estimate"]["target"] == "my_active"
    assert known_move["damage_estimate"]["is_final_battle_damage"] is False
    _assert_default_assumption_profile(known_move["damage_estimate"])
    assert "damage_range" in known_move["damage_estimate"]
    assert "percent_range" in known_move["damage_estimate"]
    assert "ko_chance" not in known_move["damage_estimate"]
    assert "ohko_chance" not in known_move["damage_estimate"]
    assert "earthquake" not in {candidate["move_id"] for candidate in opponent_moves["candidate_moves"]}
    assert all("damage_estimate" not in candidate for candidate in opponent_moves["candidate_moves"])


def test_missing_opponent_fixture_does_not_fallback_to_pokeapi_learnset() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    opponent_panel = _panel("missingno", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()
    opponent_moves = payload["opponent_moves"]

    assert opponent_moves["status"] == "unavailable_missing_champions_movepool"
    assert opponent_moves["known_moves"] == []
    assert opponent_moves["candidate_moves"] == []
    assert payload["moves"]["opponent_available_moves"] == []
    assert payload["opponent_assumptions"]["available"] is False
    assert payload["opponent_assumptions"]["reason"] == "no_samples_for_species"


def test_pokemon_payload_marks_base_stats_as_reference_data_only() -> None:
    panel = _panel("charizard", selected_move_index=0, selected_moves=[])

    payload = MainWindow._panel_to_llm_payload(panel, slot_index=0)

    assert payload["name_en"] == "charizard"
    assert payload["base_stats"] == {
        "hp": 78,
        "attack": 84,
        "defense": 78,
        "special-attack": 109,
        "special-defense": 85,
        "speed": 100,
    }
    assert "final_stats" not in payload
    assert "evs" not in payload
    assert "ivs" not in payload
    assert "nature" not in payload
    assert "item" not in payload


def test_ui_cost_text_includes_pricing_status() -> None:
    assert (
        MainWindow._format_cost_text(
            input_tokens=4031,
            output_tokens=52,
            cost=0.0,
            pricing_status="free_tier_zero_cost",
        )
        == "Free tier | input 4031 / output 52 | $0.0000000"
    )
    assert (
        MainWindow._format_cost_text(
            input_tokens=1000,
            output_tokens=100,
            cost=0.00055,
            pricing_status="paid_tier_estimated_cost",
        )
        == "Paid estimate | input 1000 / output 100 | $0.0005500"
    )
    assert (
        MainWindow._format_cost_text(
            input_tokens=1000,
            output_tokens=100,
            cost=0.0,
            pricing_status="unknown_model_or_unknown_pricing",
        )
        == "Pricing unknown | input 1000 / output 100"
    )


def test_ui_selected_prompt_preserves_opponent_move_guardrails() -> None:
    prompt = _build_ui_selected_prompt(
        {
            "moves": {
                "my_available_moves": [
                    {
                        "move_id": "flamethrower",
                        "damage_estimate": {"status": "available_with_default_assumptions"},
                    }
                ]
            },
            "opponent_moves": {
                "known_moves": [{"move_id": "earthquake", "source": "user_confirmed"}],
                "candidate_moves": [{"move_id": "rock-slide", "confidence": "possible_not_confirmed"}],
            },
        }
    )

    assert "known_moves as user-confirmed" in prompt
    assert "candidate_moves only as possible, not confirmed" in prompt
    assert "label them as unconfirmed" in prompt
    assert "Opponent known move damage estimates" in prompt
    assert "User-confirmed final stats may be used" in prompt
    assert "Opponent candidate move damage is not calculated in v0.14" not in prompt
    assert "Opponent candidate move damage is not calculated in v0.16" not in prompt
    assert "Opponent candidate move damage is not calculated in v0.18" in prompt
    assert "Only item effects marked as applied in damage_estimate.item_effects" in prompt
    assert "speed_context is present" in prompt
    assert "raw/effective Speed comparison only" in prompt
    assert "not final turn order" in prompt
    assert "speed_context.is_final_turn_order is false" in prompt
    assert "based on raw Speed only" in prompt
    assert "appears faster by raw Speed" in prompt
    assert "Default Speed fallback is not used in v0.30" in prompt
    assert "If effective_speed is present" in prompt
    assert "supported speed modifier estimate" in prompt
    assert "Choice Scarf speed may be included only when speed_context marks it applied" in prompt
    assert "for Choice Scarf, choice lock is still not modeled" in prompt
    assert "raw Speed and effective Speed disagree" in prompt
    assert "priority, Tailwind, Trick Room, paralysis, Speed stages" in prompt
    assert "Legal items and modeled item effects are separate concepts" in prompt
    assert "legal_but_not_modeled selected item may be user-confirmed" in prompt
    assert "For type boosting items, say the damage modifier is included only" in prompt
    assert "when damage_estimate.item_effects.attacker_item.status is applied" in prompt
    assert "do not say a type boosting item boosted damage when the move type does not match" in prompt
    assert "Fairy Feather is legal but not damage-modeled" in prompt
    assert "Damage-supported non-legal/debug items are not normal legal selector options" in prompt
    assert "If an attacker item effect is applied" in prompt
    assert "default assumptions plus the supported item modifier" in prompt
    assert "If Life Orb is applied, say recoil is not modeled" in prompt
    assert "If Choice Scarf, Choice Band, or Choice Specs is applied, say choice lock is not modeled" in prompt
    assert "Do not mention choice lock for non-Choice items such as Charcoal" in prompt
    assert "Life Orb recoil, Focus Sash survival, and Leftovers recovery" in prompt
    assert "Choice lock for Charcoal" not in prompt
    assert "Charcoal choice lock" not in prompt
    assert "use damage_estimate.type_effectiveness" in prompt
    assert "super effective, resisted, or immune" in prompt
    assert "Do not print raw type_effectiveness labels" in prompt
    assert "super_effective" in prompt
    assert "not_very_effective" in prompt
    assert "super effective" in prompt
    assert "not very effective" in prompt
    assert "immune/no effect" in prompt
    assert "Use my_available_moves damage_estimates to compare the user's own move options" in prompt
    assert "Do not claim OHKO, 2HKO, KO chance, survival, or speed order" in prompt
    assert "opponent_assumptions is present" in prompt
    assert "possible_samples only as context-only risk profiles" in prompt
    assert "not confirmed opponent sets" in prompt
    assert "calculation_usage is context_only" in prompt
    assert "do not say those samples changed damage_estimate or speed_context" in prompt
    assert "Do not interpret null prior_probability as zero probability" in prompt
    assert "Do not infer final turn order, KO, survival, or exact stats from possible samples" in prompt
    assert "include at most one short limitation sentence that possible sample context exists" in prompt
    assert "possible opponent samples exist, but they are context only and not confirmed" in prompt
    assert "Do not dump sample_id, full stats, source metadata, update_policy, coverage_probability" in prompt
    assert "full Top-K sample lists" in prompt
    assert "If opponent_assumptions is unavailable, do not invent samples" in prompt
    assert "Opponent sample role, archetype_id, and possible_items are context-only metadata" in prompt
    assert "Possible_items are possible assumptions, not confirmed held items" in prompt
    assert "Do not enumerate opponent sample metadata by default" in prompt


def test_advisor_contract_preserves_item_modifier_response_guardrail() -> None:
    assert (
        "When item_effects.attacker_item.status is applied, mention that the supported item damage modifier is applied."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Type boosting item damage is included only when item_effects.attacker_item.status is applied."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not say a type boosting item boosted damage when the move type does not match or the item is unsupported."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Legal item selection does not imply the selected item has a modeled effect." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "Fairy Feather is legal but not damage-modeled until a catalog-backed modifier exists."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "If an item damage modifier is applied, describe the estimate as default assumptions plus the supported item modifier, not only default assumptions."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "If Life Orb is applied, say Life Orb recoil is not modeled." in ADVISOR_KNOWN_LIMITATIONS
    assert "If Choice Scarf, Choice Band, or Choice Specs is applied, say choice lock is not modeled." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "Do not mention choice lock for non-Choice items such as Charcoal, Mystic Water, Black Belt, Metal Coat, Sharp Beak, Fairy Feather, Leftovers, or Focus Sash."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not print raw type_effectiveness labels like super_effective or not_very_effective; convert them to natural wording."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "speed_context, when present, is raw/effective Speed comparison only and is not final turn order."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Default Speed fallback is not used in v0.30." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "Do not say a Pokemon will move first when speed_context.is_final_turn_order is false."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "effective_speed, when present, is a supported speed modifier estimate and is not final turn order."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Choice Scarf speed may be applied in speed_context only when the item is user-confirmed."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Choice lock remains not modeled when a user-confirmed Choice item is applied."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "opponent_assumptions, when present, contains possible opponent profiles, not confirmed sets."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "opponent_assumptions.calculation_usage context_only means samples are not used directly for damage or speed calculations."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When opponent_assumptions.available is true and possible_samples exist, briefly mention that possible sample context exists when relevant."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When possible sample context is mentioned, keep it to at most one short limitation sentence."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not dump sample_id, full stats, source metadata, update_policy, coverage_probability, or full Top-K sample lists into the response."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When opponent_assumptions.available is false, do not invent samples or force a sample limitation."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Opponent sample role, archetype_id, and possible_items are context-only metadata, not confirmed opponent information."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Opponent sample possible_items are possible assumptions, not confirmed held items."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not enumerate opponent sample metadata by default; keep sample visibility concise."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Do not describe sample_assumed opponent samples as user-confirmed information." in ADVISOR_KNOWN_LIMITATIONS
    assert "Do not interpret prior_probability null as zero probability." in ADVISOR_KNOWN_LIMITATIONS


def _panel(
    name: str,
    *,
    selected_move_index: int | None,
    selected_moves: list[MoveView | None],
    final_stats: dict | None = None,
    item_profile: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        pokemon_view=_pokemon(name),
        current_hp_percent=100,
        selected_move_index=selected_move_index,
        selected_moves=selected_moves + [None] * (4 - len(selected_moves)),
        final_stats=final_stats,
        item_profile=item_profile,
    )


def _assert_default_assumption_profile(estimate: dict) -> None:
    assert estimate["assumption_profile"] == {
        "id": "default_level50_ivs31_evs0_neutral_no_item",
        "label": "Default Level 50 / IV 31 / EV 0 / neutral nature / no item",
        "source": "system_default",
        "confidence": "rough_reference",
        "is_user_confirmed": False,
    }


def _final_stats(
    *,
    hp: int = 153,
    atk: int = 104,
    def_: int = 98,
    spa: int = 161,
    spd: int = 105,
    spe: int = 167,
) -> dict:
    return {
        "hp": hp,
        "atk": atk,
        "def": def_,
        "spa": spa,
        "spd": spd,
        "spe": spe,
    }


def _window(my_panel, opponent_panel):
    window = MainWindow.__new__(MainWindow)
    window.selected_slots = {"team_my": 0, "team_enemy": 0}
    window.move_repo = MoveRepository(CacheManager(), KoMappingLoader())
    window.champions_move_pool_repo = ChampionsMovePoolRepository()
    window.champions_item_repo = ChampionsItemRepository()
    window.pokemon_stat_sample_repo = PokemonStatSampleRepository()

    def _slot_panel(self, column_name: str, slot_index: int):
        del slot_index
        return my_panel if column_name == "team_my" else opponent_panel

    window._slot_panel = MethodType(_slot_panel, window)
    return window


def _pokemon(name: str) -> PokemonView:
    if name == "garchomp":
        return PokemonView(
            en="garchomp",
            ko="Garchomp",
            types_en=["dragon", "ground"],
            types_ko=["Dragon", "Ground"],
            base_stats={
                "hp": 108,
                "attack": 130,
                "defense": 95,
                "special-attack": 80,
                "special-defense": 85,
                "speed": 102,
            },
            abilities_en=["sand-veil", "rough-skin"],
            abilities_ko=["Sand Veil", "Rough Skin"],
            moves_en=["earthquake", "outrage"],
        )
    if name == "missingno":
        return PokemonView(
            en="missingno",
            ko="MissingNo.",
            types_en=["normal"],
            types_ko=["Normal"],
            base_stats={
                "hp": 33,
                "attack": 33,
                "defense": 33,
                "special-attack": 33,
                "special-defense": 33,
                "speed": 33,
            },
            abilities_en=[],
            abilities_ko=[],
            moves_en=[],
        )
    if name == "corviknight":
        return PokemonView(
            en="corviknight",
            ko="Corviknight",
            types_en=["flying", "steel"],
            types_ko=["Flying", "Steel"],
            base_stats={
                "hp": 98,
                "attack": 87,
                "defense": 105,
                "special-attack": 53,
                "special-defense": 85,
                "speed": 67,
            },
            abilities_en=["pressure", "unnerve"],
            abilities_ko=["Pressure", "Unnerve"],
            moves_en=["drill-peck"],
        )
    return PokemonView(
        en="charizard",
        ko="Charizard",
        types_en=["fire", "flying"],
        types_ko=["Fire", "Flying"],
        base_stats={
            "hp": 78,
            "attack": 84,
            "defense": 78,
            "special-attack": 109,
            "special-defense": 85,
            "speed": 100,
        },
        abilities_en=["blaze", "solar-power"],
        abilities_ko=["Blaze", "Solar Power"],
        moves_en=["air-slash", "flamethrower"],
    )


def _move(move_id: str) -> MoveView:
    if move_id == "earthquake":
        return MoveView(
            move_id="earthquake",
            name_en="Earthquake",
            name_ko="Earthquake",
            type="ground",
            category="physical",
            power=100,
            accuracy=100,
            pp=10,
        )
    if move_id == "air-slash":
        return MoveView(
            move_id="air-slash",
            name_en="Air Slash",
            name_ko="Air Slash",
            type="flying",
            category="special",
            power=75,
            accuracy=95,
            pp=15,
        )
    if move_id == "drill-peck":
        return MoveView(
            move_id="drill-peck",
            name_en="Drill Peck",
            name_ko="Drill Peck",
            type="flying",
            category="physical",
            power=80,
            accuracy=100,
            pp=20,
        )
    return MoveView(
        move_id="flamethrower",
        name_en="Flamethrower",
        name_ko="Flamethrower",
        type="fire",
        category="special",
        power=90,
        accuracy=100,
        pp=15,
    )
