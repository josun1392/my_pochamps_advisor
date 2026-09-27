from __future__ import annotations

import inspect
from copy import deepcopy

from core.cache_manager import CacheManager
from core.ko_mapping_loader import KoMappingLoader
from core.move_repository import MoveRepository
from core.pokemon_repository import PokemonRepository
from llm.advisor_candidate_contract import prepare_ui_recommendation_cycle
from llm.advisor_champions_rules import (
    CHAMPIONS_BATTLE_LEVEL,
    CHAMPIONS_RULES_CONTEXT,
    build_champions_trusted_level_context,
)
from llm.advisor_recommendation_readiness import build_recommendation_readiness
from llm.advisor_turn_snapshot import BASE_STAT_KEYS, build_request_start_recommendation_snapshot, build_snapshot_trusted_level_provenance
from ui.main_window import MainWindow


class _Species:
    def get(self, name):
        return {
            "en": name,
            "types_en": ["normal"],
            "base_stats": {key: 80 for key in BASE_STAT_KEYS},
        }


def _provenance(side: str, slot: int, pokemon: str) -> dict:
    return {
        "side": side,
        "slot_index": slot,
        "pokemon_id": pokemon,
        "session_id": "s",
        "source": "user_confirmed_final_battle_stat",
        "trust": "user_confirmed_current",
    }


def _battle() -> dict:
    pokemon = {
        "my_active": {"name_en": "pikachu", "slot_index": 0},
        "opponent_active": {"name_en": "eevee", "slot_index": 1},
    }
    levels = build_champions_trusted_level_context(
        rules_context=CHAMPIONS_RULES_CONTEXT,
        session_id="s",
        pokemon=pokemon,
    )
    assert levels is not None
    stats = []
    for side, slot, name, speed in (
        ("self", 0, "pikachu", 120),
        ("opponent", 1, "eevee", 100),
    ):
        for index, stat in enumerate(BASE_STAT_KEYS):
            stats.append({
                "side": side,
                "stat": stat,
                "value": speed if stat == "speed" else 100 + index,
                "status": "user_confirmed",
                "source": "user_confirmed_final_battle_stat",
                "confidence": "known",
                "provenance": _provenance(side, slot, name),
            })
    absent = {"status": "known_absent"}
    boosts = {key: 0 for key in BASE_STAT_KEYS if key != "hp"}
    direct_side = {
        "ability": deepcopy(absent),
        "item": deepcopy(absent),
        "boosts": deepcopy(boosts),
        "current_hp": 100,
        "max_hp": 100,
        "status": deepcopy(absent),
    }
    return {
        "current_state_session_id": "s",
        "pokemon": pokemon,
        "item_profiles": {
            "my_active": {"status": "none", "source": "user_input", "item_id": None},
            "opponent_active": {"status": "none", "source": "user_input", "item_id": None},
        },
        "moves": {
            "my_available_moves": [{"slot_index": 0, "move_id": "tackle"}],
            "my_selected_move": {"slot_index": 0, "move_id": "tackle"},
            "opponent_selected_move": {"slot_index": 0, "move_id": "tackle"},
        },
        "final_stat_context": {"current_final_stats": stats},
        "condition_context": {
            "current_conditions": [
                {"side": "self", "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"},
                {"side": "opponent", "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"},
            ]
        },
        "field_state_context": {
            "current_field": {
                "weather": "none",
                "terrain": "none",
                "global_effects": [],
                "side_effects": [],
                "status": "user_confirmed",
                "source": "user_confirmed_current_field_state",
            }
        },
        "trusted_level_context": levels,
        "direct_mechanics_context": {
            "generation": "gen9",
            "attacker": deepcopy(direct_side),
            "defender": deepcopy(direct_side),
            "field": {"weather": deepcopy(absent), "terrain": deepcopy(absent)},
        },
    }


def test_champions_level_authority_is_exact_rules_metadata_and_identity_bound():
    pokemon = {
        "my_active": {"name_en": "garchomp", "slot_index": 2},
        "opponent_active": {"name_en": "tyranitar", "slot_index": 5},
    }
    result = build_champions_trusted_level_context(
        rules_context=CHAMPIONS_RULES_CONTEXT,
        session_id="battle-1",
        pokemon=pokemon,
    )
    assert result is not None
    assert [row["value"] for row in result["current_levels"]] == [CHAMPIONS_BATTLE_LEVEL, CHAMPIONS_BATTLE_LEVEL]
    assert CHAMPIONS_BATTLE_LEVEL == 50
    for row in result["current_levels"]:
        assert row["provenance"]["source"] == "deterministic_rules_metadata"
        assert row["provenance"]["trust"] == "deterministic_rules_metadata"
        assert row["provenance"]["session_id"] == "battle-1"


def test_champions_level_authority_fails_closed_outside_exact_rules_scope_and_bad_binding():
    pokemon = {
        "my_active": {"name_en": "pikachu", "slot_index": 0},
        "opponent_active": {"name_en": "eevee", "slot_index": 1},
    }
    assert build_champions_trusted_level_context(
        rules_context="custom-battle", session_id="s", pokemon=pokemon
    ) is None
    wrong = deepcopy(pokemon)
    wrong["my_active"]["slot_index"] = True
    assert build_champions_trusted_level_context(
        rules_context=CHAMPIONS_RULES_CONTEXT, session_id="s", pokemon=wrong
    ) is None
    stale = build_champions_trusted_level_context(
        rules_context=CHAMPIONS_RULES_CONTEXT, session_id="old", pokemon=pokemon
    )
    battle = _battle()
    battle["trusted_level_context"] = stale
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("tackle",))
    assert build_snapshot_trusted_level_provenance(snapshot)["available"] is False


def test_existing_trusted_level_boundary_rejects_default_malformed_and_wrong_identity_metadata():
    for mutation in ("default", "malformed", "wrong_identity", "wrong_slot"):
        battle = _battle()
        row = battle["trusted_level_context"]["current_levels"][0]
        if mutation == "default":
            row["provenance"]["source"] = "default_assumption"
            row["provenance"]["trust"] = "default_assumption"
        elif mutation == "malformed":
            row["value"] = "50"
        elif mutation == "wrong_identity":
            row["provenance"]["pokemon_id"] = "raichu"
        else:
            row["provenance"]["slot_index"] = 3
        snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("tackle",))
        assert build_snapshot_trusted_level_provenance(snapshot)["available"] is False


def test_champions_rules_authority_is_detached_and_does_not_mutate_input():
    pokemon = {
        "my_active": {"name_en": "pikachu", "slot_index": 0},
        "opponent_active": {"name_en": "eevee", "slot_index": 1},
    }
    before = deepcopy(pokemon)
    result = build_champions_trusted_level_context(
        rules_context=CHAMPIONS_RULES_CONTEXT, session_id="s", pokemon=pokemon
    )
    assert pokemon == before
    assert result is not None
    result["current_levels"][0]["provenance"]["pokemon_id"] = "mutated"
    assert pokemon == before


def test_first_supported_ordinary_case_reaches_known_mechanics_rankable_and_ready():
    battle = _battle()
    move_repo = {
        "tackle": {
            "move_id": "tackle",
            "category": "physical",
            "power": 40,
            "type": "normal",
            "accuracy": 100,
            "priority": 0,
            "target": "selected-pokemon",
        }
    }
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}],
        battle_input=battle,
        move_repository=move_repo,
        species_repository=_Species(),
    )
    candidate = prepared["candidates"][0]
    assert prepared["status"] == "ready"
    assert candidate["mechanics_result"]["status"] == "known"
    assert candidate["mechanics_result"]["missing_inputs"] == []
    assert prepared["recommendation_request"]["candidate_comparisons"][0]["mechanics_comparison"]["comparison_status"] == "rankable"
    readiness = build_recommendation_readiness(prepared_cycle=prepared)
    assert readiness["status"] == "ready", readiness

    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("tackle",))
    level = build_snapshot_trusted_level_provenance(snapshot)
    assert level["available"] is True
    assert level["value"] == 50
    assert level["source"] == level["trust"] == "deterministic_rules_metadata"


def test_first_supported_ordinary_case_is_ready_without_hidden_exact_opponent_command():
    battle = _battle()
    battle["moves"].pop("opponent_selected_move")
    move_repo = {
        "tackle": {
            "move_id": "tackle",
            "category": "physical",
            "power": 40,
            "type": "normal",
            "accuracy": 100,
            "priority": 0,
            "target": "selected-pokemon",
        }
    }

    prepared = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}],
        battle_input=battle,
        move_repository=move_repo,
        species_repository=_Species(),
    )

    candidate = prepared["candidates"][0]
    assert prepared["status"] == "ready"
    assert candidate["mechanics_result"]["status"] == "known"
    assert candidate["mechanics_result"]["missing_inputs"] == []
    assert candidate["action_order"]["status"] == "insufficient_context"
    assert candidate["action_order"]["missing_inputs"] == ["opponent_action"]
    move_success = candidate.get("move_success")
    assert not (
        isinstance(move_success, dict)
        and move_success.get("status") in {"insufficient_context", "unsupported_mechanic"}
    )

    readiness = build_recommendation_readiness(prepared_cycle=prepared)
    assert readiness == {
        "status": "ready",
        "missing": [],
        "unsupported": [],
        "action": None,
    }


def test_garchomp_earthquake_into_tyranitar_is_supported_and_rankable_with_exact_context():
    battle = _battle()
    battle["pokemon"] = {
        "my_active": {"name_en": "garchomp", "slot_index": 0},
        "opponent_active": {"name_en": "tyranitar", "slot_index": 1},
    }
    for entry in battle["final_stat_context"]["current_final_stats"]:
        entry["provenance"]["pokemon_id"] = "garchomp" if entry["side"] == "self" else "tyranitar"
    battle["trusted_level_context"] = build_champions_trusted_level_context(
        rules_context=CHAMPIONS_RULES_CONTEXT,
        session_id="s",
        pokemon=battle["pokemon"],
    )
    battle["moves"] = {
        "my_available_moves": [{"slot_index": 0, "move_id": "earthquake"}],
        "my_selected_move": {"slot_index": 0, "move_id": "earthquake"},
        "opponent_selected_move": {"slot_index": 0, "move_id": "tackle"},
    }
    battle["ability_context"] = {
        "current_abilities": [
            {"side": "self", "ability": "sand-veil", "status": "user_confirmed", "source": "user_confirmed_current_ability", "confidence": "known"},
            {"side": "opponent", "ability": "unnerve", "status": "user_confirmed", "source": "user_confirmed_current_ability", "confidence": "known"},
        ]
    }
    cache, loader = CacheManager(), KoMappingLoader()
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "earthquake"}],
        battle_input=battle,
        move_repository=MoveRepository(cache, loader),
        species_repository=PokemonRepository(cache, loader),
    )
    candidate = prepared["candidates"][0]
    assert prepared["status"] == "ready"
    assert candidate["mechanics_result"]["status"] == "known"
    assert candidate["mechanics_result"]["type_effectiveness"] == 2.0
    assert prepared["recommendation_request"]["candidate_comparisons"][0]["mechanics_comparison"]["comparison_status"] == "rankable"


def test_readiness_and_deterministic_analysis_share_one_current_input_builder():
    readiness = inspect.getsource(MainWindow._check_structured_recommendation_readiness)
    deterministic = inspect.getsource(MainWindow._start_deterministic_strategy_analysis)
    shared = inspect.getsource(MainWindow._build_current_structured_analysis_battle_input)
    assert "_build_current_structured_analysis_battle_input" in readiness
    assert "_build_current_structured_analysis_battle_input" in deterministic
    for fragment in (
        "include_current_condition_confirmations=True",
        "include_current_ability_confirmations=True",
        "include_current_stat_stage_confirmations=True",
        "include_current_field_state_confirmation=True",
        "include_current_final_stat_confirmations=True",
        "include_current_hp_confirmations=True",
        "include_current_battle_format_confirmation=True",
        "include_observed_previous_damage_confirmation=True",
        "include_direct_mechanics_context=True",
        "runtime_advice_state",
        "capture_ui_current_state_provenance",
        "build_champions_trusted_level_context",
    ):
        assert fragment in shared
