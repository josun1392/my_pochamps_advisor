from __future__ import annotations

import json
from copy import deepcopy
from types import MethodType, SimpleNamespace

from core.cache_manager import CacheManager
from core.champions_item_repository import ChampionsItemRepository
from core.champions_move_pool import ChampionsMovePoolRepository
from core.ko_mapping_loader import KoMappingLoader
from core.move_repository import MoveView
from core.move_repository import MoveRepository
from core.pokemon_repository import PokemonView
from core.pokemon_stat_sample_repository import PokemonStatSampleRepository
from llm.advisor_client import _build_ui_selected_prompt, build_ui_advice_payload
from llm.advisor_damage_estimate import attach_selected_move_damage_estimate
from llm.advisor_payload_contract import (
    ADVICE_CONTEXT_KEYS,
    ADVICE_CONTEXTS_REQUIRING_MOVE_LOCAL_ITEM_EFFECT_SCRUB,
    ADVICE_ITEM_CONTEXT_KEYS,
    DEBUG_ONLY_REASON_PHRASES,
    ADVISOR_KNOWN_LIMITATIONS,
    ADVISOR_PAYLOAD_MODE,
)
from tests.test_advisor_damage_estimate import (
    _battle_input,
    _bullet_seed,
    _default_stat_profile,
    _flamethrower,
    _ice_beam,
    _item_profiles,
    _tackle,
    _user_final_stats,
)
from ui.main_window import MainWindow
from ui.widgets.item_profile_dialog import item_profile_from_option, legal_item_options_from_repository


UNAVAILABLE_ITEM_ADVICE_PAYLOAD_FORBIDDEN_TERMS = (
    "Chilan Berry",
    "chilan",
    "effect is not applied",
    "item effect is not included",
    "not modeled",
    "not reflected",
    "unsupported",
    "deferred",
    "blocked",
)


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
    assert (
        "ko_context, when present, is limited damage-roll context only and is not final battle truth."
        in payload["scenario"]["known_limitations"]
    )
    assert "ko_context does not change raw damage_range or rolls." in payload["scenario"]["known_limitations"]
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
        "opponent_assumptions mode is a historical behavior label; schema_version and metadata_version describe the current payload shape."
        in payload["scenario"]["known_limitations"]
    )
    assert (
        "Opponent assumptions version fields are developer/contract metadata and should not be mentioned in user-facing battle advice."
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
    assert payload["moves"]["my_selected_move"]["ko_context"]["mode"] == "limited_damage_roll_ko_context"
    assert payload["moves"]["my_selected_move"]["ko_context"]["is_final_battle_truth"] is False
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
    assert all(move["ko_context"]["mode"] == "limited_damage_roll_ko_context" for move in payload["moves"]["my_available_moves"])
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
    assert assumptions["schema_version"] == "opponent_assumptions_v0.47"
    assert assumptions["metadata_version"] == "minimal_metadata_v1"
    assert assumptions["payload_features"] == {
        "possible_samples": True,
        "minimal_metadata": True,
        "debug_summary_supported": True,
        "full_stats_excluded": True,
        "damage_speed_integration": False,
    }
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
    assert known_move["ko_context"]["mode"] == "limited_damage_roll_ko_context"
    assert known_move["ko_context"]["is_final_battle_truth"] is False
    assert "ko_chance" not in known_move["damage_estimate"]
    assert "ohko_chance" not in known_move["damage_estimate"]
    assert "earthquake" not in {candidate["move_id"] for candidate in opponent_moves["candidate_moves"]}
    assert all("damage_estimate" not in candidate for candidate in opponent_moves["candidate_moves"])
    assert all("ko_context" not in candidate for candidate in opponent_moves["candidate_moves"])


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
    assert "Quick Claw speed-order context may appear only as limited speed_order_context" in prompt
    assert "speed_order_context applies only when Quick Claw is user-confirmed and Champions legal" in prompt
    assert "may affect move order or can occasionally affect move order" in prompt
    assert "Final move order, activation probability, speed ties, priority" in prompt
    assert "Do not say will move first, guaranteed outspeeds, confirmed first" in prompt
    assert "wins the speed interaction" in prompt
    assert "safe because it moves first" in prompt
    assert "Choice Scarf is not modeled through speed_order_context" in prompt
    assert "Legal items and modeled item effects are separate concepts" in prompt
    assert "legal_but_not_modeled selected item may be user-confirmed" in prompt
    assert "For type boosting items, say the damage modifier is included only" in prompt
    assert "when damage_estimate.item_effects.attacker_item.status is applied" in prompt
    assert "do not say a type boosting item boosted damage when the move type does not match" in prompt
    assert "Fairy Feather is legal but not damage-modeled" in prompt
    assert "Type-boost item context may appear only as limited type_boost_context" in prompt
    assert "type_boost_context is an advice context for user-confirmed" in prompt
    assert "damage-supported type-boosting items when the move type matches" in prompt
    assert "ko_context is unchanged by type_boost_context" in prompt
    assert "Type-boost-adjusted KO/OHKO/2HKO context is not calculated" in prompt
    assert "Do not say boosted damage guarantees KO" in prompt
    assert "secures the KO" in prompt
    assert "proves the KO" in prompt
    assert "final battle damage" in prompt
    assert "type_boost_context is unavailable" in prompt
    assert "do not mention the item name, effect, or unavailable reason" in prompt
    assert "Light Ball species-stat item context may appear only as limited species_stat_item_context" in prompt
    assert "species_stat_item_context is available, say Light Ball is a Pikachu-specific" in prompt
    assert "applied in the damage estimate" in prompt
    assert "damage_estimate.item_effects marks the supported modifier as applied" in prompt
    assert "Do not say Light Ball is not included or Light Ball is not modeled" in prompt
    assert "not final stat truth and not a final KO guarantee" in prompt
    assert "Damage-supported non-legal/debug items are not normal legal selector options" in prompt
    assert "If an attacker item effect is applied" in prompt
    assert "default assumptions plus the supported item modifier" in prompt
    assert "If Life Orb is applied, say recoil is not modeled" in prompt
    assert "If Choice Scarf, Choice Band, or Choice Specs is applied, say choice lock is not modeled" in prompt
    assert "Do not mention choice lock for non-Choice items such as Charcoal" in prompt
    assert "Life Orb recoil is not connected" in prompt
    assert "Sitrus Berry and Leftovers recovery may appear only as limited recovery_context" in prompt
    assert "survival_context does not change raw damage_range or rolls" in prompt
    assert "ko_context is unchanged by recovery_context" in prompt
    assert "KO/OHKO/2HKO estimates do not include recovery" in prompt
    assert "recovery_context applies only when Sitrus Berry or Leftovers is user-confirmed" in prompt
    assert "defender max HP is available" in prompt
    assert "Sitrus Berry recovery_context is threshold recovery limited context" in prompt
    assert "item consumption are not tracked" in prompt
    assert "Leftovers recovery_context is end-of-turn limited context" in prompt
    assert "exact activation timing, item consumption, and turn sequencing are not modeled" in prompt
    assert "Say recovery may affect follow-up KO/2HKO only under limited assumptions" in prompt
    assert "do not claim final 2HKO or 3HKO truth without Turn Engine" in prompt
    assert "do not infer recovery if the item is unknown or unconfirmed" in prompt
    assert "Do not say Sitrus Berry definitely activates" in prompt
    assert "KO chance includes recovery" in prompt
    assert "recovery changes the damage range" in prompt
    assert "Bright Powder accuracy may appear only as limited accuracy_context" in prompt
    assert "accuracy_context does not change raw damage_range or rolls" in prompt
    assert "ko_context is unchanged by accuracy_context" in prompt
    assert "KO/OHKO/2HKO estimates do not include hit chance" in prompt
    assert "Bright Powder may reduce hit reliability" in prompt
    assert "not damage reduction" in prompt
    assert "When accuracy_context is available, keep accuracy wording concise" in prompt
    assert "raw damage and KO/OHKO/2HKO estimates do not include hit chance" in prompt
    assert "Include one concise limitation sentence" in prompt
    assert "final hit probability, accuracy/evasion stages, ability/weather interactions" in prompt
    assert "multi-hit accuracy, and turn sequencing are not modeled" in prompt
    assert "Hit-adjusted KO probability is not calculated" in prompt
    assert "Final hit probability is not calculated" in prompt
    assert "Do not claim the move will miss" in prompt
    assert "miss is guaranteed" in prompt
    assert "hit-adjusted KO chance is a percent" in prompt
    assert "Do not infer Bright Powder if the item is unknown or unconfirmed" in prompt
    assert "Scope Lens critical-hit context may appear only as limited critical_context" in prompt
    assert "critical_context does not change raw damage_range or rolls" in prompt
    assert "ko_context is unchanged by critical_context" in prompt
    assert "KO/OHKO/2HKO estimates do not include crit chance" in prompt
    assert "Scope Lens may increase critical-hit likelihood" in prompt
    assert "not a direct damage boost" in prompt
    assert "critical_context applies only when Scope Lens is user-confirmed" in prompt
    assert "Final critical-hit probability is not calculated" in prompt
    assert "Crit-adjusted KO probability is not calculated" in prompt
    assert "Do not claim the move will crit" in prompt
    assert "critical hit is guaranteed" in prompt
    assert "Do not infer Scope Lens if the item is unknown or unconfirmed" in prompt
    assert "Critical-hit stages, abilities, move-specific crit effects, and turn sequencing are not modeled" in prompt
    assert "King's Rock flinch context may appear only as limited flinch_context" in prompt
    assert "flinch_context does not change raw damage_range or rolls" in prompt
    assert "ko_context is unchanged by flinch_context" in prompt
    assert "KO/OHKO/2HKO estimates do not include flinch chance" in prompt
    assert "King's Rock may add flinch pressure" in prompt
    assert "not a direct damage boost" in prompt
    assert "flinch_context applies only when King's Rock is user-confirmed" in prompt
    assert "say the raw damage estimate is unchanged and raw ko_context is unchanged" in prompt
    assert "damage modifier is not included" in prompt
    assert "say raw damage estimate is unchanged instead" in prompt
    assert "Final flinch probability is not calculated" in prompt
    assert "Flinch-adjusted turn or outcome probability is not calculated" in prompt
    assert "Include one concise limitation sentence that speed order, target action state, abilities" in prompt
    assert "multi-hit handling, and turn sequencing are not modeled" in prompt
    assert "Do not claim the target will flinch" in prompt
    assert "cannot move" in prompt
    assert "flinch is guaranteed" in prompt
    assert "Do not infer King's Rock if the item is unknown or unconfirmed" in prompt
    assert "Speed order, target action state, abilities, multi-hit handling, and turn sequencing are not modeled" in prompt
    assert "Loaded Dice multi-hit context may appear only as limited multi_hit_context" in prompt
    assert "multi_hit_context does not change raw damage_range or rolls" in prompt
    assert "ko_context is unchanged by multi_hit_context" in prompt
    assert "KO/OHKO/2HKO estimates do not include multi-hit count changes" in prompt
    assert "Loaded Dice may improve multi-hit reliability for eligible moves" in prompt
    assert "not a direct damage boost" in prompt
    assert "multi_hit_context applies only when Loaded Dice is user-confirmed" in prompt
    assert "Champions legal coverage is confirmed" in prompt
    assert "move multi-hit metadata is available" in prompt
    assert "Final hit count probability is not calculated" in prompt
    assert "Multi-hit-adjusted KO probability is not calculated" in prompt
    assert "Do not claim a specific number of hits will occur" in prompt
    assert "5 hits are guaranteed" in prompt
    assert "Do not claim Loaded Dice breaks Focus Sash" in prompt
    assert "Do not infer Loaded Dice if the item is unknown or unconfirmed" in prompt
    assert "Focus Sash, King's Rock, accuracy, crit per-hit handling, and turn sequencing are not modeled" in prompt
    assert "Type-resist berry context may appear only as limited resist_berry_context" in prompt
    assert "resist_berry_context does not change raw damage_range or rolls" in prompt
    assert "ko_context is unchanged by resist_berry_context" in prompt
    assert "KO/OHKO/2HKO estimates do not include berry reduction" in prompt
    assert "the raw damage estimate is unchanged and raw ko_context is unchanged" in prompt
    assert "resist_berry_context is unavailable" in prompt
    assert "developer/debug/contract metadata only" in prompt
    assert "do not mention the berry name, berry effect, or unavailable reason" in prompt
    assert "Do not say Yache Berry effect is not applied" in prompt
    assert "do not say the berry effect is not included" in prompt
    assert "do not say the berry is not modeled" in prompt
    assert "standard type-resist berry may reduce a qualifying super-effective hit" in prompt
    assert "berry-adjusted damage is not calculated" in prompt
    assert "Berry-adjusted KO probability is not calculated" in prompt
    assert "Item consumption is not tracked" in prompt
    assert "Do not say the Pokemon definitely survives" in prompt
    assert "Do not infer a resist berry if the item is unknown or unconfirmed" in prompt
    assert "Resist berry edge cases require explicit support before advice can use them" in prompt
    assert "Unsupported resist berry edge cases" not in prompt
    assert "Chilan Berry and edge cases are not modeled unless explicitly supported" not in prompt
    assert "Chilan Berry context may appear only as limited chilan_berry_context" in prompt
    assert "chilan_berry_context applies only when Chilan Berry is user-confirmed" in prompt
    assert "local metadata marks always_resist true for Normal" in prompt
    assert "incoming move type is Normal" in prompt
    assert "It does not change raw damage_range or rolls, and ko_context is unchanged" in prompt
    assert "KO/OHKO/2HKO estimates do not include Chilan Berry reduction" in prompt
    assert "Chilan-adjusted damage and Chilan-adjusted KO probability are not calculated" in prompt
    assert "When chilan_berry_context is available" in prompt
    assert "Chilan Berry is a Normal-type limited context" in prompt
    assert "Chilan Berry is a Normal-type limited context and may reduce damage" in prompt
    assert "from a Normal-type damaging move" in prompt
    assert "raw damage rolls and ko_context remain based on the current calculator" in prompt
    assert "not integrated into final KO odds" in prompt
    assert "Do not say Chilan Berry is not included or Chilan Berry is not modeled" in prompt
    assert "Do not say guaranteed survival" in prompt
    assert "confirmed live" in prompt
    assert "will survive because of Chilan Berry" in prompt
    assert "final damage is halved" in prompt
    assert "raw damage rolls already include Chilan Berry" in prompt
    assert "Chilan Berry applies to all move types" in prompt
    assert "If chilan_berry_context is unavailable" in prompt
    assert "do not mention Chilan Berry, its effect, or unavailable reason" in prompt
    assert "blocked by legal item coverage" in prompt
    assert "developer/debug/contract metadata" in prompt
    assert "do not include that item effect in normal user-facing recommendation text" in prompt
    assert "do not mention the blocked item name" in prompt
    assert "do not say user-confirmed Loaded Dice" in prompt
    assert "do not say Power Herb" in prompt
    assert "do not say the item is not modeled" in prompt
    assert "do not say the item effect is not included" in prompt
    assert "Do not use generic substitutes such as the user-confirmed item effect" in prompt
    assert "held item effect, selected item effect, or item-based limitation" in prompt
    assert "Do not mention that a blocked item exists by saying its effect is absent" in prompt
    assert "ignored, unavailable, excluded, unsupported, or outside the estimate" in prompt
    assert "Do not say Loaded Dice is not modeled or Power Herb is not modeled unless the user explicitly asks" in prompt
    assert "If the user explicitly asks about a blocked item" in prompt
    assert "Champions legal coverage is not confirmed" in prompt
    assert "item effect is not reflected in advice" in prompt
    assert "Do not imply blocked or future-only items are available in Champions" in prompt
    assert "unavailable, deferred, blocked, unconfirmed, non-triggered, or absent item contexts" in prompt
    assert "developer/debug/contract metadata by default" in prompt
    assert "Do not say item effect is not included" in prompt
    assert "opponent's item effect is not included" in prompt
    assert "user-confirmed item effect is not included" in prompt
    assert "item is not modeled" in prompt
    assert "item effect is not applied" in prompt
    assert "not included in this estimate" in prompt
    assert "not reflected in the calculation" in prompt
    assert "Do not mention unavailable or deferred item names or effects" in prompt
    assert "Focus Sash and Focus Band survival may appear only as limited survival_context" in prompt
    assert "not as damage reduction" in prompt
    assert "it does not change raw damage_range or rolls" in prompt
    assert "Focus Sash survival_context applies only when Focus Sash is user-confirmed and HP is full" in prompt
    assert "say may survive at 1 HP" in prompt
    assert "Focus Band survival_context applies only when Focus Band is user-confirmed" in prompt
    assert "raw incoming hit is potentially lethal" in prompt
    assert "say may occasionally survive and survival is not guaranteed" in prompt
    assert "Focus Band activation probability and final survival probability are not calculated" in prompt
    assert "KO/OHKO/2HKO estimates do not include Focus Band activation" in prompt
    assert "do not say will survive" in prompt
    assert "guaranteed survive" in prompt
    assert "cannot be KO'd" in prompt
    assert "confirmed survival" in prompt
    assert "safe to take the hit" in prompt
    assert "survives this hit" in prompt
    assert "definitely survives" in prompt
    assert "include one concise limitation sentence" in prompt
    assert "activation probability, and exact turn sequencing are not modeled" in prompt
    assert "Do not infer Focus Sash or Focus Band if the item is unknown or unconfirmed" in prompt
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
    assert "If ko_context is present, treat it as limited damage-roll context only" in prompt
    assert "ko_context does not change raw damage_range or rolls" in prompt
    assert "OHKO chance is based on damage rolls only" in prompt
    assert "2HKO context is a limited min/max estimate" in prompt
    assert "not final turn simulation" in prompt
    assert "does not model accuracy, speed order, priority, recovery, hazards, chip damage" in prompt
    assert "survival_context is separate from raw ko_context" in prompt
    assert "not included in KO probability" in prompt
    assert "opponent_assumptions is present" in prompt
    assert "Opponent assumptions version fields are developer/contract metadata" in prompt
    assert "do not mention schema_version, metadata_version, or payload_features" in prompt
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


def test_advice_payload_filters_unavailable_resist_berry_context_but_keeps_debug_reason() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="yache-berry")
    enriched = attach_selected_move_damage_estimate(payload)

    debug_move = enriched["moves"]["my_selected_move"]
    assert debug_move["resist_berry_context"]["available"] is False
    assert debug_move["resist_berry_context"]["reason"] == "move_not_super_effective"

    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]

    assert "resist_berry_context" not in advice_move
    assert "damage_estimate" in advice_move
    assert "ko_context" in advice_move
    assert advice_move["damage_estimate"]["damage_range"] == debug_move["damage_estimate"]["damage_range"]
    assert advice_move["damage_estimate"]["rolls"] == debug_move["damage_estimate"]["rolls"]
    assert advice_move["ko_context"]["ohko"] == debug_move["ko_context"]["ohko"]
    assert advice_move["ko_context"]["two_hko"] == debug_move["ko_context"]["two_hko"]
    _assert_forbidden_terms_absent_from_advice_payload(
        advice_payload,
        extra_terms=("move_not_super_effective", "yache-berry"),
    )


def test_advice_payload_preserves_available_chilan_context_for_normal_move() -> None:
    payload = _battle_input(selected_move=_tackle())
    payload["item_profiles"] = _item_profiles(opponent_item="chilan-berry")
    enriched = attach_selected_move_damage_estimate(payload)

    debug_move = enriched["moves"]["my_selected_move"]
    assert debug_move["resist_berry_context"]["available"] is False
    assert debug_move["resist_berry_context"]["reason"] == "chilan_berry_deferred"
    assert debug_move["chilan_berry_context"]["available"] is True
    assert debug_move["chilan_berry_context"]["normal_resist_effect"]["berry_type"] == "normal"
    assert debug_move["chilan_berry_context"]["normal_resist_effect"]["incoming_move_type"] == "normal"
    assert debug_move["chilan_berry_context"]["normal_resist_effect"]["requires_super_effective_hit"] is False
    assert debug_move["chilan_berry_context"]["normal_resist_effect"]["always_resist"] is True
    assert debug_move["chilan_berry_context"]["normal_resist_effect"]["raw_damage_rolls_changed"] is False
    assert debug_move["chilan_berry_context"]["normal_resist_effect"]["ko_context_changed"] is False
    assert debug_move["chilan_berry_context"]["normal_resist_effect"]["chilan_adjusted_damage_integrated"] is False
    assert debug_move["chilan_berry_context"]["normal_resist_effect"]["chilan_adjusted_ko_integrated"] is False
    assert debug_move["chilan_berry_context"]["normal_resist_effect"]["item_consumption_tracked"] is False

    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]

    assert "resist_berry_context" not in advice_move
    assert advice_move["chilan_berry_context"]["available"] is True
    assert advice_move["chilan_berry_context"]["item"]["item_id"] == "chilan-berry"
    assert advice_move["chilan_berry_context"]["normal_resist_effect"] == debug_move["chilan_berry_context"][
        "normal_resist_effect"
    ]
    assert "Normal-type limited Chilan Berry context only." in advice_move["chilan_berry_context"]["limitations"]
    assert (
        "Chilan Berry may reduce damage from a Normal-type damaging move."
        in advice_move["chilan_berry_context"]["limitations"]
    )
    assert (
        "Raw damage rolls and ko_context remain based on the current calculator."
        in advice_move["chilan_berry_context"]["limitations"]
    )
    assert (
        "This context is not integrated into final KO odds and is not final survival truth."
        in advice_move["chilan_berry_context"]["limitations"]
    )
    assert advice_payload["item_profiles"]["opponent_active"]["item_id"] == "chilan-berry"
    assert advice_move["damage_estimate"]["damage_range"] == debug_move["damage_estimate"]["damage_range"]
    assert advice_move["damage_estimate"]["rolls"] == debug_move["damage_estimate"]["rolls"]
    assert advice_move["ko_context"]["ohko"] == debug_move["ko_context"]["ohko"]
    assert advice_move["ko_context"]["two_hko"] == debug_move["ko_context"]["two_hko"]
    rendered = json.dumps(advice_payload, ensure_ascii=False)
    assert "guaranteed survival" not in rendered
    assert "confirmed live" not in rendered
    assert "final damage is halved" not in rendered
    assert "raw damage rolls already include Chilan Berry" not in rendered
    assert "Chilan Berry applies to all move types" not in rendered
    prompt = _build_ui_selected_prompt(enriched)
    assert "Available item contexts are present in the advice payload" in prompt
    assert "Chilan Berry / chilan_berry_context as Normal-type limited context" in prompt
    assert "Mention each listed available item context at least once" in prompt
    assert "Do not describe these available item effects as unavailable, unmodeled, not included" in prompt
    assert "no item is considered, assuming no item, without item effects, or default no-item assumption" in prompt
    assert "raw damage/ko_context limitations remain, but do not erase the available item context" in prompt
    assert "final KO odds, guaranteed survival, guaranteed move order, exact final stats" in prompt
    assert "chilan_berry_deferred" not in prompt


def test_advice_payload_hides_unavailable_chilan_context_for_non_normal_move() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="chilan-berry")
    enriched = attach_selected_move_damage_estimate(payload)

    debug_move = enriched["moves"]["my_selected_move"]
    assert debug_move["resist_berry_context"]["available"] is False
    assert debug_move["resist_berry_context"]["reason"] == "chilan_berry_deferred"
    assert debug_move["chilan_berry_context"]["available"] is False
    assert debug_move["chilan_berry_context"]["reason"] == "move_type_not_normal"

    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]

    assert "resist_berry_context" not in advice_move
    assert "chilan_berry_context" not in advice_move
    assert advice_payload["item_profiles"]["opponent_active"]["status"] == "unknown"
    assert advice_payload["item_profiles"]["opponent_active"]["item_id"] is None
    _assert_forbidden_terms_absent_from_advice_payload(
        advice_payload,
        extra_terms=("chilan-berry", "move_type_not_normal"),
    )
    prompt = _build_ui_selected_prompt(enriched)
    assert "Available item contexts are present in the advice payload" not in prompt
    assert "chilan-berry" not in prompt
    assert "chilan_berry_deferred" not in prompt
    assert "move_type_not_normal" not in prompt


def test_advice_payload_hides_unconfirmed_chilan_context_from_default_advice_payload() -> None:
    payload = _battle_input(selected_move=_tackle())
    payload["item_profiles"] = _item_profiles(opponent_item="chilan-berry")
    payload["item_profiles"]["opponent_active"]["status"] = "unknown"
    enriched = attach_selected_move_damage_estimate(payload)

    debug_move = enriched["moves"]["my_selected_move"]
    assert debug_move["chilan_berry_context"]["available"] is False
    assert debug_move["chilan_berry_context"]["reason"] == "item_not_user_confirmed"

    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]

    assert "chilan_berry_context" not in advice_move
    assert advice_payload["item_profiles"]["opponent_active"]["status"] == "unknown"
    assert advice_payload["item_profiles"]["opponent_active"]["item_id"] is None
    _assert_forbidden_terms_absent_from_advice_payload(
        advice_payload,
        extra_terms=("chilan-berry", "item_not_user_confirmed"),
    )
    assert "chilan-berry" not in _build_ui_selected_prompt(enriched)
    assert "item_not_user_confirmed" not in _build_ui_selected_prompt(enriched)


def test_advice_payload_hides_loaded_dice_blocked_context_and_item_profile() -> None:
    payload = _battle_input(selected_move=_bullet_seed())
    payload["item_profiles"] = _item_profiles(my_item="loaded-dice")
    enriched = attach_selected_move_damage_estimate(payload)

    debug_move = enriched["moves"]["my_selected_move"]
    assert debug_move["multi_hit_context"]["available"] is False
    assert debug_move["multi_hit_context"]["reason"] == "blocked_by_legal_item_coverage"
    assert enriched["item_profiles"]["my_active"]["item_id"] == "loaded-dice"

    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]

    assert "multi_hit_context" not in advice_move
    assert advice_payload["item_profiles"]["my_active"]["status"] == "unknown"
    assert advice_payload["item_profiles"]["my_active"]["item_id"] is None
    _assert_forbidden_terms_absent_from_advice_payload(
        advice_payload,
        extra_terms=("Loaded Dice", "loaded-dice"),
    )
    prompt = _build_ui_selected_prompt(enriched)
    assert '"loaded-dice"' not in prompt
    assert "blocked_by_legal_item_coverage" not in prompt


def test_advice_payload_hides_power_herb_non_legal_item_profile_without_charge_context() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(my_item="power-herb")
    enriched = attach_selected_move_damage_estimate(payload)

    assert enriched["item_profiles"]["my_active"]["item_id"] == "power-herb"
    assert "charge_context" not in enriched["moves"]["my_selected_move"]

    advice_payload = build_ui_advice_payload(enriched)

    assert advice_payload["item_profiles"]["my_active"]["status"] == "unknown"
    assert advice_payload["item_profiles"]["my_active"]["item_id"] is None
    assert "charge_context" not in advice_payload["moves"]["my_selected_move"]
    _assert_forbidden_terms_absent_from_advice_payload(
        advice_payload,
        extra_terms=("Power Herb", "power-herb"),
    )
    assert '"power-herb"' not in _build_ui_selected_prompt(enriched)


def test_advice_payload_preserves_available_yache_context_and_legal_contexts() -> None:
    payload = _battle_input(selected_move=_ice_beam())
    payload["item_profiles"] = _item_profiles(opponent_item="yache-berry")
    enriched = attach_selected_move_damage_estimate(payload)

    debug_move = enriched["moves"]["my_selected_move"]
    assert debug_move["resist_berry_context"]["available"] is True

    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]

    assert advice_move["resist_berry_context"]["available"] is True
    assert advice_move["resist_berry_context"]["item"] == debug_move["resist_berry_context"]["item"]
    assert advice_move["resist_berry_context"]["resist_effect"] == debug_move["resist_berry_context"]["resist_effect"]
    assert advice_payload["item_profiles"]["opponent_active"]["item_id"] == "yache-berry"
    assert advice_move["damage_estimate"]["damage_range"] == debug_move["damage_estimate"]["damage_range"]
    assert advice_move["damage_estimate"]["rolls"] == debug_move["damage_estimate"]["rolls"]
    assert advice_move["ko_context"]["ohko"] == debug_move["ko_context"]["ohko"]
    assert advice_move["ko_context"]["two_hko"] == debug_move["ko_context"]["two_hko"]


def test_advice_payload_preserves_available_focus_band_survival_context() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="focus-band")
    payload["pokemon"]["opponent_active"]["hp_percent"] = 50
    payload["pokemon"]["opponent_active"]["current_hp"] = 18
    payload["pokemon"]["opponent_active"]["max_hp"] = 35
    payload["stat_profiles"] = {
        "my_active": _default_stat_profile(),
        "opponent_active": _user_final_stats(hp=35),
    }
    enriched = attach_selected_move_damage_estimate(payload)

    debug_move = enriched["moves"]["my_selected_move"]
    assert debug_move["survival_context"]["available"] is True
    assert debug_move["survival_context"]["survival_effect"]["type"] == "focus_band"

    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]

    assert advice_move["survival_context"]["available"] is True
    assert advice_move["survival_context"]["item"]["item_id"] == "focus-band"
    assert advice_move["survival_context"]["survival_effect"]["type"] == "focus_band"
    assert advice_move["survival_context"]["survival_effect"]["survival_is_not_guaranteed"] is True
    assert advice_move["survival_context"]["survival_effect"]["activation_probability_calculated"] is False
    assert advice_move["survival_context"]["survival_effect"]["final_survival_probability_integrated"] is False
    assert advice_payload["item_profiles"]["opponent_active"]["item_id"] == "focus-band"
    assert advice_move["damage_estimate"]["damage_range"] == debug_move["damage_estimate"]["damage_range"]
    assert advice_move["damage_estimate"]["rolls"] == debug_move["damage_estimate"]["rolls"]
    assert advice_move["ko_context"]["ohko"] == debug_move["ko_context"]["ohko"]
    assert advice_move["ko_context"]["two_hko"] == debug_move["ko_context"]["two_hko"]


def test_advice_payload_hides_unavailable_focus_band_survival_context() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(opponent_item="focus-band")
    payload["stat_profiles"] = {
        "my_active": _default_stat_profile(),
        "opponent_active": _user_final_stats(hp=999),
    }
    enriched = attach_selected_move_damage_estimate(payload)

    debug_move = enriched["moves"]["my_selected_move"]
    assert debug_move["survival_context"]["available"] is False
    assert debug_move["survival_context"]["reason"] == "damage_not_lethal"

    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]

    assert "survival_context" not in advice_move
    assert advice_payload["item_profiles"]["opponent_active"]["status"] == "unknown"
    assert advice_payload["item_profiles"]["opponent_active"]["item_id"] is None
    assert advice_move["damage_estimate"]["damage_range"] == debug_move["damage_estimate"]["damage_range"]
    assert advice_move["damage_estimate"]["rolls"] == debug_move["damage_estimate"]["rolls"]
    assert advice_move["ko_context"]["ohko"] == debug_move["ko_context"]["ohko"]
    assert advice_move["ko_context"]["two_hko"] == debug_move["ko_context"]["two_hko"]
    _assert_forbidden_terms_absent_from_advice_payload(
        advice_payload,
        extra_terms=("Focus Band", "focus-band", "damage_not_lethal"),
    )


def test_type_boost_context_preserves_matching_charcoal_context_in_advice_payload() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = {
        "my_active": _type_boost_profile("charcoal", "Charcoal"),
        "opponent_active": _item_profiles()["opponent_active"],
    }
    enriched = attach_selected_move_damage_estimate(payload)

    debug_move = enriched["moves"]["my_selected_move"]
    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]

    assert debug_move["type_boost_context"]["available"] is True
    assert advice_move["type_boost_context"]["available"] is True
    assert advice_move["type_boost_context"]["item"]["item_id"] == "charcoal"
    assert advice_move["type_boost_context"]["type_boost_effect"]["boosted_type"] == "fire"
    assert advice_move["type_boost_context"]["type_boost_effect"]["move_type"] == "fire"
    assert advice_move["type_boost_context"]["type_boost_effect"]["damage_estimate_item_effect_status"] == "applied"
    assert advice_move["damage_estimate"]["damage_range"] == debug_move["damage_estimate"]["damage_range"]
    assert advice_move["damage_estimate"]["rolls"] == debug_move["damage_estimate"]["rolls"]
    assert advice_move["ko_context"]["ohko"] == debug_move["ko_context"]["ohko"]
    assert advice_move["ko_context"]["two_hko"] == debug_move["ko_context"]["two_hko"]


def test_type_boost_context_hides_mismatched_charcoal_context_from_advice_payload() -> None:
    payload = _battle_input(selected_move=_water_gun())
    payload["item_profiles"] = {
        "my_active": _type_boost_profile("charcoal", "Charcoal"),
        "opponent_active": _item_profiles()["opponent_active"],
    }
    enriched = attach_selected_move_damage_estimate(payload)

    debug_move = enriched["moves"]["my_selected_move"]
    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]

    assert debug_move["type_boost_context"]["available"] is False
    assert debug_move["type_boost_context"]["reason"] == "move_type_does_not_match_boosted_type"
    assert "type_boost_context" not in advice_move
    assert advice_move["damage_estimate"]["damage_range"] == debug_move["damage_estimate"]["damage_range"]
    assert advice_move["damage_estimate"]["rolls"] == debug_move["damage_estimate"]["rolls"]
    assert advice_move["ko_context"]["ohko"] == debug_move["ko_context"]["ohko"]
    assert advice_move["ko_context"]["two_hko"] == debug_move["ko_context"]["two_hko"]
    _assert_forbidden_terms_absent_from_advice_payload(
        advice_payload,
        extra_terms=("move_type_does_not_match_boosted_type",),
    )


def test_type_boost_context_preserves_mystic_water_and_magnet_matching_contexts() -> None:
    water_payload = _battle_input(selected_move=_water_gun())
    water_payload["item_profiles"] = {
        "my_active": _type_boost_profile("mystic-water", "Mystic Water"),
        "opponent_active": _item_profiles()["opponent_active"],
    }
    electric_payload = _battle_input(selected_move=_thunderbolt())
    electric_payload["item_profiles"] = {
        "my_active": _type_boost_profile("magnet", "Magnet"),
        "opponent_active": _item_profiles()["opponent_active"],
    }

    water_context = build_ui_advice_payload(attach_selected_move_damage_estimate(water_payload))["moves"][
        "my_selected_move"
    ]["type_boost_context"]
    electric_context = build_ui_advice_payload(attach_selected_move_damage_estimate(electric_payload))["moves"][
        "my_selected_move"
    ]["type_boost_context"]

    assert water_context["available"] is True
    assert water_context["item"]["item_id"] == "mystic-water"
    assert water_context["type_boost_effect"]["boosted_type"] == "water"
    assert electric_context["available"] is True
    assert electric_context["item"]["item_id"] == "magnet"
    assert electric_context["type_boost_effect"]["boosted_type"] == "electric"


def test_type_boost_context_hides_fairy_feather_and_non_legal_incense_from_advice_payload() -> None:
    fairy_payload = _battle_input(selected_move=_moonblast())
    fairy_payload["item_profiles"] = {
        "my_active": _type_boost_profile(
            "fairy-feather",
            "Fairy Feather",
            effect_support_status="legal_but_not_modeled",
            ui_status="recognized_not_modeled",
        ),
        "opponent_active": _item_profiles()["opponent_active"],
    }
    incense_payload = _battle_input(selected_move=_water_gun())
    incense_payload["item_profiles"] = {
        "my_active": _type_boost_profile(
            "wave-incense",
            "Wave Incense",
            legal=False,
            legality_status="unknown",
        ),
        "opponent_active": _item_profiles()["opponent_active"],
    }

    fairy_enriched = attach_selected_move_damage_estimate(fairy_payload)
    incense_enriched = attach_selected_move_damage_estimate(incense_payload)
    fairy_advice = build_ui_advice_payload(fairy_enriched)
    incense_advice = build_ui_advice_payload(incense_enriched)

    assert fairy_enriched["moves"]["my_selected_move"]["type_boost_context"]["available"] is False
    assert fairy_enriched["moves"]["my_selected_move"]["type_boost_context"]["reason"] == "type_boost_metadata_missing"
    assert incense_enriched["moves"]["my_selected_move"]["type_boost_context"]["available"] is False
    assert incense_enriched["moves"]["my_selected_move"]["type_boost_context"]["reason"] == "blocked_by_legal_item_coverage"
    assert "type_boost_context" not in fairy_advice["moves"]["my_selected_move"]
    assert "type_boost_context" not in incense_advice["moves"]["my_selected_move"]
    _assert_forbidden_terms_absent_from_advice_payload(
        fairy_advice,
        extra_terms=("Fairy Feather", "fairy-feather", "type_boost_metadata_missing"),
    )
    _assert_forbidden_terms_absent_from_advice_payload(
        incense_advice,
        extra_terms=("Wave Incense", "wave-incense", "blocked_by_legal_item_coverage"),
    )


def test_species_stat_item_context_preserves_pikachu_light_ball_context_in_advice_payload() -> None:
    payload = _battle_input(selected_move=_thunderbolt())
    payload["pokemon"]["my_active"] = _pikachu_payload()
    payload["item_profiles"] = {
        "my_active": _light_ball_profile(),
        "opponent_active": _item_profiles()["opponent_active"],
    }
    enriched = attach_selected_move_damage_estimate(payload)

    debug_move = enriched["moves"]["my_selected_move"]
    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]

    assert debug_move["species_stat_item_context"]["available"] is True
    assert advice_move["species_stat_item_context"]["available"] is True
    assert advice_move["species_stat_item_context"]["item"]["item_id"] == "light-ball"
    effect = advice_move["species_stat_item_context"]["species_stat_effect"]
    assert effect["holder_species_id"] == "pikachu"
    assert effect["supported_species"] == ["pikachu"]
    assert effect["boosted_stats"] == ["atk", "spa"]
    assert effect["effect_label"] == "may_boost_pikachu_offensive_stats"
    assert effect["raw_damage_rolls_changed"] is True
    assert effect["ko_context_changed"] is True
    assert effect["species_stat_adjusted_ko_integrated"] is True
    assert effect["species_stat_adjusted_ohko_2hko_integrated"] is True
    assert effect["damage_estimate_item_effect_status"] == "applied"
    assert debug_move["damage_estimate"]["item_effects"]["attacker_item"]["status"] == "applied"
    assert advice_move["damage_estimate"]["item_effects"]["attacker_item"]["status"] == "applied"
    assert advice_move["damage_estimate"]["assumptions"]["item"] == "supported_attacker_damage_item_applied"
    assert "no item" not in advice_move["damage_estimate"]["assumption_profile"]["label"].lower()
    assert advice_move["damage_estimate"]["damage_range"] == debug_move["damage_estimate"]["damage_range"]
    assert advice_move["damage_estimate"]["rolls"] == debug_move["damage_estimate"]["rolls"]
    assert advice_move["ko_context"]["ohko"] == debug_move["ko_context"]["ohko"]
    assert advice_move["ko_context"]["two_hko"] == debug_move["ko_context"]["two_hko"]
    assert (
        "Light Ball is a Pikachu-specific offensive item context."
        in advice_move["species_stat_item_context"]["limitations"]
    )
    assert (
        "Light Ball is applied for Pikachu in the damage estimate when damage_estimate.item_effects marks the supported modifier as applied."
        in advice_move["species_stat_item_context"]["limitations"]
    )
    assert (
        "This context is not final stat truth and not a final KO guarantee."
        in advice_move["species_stat_item_context"]["limitations"]
    )
    assert (
        "The existing ko_context uses the adjusted damage estimate rolls and remains limited damage-roll context only."
        in advice_move["species_stat_item_context"]["limitations"]
    )
    prompt = _build_ui_selected_prompt(enriched)
    assert "Available item contexts are present in the advice payload" in prompt
    assert "Light Ball / species_stat_item_context as Pikachu-specific offensive item context" in prompt
    assert "Mention each listed available item context at least once" in prompt
    assert "Do not describe these available item effects as unavailable, unmodeled, not included" in prompt
    assert "not reflected, no item is considered, assuming no item, without item effects" in prompt
    assert "default no-item assumption" in prompt
    assert "do not erase the available item context" in prompt
    assert "For Light Ball / species_stat_item_context specifically" in prompt
    assert "do not say or imply that no item effects are included for this move or recommendation" in prompt
    assert "Do not use generic no-item/default-assumption wording" in prompt
    assert "default assumptions plus the supported Light Ball modifier" in prompt
    assert "exact final stats" in prompt
    assert "final EV/IV/nature-adjusted stats" in prompt
    _assert_forbidden_terms_absent_from_advice_payload(
        advice_payload,
        extra_terms=(
            "guaranteed KO",
            "always doubles damage",
            "confirmed OHKO because of Light Ball",
            "all Electric-type Pokemon benefit",
            "Light Ball works on any holder",
            "final stats are fully known",
            "exact EV/IV/nature-adjusted stats are known",
        ),
    )


def test_species_stat_item_context_hides_non_pikachu_light_ball_from_advice_payload() -> None:
    payload = _battle_input(selected_move=_thunderbolt())
    payload["item_profiles"] = {
        "my_active": _light_ball_profile(),
        "opponent_active": _item_profiles()["opponent_active"],
    }
    enriched = attach_selected_move_damage_estimate(payload)

    debug_move = enriched["moves"]["my_selected_move"]
    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]

    assert debug_move["species_stat_item_context"]["available"] is False
    assert debug_move["species_stat_item_context"]["reason"] == "holder_species_not_supported"
    assert "species_stat_item_context" not in advice_move
    assert advice_payload["item_profiles"]["my_active"]["status"] == "unknown"
    assert advice_payload["item_profiles"]["my_active"]["item_id"] is None
    assert advice_move["damage_estimate"]["damage_range"] == debug_move["damage_estimate"]["damage_range"]
    assert advice_move["damage_estimate"]["rolls"] == debug_move["damage_estimate"]["rolls"]
    assert advice_move["ko_context"]["ohko"] == debug_move["ko_context"]["ohko"]
    assert advice_move["ko_context"]["two_hko"] == debug_move["ko_context"]["two_hko"]
    _assert_forbidden_terms_absent_from_advice_payload(
        advice_payload,
        extra_terms=("Light Ball", "light-ball", "holder_species_not_supported"),
    )
    assert "Available item contexts are present in the advice payload" not in _build_ui_selected_prompt(enriched)


def test_species_stat_item_context_hides_unconfirmed_light_ball_from_advice_payload() -> None:
    payload = _battle_input(selected_move=_thunderbolt())
    payload["pokemon"]["my_active"] = _pikachu_payload()
    payload["item_profiles"] = {
        "my_active": {
            **_light_ball_profile(),
            "status": "unknown",
            "source": "user_unconfirmed",
        },
        "opponent_active": _item_profiles()["opponent_active"],
    }
    enriched = attach_selected_move_damage_estimate(payload)

    debug_move = enriched["moves"]["my_selected_move"]
    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]

    assert debug_move["species_stat_item_context"]["available"] is False
    assert debug_move["species_stat_item_context"]["reason"] == "item_not_user_confirmed"
    assert "species_stat_item_context" not in advice_move
    assert advice_payload["item_profiles"]["my_active"]["status"] == "unknown"
    assert advice_payload["item_profiles"]["my_active"]["item_id"] is None
    _assert_forbidden_terms_absent_from_advice_payload(
        advice_payload,
        extra_terms=("Light Ball", "light-ball", "item_not_user_confirmed"),
    )
    assert "Available item contexts are present in the advice payload" not in _build_ui_selected_prompt(enriched)


def test_speed_order_context_preserves_available_quick_claw_context_in_advice_payload() -> None:
    baseline = attach_selected_move_damage_estimate(_battle_input(selected_move=_flamethrower()))
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = {
        "my_active": _quick_claw_profile(),
        "opponent_active": _item_profiles()["opponent_active"],
    }
    enriched = attach_selected_move_damage_estimate(payload)

    debug_move = enriched["moves"]["my_selected_move"]
    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]

    assert debug_move["speed_order_context"]["available"] is True
    assert advice_move["speed_order_context"]["available"] is True
    assert advice_move["speed_order_context"]["item"]["item_id"] == "quick-claw"
    assert advice_move["speed_order_context"]["speed_order_effect"]["type"] == "quick_claw"
    assert advice_move["speed_order_context"]["speed_order_effect"]["effect_label"] == "may_affect_move_order"
    assert advice_move["speed_order_context"]["speed_order_effect"]["activation_probability_calculated"] is False
    assert advice_move["speed_order_context"]["speed_order_effect"]["final_move_order_calculated"] is False
    assert advice_move["speed_order_context"]["speed_order_effect"]["speed_tie_resolved"] is False
    assert advice_move["speed_order_context"]["speed_order_effect"]["priority_integrated"] is False
    assert advice_move["speed_order_context"]["speed_order_effect"]["turn_engine_integrated"] is False
    assert advice_payload["item_profiles"]["my_active"]["item_id"] == "quick-claw"
    assert advice_move["damage_estimate"]["damage_range"] == baseline["moves"]["my_selected_move"]["damage_estimate"][
        "damage_range"
    ]
    assert advice_move["damage_estimate"]["rolls"] == baseline["moves"]["my_selected_move"]["damage_estimate"]["rolls"]
    assert advice_move["ko_context"]["ohko"] == baseline["moves"]["my_selected_move"]["ko_context"]["ohko"]
    assert advice_move["ko_context"]["two_hko"] == baseline["moves"]["my_selected_move"]["ko_context"]["two_hko"]
    _assert_forbidden_terms_absent_from_advice_payload(
        advice_payload,
        extra_terms=(
            "will move first",
            "guaranteed outspeeds",
            "confirmed first",
            "always acts before",
            "wins the speed interaction",
            "safe because it moves first",
        ),
    )


def test_speed_order_context_hides_unconfirmed_quick_claw_from_advice_payload() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = {
        "my_active": {
            **_quick_claw_profile(),
            "status": "unknown",
            "source": "user_unconfirmed",
        },
        "opponent_active": _item_profiles()["opponent_active"],
    }
    enriched = attach_selected_move_damage_estimate(payload)

    debug_move = enriched["moves"]["my_selected_move"]
    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]

    assert debug_move["speed_order_context"]["available"] is False
    assert debug_move["speed_order_context"]["reason"] == "item_not_user_confirmed"
    assert "speed_order_context" not in advice_move
    assert advice_payload["item_profiles"]["my_active"]["status"] == "unknown"
    assert advice_payload["item_profiles"]["my_active"]["item_id"] is None
    assert advice_move["damage_estimate"]["damage_range"] == debug_move["damage_estimate"]["damage_range"]
    assert advice_move["damage_estimate"]["rolls"] == debug_move["damage_estimate"]["rolls"]
    assert advice_move["ko_context"]["ohko"] == debug_move["ko_context"]["ohko"]
    assert advice_move["ko_context"]["two_hko"] == debug_move["ko_context"]["two_hko"]
    _assert_forbidden_terms_absent_from_advice_payload(
        advice_payload,
        extra_terms=("Quick Claw", "quick-claw", "item_not_user_confirmed"),
    )


def test_speed_order_context_hides_non_quick_claw_item_from_advice_payload() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(my_item="power-herb")
    enriched = attach_selected_move_damage_estimate(payload)

    debug_move = enriched["moves"]["my_selected_move"]
    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]

    assert debug_move["speed_order_context"]["available"] is False
    assert debug_move["speed_order_context"]["reason"] == "unsupported_speed_order_item"
    assert "speed_order_context" not in advice_move
    assert advice_payload["item_profiles"]["my_active"]["status"] == "unknown"
    assert advice_payload["item_profiles"]["my_active"]["item_id"] is None
    _assert_forbidden_terms_absent_from_advice_payload(
        advice_payload,
        extra_terms=("Power Herb", "power-herb", "unsupported_speed_order_item"),
    )


def test_speed_order_context_does_not_hide_available_choice_scarf_speed_context() -> None:
    item_options = legal_item_options_from_repository(ChampionsItemRepository())
    my_panel = _panel(
        "charizard",
        selected_move_index=0,
        selected_moves=[_move("flamethrower")],
        final_stats=_final_stats(spe=100),
        item_profile=item_profile_from_option("choice-scarf", item_options=item_options),
    )
    opponent_panel = _panel(
        "garchomp",
        selected_move_index=None,
        selected_moves=[],
        final_stats=_final_stats(spe=120),
    )
    payload = _window(my_panel, opponent_panel)._build_llm_battle_input()
    enriched = attach_selected_move_damage_estimate(payload)
    advice_payload = build_ui_advice_payload(enriched)

    assert enriched["moves"]["my_selected_move"]["speed_order_context"]["available"] is False
    assert enriched["moves"]["my_selected_move"]["speed_order_context"]["reason"] == "unsupported_speed_order_item"
    assert advice_payload["item_profiles"]["my_active"]["item_id"] == "choice-scarf"
    assert advice_payload["speed_context"]["my_active"]["speed_modifiers"][0]["item_id"] == "choice-scarf"
    assert advice_payload["speed_context"]["my_active"]["effective_speed"] == 150
    assert "speed_order_context" not in advice_payload["moves"]["my_selected_move"]


def test_advice_context_registry_lists_current_context_surfaces() -> None:
    assert ADVICE_CONTEXT_KEYS == {
        "survival_context",
        "recovery_context",
        "accuracy_context",
        "critical_context",
        "flinch_context",
        "multi_hit_context",
        "resist_berry_context",
        "chilan_berry_context",
        "type_boost_context",
        "species_stat_item_context",
        "speed_context",
        "speed_order_context",
        "charge_context",
    }
    assert ADVICE_ITEM_CONTEXT_KEYS == ADVICE_CONTEXT_KEYS - {"speed_context"}
    assert ADVICE_CONTEXTS_REQUIRING_MOVE_LOCAL_ITEM_EFFECT_SCRUB == {
        "type_boost_context",
        "species_stat_item_context",
    }
    assert "blocked" in DEBUG_ONLY_REASON_PHRASES
    assert "deferred" in DEBUG_ONLY_REASON_PHRASES
    assert "not modeled" in DEBUG_ONLY_REASON_PHRASES


def test_advice_context_registry_hides_all_unavailable_item_context_keys() -> None:
    payload = _registry_payload_with_contexts(available=False)
    enriched = deepcopy(payload)

    advice_payload = build_ui_advice_payload(enriched)
    advice_move = advice_payload["moves"]["my_selected_move"]
    rendered = json.dumps(advice_payload, ensure_ascii=False)

    for context_key in ADVICE_ITEM_CONTEXT_KEYS:
        assert context_key not in advice_move
        assert payload["moves"]["my_selected_move"][context_key]["reason"] == f"{context_key}_debug_reason"
        assert enriched["moves"]["my_selected_move"][context_key]["reason"] == f"{context_key}_debug_reason"
        assert f"{context_key}_debug_reason" not in rendered
    assert advice_move["damage_estimate"]["damage_range"] == payload["moves"]["my_selected_move"]["damage_estimate"][
        "damage_range"
    ]
    assert advice_move["damage_estimate"]["rolls"] == payload["moves"]["my_selected_move"]["damage_estimate"]["rolls"]
    assert advice_move["ko_context"] == payload["moves"]["my_selected_move"]["ko_context"]


def test_advice_context_registry_keeps_all_available_item_context_keys() -> None:
    payload = _registry_payload_with_contexts(available=True)

    advice_payload = build_ui_advice_payload(payload)
    advice_move = advice_payload["moves"]["my_selected_move"]

    for context_key in ADVICE_ITEM_CONTEXT_KEYS:
        assert advice_move[context_key]["available"] is True
        assert advice_move[context_key]["item"]["item_id"] == "charcoal"
    assert advice_move["damage_estimate"]["damage_range"] == payload["moves"]["my_selected_move"]["damage_estimate"][
        "damage_range"
    ]
    assert advice_move["damage_estimate"]["rolls"] == payload["moves"]["my_selected_move"]["damage_estimate"]["rolls"]
    assert advice_move["ko_context"] == payload["moves"]["my_selected_move"]["ko_context"]


def _assert_forbidden_terms_absent_from_advice_payload(
    advice_payload: dict,
    *,
    extra_terms: tuple[str, ...] = (),
) -> None:
    rendered = json.dumps(advice_payload, ensure_ascii=False)
    for term in (*UNAVAILABLE_ITEM_ADVICE_PAYLOAD_FORBIDDEN_TERMS, *extra_terms):
        assert term.lower() not in rendered.lower()


def _registry_payload_with_contexts(*, available: bool) -> dict:
    move = {
        "move_id": "registry-test-move",
        "damage_estimate": {
            "damage_range": {"min": 10, "max": 12},
            "rolls": [10, 11, 12],
            "item_effects": {
                "attacker_item": {
                    "item_id": "charcoal",
                    "status": "not_applicable",
                }
            },
        },
        "ko_context": {
            "mode": "limited_damage_roll_ko_context",
            "ohko": {"chance": 0.0},
            "two_hko": {"possible": False},
        },
    }
    for context_key in ADVICE_ITEM_CONTEXT_KEYS:
        move[context_key] = {
            "available": available,
            "reason": f"{context_key}_debug_reason",
            "attacker_side": "my_active",
            "item": {
                "item_id": "charcoal",
                "status": "user_confirmed",
            },
        }
    return {
        "item_profiles": {
            "my_active": {
                "status": "user_confirmed",
                "source": "user_input",
                "item_id": "charcoal",
                "name_en": "Charcoal",
                "name_ko": None,
                "effects_scope": [],
                "damage_modifier_status": "not_applicable",
            }
        },
        "moves": {
            "my_selected_move": move,
        },
    }


def _type_boost_profile(
    item_id: str,
    name_en: str,
    *,
    legal: bool = True,
    legality_status: str = "legal",
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
        "legal": legal,
        "legality_status": legality_status,
        "effect_support_status": effect_support_status,
        "damage_modifier_status": "not_applied",
        "ui_status": ui_status,
        "notes": [],
    }


def _quick_claw_profile() -> dict:
    return {
        "status": "user_confirmed",
        "source": "user_input",
        "item_id": "quick-claw",
        "name_en": "Quick Claw",
        "name_ko": None,
        "effects_scope": ["speed_order"],
        "category": "hold_item",
        "legal": True,
        "legality_status": "legal",
        "effect_support_status": "legal_but_not_modeled",
        "damage_modifier_status": "not_applicable",
        "ui_status": "recognized_not_modeled",
        "notes": ["Speed/order effects are not modeled."],
    }


def _light_ball_profile() -> dict:
    return {
        "status": "user_confirmed",
        "source": "user_input",
        "item_id": "light-ball",
        "name_en": "Light Ball",
        "name_ko": None,
        "effects_scope": ["species_stat"],
        "category": "hold_item",
        "legal": True,
        "legality_status": "legal",
        "effect_support_status": "legal_but_not_modeled",
        "damage_modifier_status": "not_applied",
        "ui_status": "recognized_not_modeled",
        "notes": [],
    }


def _pikachu_payload() -> dict:
    return {
        "slot_index": 0,
        "name_en": "pikachu",
        "name_ko": "Pikachu",
        "types": ["electric"],
        "types_ko": ["Electric"],
        "base_stats": {
            "hp": 35,
            "attack": 55,
            "defense": 40,
            "special-attack": 50,
            "special-defense": 50,
            "speed": 90,
        },
        "abilities": ["static", "lightning-rod"],
        "abilities_ko": ["Static", "Lightning Rod"],
        "hp_percent": 100,
        "selected_move_index": 0,
    }


def _water_gun() -> dict:
    return {
        "slot": 0,
        "move_id": "water-gun",
        "name_en": "Water Gun",
        "name_ko": "Water Gun",
        "type": "water",
        "category": "special",
        "power": 40,
        "accuracy": 100,
        "pp": 25,
    }


def _thunderbolt() -> dict:
    return {
        "slot": 0,
        "move_id": "thunderbolt",
        "name_en": "Thunderbolt",
        "name_ko": "Thunderbolt",
        "type": "electric",
        "category": "special",
        "power": 90,
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
        "When available=true item contexts are present in the default advice payload, the prompt must require the LLM to mention each listed available item context at least once when directly relevant."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When available=true item contexts are present, do not describe those available item effects as unavailable, unmodeled, not included, not reflected, no item is considered, assuming no item, without item effects, or default no-item assumption."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Available item context wording must remain limited and must not become final KO odds, guaranteed survival, guaranteed move order, exact final stats, or final battle truth."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Type-boost item context may appear only as limited type_boost_context." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "type_boost_context applies only to user-confirmed, Champions legal, damage-supported type-boosting items when move type matches boosted type."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "type_boost_context does not change raw damage_range or rolls beyond the existing damage_estimate.item_effects calculation."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "ko_context is unchanged by type_boost_context." in ADVISOR_KNOWN_LIMITATIONS
    assert "Type-boost-adjusted KO/OHKO/2HKO context is not calculated." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "If type_boost_context is unavailable, treat the reason as developer/debug/contract metadata only."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not say boosted damage guarantees KO, secures the KO, proves the KO, or is final battle damage."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Light Ball species-stat item context may appear only as limited species_stat_item_context." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "species_stat_item_context applies only to user-confirmed, Champions legal Light Ball on Pikachu when local species-stat metadata exists."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "species_stat_item_context is a sibling explanation of an applied Light Ball modifier in damage_estimate.item_effects."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Eligible Pikachu Light Ball damage estimates use default stat assumptions plus the supported Light Ball species-stat modifier."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Eligible Pikachu Light Ball raw damage rolls and ko_context are based on the adjusted damage estimate rolls."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "species_stat_item_context does not infer exact EV/IV/nature-adjusted final stats and does not create final KO truth."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When species_stat_item_context is available, say Light Ball is a Pikachu-specific offensive item context applied in the damage estimate when damage_estimate.item_effects marks the supported modifier as applied."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not say Light Ball is not included or Light Ball is not modeled when species_stat_item_context is available."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When species_stat_item_context is available, do not use generic no-item/default-assumption wording such as no item effects, without item effects, assuming no item, default no-item assumption, item not included, item not modeled, or item not reflected."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When species_stat_item_context is available and item_effects marks the supported modifier as applied, describe the damage estimate as default assumptions plus the supported Light Ball modifier."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When species_stat_item_context is available, say the context is not final stat truth and not a final KO guarantee."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "If an item damage modifier is applied, describe the estimate as default assumptions plus the supported item modifier, not only default assumptions."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "If Life Orb is applied, say Life Orb recoil is not modeled." in ADVISOR_KNOWN_LIMITATIONS
    assert "If Choice Scarf, Choice Band, or Choice Specs is applied, say choice lock is not modeled." in ADVISOR_KNOWN_LIMITATIONS
    assert "Life Orb recoil is not connected." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "Sitrus Berry and Leftovers recovery may appear only as limited recovery_context."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "recovery_context does not change raw damage_range or rolls." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "ko_context is unchanged by recovery_context and KO/OHKO/2HKO estimates do not include recovery."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "recovery_context applies only when Sitrus Berry or Leftovers is user-confirmed and defender max HP is available."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Sitrus Berry recovery_context is threshold recovery limited context; exact activation timing and item consumption are not tracked."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Leftovers recovery_context is end-of-turn limited context; exact turn sequencing is not modeled."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When recovery_context is available, keep recovery wording concise and say exact activation timing, item consumption, and turn sequencing are not modeled."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Say recovery may affect follow-up KO/2HKO only under limited assumptions." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "Do not claim final 2HKO or 3HKO truth from recovery_context without Turn Engine."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not infer Sitrus Berry or Leftovers recovery if the item is unknown or unconfirmed."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not say Sitrus Berry definitely activates, KO chance includes recovery, or recovery changes the damage range."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Bright Powder accuracy may appear only as limited accuracy_context." in ADVISOR_KNOWN_LIMITATIONS
    assert "accuracy_context does not change raw damage_range or rolls." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "ko_context is unchanged by accuracy_context and KO/OHKO/2HKO estimates do not include hit chance."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "accuracy_context applies only when Bright Powder is user-confirmed and move accuracy metadata is available."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Bright Powder may reduce hit reliability, but it is not damage reduction."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When accuracy_context is available, keep accuracy wording concise and mention that raw damage and KO/OHKO/2HKO estimates do not include hit chance."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When accuracy_context is available, include one concise limitation sentence that final hit probability, accuracy/evasion stages, ability/weather interactions, multi-hit accuracy, and turn sequencing are not modeled."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Hit-adjusted KO probability is not calculated in accuracy_context." in ADVISOR_KNOWN_LIMITATIONS
    assert "Final hit probability is not calculated in accuracy_context." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "Do not claim the move will miss or that a miss is guaranteed from accuracy_context."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not say the hit-adjusted KO chance is a percent unless an explicit future field calculates it."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not infer Bright Powder accuracy effects if the item is unknown or unconfirmed."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Accuracy/evasion stages, ability interactions, weather, multi-hit accuracy, and turn sequencing are not modeled for accuracy_context."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Scope Lens critical-hit context may appear only as limited critical_context." in ADVISOR_KNOWN_LIMITATIONS
    assert "critical_context does not change raw damage_range or rolls." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "ko_context is unchanged by critical_context and KO/OHKO/2HKO estimates do not include crit chance."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "critical_context applies only when Scope Lens is user-confirmed." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "Scope Lens may increase critical-hit likelihood, but it is not a direct damage boost."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When critical_context is available, keep critical-hit wording concise and mention that raw damage and KO/OHKO/2HKO estimates do not include crit chance."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Final critical-hit probability is not calculated in critical_context." in ADVISOR_KNOWN_LIMITATIONS
    assert "Crit-adjusted KO probability is not calculated in critical_context." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "Do not claim the move will crit or that a critical hit is guaranteed from critical_context."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not infer Scope Lens critical-hit effects if the item is unknown or unconfirmed."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Critical-hit stages, abilities, move-specific crit effects, and turn sequencing are not modeled for critical_context."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "King's Rock flinch context may appear only as limited flinch_context." in ADVISOR_KNOWN_LIMITATIONS
    assert "flinch_context does not change raw damage_range or rolls." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "ko_context is unchanged by flinch_context and KO/OHKO/2HKO estimates do not include flinch chance."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "flinch_context applies only when King's Rock is user-confirmed." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "King's Rock may add flinch pressure, but it is not a direct damage boost."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When flinch_context is available, say the raw damage estimate is unchanged and raw ko_context is unchanged."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When flinch_context is available, avoid wording like damage modifier is not included; prefer raw damage estimate is unchanged."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When flinch_context is available, keep flinch wording concise and mention that raw damage and KO/OHKO/2HKO estimates do not include flinch chance."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When flinch_context is available, include one concise limitation sentence that speed order, target action state, abilities, multi-hit handling, and turn sequencing are not modeled."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Final flinch probability is not calculated in flinch_context." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "Flinch-adjusted turn or outcome probability is not calculated in flinch_context."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not claim the target will flinch, cannot move, or that flinch is guaranteed from flinch_context."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not infer King's Rock flinch effects if the item is unknown or unconfirmed."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Speed order, target action state, abilities, multi-hit handling, and turn sequencing are not modeled for flinch_context."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Loaded Dice multi-hit context is blocked/future-only until Loaded Dice legal coverage is confirmed."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "multi_hit_context does not change raw damage_range or rolls." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "ko_context is unchanged by multi_hit_context and KO/OHKO/2HKO estimates do not include multi-hit count changes."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "multi_hit_context applies only when Loaded Dice is user-confirmed, legal coverage is confirmed, and move multi-hit metadata is available."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Loaded Dice may improve multi-hit reliability for eligible moves, but it is not a direct damage boost."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When multi_hit_context is available, keep multi-hit wording concise and mention that raw damage and KO/OHKO/2HKO estimates do not include multi-hit count changes."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Final hit count probability is not calculated in multi_hit_context." in ADVISOR_KNOWN_LIMITATIONS
    assert "Multi-hit-adjusted KO probability is not calculated in multi_hit_context." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "Do not claim a specific number of hits will occur or that 5 hits are guaranteed from multi_hit_context."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not claim Loaded Dice breaks Focus Sash unless that interaction is explicitly modeled."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not infer Loaded Dice multi-hit effects if the item is unknown or unconfirmed."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Focus Sash, King's Rock, accuracy, crit per-hit handling, and turn sequencing are not modeled for multi_hit_context."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Type-resist berry context may appear only as limited resist_berry_context." in ADVISOR_KNOWN_LIMITATIONS
    assert "resist_berry_context does not change raw damage_range or rolls." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "ko_context is unchanged by resist_berry_context and KO/OHKO/2HKO estimates do not include berry reduction."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When resist_berry_context is available, explicitly say the raw damage estimate is unchanged and raw ko_context is unchanged."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "resist_berry_context applies only when a standard type-resist berry is user-confirmed, legal coverage is confirmed, incoming move type is known, and the move is super-effective."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Resist berry edge cases require explicit support before advice can use them."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "A type-resist berry may reduce a qualifying super-effective hit, but berry-adjusted damage is not calculated."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Berry-adjusted KO probability is not calculated in resist_berry_context." in ADVISOR_KNOWN_LIMITATIONS
    assert "Item consumption is not tracked in resist_berry_context." in ADVISOR_KNOWN_LIMITATIONS
    assert "Do not say the Pokemon definitely survives from resist_berry_context." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "Do not infer resist berry effects if the item is unknown or unconfirmed."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "If resist_berry_context is unavailable, treat the unavailable reason as developer/debug/contract metadata only."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not mention unavailable resist berry names, berry effects, or unavailable reasons in default advice."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not say Yache Berry effect is not applied, the berry effect is not included, or the berry is not modeled in default advice unless the user explicitly asks about that berry."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Ability, weather, Tera, multi-hit handling, item consumption, and turn sequencing are not modeled for resist_berry_context."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Chilan Berry context may appear only as limited chilan_berry_context." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "chilan_berry_context applies only when Chilan Berry is user-confirmed, legal coverage is confirmed, local metadata marks always_resist true for Normal, incoming move type is Normal, and the move is damaging."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "chilan_berry_context does not change raw damage_range or rolls." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "ko_context is unchanged by chilan_berry_context and KO/OHKO/2HKO estimates do not include Chilan Berry reduction."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Chilan-adjusted damage and Chilan-adjusted KO probability are not calculated in chilan_berry_context."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Item consumption is not tracked in chilan_berry_context." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "When chilan_berry_context is available, say Chilan Berry is a Normal-type limited context and may reduce damage from a Normal-type damaging move."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When chilan_berry_context is available, say raw damage rolls and ko_context remain based on the current calculator and the context is not integrated into final KO odds."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not say Chilan Berry is not included or Chilan Berry is not modeled when chilan_berry_context is available."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not say guaranteed survival, confirmed live, will survive because of Chilan Berry, KO chance is reduced to a value, final damage is halved, raw damage rolls already include Chilan Berry, or Chilan Berry applies to all move types."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "If chilan_berry_context is unavailable, treat the unavailable reason as developer/debug/contract metadata only."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not mention unavailable Chilan Berry names, effects, or unavailable reasons in default advice."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "User-facing modeled item contexts require Champions legal item coverage from data/static/champions_legal_items.json."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "items.json and items_damage.json are item/effect metadata, not Champions legal coverage sources."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "If a user-confirmed item is absent from the Champions legal item fixture, do not emit modeled item context; use blocked_by_legal_item_coverage."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Blocked or future-only item reasons are developer/debug/contract metadata, not normal user-facing advice content."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not include blocked or future-only item effects in user-facing recommendation text unless the user explicitly asks about that item."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "In default advice, do not mention blocked item names, do not say user-confirmed Loaded Dice, and do not say Power Herb when those items are blocked by legal coverage."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not say Loaded Dice is not modeled or Power Herb is not modeled by default when those items are blocked by legal coverage."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not say a blocked item effect is not included by default; keep blocked item explanations out of normal advice."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not use generic blocked item substitutes such as the user-confirmed item effect, held item effect, selected item effect, or item-based limitation in default advice."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not mention that a blocked item exists by saying its effect is absent, ignored, unavailable, excluded, unsupported, or outside the estimate."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "If the user explicitly asks about a blocked item, explain only that Champions legal coverage is not confirmed, so the item effect is not reflected in advice."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Do not imply blocked or future-only items are available in Champions." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "For unavailable, deferred, blocked, unconfirmed, non-triggered, or absent item contexts, treat the reason as developer/debug/contract metadata by default."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not say item effect is not included, opponent's item effect is not included, or user-confirmed item effect is not included for unavailable item contexts in default advice."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not say item is not modeled, item effect is not applied, not included in this estimate, or not reflected in the calculation for unavailable item contexts in default advice."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not mention unavailable or deferred item names or effects unless the user explicitly asks about that item."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Loaded Dice multi-hit context is blocked/future-only until Loaded Dice legal coverage is confirmed."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Power Herb remains blocked; charge_moves.json is move metadata and does not establish Power Herb legality."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Focus Sash and Focus Band survival may appear only as limited survival_context, not as damage reduction."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "survival_context does not change raw damage_range or rolls." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "ko_context is unchanged by survival_context and KO/OHKO/2HKO estimates do not include Focus Band activation."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Focus Sash survival_context applies only when Focus Sash is user-confirmed and HP is full."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When Focus Sash survival_context is available, say may survive at 1 HP; do not say will survive, definitely survives, or guarantees survival."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Focus Band survival_context applies only when Focus Band is user-confirmed, Champions legal, and raw incoming damage is potentially lethal."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When Focus Band survival_context is available, say may occasionally survive and survival is not guaranteed."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not say Focus Band will survive, guaranteed survive, cannot be KO'd, confirmed survival, safe to take the hit, or survives this hit."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Focus Band activation probability and final survival probability are not calculated."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "When survival_context is available, include one concise limitation sentence that multi-hit moves, hazards, chip damage, item consumption, activation probability, and exact turn sequencing are not modeled."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Multi-hit moves, hazards, residual damage, weather/status chip, ability interactions, and exact turn sequencing are not modeled for survival_context."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Do not infer Focus Sash or Focus Band if the item is unknown or unconfirmed." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "ko_context, when present, is limited damage-roll context only and is not final battle truth."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "ko_context does not change raw damage_range or rolls." in ADVISOR_KNOWN_LIMITATIONS
    assert "OHKO chance in ko_context is based on damage rolls only." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "2HKO context uses limited min/max assumptions and is not final turn simulation."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "ko_context does not model accuracy, speed order, priority, recovery, hazards, chip damage, switching, protection, or turn sequencing."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "survival_context is separate from raw ko_context and is not included in KO probability."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not mention choice lock for non-Choice items such as Charcoal, Mystic Water, Black Belt, Metal Coat, Sharp Beak, Fairy Feather, Leftovers, Focus Sash, or Focus Band."
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
    assert "Quick Claw speed-order context may appear only as limited speed_order_context." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "speed_order_context applies only when Quick Claw is user-confirmed and Champions legal."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "speed_order_context may say Quick Claw may affect move order, but final move order is not calculated."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "Quick Claw activation probability is not calculated in speed_order_context." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "speed_order_context does not calculate speed ties, priority, Trick Room, Tailwind, paralysis, boosts, abilities, weather, item consumption, or turn sequencing."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Do not say will move first, guaranteed outspeeds, confirmed first, always acts before, wins the speed interaction, or safe because it moves first from speed_order_context."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "If speed_order_context is unavailable, treat the reason as developer/debug/contract metadata only."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Choice Scarf is not modeled through speed_order_context; keep Choice Scarf in speed_context."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "opponent_assumptions, when present, contains possible opponent profiles, not confirmed sets."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "opponent_assumptions mode is a historical behavior label; schema_version and metadata_version describe the current payload shape."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "Opponent assumptions version fields are developer/contract metadata and should not be mentioned in user-facing battle advice."
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
