"""Approval-gated, redacted smoke for deterministic multi-move mechanics ranking."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm.advisor_candidate_contract import (
    build_provider_recommendation_payload,
    build_recommendation_presentation_model,
    complete_recommendation_cycle,
    prepare_ui_recommendation_cycle,
)
from llm.advisor_client import SAFE_PROVIDER_DIAGNOSTIC_CODES, format_recommendation_presentation_text, sanitize_provider_failure_context
from scripts.spike_advisor import DEFAULT_MODEL

FIXTURES = ("multi-move-clear-winner", "multi-move-mixed-availability", "multi-move-stable-tie")
GROUNDING_FIXTURES = ("complete-multi-candidate-mechanics", "mixed-context-multi-candidate-mechanics")
ACCURACY_FIXTURES = ("known-accuracy-multi-candidate", "mixed-accuracy-state-multi-candidate")
STATUS_FIXTURES = ("mixed-damage-status-candidates", "mixed-status-state-candidates")
CONSEQUENCE_FIXTURES = ("recoil-drain-consequence-candidates", "turn-terminal-consequence-candidates")
FIXED_HIT_FIXTURES = ("complete-fixed-hit-candidates", "mixed-fixed-variable-hit-candidates")
FIXED_DAMAGE_FIXTURES = ("complete-level-fixed-damage-candidates", "mixed-fixed-damage-state-candidates")
MODIFIER_FIXTURES = ("combined-known-damage-modifiers", "mixed-modifier-authority-states")
ABILITY_FIXTURES = ("supported-attacker-ability-candidates", "unsupported-ability-with-level-fixed-control")
ITEM_FIXTURES = ("supported-held-item-candidates", "unsupported-item-with-level-fixed-control")
DEFENDER_ABILITY_FIXTURES = ("supported-defender-ability-candidates", "unsupported-defender-ability-with-level-fixed-control")
_ALLOWED_FIXTURE_SETS = frozenset({FIXTURES, GROUNDING_FIXTURES, ACCURACY_FIXTURES, STATUS_FIXTURES, CONSEQUENCE_FIXTURES, FIXED_HIT_FIXTURES, FIXED_DAMAGE_FIXTURES, MODIFIER_FIXTURES, ABILITY_FIXTURES, ITEM_FIXTURES, DEFENDER_ABILITY_FIXTURES})
EXIT = {"ok": 0, "usage": 2, "credential": 3, "provider": 4, "parse": 5, "structural": 6, "semantic": 7, "redaction": 8, "blocked": 9}


class _Species:
    def get(self, name: str) -> dict[str, Any]:
        return {"en": name, "types_en": ["ghost"] if name == "gengar" else ["normal"], "base_stats": {key: 80 for key in ("hp", "attack", "defense", "special-attack", "special-defense", "speed")}}


def _provenance(side: str, slot: int, pokemon: str, *, source: str = "user_confirmed_final_battle_stat") -> dict[str, Any]:
    return {"side": side, "slot_index": slot, "pokemon_id": pokemon, "session_id": "multi-smoke", "source": source, "trust": "user_confirmed_current"}


def _battle(*, known_action_order: bool = False) -> dict[str, Any]:
    entries = []
    for side, pokemon, slot in (("self", "pikachu", 0), ("opponent", "eevee", 1)):
        entries.extend({"side": side, "stat": stat, "value": 100 + index, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "provenance": _provenance(side, slot, pokemon)} for index, stat in enumerate(("hp", "attack", "defense", "special-attack", "special-defense", "speed")))
    absent = {"status": "known_absent"}
    side = {"ability": absent, "item": absent, "status": absent, "boosts": {key: 0 for key in ("attack", "defense", "special-attack", "special-defense", "speed")}, "current_hp": 100, "max_hp": 100}
    battle = {"current_state_session_id": "multi-smoke", "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 1}}, "moves": {"my_available_moves": []}, "final_stat_context": {"current_final_stats": entries}, "trusted_level_context": {"current_levels": [{"side": "self", "value": 50, "provenance": _provenance("self", 0, "pikachu", source="user_confirmed_current_level")}]}, "direct_mechanics_context": {"generation": "gen9", "attacker": deepcopy(side), "defender": deepcopy(side), "field": {"weather": absent, "terrain": absent}}}
    if known_action_order:
        battle["opponent_selected_move"] = {"move_id": "tackle"}
        battle["condition_context"] = {"current_conditions": [{"side": "self", "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"}]}
        battle["field_state_context"] = {"current_field": {"weather": "none", "terrain": "none", "global_effects": [], "side_effects": [], "status": "user_confirmed", "source": "user_confirmed_current_field_state", "confidence": "known"}}
    return battle


def _fixture(fixture_id: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    if fixture_id == FIXTURES[0]:
        return [{"move_id": "tackle"}, {"move_id": "slam"}], {"tackle": {"category": "physical", "power": 40, "type": "normal"}, "slam": {"category": "physical", "power": 100, "type": "normal"}}
    if fixture_id == FIXTURES[1]:
        return [{"move_id": "tackle"}, {"move_id": "missing-power"}, {"move_id": "double-hit"}], {"tackle": {"category": "physical", "power": 40, "type": "normal"}, "missing-power": {"category": "physical", "type": "normal"}, "double-hit": {"category": "physical", "power": 35, "type": "normal", "min_hits": 2, "max_hits": 5}}
    if fixture_id == FIXTURES[2]:
        return [{"move_id": "tackle"}, {"move_id": "tackle"}], {"tackle": {"category": "physical", "power": 40, "type": "normal"}}
    if fixture_id == GROUNDING_FIXTURES[0]:
        return [{"move_id": "quick-attack"}, {"move_id": "slam"}], {"quick-attack": {"category": "physical", "power": 40, "type": "normal", "priority": 1}, "slam": {"category": "physical", "power": 100, "type": "normal", "priority": 0}, "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}
    if fixture_id == GROUNDING_FIXTURES[1]:
        return [{"move_id": "tackle"}, {"move_id": "missing-power"}, {"move_id": "double-hit"}], {"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}, "missing-power": {"category": "physical", "type": "normal", "priority": 0}, "double-hit": {"category": "physical", "power": 35, "type": "normal", "min_hits": 2, "max_hits": 5, "priority": 0}}
    if fixture_id == ACCURACY_FIXTURES[0]:
        return [{"move_id": "thunderbolt"}, {"move_id": "stone-edge"}], {"thunderbolt": {"category": "special", "power": 90, "type": "electric", "accuracy": 100, "priority": 0}, "stone-edge": {"category": "physical", "power": 100, "type": "rock", "accuracy": 80, "priority": 0}, "tackle": {"category": "physical", "power": 40, "type": "normal", "accuracy": 100, "priority": 0}}
    if fixture_id == ACCURACY_FIXTURES[1]:
        return [{"move_id": "tackle"}, {"move_id": "swift"}, {"move_id": "dynamic"}], {"tackle": {"category": "physical", "power": 40, "type": "normal", "accuracy": 100, "priority": 0}, "swift": {"category": "special", "power": 60, "type": "normal", "always_hit": True, "priority": 0}, "dynamic": {"category": "special", "power": 1, "type": "normal", "dynamic_accuracy": True, "priority": 0}}
    if fixture_id == STATUS_FIXTURES[0]:
        return [{"move_id": "slam"}, {"move_id": "recover"}, {"move_id": "swords-dance"}], {"slam": {"category": "physical", "power": 100, "type": "normal", "accuracy": 75, "priority": 0}, "recover": {"category": "status", "target": "user", "healing": 50, "effect_category": "heal", "priority": 0}, "swords-dance": {"category": "status", "target": "user", "stat_changes": [{"stat": "attack", "change": 2}], "effect_category": "net-good-stats", "priority": 0}, "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}
    if fixture_id == STATUS_FIXTURES[1]:
        return [{"move_id": "tackle"}, {"move_id": "will-o-wisp"}, {"move_id": "mystery-status"}, {"move_id": "broken-status"}], {"tackle": {"category": "physical", "power": 40, "type": "normal", "accuracy": 100, "priority": 0}, "will-o-wisp": {"category": "status", "target": "selected-pokemon", "ailment": "burn", "effect_category": "ailment", "priority": 0}, "mystery-status": {"category": "status", "priority": 0}, "broken-status": {"category": "status", "target": "user", "stat_changes": "invalid", "priority": 0}}
    if fixture_id == CONSEQUENCE_FIXTURES[0]:
        return [{"move_id": "brave-bird"}, {"move_id": "drain-punch"}, {"move_id": "tackle"}], {"brave-bird": {"category": "physical", "power": 120, "type": "flying", "drain": -33, "priority": 0}, "drain-punch": {"category": "physical", "power": 75, "type": "fighting", "drain": 50, "priority": 0}, "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}
    if fixture_id == CONSEQUENCE_FIXTURES[1]:
        return [{"move_id": "solar-beam"}, {"move_id": "hyper-beam"}, {"move_id": "explosion"}, {"move_id": "dynamic-consequence"}], {"solar-beam": {"category": "special", "power": 120, "type": "grass", "priority": 0}, "hyper-beam": {"category": "special", "power": 150, "type": "normal", "priority": 0}, "explosion": {"category": "physical", "power": 250, "type": "normal", "priority": 0}, "dynamic-consequence": {"category": "physical", "power": 1, "type": "normal", "dynamic_consequence": True, "priority": 0}, "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}
    if fixture_id == FIXED_HIT_FIXTURES[0]:
        return [{"move_id": "double-hit"}, {"move_id": "slam"}], {"double-hit": {"category": "physical", "power": 60, "type": "normal", "min_hits": 2, "max_hits": 2, "priority": 0}, "slam": {"category": "physical", "power": 100, "type": "normal", "priority": 0}, "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}
    if fixture_id == FIXED_HIT_FIXTURES[1]:
        return [{"move_id": "double-hit"}, {"move_id": "variable-hit"}, {"move_id": "broken-hit"}], {"double-hit": {"category": "physical", "power": 60, "type": "normal", "min_hits": 2, "max_hits": 2, "priority": 0}, "variable-hit": {"category": "physical", "power": 35, "type": "normal", "min_hits": 2, "max_hits": 5, "priority": 0}, "broken-hit": {"category": "physical", "power": 35, "type": "normal", "min_hits": "two", "max_hits": 2, "priority": 0}, "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}
    if fixture_id == FIXED_DAMAGE_FIXTURES[0]:
        return [{"move_id": "seismic-toss"}, {"move_id": "tackle"}], {"seismic-toss": {"category": "physical", "type": "normal", "priority": 0}, "tackle": {"category": "physical", "power": 30, "type": "normal", "priority": 0}}
    if fixture_id == FIXED_DAMAGE_FIXTURES[1]:
        return [{"move_id": "seismic-toss"}, {"move_id": "night-shade"}, {"move_id": "psywave"}], {"seismic-toss": {"category": "physical", "type": "normal", "priority": 0}, "night-shade": {"category": "special", "type": "ghost", "priority": 0}, "psywave": {"category": "special", "power": 1, "type": "psychic", "priority": 0}, "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}
    if fixture_id == MODIFIER_FIXTURES[0]:
        return [{"move_id": "aqua-tail"}, {"move_id": "flamethrower"}, {"move_id": "seismic-toss"}], {"aqua-tail": {"category": "physical", "power": 90, "type": "water", "priority": 1}, "flamethrower": {"category": "special", "power": 90, "type": "fire", "priority": 0}, "seismic-toss": {"category": "physical", "type": "normal", "priority": 0}, "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}
    if fixture_id == MODIFIER_FIXTURES[1]:
        return [{"move_id": "aqua-tail"}, {"move_id": "hyper-beam"}, {"move_id": "seismic-toss"}], {"aqua-tail": {"category": "physical", "power": 90, "type": "water", "priority": 0}, "hyper-beam": {"category": "special", "power": 150, "type": "normal", "priority": 0}, "seismic-toss": {"category": "physical", "type": "normal", "priority": 0}, "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}
    if fixture_id == ABILITY_FIXTURES[0]:
        return [{"move_id": "mach-punch"}, {"move_id": "tackle"}, {"move_id": "seismic-toss"}], {"mach-punch": {"category": "physical", "power": 40, "type": "fighting", "priority": 1}, "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}, "seismic-toss": {"category": "physical", "type": "normal", "priority": 0}}
    if fixture_id == ABILITY_FIXTURES[1]:
        return [{"move_id": "tackle"}, {"move_id": "seismic-toss"}], {"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}, "seismic-toss": {"category": "physical", "type": "normal", "priority": 0}}
    if fixture_id == ITEM_FIXTURES[0]:
        return [{"move_id": "double-hit"}, {"move_id": "tackle"}, {"move_id": "swift"}, {"move_id": "seismic-toss"}], {"double-hit": {"category": "physical", "power": 60, "type": "normal", "min_hits": 2, "max_hits": 2, "priority": 0}, "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}, "swift": {"category": "special", "power": 60, "type": "normal", "priority": 0}, "seismic-toss": {"category": "physical", "type": "normal", "priority": 0}}
    if fixture_id == ITEM_FIXTURES[1]:
        return [{"move_id": "tackle"}, {"move_id": "seismic-toss"}], {"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}, "seismic-toss": {"category": "physical", "type": "normal", "priority": 0}}
    if fixture_id == DEFENDER_ABILITY_FIXTURES[0]:
        return [{"move_id": "double-hit"}, {"move_id": "swift"}, {"move_id": "seismic-toss"}], {"double-hit": {"category": "physical", "power": 60, "type": "normal", "min_hits": 2, "max_hits": 2, "priority": 0}, "swift": {"category": "special", "power": 60, "type": "normal", "priority": 0}, "seismic-toss": {"category": "physical", "type": "normal", "priority": 0}}
    if fixture_id == DEFENDER_ABILITY_FIXTURES[1]:
        return [{"move_id": "tackle"}, {"move_id": "seismic-toss"}], {"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}, "seismic-toss": {"category": "physical", "type": "normal", "priority": 0}}
    raise ValueError("invalid_fixture")


def _prepared(fixture_id: str) -> dict[str, Any]:
    moves, repository = _fixture(fixture_id)
    battle = _battle(known_action_order=fixture_id in {*GROUNDING_FIXTURES, *ACCURACY_FIXTURES, *STATUS_FIXTURES, *CONSEQUENCE_FIXTURES, *FIXED_HIT_FIXTURES, *FIXED_DAMAGE_FIXTURES, *MODIFIER_FIXTURES, *ABILITY_FIXTURES, *ITEM_FIXTURES, *DEFENDER_ABILITY_FIXTURES})
    if fixture_id == FIXED_DAMAGE_FIXTURES[0]:
        battle["direct_mechanics_context"]["defender"].update(current_hp=50, max_hp=200)
    if fixture_id == FIXED_DAMAGE_FIXTURES[1]:
        battle["pokemon"]["opponent_active"]["name_en"] = "gengar"
        for entry in battle["final_stat_context"]["current_final_stats"]:
            if entry.get("side") == "opponent":
                entry["provenance"]["pokemon_id"] = "gengar"
    if fixture_id == MODIFIER_FIXTURES[0]:
        battle["trusted_level_context"]["current_levels"][0]["value"] = 1
        battle["field_state_context"] = {"current_field": {"weather": "rain", "terrain": "none", "global_effects": [], "side_effects": [{"side": "opponent", "effect": "reflect"}, {"side": "opponent", "effect": "light-screen"}], "status": "user_confirmed", "source": "user_confirmed_current_field_state", "confidence": "known"}}
        battle["condition_context"] = {"current_conditions": [{"side": "self", "condition_type": "burn", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"}]}
        battle["battle_format_context"] = {"current_battle_format": {"battle_format": "singles", "source": "user_confirmed_battle_format", "confidence": "known"}}
    if fixture_id == MODIFIER_FIXTURES[1]:
        battle["field_state_context"] = {"current_field": {"weather": "unknown", "terrain": "none", "global_effects": [], "side_effects": [{"side": "opponent", "effect": "light-screen"}], "status": "user_confirmed", "source": "user_confirmed_current_field_state", "confidence": "known"}}
        battle["condition_context"] = {"current_conditions": [{"side": "self", "condition_type": "unknown", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"}]}
        battle["battle_format_context"] = {"current_battle_format": {"battle_format": "doubles", "source": "user_confirmed_battle_format", "confidence": "known"}}
    if fixture_id == ABILITY_FIXTURES[0]:
        battle["trusted_level_context"]["current_levels"][0]["value"] = 1
        battle["ability_context"] = {"current_abilities": [_current_ability("iron-fist")]}
    if fixture_id == ABILITY_FIXTURES[1]:
        battle["ability_context"] = {"current_abilities": [_current_ability("guts")]}
    if fixture_id == ITEM_FIXTURES[0]:
        battle["trusted_level_context"]["current_levels"][0]["value"] = 1
        battle["item_profiles"] = {"my_active": {"status": "user_confirmed", "source": "user_input", "item_id": "choice-band"}}
    if fixture_id == ITEM_FIXTURES[1]:
        battle["item_profiles"] = {"my_active": {"status": "user_confirmed", "source": "user_input", "item_id": "choice-scarf"}}
    if fixture_id == DEFENDER_ABILITY_FIXTURES[0]:
        battle["trusted_level_context"]["current_levels"][0]["value"] = 1
        battle["ability_context"] = {"current_abilities": [_current_ability("fur-coat", side="opponent", pokemon="eevee", slot=1)]}
    if fixture_id == DEFENDER_ABILITY_FIXTURES[1]:
        battle["ability_context"] = {"current_abilities": [_current_ability("solid-rock", side="opponent", pokemon="eevee", slot=1)]}
    battle["moves"]["my_available_moves"] = [{"slot_index": index, "move_id": item["move_id"]} for index, item in enumerate(moves)]
    return prepare_ui_recommendation_cycle(selected_moves=moves, battle_input=battle, move_repository=repository, species_repository=_Species())


def _current_ability(ability: str, *, side: str = "self", pokemon: str = "pikachu", slot: int = 0) -> dict[str, Any]:
    return {"side": side, "ability": ability, "status": "user_confirmed", "source": "user_confirmed_current_ability", "confidence": "known", "provenance": _provenance(side, slot, pokemon, source="user_confirmed_current_ability")}


def offline_ability_authority_variants() -> dict[str, Any]:
    """Exercise non-provider ability states without converting them to absence."""
    variants: dict[str, dict[str, Any]] = {}
    for name, ability in (("unknown", "unknown"), ("malformed", "bad/ability"), ("unsupported", "guts")):
        battle = _battle(known_action_order=True)
        battle["ability_context"] = {"current_abilities": [_current_ability(ability)]}
        battle["moves"]["my_available_moves"] = [{"slot_index": 0, "move_id": "tackle"}]
        prepared = prepare_ui_recommendation_cycle(
            selected_moves=[{"move_id": "tackle"}], battle_input=battle,
            move_repository={"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}, species_repository=_Species(),
        )
        rows = prepared.get("recommendation_request", {}).get("candidate_comparisons", []) if isinstance(prepared.get("recommendation_request"), Mapping) else []
        mechanics = rows[0].get("mechanics_result", {}) if isinstance(rows, list) and rows and isinstance(rows[0], Mapping) else {}
        comparison = rows[0].get("mechanics_comparison", {}) if isinstance(rows, list) and rows and isinstance(rows[0], Mapping) else {}
        variants[name] = {"cycle_status": prepared.get("status"), "mechanics_status": mechanics.get("status"), "rank": comparison.get("rank")}
    no_usable_battle = _battle(known_action_order=True)
    no_usable_battle["moves"]["my_available_moves"] = [{"slot_index": 0, "move_id": "missing"}]
    no_usable = prepare_ui_recommendation_cycle(selected_moves=[{"move_id": "missing"}], battle_input=no_usable_battle, move_repository={}, species_repository=_Species())
    return {"provider_calls": 0, "variants": variants, "no_usable_cycle_status": no_usable.get("status")}


def offline_item_authority_variants() -> dict[str, Any]:
    """Exercise non-provider item states without converting them to no-item."""
    variants: dict[str, dict[str, Any]] = {}
    profiles = {
        "unknown": {"status": "unknown", "source": "user_unconfirmed", "item_id": None},
        "malformed": {"status": "user_confirmed", "source": "user_input", "item_id": "bad/item"},
        "explicit_none": {"status": "none", "source": "user_input", "item_id": None},
        "system_default": {"status": "system_default_none", "source": "system_default", "item_id": None},
        "unsupported": {"status": "user_confirmed", "source": "user_input", "item_id": "choice-scarf"},
    }
    for name, profile in profiles.items():
        battle = _battle(known_action_order=True)
        battle["item_profiles"] = {"my_active": profile}
        battle["moves"]["my_available_moves"] = [{"slot_index": 0, "move_id": "tackle"}]
        prepared = prepare_ui_recommendation_cycle(
            selected_moves=[{"move_id": "tackle"}], battle_input=battle,
            move_repository={"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}, species_repository=_Species(),
        )
        rows = prepared.get("recommendation_request", {}).get("candidate_comparisons", []) if isinstance(prepared.get("recommendation_request"), Mapping) else []
        mechanics = rows[0].get("mechanics_result", {}) if isinstance(rows, list) and rows and isinstance(rows[0], Mapping) else {}
        comparison = rows[0].get("mechanics_comparison", {}) if isinstance(rows, list) and rows and isinstance(rows[0], Mapping) else {}
        variants[name] = {"cycle_status": prepared.get("status"), "mechanics_status": mechanics.get("status"), "rank": comparison.get("rank")}
    no_usable = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}], battle_input={**_battle(known_action_order=True), "item_profiles": {"my_active": profiles["unsupported"]}, "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]}},
        move_repository={"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}, species_repository=_Species(),
    )
    return {"provider_calls": 0, "variants": variants, "no_usable_cycle_status": no_usable.get("status")}


def offline_defender_ability_authority_variants() -> dict[str, Any]:
    """Exercise target ability authority without turning it into no effect."""
    variants: dict[str, dict[str, Any]] = {}
    for name, ability in (("unknown", "unknown"), ("malformed", "bad/ability"), ("unsupported", "solid-rock")):
        battle = _battle(known_action_order=True)
        battle["ability_context"] = {"current_abilities": [_current_ability(ability, side="opponent", pokemon="eevee", slot=1)]}
        battle["moves"]["my_available_moves"] = [{"slot_index": 0, "move_id": "tackle"}]
        prepared = prepare_ui_recommendation_cycle(
            selected_moves=[{"move_id": "tackle"}], battle_input=battle,
            move_repository={"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}, species_repository=_Species(),
        )
        rows = prepared.get("recommendation_request", {}).get("candidate_comparisons", []) if isinstance(prepared.get("recommendation_request"), Mapping) else []
        mechanics = rows[0].get("mechanics_result", {}) if isinstance(rows, list) and rows and isinstance(rows[0], Mapping) else {}
        comparison = rows[0].get("mechanics_comparison", {}) if isinstance(rows, list) and rows and isinstance(rows[0], Mapping) else {}
        variants[name] = {"cycle_status": prepared.get("status"), "mechanics_status": mechanics.get("status"), "rank": comparison.get("rank")}
    stale_battle = _battle(known_action_order=True)
    stale_battle["moves"]["my_available_moves"] = [{"slot_index": 0, "move_id": "tackle"}]
    stale = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}], battle_input=stale_battle,
        move_repository={"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}, species_repository=_Species(),
    )
    prepared = _prepared(DEFENDER_ABILITY_FIXTURES[0])
    mismatch = complete_recommendation_cycle(prepared_cycle=prepared, response_payload={"recommendation_status": "resolved", "selected_candidate_id": 1, "explanation_code": "clear_ranked_winner"})
    no_usable = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}], battle_input={**_battle(known_action_order=True), "ability_context": {"current_abilities": [_current_ability("solid-rock", side="opponent", pokemon="eevee", slot=1)]}, "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]}},
        move_repository={"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}, species_repository=_Species(),
    )
    stale_rows = stale.get("recommendation_request", {}).get("candidate_comparisons", []) if isinstance(stale.get("recommendation_request"), Mapping) else []
    stale_mechanics = stale_rows[0].get("mechanics_result", {}) if isinstance(stale_rows, list) and stale_rows and isinstance(stale_rows[0], Mapping) else {}
    return {"provider_calls": 0, "variants": variants, "stale_context_status": stale_mechanics.get("status"), "candidate_mismatch_errors": mismatch.get("errors"), "no_usable_cycle_status": no_usable.get("status")}


def _expected_rank_one(payload: Mapping[str, Any]) -> tuple[str, int] | None:
    comparisons = payload.get("candidate_comparisons")
    if not isinstance(comparisons, list):
        return None
    winners = [(row.get("move"), row.get("slot_index")) for row in comparisons if isinstance(row, Mapping) and isinstance(row.get("mechanics_comparison"), Mapping) and row["mechanics_comparison"].get("rank") == 1]
    if len(winners) != 1 or not isinstance(winners[0][0], str) or not isinstance(winners[0][1], int):
        return None
    return winners[0]


def _fixture_contract_valid(fixture_id: str, payload: Mapping[str, Any]) -> bool:
    rows = payload.get("candidate_comparisons")
    if not isinstance(rows, list):
        return False
    comparisons = [row.get("mechanics_comparison") for row in rows if isinstance(row, Mapping)]
    if fixture_id == FIXTURES[0]:
        return [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [2, 1] and all(isinstance(row.get("mechanics_result"), Mapping) and row["mechanics_result"].get("status") == "known" for row in rows if isinstance(row, Mapping))
    if fixture_id == FIXTURES[1]:
        mechanics = [row.get("mechanics_result") for row in rows if isinstance(row, Mapping)]
        return [item.get("comparison_status") for item in comparisons if isinstance(item, Mapping)] == ["rankable", "insufficient_context", "unsupported_mechanic"] and [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [1, None, None] and isinstance(mechanics[1], Mapping) and isinstance(mechanics[1].get("missing_inputs"), list) and bool(mechanics[1]["missing_inputs"]) and isinstance(mechanics[2], Mapping) and isinstance(mechanics[2].get("unsupported_reason"), str)
    if fixture_id == FIXTURES[2]:
        return [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [1, 2]
    if fixture_id == GROUNDING_FIXTURES[0]:
        if [item.get("rank") for item in comparisons if isinstance(item, Mapping)] != [2, 1]:
            return False
        return all(
            isinstance(row, Mapping)
            and isinstance(row.get("mechanics_result"), Mapping)
            and row["mechanics_result"].get("status") == "known"
            and isinstance(row.get("comparison_facts"), Mapping)
            and row["comparison_facts"].get("candidate_id") == {"slot_index": row.get("slot_index"), "move": row.get("move")}
            for row in rows
        ) and any(row["comparison_facts"].get("action_order_status") == "acts_first" for row in rows)
    if fixture_id == GROUNDING_FIXTURES[1]:
        mechanics = [row.get("mechanics_result") for row in rows if isinstance(row, Mapping)]
        return [item.get("comparison_status") for item in comparisons if isinstance(item, Mapping)] == ["rankable", "insufficient_context", "unsupported_mechanic"] and [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [1, None, None] and all(isinstance(row.get("comparison_facts"), Mapping) and row["comparison_facts"].get("candidate_id") == {"slot_index": row.get("slot_index"), "move": row.get("move")} for row in rows if isinstance(row, Mapping)) and isinstance(mechanics[1], Mapping) and isinstance(mechanics[1].get("missing_inputs"), list) and bool(mechanics[1]["missing_inputs"]) and isinstance(mechanics[2], Mapping) and isinstance(mechanics[2].get("unsupported_reason"), str)
    if fixture_id == ACCURACY_FIXTURES[0]:
        states = [row.get("accuracy_evidence", {}).get("status") for row in rows if isinstance(row, Mapping)]
        tags = [row.get("comparison_facts", {}).get("comparison_tags", []) for row in rows if isinstance(row, Mapping)]
        return states == ["known_accuracy", "known_accuracy"] and "known_higher_canonical_accuracy" in tags[0] and "known_lower_canonical_accuracy" in tags[1]
    if fixture_id == ACCURACY_FIXTURES[1]:
        states = [row.get("accuracy_evidence", {}).get("status") for row in rows if isinstance(row, Mapping)]
        return states == ["known_accuracy", "always_hits", "unsupported_mechanic"]
    if fixture_id == STATUS_FIXTURES[0]:
        roles = [row.get("status_move_evidence", {}).get("role_tags") for row in rows if isinstance(row, Mapping)]
        tags = [row.get("comparison_facts", {}).get("comparison_tags", []) for row in rows if isinstance(row, Mapping)]
        return [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [1, None, None] and roles == [[], ["recovery"], ["self_stat_raise"]] and "known_recovery_role" in tags[1] and "known_setup_role" in tags[2] and all("damage_range" not in row["mechanics_result"] for row in rows[1:] if isinstance(row.get("mechanics_result"), Mapping))
    if fixture_id == STATUS_FIXTURES[1]:
        role_statuses = [row.get("status_move_evidence", {}).get("status") for row in rows if isinstance(row, Mapping)]
        tags = [row.get("comparison_facts", {}).get("comparison_tags", []) for row in rows if isinstance(row, Mapping)]
        return [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [1, None, None, None] and role_statuses == ["not_applicable", "known_role", "insufficient_context", "unsupported_mechanic"] and "known_status_infliction_role" in tags[1] and "status_role_unknown" in tags[2] and "status_role_unsupported" in tags[3] and all("damage_range" not in row["mechanics_result"] for row in rows[1:] if isinstance(row.get("mechanics_result"), Mapping))
    if fixture_id == CONSEQUENCE_FIXTURES[0]:
        consequences = [row.get("move_consequence_evidence", {}) for row in rows if isinstance(row, Mapping)]
        return [item.get("status") for item in consequences] == ["known", "known", "no_known_consequence"] and consequences[0].get("consequence_tags") == ["recoil"] and consequences[1].get("consequence_tags") == ["drain_or_healing_from_damage"]
    if fixture_id == CONSEQUENCE_FIXTURES[1]:
        consequences = [row.get("move_consequence_evidence", {}) for row in rows if isinstance(row, Mapping)]
        return consequences[0].get("consequence_tags") == ["charge_turn"] and consequences[1].get("consequence_tags") == ["recharge_turn"] and consequences[2].get("consequence_tags") == ["self_faint"] and consequences[3].get("status") == "unsupported_mechanic"
    if fixture_id == FIXED_HIT_FIXTURES[0]:
        fixed = rows[0].get("mechanics_result", {}) if rows else {}
        return fixed.get("status") == "known" and fixed.get("hit_count") == 2 and isinstance(fixed.get("per_hit_damage_range"), Mapping) and isinstance(fixed.get("damage_range"), Mapping) and rows[1].get("mechanics_result", {}).get("hit_count") == 1
    if fixture_id == FIXED_HIT_FIXTURES[1]:
        mechanics = [row.get("mechanics_result", {}) for row in rows if isinstance(row, Mapping)]
        return mechanics[0].get("hit_count") == 2 and mechanics[1].get("unsupported_reason") == "variable_multi_hit_move" and mechanics[2].get("unsupported_reason") == "invalid_fixed_hit_count"
    if fixture_id == FIXED_DAMAGE_FIXTURES[0]:
        fixed, q12 = rows[0].get("mechanics_result", {}), rows[1].get("mechanics_result", {})
        return fixed.get("status") == "known" and fixed.get("damage_model") == "level_based_fixed" and fixed.get("fixed_damage") == 50 and fixed.get("damage_range") == {"minimum": 50, "maximum": 50} and fixed.get("damage_percent_range") == {"minimum": 25.0, "maximum": 25.0} and fixed.get("ko_result", {}).get("single_hit_probability") == 1.0 and q12.get("mechanics_source") == "native_q12_direct_damage" and q12.get("damage_model") == "single_hit_formula" and comparisons[0].get("rank") == 1
    if fixture_id == FIXED_DAMAGE_FIXTURES[1]:
        immune, fixed, unsupported = [row.get("mechanics_result", {}) for row in rows]
        return immune.get("damage_model") == "level_based_fixed" and immune.get("fixed_damage") == 0 and immune.get("type_effectiveness") == 0.0 and immune.get("ko_result", {}).get("single_hit_probability") == 0.0 and fixed.get("damage_model") == "level_based_fixed" and fixed.get("fixed_damage") == 50 and fixed.get("damage_range") == {"minimum": 50, "maximum": 50} and fixed.get("type_effectiveness") == 2.0 and unsupported.get("status") == "unsupported_mechanic" and unsupported.get("unsupported_reason") == "unsupported_fixed_damage_rule" and comparisons[1].get("rank") == 1
    if fixture_id == MODIFIER_FIXTURES[0]:
        mechanics = [row.get("mechanics_result", {}) for row in rows if isinstance(row, Mapping)]
        return [item.get("status") for item in mechanics] == ["known", "known", "known"] and [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [1, 3, 2] and mechanics[0].get("applied_damage_modifiers") == ["rain_water_boost", "burn_physical_reduction", "reflect_reduction"] and mechanics[1].get("applied_damage_modifiers") == ["rain_fire_reduction", "light_screen_reduction"] and mechanics[2].get("damage_model") == "level_based_fixed" and "applied_damage_modifiers" not in mechanics[2]
    if fixture_id == MODIFIER_FIXTURES[1]:
        mechanics = [row.get("mechanics_result", {}) for row in rows if isinstance(row, Mapping)]
        return mechanics[0].get("status") == "insufficient_context" and {"field.weather", "attacker.condition"} <= set(mechanics[0].get("missing_inputs", [])) and mechanics[1].get("status") == "unsupported_mechanic" and mechanics[1].get("unsupported_reason") == "battle_format" and mechanics[2].get("status") == "known" and mechanics[2].get("damage_model") == "level_based_fixed" and "applied_damage_modifiers" not in mechanics[2]
    if fixture_id == ABILITY_FIXTURES[0]:
        matching, nonmatching, fixed = [row.get("mechanics_result", {}) for row in rows]
        return [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [1, 2, 3] and matching.get("status") == nonmatching.get("status") == fixed.get("status") == "known" and matching.get("applied_damage_modifiers") == ["ability_iron_fist_boost"] and nonmatching.get("applied_damage_modifiers") == [] and fixed.get("damage_model") == "level_based_fixed" and "applied_damage_modifiers" not in fixed
    if fixture_id == ABILITY_FIXTURES[1]:
        unsupported, fixed = [row.get("mechanics_result", {}) for row in rows]
        return [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [None, 1] and unsupported.get("status") == "unsupported_mechanic" and unsupported.get("unsupported_reason") == "ability_modifier" and fixed.get("status") == "known" and fixed.get("damage_model") == "level_based_fixed" and "applied_damage_modifiers" not in fixed
    if fixture_id == ITEM_FIXTURES[0]:
        fixed_hit, matching, nonmatching, level_fixed = [row.get("mechanics_result", {}) for row in rows]
        return [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [1, 2, 3, 4] and fixed_hit.get("status") == matching.get("status") == nonmatching.get("status") == level_fixed.get("status") == "known" and fixed_hit.get("hit_count") == 2 and fixed_hit.get("applied_damage_modifiers") == ["item_choice_band_boost"] and matching.get("applied_damage_modifiers") == ["item_choice_band_boost"] and nonmatching.get("applied_damage_modifiers") == [] and level_fixed.get("damage_model") == "level_based_fixed" and "applied_damage_modifiers" not in level_fixed
    if fixture_id == ITEM_FIXTURES[1]:
        unsupported, fixed = [row.get("mechanics_result", {}) for row in rows]
        return [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [None, 1] and unsupported.get("status") == "unsupported_mechanic" and unsupported.get("unsupported_reason") == "item_modifier" and fixed.get("status") == "known" and fixed.get("damage_model") == "level_based_fixed" and "applied_damage_modifiers" not in fixed
    if fixture_id == DEFENDER_ABILITY_FIXTURES[0]:
        fixed_hit, nonmatching, level_fixed = [row.get("mechanics_result", {}) for row in rows]
        return [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [1, 2, 3] and fixed_hit.get("status") == nonmatching.get("status") == level_fixed.get("status") == "known" and fixed_hit.get("hit_count") == 2 and fixed_hit.get("applied_damage_modifiers") == ["defender_ability_fur_coat_reduction"] and nonmatching.get("applied_damage_modifiers") == [] and level_fixed.get("damage_model") == "level_based_fixed" and "applied_damage_modifiers" not in level_fixed
    if fixture_id == DEFENDER_ABILITY_FIXTURES[1]:
        unsupported, fixed = [row.get("mechanics_result", {}) for row in rows]
        return [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [None, 1] and unsupported.get("status") == "unsupported_mechanic" and unsupported.get("unsupported_reason") == "defender_ability_modifier" and fixed.get("status") == "known" and fixed.get("damage_model") == "level_based_fixed" and "applied_damage_modifiers" not in fixed
    return False


def _completed_candidate_evidence_isolated(*, payload: Mapping[str, Any], completed: Mapping[str, Any]) -> bool:
    """Confirm completion retained each candidate's own native evidence only."""
    rows, candidates = payload.get("candidate_comparisons"), completed.get("candidates")
    if not isinstance(rows, list) or not isinstance(candidates, list) or len(rows) != len(candidates):
        return False
    indexed = {(candidate.get("slot_index"), candidate.get("move")): candidate for candidate in candidates if isinstance(candidate, Mapping)}
    if len(indexed) != len(candidates):
        return False
    for row in rows:
        if not isinstance(row, Mapping):
            return False
        pair = (row.get("slot_index"), row.get("move"))
        candidate = indexed.get(pair)
        facts = row.get("comparison_facts")
        if not isinstance(candidate, Mapping) or not isinstance(facts, Mapping):
            return False
        if facts.get("candidate_id") != {"slot_index": pair[0], "move": pair[1]}:
            return False
        if candidate.get("mechanics_result") != row.get("mechanics_result") or candidate.get("action_order") != row.get("action_order") or candidate.get("accuracy_evidence") != row.get("accuracy_evidence") or candidate.get("status_move_evidence") != row.get("status_move_evidence") or candidate.get("move_consequence_evidence") != row.get("move_consequence_evidence"):
            return False
    return True


def _presentation_contract_valid(*, fixture_id: str, completed: Mapping[str, Any]) -> bool:
    result = completed.get("recommendation_result")
    if not isinstance(result, Mapping) or result.get("status") != "resolved":
        return False
    selected = result.get("selected_candidate_evidence")
    action = result.get("selected_action")
    facts = selected.get("comparison_facts") if isinstance(selected, Mapping) else None
    if not isinstance(selected, Mapping) or not isinstance(action, Mapping) or not isinstance(facts, Mapping) or facts.get("candidate_id") != action:
        return False
    presentation = build_recommendation_presentation_model(completed_cycle=completed)
    summary = presentation.get("selected_candidate") if isinstance(presentation, Mapping) else None
    if not isinstance(summary, Mapping) or summary.get("selected_action") != action:
        return False
    text = format_recommendation_presentation_text(presentation_model=presentation)
    forbidden = ("candidate_comparisons", "raw_response", "mechanics_path", "numeric_scope", "multi_provider_", "canonical_effect", "target_scope", "role_tags", "canonical_ratio", "HP")
    if not isinstance(text, str) or any(item in text for item in forbidden) or "선택 행동:" not in text:
        return False
    mechanics = selected.get("mechanics_result")
    if fixture_id in ABILITY_FIXTURES:
        ability_labels = {
            "ability_iron_fist_boost": "\uc544\uc774\uc5b8\ud53c\uc2a4\ud2b8\uc5d0 \uc758\ud55c \ud380\uce58 \uae30\uc220 \uac15\ud654",
            "ability_strong_jaw_boost": "\uc2a4\ud2b8\ub871\uc870에 \uc758\ud55c \ubb3c\uae30 \uae30\uc220 \uac15\ud654",
            "ability_mega_launcher_boost": "\uba54\uac00\ub7f0\uccd0에 \uc758\ud55c \ud30c\ub3d9 \uae30\uc220 \uac15\ud654",
            "ability_technician_boost": "\ud14c\ud06c\ub2c8션에 \uc758\ud55c \uc800\uc704\ub825 \uae30\uc220 \uac15\ud654",
        }
        applied = mechanics.get("applied_damage_modifiers") if isinstance(mechanics, Mapping) else None
        if fixture_id == ABILITY_FIXTURES[0]:
            return isinstance(applied, list) and applied == ["ability_iron_fist_boost"] and ability_labels["ability_iron_fist_boost"] in text and all(tag not in text for tag in ability_labels)
        return isinstance(mechanics, Mapping) and mechanics.get("damage_model") == "level_based_fixed" and not any(label in text for label in ability_labels.values())
    if fixture_id in ITEM_FIXTURES:
        item_labels = {
            "item_life_orb_boost": "\uc0dd\uba85\uc758\uad6c\uc2ac \uc18c\uc9c0\ud488\uc73c\ub85c \uc778\ud55c \ud53c\ud574 \uac15\ud654",
            "item_choice_band_boost": "\uad6c\uc560\uc758\ubc34\ub4dc \uc18c\uc9c0\ud488\uc73c\ub85c \uc778\ud55c \ubb3c\ub9ac \ud53c\ud574 \uac15\ud654",
            "item_choice_specs_boost": "\uad6c\uc560\uc758\uc548\uacbd \uc18c\uc9c0\ud488\uc73c\ub85c \uc778\ud55c \ud2b9\uc218 \ud53c\ud574 \uac15\ud654",
            "item_muscle_band_boost": "\uadfc\ub825\ubc34\ub4dc \uc18c\uc9c0\ud488\uc73c\ub85c \uc778\ud55c \ubb3c\ub9ac \ud53c\ud574 \uac15\ud654",
        }
        applied = mechanics.get("applied_damage_modifiers") if isinstance(mechanics, Mapping) else None
        if fixture_id == ITEM_FIXTURES[0]:
            return isinstance(applied, list) and applied == ["item_choice_band_boost"] and item_labels["item_choice_band_boost"] in text and all(tag not in text for tag in item_labels)
        return isinstance(mechanics, Mapping) and mechanics.get("damage_model") == "level_based_fixed" and not any(label in text for label in item_labels.values())
    if fixture_id in DEFENDER_ABILITY_FIXTURES:
        labels = {
            "defender_ability_thick_fat_reduction": "두꺼운지방 특성으로 불꽃 또는 얼음 기술 피해 감소",
            "defender_ability_fur_coat_reduction": "퍼코트 특성으로 물리 피해 감소",
            "defender_ability_ice_scales_reduction": "아이스스케일 특성으로 특수 피해 감소",
            "defender_ability_filter_reduction": "필터 특성으로 약점 기술 피해 감소",
        }
        applied = mechanics.get("applied_damage_modifiers") if isinstance(mechanics, Mapping) else None
        if fixture_id == DEFENDER_ABILITY_FIXTURES[0]:
            return isinstance(applied, list) and applied == ["defender_ability_fur_coat_reduction"] and labels["defender_ability_fur_coat_reduction"] in text and all(tag not in text for tag in labels)
        return isinstance(mechanics, Mapping) and mechanics.get("damage_model") == "level_based_fixed" and not any(label in text for label in labels.values())
    if fixture_id in MODIFIER_FIXTURES:
        applied = mechanics.get("applied_damage_modifiers") if isinstance(mechanics, Mapping) else None
        labels = {
            "rain_water_boost": "\ube44\ub85c \uc778\ud55c \ubb3c\ud0c0\uc785 \uae30\uc220 \uac15\ud654",
            "rain_fire_reduction": "\ube44\ub85c \uc778\ud55c \ubd88\uaf43\ud0c0\uc785 \uae30\uc220 \uc57d\ud654",
            "burn_physical_reduction": "\ud654\uc0c1\uc73c\ub85c \uc778\ud55c \ubb3c\ub9ac \ud53c\ud574 \uac10\uc18c",
            "reflect_reduction": "\uc0c1\ub300 \uce21 \ub9ac\ud50c\ub809\ud130 \uc801\uc6a9",
            "light_screen_reduction": "\uc0c1\ub300 \uce21 \ub77c\uc774\ud2b8\uc2a4\ud06c\ub9b0 \uc801\uc6a9",
        }
        if isinstance(applied, list):
            return all(labels[tag] in text for tag in applied if tag in labels) and all(tag not in text for tag in labels)
        return not any(label in text for label in labels.values())
    if isinstance(mechanics, Mapping) and mechanics.get("status") == "known":
        if fixture_id in FIXED_DAMAGE_FIXTURES and mechanics.get("damage_model") == "level_based_fixed":
            labels = ("\ud53c\ud574 \ubc29\uc2dd: \uc0ac\uc6a9\uc790 \ub808\ubca8\uacfc \ub3d9\uc77c\ud55c \uace0\uc815 \ud53c\ud574",)
            return all(label in text for label in labels) and (("\ud53c\ud574 \uc5c6\uc74c: \ud0c0\uc785 \ubb34\ud6a8" in text) if mechanics.get("type_effectiveness") == 0 else (f"\uace0\uc815 \ud53c\ud574: {mechanics.get('fixed_damage')}" in text))
        if fixture_id in FIXED_HIT_FIXTURES and mechanics.get("hit_count") == 2:
            return all(label in text for label in ("\uace0\uc815 2\ud68c \uacf5\uaca9", "1\ud68c\ub2f9 \ud53c\ud574 \ubc94\uc704:", "\uc804\uccb4 \ud53c\ud574 \ubc94\uc704:"))
        return "피해 범위:" in text and "피해 비율:" in text
    accuracy = selected.get("accuracy_evidence")
    if isinstance(accuracy, Mapping) and accuracy.get("status") == "known_accuracy":
        if accuracy.get("canonical_accuracy") == 100 and "항상 명중하는 기술" in text:
            return False
        if "기본 명중률:" not in text:
            return False
    if isinstance(accuracy, Mapping) and accuracy.get("status") in {"insufficient_context", "unsupported_mechanic"} and isinstance(accuracy.get("canonical_accuracy"), (int, float)):
        return False
    return "피해 범위:" not in text and "피해 비율:" not in text if not (isinstance(mechanics, Mapping) and mechanics.get("status") == "known") else True


def _actual_adapters(*, model: str) -> tuple[Callable[[], bool], Callable[[Mapping[str, Any]], dict[str, Any]]]:
    def credential_available() -> bool:
        return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))

    def provider_call(payload: Mapping[str, Any]) -> dict[str, Any]:
        from llm.advisor_client import call_structured_recommendation_provider
        response, _usage = call_structured_recommendation_provider(provider_payload=payload, model=model)
        return response

    return credential_available, provider_call


def run_smoke(*, actual: bool = False, model: str | None = None, fixtures: Sequence[str] = FIXTURES, max_calls: int = 3, no_retry: bool = True, credential_available: Callable[[], bool] | None = None, provider_call: Callable[[Mapping[str, Any]], dict[str, Any]] | None = None) -> dict[str, Any]:
    selected = tuple(fixtures)
    if not actual:
        return {"exit_code": EXIT["ok"], "provider_calls": 0, "results": []}
    if model != DEFAULT_MODEL or not no_retry or selected not in _ALLOWED_FIXTURE_SETS or max_calls != len(selected):
        return {"exit_code": EXIT["usage"], "provider_calls": 0, "results": []}
    if credential_available is None or not credential_available():
        return {"exit_code": EXIT["credential"], "provider_calls": 0, "results": []}
    if provider_call is None:
        return {"exit_code": EXIT["blocked"], "provider_calls": 0, "results": []}
    results: list[dict[str, Any]] = []
    for fixture_id in selected:
        prepared = _prepared(fixture_id)
        payload = build_provider_recommendation_payload(prepared_cycle=prepared)
        if prepared.get("status") != "ready" or not isinstance(payload, Mapping) or "status" in payload or not _fixture_contract_valid(fixture_id, payload):
            return {"exit_code": EXIT["blocked"], "provider_calls": len(results), "fixture_id": fixture_id, "failure_category": "fixture_preparation_failure", "results": results}
        expected = _expected_rank_one(payload)
        if expected is None:
            return {"exit_code": EXIT["blocked"], "provider_calls": len(results), "fixture_id": fixture_id, "failure_category": "ranking_contract_failure", "results": results}
        try:
            response = provider_call(payload)
        except Exception as error:
            code = getattr(error, "code", "provider_failure")
            diagnostic = code if isinstance(code, str) and code in SAFE_PROVIDER_DIAGNOSTIC_CODES else "provider_unknown_failure"
            safe_context = sanitize_provider_failure_context(getattr(error, "safe_context", None))
            result = {"exit_code": EXIT["provider"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": "provider_failure", "diagnostic": diagnostic, "results": results}
            if safe_context:
                result["provider_diagnostic"] = safe_context
            return result
        if not isinstance(response, dict):
            return {"exit_code": EXIT["parse"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": "structured_response_parse_failure", "results": results}
        completed = complete_recommendation_cycle(prepared_cycle=prepared, response_payload=response)
        if completed.get("status") != "resolved":
            errors = completed.get("errors") if isinstance(completed.get("errors"), list) else []
            category = "grounding_structural_failure" if any(str(error).startswith("grounding_") for error in errors) else "grounding_semantic_failure"
            return {"exit_code": EXIT["structural"] if category == "grounding_structural_failure" else EXIT["semantic"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": category, "diagnostic": next((error for error in errors if isinstance(error, str)), "validation_failed"), "results": results}
        if not _completed_candidate_evidence_isolated(payload=payload, completed=completed):
            return {"exit_code": EXIT["semantic"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": "multi_candidate_evidence_mixed", "diagnostic": "multi_candidate_evidence_mixed", "results": results}
        if not _presentation_contract_valid(fixture_id=fixture_id, completed=completed):
            return {"exit_code": EXIT["semantic"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": "presentation_contract_invalid", "diagnostic": "presentation_contract_invalid", "results": results}
        recommendation = completed.get("recommendation_result")
        if not isinstance(recommendation, Mapping) or (recommendation.get("recommended_move"), recommendation.get("recommended_slot_index")) != expected:
            return {"exit_code": EXIT["semantic"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": "ranking_selection_mismatch", "diagnostic": "ranking_selection_mismatch", "results": results}
        results.append({"fixture_id": fixture_id, "status": "passed"})
    return {"exit_code": EXIT["ok"], "provider_calls": len(results), "results": results}


def _surface(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: result[key] for key in ("fixture_id", "failure_category", "diagnostic", "provider_diagnostic", "exit_code", "provider_calls") if key in result}


def main(argv: Sequence[str] | None = None, *, adapter_factory: Callable[..., tuple[Callable[[], bool], Callable[[Mapping[str, Any]], dict[str, Any]]]] = _actual_adapters) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--actual", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--fixtures", nargs="*")
    parser.add_argument("--max-calls", type=int)
    parser.add_argument("--no-retry", action="store_true")
    args, _ = parser.parse_known_args(argv)
    kwargs: dict[str, Any] = {"actual": args.actual, "model": args.model, "fixtures": tuple(args.fixtures or FIXTURES), "max_calls": args.max_calls or 3, "no_retry": args.no_retry}
    if args.actual and args.model == DEFAULT_MODEL and args.no_retry:
        credential, provider = adapter_factory(model=args.model)
        kwargs.update(credential_available=credential, provider_call=provider)
    result = run_smoke(**kwargs)
    print(json.dumps(_surface(result), separators=(",", ":")))
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
