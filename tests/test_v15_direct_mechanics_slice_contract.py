from copy import deepcopy

from llm.advisor_candidate_contract import build_recommendation_presentation_model, complete_recommendation_cycle, prepare_ui_recommendation_cycle
from llm.advisor_client import format_recommendation_presentation_text
from llm.advisor_direct_mechanics import evaluate_direct_damage_mechanics
from llm.advisor_recommendation_readiness import build_recommendation_readiness
from llm.advisor_turn_snapshot import (
    BASE_STAT_KEYS,
    build_request_start_recommendation_snapshot,
    build_snapshot_damage_input,
    build_snapshot_stat_provenance,
    capture_ui_current_state_provenance,
)
from core.cache_manager import CacheManager
from core.ko_mapping_loader import KoMappingLoader
from core.move_repository import MoveRepository
from core.pokemon_repository import PokemonRepository


class _Species:
    def get(self, name):
        return {"en": name, "types_en": ["normal"], "base_stats": {key: 80 for key in BASE_STAT_KEYS}}


def _provenance(side, slot, pokemon):
    return {"side": side, "slot_index": slot, "pokemon_id": pokemon, "session_id": "s", "source": "user_confirmed_final_battle_stat", "trust": "user_confirmed_current"}


def _direct_context(*, generation="gen9"):
    absent = {"status": "known_absent"}
    side = {"ability": absent, "item": absent, "boosts": {key: 0 for key in BASE_STAT_KEYS if key != "hp"}, "current_hp": 100, "max_hp": 100, "status": absent}
    return {"generation": generation, "attacker": deepcopy(side), "defender": deepcopy(side), "field": {"weather": absent, "terrain": absent}}


def _battle(*, direct=True, self_pokemon="pikachu", opponent_pokemon="eevee", self_slot=0, opponent_slot=1):
    entries = []
    for side, pokemon, slot in (("self", self_pokemon, self_slot), ("opponent", opponent_pokemon, opponent_slot)):
        entries.extend({"side": side, "stat": key, "value": 100 + index, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "provenance": _provenance(side, slot, pokemon)} for index, key in enumerate(BASE_STAT_KEYS))
    battle = {"current_state_session_id": "s", "pokemon": {"my_active": {"name_en": self_pokemon, "slot_index": self_slot}, "opponent_active": {"name_en": opponent_pokemon, "slot_index": opponent_slot}}, "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]}, "final_stat_context": {"current_final_stats": entries}, "trusted_level_context": {"current_levels": [{"side": "self", "value": 50, "provenance": {**_provenance("self", self_slot, self_pokemon), "source": "user_confirmed_current_level"}}]}}
    if direct:
        battle["direct_mechanics_context"] = _direct_context()
    return battle


def _direct_result(battle):
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("tackle",))
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="tackle", selectable_moves=("tackle",), move_metadata={"category": "physical", "power": 40, "type": "normal"})
    return evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)


def _modifier_result(*, category="physical", move_type="normal", move_id="tackle", power=40, min_hits=None, max_hits=None, weather=None, conditions=None, side_effects=None, battle_format=None, ability=None, item=None, defender_item=None, defender_ability=None, defender_types=None, attacker_current_hp=None, attacker_max_hp=None, defender_current_hp=None, stages=None, is_critical=False):
    """Exercise only the frozen request-start modifier authority inputs."""
    battle = _battle()
    battle["moves"]["my_available_moves"][0]["move_id"] = move_id
    if item is not None:
        if item == "unknown":
            battle["item_profiles"] = {"my_active": {"status": "unknown", "source": "user_unconfirmed", "item_id": None}}
        elif item == "system_default":
            battle["item_profiles"] = {"my_active": {"status": "system_default_none", "source": "system_default", "item_id": None}}
        elif item == "none":
            battle["item_profiles"] = {"my_active": {"status": "none", "source": "user_input", "item_id": None}}
        else:
            battle["item_profiles"] = {"my_active": {"status": "user_confirmed", "source": "user_input", "item_id": item}}
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=(move_id,))
    metadata = {"category": category, "power": power, "type": move_type}
    if min_hits is not None: metadata.update(min_hits=min_hits, max_hits=max_hits)
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id=move_id, selectable_moves=(move_id,), move_metadata=metadata)
    current = damage["battle_context"]["current_state"]
    if attacker_current_hp is not None:
        current["direct_mechanics_context"]["attacker"]["current_hp"] = attacker_current_hp
    if attacker_max_hp is not None:
        current["direct_mechanics_context"]["attacker"]["max_hp"] = attacker_max_hp
    if defender_current_hp is not None:
        current["direct_mechanics_context"]["defender"]["current_hp"] = defender_current_hp
    if weather is not None or side_effects is not None:
        current["field_state_context"] = {"current_field": {"weather": weather, "side_effects": side_effects}}
    if conditions is not None:
        current["condition_context"] = {"current_conditions": conditions}
    if battle_format is not None:
        current["battle_format_context"] = {"current_battle_format": {"battle_format": battle_format}}
    if ability == "unknown":
        current["direct_mechanics_context"]["attacker"]["ability"] = {"status": "unknown"}
    elif ability is not None:
        current["ability_context"] = {"current_abilities": [{"side": "self", "ability": ability}]}
    if defender_ability is not None:
        entries = current.setdefault("ability_context", {}).setdefault("current_abilities", [])
        entries.append({"side": "opponent", "ability": defender_ability})
    if stages is not None:
        current["stat_stage_context"] = {"current_stages": [{"side": side, "stat": stat, "stage": stage, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"} for side, stat, stage in stages]}
    provenance = build_snapshot_stat_provenance(snapshot, species_repository=_Species())
    if defender_types is not None:
        provenance["defender"]["types"] = {"available": True, "value": defender_types}
    if defender_item is not None:
        provenance["defender"]["known_item"] = {"status": "unknown", "profile_source": "frozen_candidate_item_authority"} if defender_item == "unknown" else {"status": "known", "value": defender_item}
    return evaluate_direct_damage_mechanics(damage, stat_provenance=provenance, trusted_level=50, is_critical=is_critical)


def test_complete_direct_input_returns_native_damage_type_and_ko_result():
    result = _direct_result(_battle())
    assert result["status"] == "known"
    assert result["move"] == "tackle"
    assert result["type_effectiveness"] == 1.0
    assert result["damage_range"]["minimum"] <= result["damage_range"]["maximum"]
    assert result["ko_result"]["status"] == "resolved"
    assert result["mechanics_source"] == "native_q12_direct_damage"
    assert result["generation"] == "gen9"


def test_incomplete_or_unsupported_direct_input_never_receives_defaults():
    missing_generation = _battle()
    missing_generation["direct_mechanics_context"].pop("generation")
    result = _direct_result(missing_generation)
    assert result["status"] == "insufficient_context"
    assert result["missing_inputs"] == ["generation"]
    assert result["damage_range"] is None and result["ko_result"] is None

    missing = _battle()
    missing["direct_mechanics_context"]["defender"]["item"] = {"status": "unknown"}
    result = _direct_result(missing)
    assert result["status"] == "insufficient_context"
    assert result["missing_inputs"] == ["defender.item"]

    for path, expected in (("ability", "attacker.ability"), ("boosts", "attacker.boosts"), ("current_hp", "attacker.current_hp"), ("max_hp", "attacker.max_hp")):
        incomplete = _battle()
        incomplete["direct_mechanics_context"]["attacker"].pop(path)
        result = _direct_result(incomplete)
        assert result["status"] == "insufficient_context"
        assert expected in result["missing_inputs"]

    snapshot = build_request_start_recommendation_snapshot(_battle(), selectable_moves=("tackle",))
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="tackle", selectable_moves=("tackle",), move_metadata={"category": "physical", "power": 40, "type": "normal"})
    provenance = build_snapshot_stat_provenance(snapshot, species_repository=_Species())
    provenance["attacker"]["final_stats"] = {"available": False, "value": None}
    result = evaluate_direct_damage_mechanics(damage, stat_provenance=provenance, trusted_level=50)
    assert result["status"] == "insufficient_context"
    assert "attacker.final_stats" in result["missing_inputs"]

    unsupported = _battle()
    snapshot = build_request_start_recommendation_snapshot(unsupported, selectable_moves=("tackle",))
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="tackle", selectable_moves=("tackle",), move_metadata={"category": "status", "type": "normal"})
    result = evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)
    assert result["status"] == "unsupported_mechanic"
    assert result["unsupported_reason"] == "status_move"

    dynamic_battle = _battle()
    dynamic_battle["moves"]["my_available_moves"][0]["move_id"] = "electro-ball"
    dynamic = build_request_start_recommendation_snapshot(dynamic_battle, selectable_moves=("electro-ball",))
    damage = build_snapshot_damage_input(dynamic, candidate_slot_index=0, candidate_move_id="electro-ball", selectable_moves=("electro-ball",), move_metadata={"category": "special", "power": 1, "type": "electric"})
    result = evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(dynamic, species_repository=_Species()), trusted_level=50)
    assert result["status"] == "unsupported_mechanic"
    assert result["unsupported_reason"] == "dynamic_base_power"

    modifier = _battle()
    modifier["direct_mechanics_context"]["attacker"]["item"] = {"status": "known", "value": "choice-band"}
    result = _direct_result(modifier)
    assert result["status"] == "unsupported_mechanic"
    assert result["unsupported_reason"] == "item_modifier"


def test_ui_direct_mechanics_opt_in_projects_only_explicit_hp_and_keeps_item_unknown():
    battle = _battle(direct=False)
    battle["request_native_direct_mechanics"] = True
    battle["current_hp_confirmations"] = [
        {"side": "self", "current_hp": 90, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp"},
        {"side": "opponent", "current_hp": 80, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp"},
    ]

    captured = capture_ui_current_state_provenance(battle, session_id="s")
    direct = captured["direct_mechanics_context"]
    assert direct["generation"] == "gen9"
    assert direct["attacker"]["current_hp"] == 90
    assert direct["defender"]["current_hp"] == 80
    assert "item" not in direct["attacker"]

    snapshot = build_request_start_recommendation_snapshot(captured, selectable_moves=("tackle",))
    damage = build_snapshot_damage_input(
        snapshot, candidate_slot_index=0, candidate_move_id="tackle",
        selectable_moves=("tackle",), move_metadata={"category": "physical", "power": 40, "type": "normal"},
    )
    result = evaluate_direct_damage_mechanics(
        damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50,
    )
    assert result["status"] == "insufficient_context"
    assert result["mechanics_source"] == "native_q12_direct_damage"
    assert "attacker.item" in result["missing_inputs"]
    readiness = build_recommendation_readiness(
        prepared_cycle={"status": "ready", "candidates": [{"mechanics_result": result}]}
    )
    assert {entry["path"] for entry in readiness["missing"]} >= {"attacker.item"}
    assert readiness["action"] == "current_item"


def test_cached_thunderbolt_priority_reaches_native_q12_and_preserves_item_readiness() -> None:
    battle = _battle()
    battle["moves"]["my_available_moves"][0]["move_id"] = "thunderbolt"
    battle["direct_mechanics_context"]["attacker"]["item"] = {"status": "unknown"}
    repository = MoveRepository(CacheManager(), KoMappingLoader())

    prepared = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "thunderbolt"}], battle_input=battle,
        move_repository=repository, species_repository=_Species(),
    )
    candidate = prepared["candidates"][0]

    assert repository.get("thunderbolt").priority == 0
    assert candidate["status"] == "partial"
    assert candidate["action_order"]["missing_inputs"] == ["opponent_action"]
    assert "self_move_priority" not in candidate["action_order"]["missing_inputs"]
    assert candidate["q12_damage"]["status"] == "resolved"
    assert candidate["mechanics_result"]["status"] == "insufficient_context"
    assert candidate["mechanics_result"]["mechanics_source"] == "native_q12_direct_damage"
    assert candidate["mechanics_result"]["missing_inputs"] == ["attacker.item"]
    readiness = build_recommendation_readiness(prepared_cycle=prepared)
    assert {entry["path"] for entry in readiness["missing"]} >= {"attacker.item"}
    assert readiness["action"] == "current_item"


def test_repository_backed_pikachu_arcanine_thunderbolt_fixture_reaches_item_readiness() -> None:
    """Keep the production-cache smoke fixture identity-bound and deterministic."""
    battle = _battle(opponent_pokemon="arcanine", opponent_slot=0)
    battle["moves"]["my_available_moves"][0]["move_id"] = "thunderbolt"
    battle["direct_mechanics_context"]["attacker"]["item"] = {"status": "unknown"}
    cache, loader = CacheManager(), KoMappingLoader()

    prepared = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "thunderbolt"}], battle_input=battle,
        move_repository=MoveRepository(cache, loader), species_repository=PokemonRepository(cache, loader),
    )
    candidate = prepared["candidates"][0]

    assert prepared["status"] == "ready"
    assert candidate["status"] == "partial"
    assert candidate["q12_damage"]["status"] == "resolved"
    assert candidate["mechanics_result"]["missing_inputs"] == ["attacker.item"]
    readiness = build_recommendation_readiness(prepared_cycle=prepared)
    assert {entry["path"] for entry in readiness["missing"]} >= {"attacker.item"}
    assert readiness["action"] == "current_item"

    battle["pokemon"]["opponent_active"]["name_en"] = "eevee"
    assert candidate["q12_damage"]["status"] == "resolved"

    stale = _battle(opponent_pokemon="arcanine", opponent_slot=0)
    stale["final_stat_context"]["current_final_stats"][-1]["provenance"]["pokemon_id"] = "eevee"
    rejected = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}], battle_input=stale,
        move_repository={"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}},
        species_repository=PokemonRepository(cache, loader),
    )
    assert rejected["candidates"][0]["q12_damage"]["status"] != "resolved"


def test_facade_consumes_exact_attacker_condition_in_native_direct_damage():
    condition = lambda value: {
        "side": "self", "condition_type": value, "status": "user_confirmed",
        "source": "user_confirmed_current_condition", "confidence": "known",
    }
    normal = _modifier_result(move_id="facade", power=70, conditions=[condition("none")])
    burn = _modifier_result(move_id="facade", power=70, conditions=[condition("burn")])
    poison = _modifier_result(move_id="facade", power=70, conditions=[condition("poison")])
    assert normal["status"] == burn["status"] == poison["status"] == "known"
    assert normal["dynamic_power_evidence"]["effective_power"] == 70
    assert burn["dynamic_power_evidence"] == {
        "status": "known", "mechanic": "facade", "attacker_condition": "burn",
        "effective_power": 140, "burn_attack_reduction_ignored": True, "missing_inputs": [],
    }
    assert poison["dynamic_power_evidence"]["effective_power"] == 140
    assert burn["damage_range"]["maximum"] == poison["damage_range"]["maximum"]
    assert burn["damage_range"]["maximum"] > normal["damage_range"]["maximum"]

    missing = _modifier_result(move_id="facade", power=70)
    assert missing["status"] == "insufficient_context" and "attacker.condition" in missing["missing_inputs"]
    malformed = _modifier_result(move_id="facade", power=70, conditions=[{"side": "self", "condition_type": "burn"}])
    assert malformed["status"] == "unsupported_mechanic" and malformed["unsupported_reason"] == "facade_condition_context"


def test_current_hp_proportional_moves_consume_exact_attacker_hp_in_native_direct_damage():
    def resolve(move, type_, current_hp):
        battle = _battle()
        battle["moves"]["my_available_moves"][0]["move_id"] = move
        snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=(move,))
        damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id=move, selectable_moves=(move,), move_metadata={"category": "special", "power": 150, "type": type_})
        current = damage["battle_context"]["current_state"]
        current["direct_mechanics_context"]["attacker"].update(current_hp=current_hp, max_hp=100)
        current["field_state_context"] = {"current_field": {"weather": "none", "terrain": "none", "side_effects": []}}
        return evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)

    full = resolve("eruption", "fire", 100)
    half = resolve("eruption", "fire", 50)
    water = resolve("water-spout", "water", 50)
    dragon = resolve("dragon-energy", "dragon", 50)
    assert full["status"] == half["status"] == water["status"] == dragon["status"] == "known"
    assert full["dynamic_power_evidence"]["effective_power"] == 150
    assert half["dynamic_power_evidence"] == {
        "status": "known", "mechanic": "current_hp_proportional_power", "move": "eruption",
        "attacker_current_hp": 50, "attacker_maximum_hp": 100, "effective_power": 75,
        "rule": "current-hp-proportional-150", "missing_inputs": [],
    }
    assert water["dynamic_power_evidence"]["effective_power"] == dragon["dynamic_power_evidence"]["effective_power"] == 75
    assert full["damage_range"]["maximum"] > half["damage_range"]["maximum"]


def test_brine_consumes_exact_defender_hp_in_native_direct_damage():
    def resolve(current_hp):
        battle = _battle()
        battle["moves"]["my_available_moves"][0]["move_id"] = "brine"
        snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("brine",))
        damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="brine", selectable_moves=("brine",), move_metadata={"category": "special", "power": 65, "type": "water"})
        current = damage["battle_context"]["current_state"]
        current["direct_mechanics_context"]["defender"].update(current_hp=current_hp, max_hp=200)
        current["field_state_context"] = {"current_field": {"weather": "none", "terrain": "none", "side_effects": []}}
        return evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)

    above_half = resolve(101)
    at_half = resolve(100)
    below_half = resolve(99)
    assert above_half["status"] == at_half["status"] == below_half["status"] == "known"
    assert above_half["dynamic_power_evidence"] == {
        "status": "known", "mechanic": "brine", "defender_current_hp": 101,
        "defender_maximum_hp": 200, "condition_met": False, "effective_power": 65,
        "rule": "opponent-half-hp-or-less-doubles-power", "missing_inputs": [],
    }
    assert at_half["dynamic_power_evidence"]["effective_power"] == below_half["dynamic_power_evidence"]["effective_power"] == 130
    assert at_half["damage_range"]["maximum"] > above_half["damage_range"]["maximum"]


def test_hex_and_venoshock_consume_exact_defender_condition_in_native_direct_damage():
    def condition(value):
        return {
            "side": "opponent", "condition_type": value, "status": "user_confirmed",
            "source": "user_confirmed_current_condition", "confidence": "known",
        }

    hex_normal = _modifier_result(category="special", move_type="ghost", move_id="hex", power=65, conditions=[condition("none")], defender_types=["water"])
    hex_burn = _modifier_result(category="special", move_type="ghost", move_id="hex", power=65, conditions=[condition("burn")], defender_types=["water"])
    venoshock_burn = _modifier_result(category="special", move_type="poison", move_id="venoshock", power=65, conditions=[condition("burn")])
    venoshock_poison = _modifier_result(category="special", move_type="poison", move_id="venoshock", power=65, conditions=[condition("poison")])
    assert hex_normal["status"] == hex_burn["status"] == venoshock_burn["status"] == venoshock_poison["status"] == "known"
    assert hex_normal["dynamic_power_evidence"]["effective_power"] == venoshock_burn["dynamic_power_evidence"]["effective_power"] == 65
    assert hex_burn["dynamic_power_evidence"] == {
        "status": "known", "mechanic": "status_condition_power", "move": "hex",
        "defender_condition": "burn", "condition_met": True, "effective_power": 130,
        "rule": "defender-major-status-doubles-power", "missing_inputs": [],
    }
    assert venoshock_poison["dynamic_power_evidence"]["effective_power"] == 130
    assert hex_burn["damage_range"]["maximum"] > hex_normal["damage_range"]["maximum"]
    assert venoshock_poison["damage_range"]["maximum"] > venoshock_burn["damage_range"]["maximum"]

    missing = _modifier_result(category="special", move_type="ghost", move_id="hex", power=65)
    assert missing["status"] == "insufficient_context" and "defender.condition" in missing["missing_inputs"]
    malformed = _modifier_result(category="special", move_type="ghost", move_id="hex", power=65, conditions=[{"side": "opponent", "condition_type": "burn"}])
    assert malformed["status"] == "unsupported_mechanic" and malformed["unsupported_reason"] == "status_condition_power_context"


def test_weather_ball_and_terrain_pulse_consume_trusted_field_and_groundedness():
    def resolve(move, field, grounded=None):
        battle = _battle()
        battle["moves"]["my_available_moves"][0]["move_id"] = move
        snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=(move,))
        damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id=move, selectable_moves=(move,), move_metadata={"category": "special", "power": 50, "type": "normal"})
        current = damage["battle_context"]["current_state"]
        current["field_state_context"] = {"current_field": field}
        if grounded is not None:
            current["grounded_context"] = {"self": grounded}
        return evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)

    sun = {"weather": "sun", "terrain": "none", "global_effects": [], "side_effects": [], "status": "user_confirmed", "source": "user_confirmed_current_field_state", "confidence": "known"}
    electric = {**sun, "weather": "none", "terrain": "electric"}
    weather_ball = resolve("weather-ball", sun)
    grounded_pulse = resolve("terrain-pulse", electric, {"status": "known_grounded", "provenance": "user_confirmed_current"})
    ungrounded_pulse = resolve("terrain-pulse", electric, {"status": "known_ungrounded", "provenance": "user_confirmed_current"})
    assert weather_ball["status"] == grounded_pulse["status"] == ungrounded_pulse["status"] == "known"
    assert weather_ball["dynamic_power_evidence"] == {
        "status": "known", "mechanic": "environment_transformation", "move": "weather-ball",
        "weather": "sun", "effective_type": "fire", "effective_power": 100, "transformed": True,
        "rule": "weather-ball-current-weather", "missing_inputs": [],
    }
    assert grounded_pulse["dynamic_power_evidence"]["effective_type"] == "electric"
    assert grounded_pulse["dynamic_power_evidence"]["effective_power"] == 100
    assert ungrounded_pulse["dynamic_power_evidence"]["effective_type"] == "normal"
    assert ungrounded_pulse["dynamic_power_evidence"]["effective_power"] == 50
    assert "sun_fire_boost" in weather_ball["applied_damage_modifiers"]
    assert "terrain_electric_boost" in grounded_pulse["applied_damage_modifiers"]
    assert grounded_pulse["damage_range"]["maximum"] > ungrounded_pulse["damage_range"]["maximum"]

    missing = resolve("terrain-pulse", electric)
    assert missing["status"] == "insufficient_context" and "self.grounded" in missing["missing_inputs"]
    unknown = resolve("weather-ball", {**sun, "weather": "unknown"})
    assert unknown["status"] == "insufficient_context" and "field.weather" in unknown["missing_inputs"]
    malformed = resolve("weather-ball", {"weather": "sun"})
    assert malformed["status"] == "unsupported_mechanic" and malformed["unsupported_reason"] == "environment_transformation_context"


def test_type_effectiveness_covers_super_effective_and_immunity():
    class Types:
        def get(self, name):
            types = {"pikachu": ["electric"], "eevee": ["water"], "gengar": ["ghost"]}
            return {"en": name, "types_en": types[name], "base_stats": {key: 80 for key in BASE_STAT_KEYS}}

    battle = _battle()
    result = _direct_result(battle)
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("tackle",))
    super_damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="tackle", selectable_moves=("tackle",), move_metadata={"category": "special", "power": 40, "type": "electric"})
    super_result = evaluate_direct_damage_mechanics(super_damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=Types()), trusted_level=50)
    assert result["type_effectiveness"] == 1.0
    assert super_result["type_effectiveness"] == 2.0

    immune_battle = _battle()
    immune_battle["pokemon"]["opponent_active"]["name_en"] = "gengar"
    for entry in immune_battle["final_stat_context"]["current_final_stats"]:
        if entry["side"] == "opponent":
            entry["provenance"]["pokemon_id"] = "gengar"
    immune_snapshot = build_request_start_recommendation_snapshot(immune_battle, selectable_moves=("tackle",))
    immune_damage = build_snapshot_damage_input(immune_snapshot, candidate_slot_index=0, candidate_move_id="tackle", selectable_moves=("tackle",), move_metadata={"category": "physical", "power": 40, "type": "normal"})
    immune_result = evaluate_direct_damage_mechanics(immune_damage, stat_provenance=build_snapshot_stat_provenance(immune_snapshot, species_repository=Types()), trusted_level=50)
    assert immune_result["type_effectiveness"] == 0.0
    assert immune_result["damage_range"] == {"minimum": 0, "maximum": 0}


def test_mechanics_result_reaches_provider_candidate_without_snapshot_or_engine_raw_data():
    prepared = prepare_ui_recommendation_cycle(selected_moves=[{"move_id": "tackle"}], battle_input=_battle(), move_repository={"tackle": {"category": "physical", "power": 40, "type": "normal"}}, species_repository=_Species())
    candidate = prepared["candidates"][0]
    assert candidate["mechanics_result"]["status"] == "known"
    provider_result = prepared["recommendation_request"]["candidate_comparisons"][0]["mechanics_result"]
    assert candidate["mechanics_result"]["exact_damage_rolls"]
    assert provider_result == {
        key: value for key, value in candidate["mechanics_result"].items() if key != "exact_damage_rolls"
    }
    assert "damage_rolls" not in provider_result
    assert "exact_damage_rolls" not in provider_result
    assert "stat_provenance" not in provider_result


def test_fixed_two_hit_uses_exact_convolved_total_distribution_and_rejects_variable_hits():
    battle = _battle()
    battle["moves"]["my_available_moves"][0]["move_id"] = "double-hit"
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("double-hit",))
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="double-hit", selectable_moves=("double-hit",), move_metadata={"category": "physical", "power": 40, "type": "normal", "min_hits": 2, "max_hits": 2})
    result = evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)
    assert result["status"] == "known" and result["hit_count"] == 2
    assert result["per_hit_damage_range"]["maximum"] * 2 == result["damage_range"]["maximum"]
    assert result["per_hit_damage_range"]["minimum"] * 2 == result["damage_range"]["minimum"]
    assert result["ko_result"]["status"] == "resolved"
    variable = deepcopy(damage)
    variable["move"] = {"move_id": "variable", "category": "physical", "power": 40, "type": "normal", "min_hits": 2, "max_hits": 5}
    unsupported = evaluate_direct_damage_mechanics(variable, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)
    assert unsupported["status"] == "unsupported_mechanic" and unsupported["unsupported_reason"] == "variable_multi_hit_move"


def test_level_based_fixed_damage_uses_only_trusted_level_target_hp_and_canonical_identity():
    battle = _battle()
    battle["moves"]["my_available_moves"][0]["move_id"] = "seismic-toss"
    battle["direct_mechanics_context"]["defender"].update(current_hp=50, max_hp=200)
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("seismic-toss",))
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="seismic-toss", selectable_moves=("seismic-toss",), move_metadata={"category": "physical", "type": "normal"})
    provenance = build_snapshot_stat_provenance(snapshot, species_repository=_Species())
    provenance["attacker"]["final_stats"] = {"available": False, "value": None}
    result = evaluate_direct_damage_mechanics(damage, stat_provenance=provenance, trusted_level=50)
    assert result["status"] == "known" and result["damage_model"] == "level_based_fixed"
    assert result["fixed_damage"] == 50 and result["damage_range"] == {"minimum": 50, "maximum": 50}
    assert result["damage_percent_range"] == {"minimum": 25.0, "maximum": 25.0}
    assert result["ko_result"]["single_hit_probability"] == 1.0
    assert result["mechanics_source"] == "native_level_based_fixed_damage"


def test_level_based_fixed_damage_preserves_immunity_unknowns_and_unsupported_special_rules():
    class Types(_Species):
        def get(self, name):
            result = super().get(name)
            result["types_en"] = ["ghost"] if name == "eevee" else ["normal"]
            return result

    battle = _battle()
    battle["moves"]["my_available_moves"][0]["move_id"] = "seismic-toss"
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("seismic-toss",))
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="seismic-toss", selectable_moves=("seismic-toss",), move_metadata={"category": "physical", "type": "normal"})
    provenance = build_snapshot_stat_provenance(snapshot, species_repository=Types())
    immune = evaluate_direct_damage_mechanics(damage, stat_provenance=provenance, trusted_level=50)
    assert immune["status"] == "known" and immune["fixed_damage"] == 0 and immune["type_effectiveness"] == 0.0
    assert immune["ko_result"]["single_hit_probability"] == 0.0
    assert evaluate_direct_damage_mechanics(damage, stat_provenance=provenance, trusted_level=None)["missing_inputs"] == ["attacker.level"]
    unknown_hp = deepcopy(damage)
    unknown_hp["battle_context"]["current_state"]["direct_mechanics_context"]["defender"].pop("current_hp")
    assert "defender.current_hp" in evaluate_direct_damage_mechanics(unknown_hp, stat_provenance=provenance, trusted_level=50)["missing_inputs"]
    unknown_max_hp = deepcopy(damage)
    unknown_max_hp["battle_context"]["current_state"]["direct_mechanics_context"]["defender"].pop("max_hp")
    assert "defender.max_hp" in evaluate_direct_damage_mechanics(unknown_max_hp, stat_provenance=provenance, trusted_level=50)["missing_inputs"]
    unsupported = deepcopy(damage)
    unsupported["move"] = {"move_id": "psywave", "category": "special", "power": 1, "type": "psychic"}
    result = evaluate_direct_damage_mechanics(unsupported, stat_provenance=provenance, trusted_level=50)
    assert result["status"] == "unsupported_mechanic" and result["unsupported_reason"] == "unsupported_fixed_damage_rule"


def test_level_based_fixed_damage_reaches_candidate_comparison_result_and_presentation():
    battle = _battle()
    battle["moves"]["my_available_moves"] = [{"slot_index": 0, "move_id": "seismic-toss"}, {"slot_index": 1, "move_id": "tackle"}]
    battle["direct_mechanics_context"]["defender"].update(current_hp=50, max_hp=200)
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "seismic-toss"}, {"move_id": "tackle"}], battle_input=battle,
        move_repository={"seismic-toss": {"category": "physical", "type": "normal", "priority": 0}, "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}, species_repository=_Species(),
    )
    assert prepared["status"] == "ready"
    rows = prepared["recommendation_request"]["candidate_comparisons"]
    assert rows[0]["mechanics_result"]["damage_model"] == "level_based_fixed"
    assert rows[0]["mechanics_comparison"]["rank"] == 1
    completed = complete_recommendation_cycle(prepared_cycle=prepared, response_payload={"recommendation_status": "resolved", "selected_candidate_id": 0, "explanation_code": "clear_ranked_winner"})
    assert completed["recommendation_result"]["selected_action"] == {"slot_index": 0, "move": "seismic-toss"}
    text = format_recommendation_presentation_text(presentation_model=build_recommendation_presentation_model(completed_cycle=completed))
    assert "피해 방식: 사용자 레벨과 동일한 고정 피해" in text and "고정 피해: 50" in text


def test_level_based_fixed_damage_and_fixed_hit_remain_distinct_candidate_models():
    battle = _battle()
    battle["moves"]["my_available_moves"] = [{"slot_index": 0, "move_id": "seismic-toss"}, {"slot_index": 1, "move_id": "double-hit"}]
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "seismic-toss"}, {"move_id": "double-hit"}], battle_input=battle,
        move_repository={"seismic-toss": {"category": "physical", "type": "normal", "priority": 0}, "double-hit": {"category": "physical", "power": 40, "type": "normal", "min_hits": 2, "max_hits": 2, "priority": 0}}, species_repository=_Species(),
    )
    rows = prepared["recommendation_request"]["candidate_comparisons"]
    assert [row["mechanics_result"]["damage_model"] for row in rows] == ["level_based_fixed", "fixed_hit_formula"]
    assert rows[0]["mechanics_result"]["per_hit_damage_range"] is None
    assert isinstance(rows[1]["mechanics_result"]["per_hit_damage_range"], dict)


def test_known_weather_and_burn_use_native_q12_hooks_without_defaults():
    baseline_water = _modifier_result(category="special", move_type="water", weather="none", side_effects=[])
    rain_water = _modifier_result(category="special", move_type="water", weather="rain", side_effects=[])
    rain_fire = _modifier_result(category="special", move_type="fire", weather="rain", side_effects=[])
    sun_fire = _modifier_result(category="special", move_type="fire", weather="sun", side_effects=[])
    sun_water = _modifier_result(category="special", move_type="water", weather="sun", side_effects=[])
    assert rain_water["status"] == sun_fire["status"] == "known"
    assert rain_water["damage_range"]["maximum"] > baseline_water["damage_range"]["maximum"]
    assert rain_fire["damage_range"]["maximum"] < sun_fire["damage_range"]["maximum"]
    assert sun_water["damage_range"]["maximum"] < baseline_water["damage_range"]["maximum"]
    assert "rain_water_boost" in rain_water["applied_damage_modifiers"]
    assert "sun_fire_boost" in sun_fire["applied_damage_modifiers"]

    burned = [{"side": "self", "condition_type": "burn"}]
    physical = _modifier_result(weather="none", side_effects=[], conditions=burned)
    special = _modifier_result(category="special", weather="none", side_effects=[], conditions=burned)
    unburned = _modifier_result(weather="none", side_effects=[], conditions=[{"side": "self", "condition_type": "none"}])
    assert physical["damage_range"]["maximum"] < unburned["damage_range"]["maximum"]
    assert "burn_physical_reduction" in physical["applied_damage_modifiers"]
    assert special["status"] == "known" and "burn_physical_reduction" not in special["applied_damage_modifiers"]


def test_unknown_relevant_modifier_context_fails_closed_but_irrelevant_context_does_not():
    unknown_weather = _modifier_result(category="special", move_type="water", weather="unknown", side_effects=[])
    neutral_weather = _modifier_result(category="physical", move_type="normal", weather="unknown", side_effects=[], conditions=[{"side": "self", "condition_type": "none"}])
    unknown_burn = _modifier_result(weather="none", side_effects=[], conditions=[{"side": "opponent", "condition_type": "burn"}])
    special_unknown_burn = _modifier_result(category="special", weather="none", side_effects=[], conditions=[{"side": "opponent", "condition_type": "burn"}])
    assert unknown_weather["status"] == "insufficient_context" and "field.weather" in unknown_weather["missing_inputs"]
    assert neutral_weather["status"] == "known"
    assert unknown_burn["status"] == "insufficient_context" and "attacker.condition" in unknown_burn["missing_inputs"]
    assert special_unknown_burn["status"] == "known"


def test_sandstorm_and_snow_reuse_canonical_defender_weather_stat_modifiers():
    special_baseline = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, weather="none", side_effects=[], defender_types=["rock"])
    sandstorm = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, weather="sandstorm", side_effects=[], defender_types=["rock"])
    sandstorm_nonrock = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, weather="sandstorm", side_effects=[])
    physical_baseline = _modifier_result(category="physical", move_type="normal", move_id="tackle", power=60, weather="none", side_effects=[], conditions=[{"side": "self", "condition_type": "none"}], defender_types=["ice"])
    snow = _modifier_result(category="physical", move_type="normal", move_id="tackle", power=60, weather="snow", side_effects=[], conditions=[{"side": "self", "condition_type": "none"}], defender_types=["ice"])

    assert sandstorm["damage_range"]["maximum"] < special_baseline["damage_range"]["maximum"]
    assert sandstorm["applied_damage_modifiers"] == ["sandstorm_rock_special_defense_boost"]
    assert sandstorm_nonrock["applied_damage_modifiers"] == []
    assert snow["damage_range"]["maximum"] < physical_baseline["damage_range"]["maximum"]
    assert snow["applied_damage_modifiers"] == ["snow_ice_defense_boost"]
    missing_physical_condition = _modifier_result(weather="none", side_effects=[])
    assert missing_physical_condition["status"] == "insufficient_context"
    assert "attacker.condition" in missing_physical_condition["missing_inputs"]


def test_target_side_screens_require_explicit_ownership_and_known_singles():
    baseline = _modifier_result(weather="none", side_effects=[], conditions=[{"side": "self", "condition_type": "none"}])
    reflect = _modifier_result(weather="none", side_effects=[{"side": "opponent", "effect": "reflect"}], conditions=[{"side": "self", "condition_type": "none"}], battle_format="singles")
    self_reflect = _modifier_result(weather="none", side_effects=[{"side": "self", "effect": "reflect"}], conditions=[{"side": "self", "condition_type": "none"}])
    unknown_owner = _modifier_result(weather="none", side_effects=[{"effect": "reflect"}], conditions=[{"side": "self", "condition_type": "none"}])
    unknown_format = _modifier_result(weather="none", side_effects=[{"side": "opponent", "effect": "reflect"}], conditions=[{"side": "self", "condition_type": "none"}])
    doubles = _modifier_result(weather="none", side_effects=[{"side": "opponent", "effect": "reflect"}], conditions=[{"side": "self", "condition_type": "none"}], battle_format="doubles")
    special_baseline = _modifier_result(category="special", weather="none", side_effects=[])
    light_screen = _modifier_result(category="special", weather="none", side_effects=[{"side": "opponent", "effect": "light-screen"}], battle_format="singles")
    reflect_special = _modifier_result(category="special", weather="none", side_effects=[{"side": "opponent", "effect": "reflect"}])
    light_screen_physical = _modifier_result(weather="none", side_effects=[{"side": "opponent", "effect": "light-screen"}], conditions=[{"side": "self", "condition_type": "none"}])
    missing_effects = _modifier_result(weather="none", side_effects=None, conditions=[{"side": "self", "condition_type": "none"}])
    assert reflect["damage_range"]["maximum"] < baseline["damage_range"]["maximum"]
    assert "reflect_reduction" in reflect["applied_damage_modifiers"]
    assert self_reflect["damage_range"] == baseline["damage_range"]
    assert unknown_owner["status"] == "insufficient_context" and "target_side_conditions" in unknown_owner["missing_inputs"]
    assert unknown_format["status"] == "insufficient_context" and "battle_format" in unknown_format["missing_inputs"]
    assert doubles["status"] == "unsupported_mechanic" and doubles["unsupported_reason"] == "battle_format"
    assert light_screen["damage_range"]["maximum"] < special_baseline["damage_range"]["maximum"]
    assert light_screen["applied_damage_modifiers"] == ["light_screen_reduction"]
    assert reflect_special["damage_range"] == special_baseline["damage_range"]
    assert light_screen_physical["damage_range"] == baseline["damage_range"]
    assert missing_effects["status"] == "insufficient_context" and "target_side_conditions" in missing_effects["missing_inputs"]


def test_fixed_hit_keeps_modifier_per_hit_and_level_fixed_damage_ignores_them():
    fixed_hit = _modifier_result(move_id="double-hit", min_hits=2, max_hits=2, weather="rain", side_effects=[], conditions=[{"side": "self", "condition_type": "burn"}])
    assert fixed_hit["status"] == "known" and fixed_hit["hit_count"] == 2
    assert fixed_hit["damage_range"]["minimum"] == fixed_hit["per_hit_damage_range"]["minimum"] * 2
    assert "burn_physical_reduction" in fixed_hit["applied_damage_modifiers"]

    battle = _battle()
    battle["moves"]["my_available_moves"][0]["move_id"] = "seismic-toss"
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("seismic-toss",))
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="seismic-toss", selectable_moves=("seismic-toss",), move_metadata={"category": "physical", "type": "normal"})
    damage["battle_context"]["current_state"].update({"field_state_context": {"current_field": {"weather": "rain", "side_effects": [{"side": "opponent", "effect": "reflect"}]}}, "condition_context": {"current_conditions": [{"side": "self", "condition_type": "burn"}]}, "battle_format_context": {"current_battle_format": {"battle_format": "singles"}}})
    result = evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)
    assert result["status"] == "known" and result["fixed_damage"] == 50
    assert "applied_damage_modifiers" not in result


def test_weather_burn_and_screen_combine_only_from_one_request_start_snapshot():
    combined = _modifier_result(
        move_type="water", weather="rain",
        side_effects=[{"side": "opponent", "effect": "reflect"}],
        conditions=[{"side": "self", "condition_type": "burn"}], battle_format="singles",
    )
    assert combined["status"] == "known"
    assert combined["applied_damage_modifiers"] == [
        "rain_water_boost", "burn_physical_reduction", "reflect_reduction",
    ]


def test_known_ability_exception_remains_unsupported_instead_of_applying_burn():
    battle = _battle()
    battle["direct_mechanics_context"]["attacker"]["ability"] = {"status": "known", "value": "guts"}
    result = _direct_result(battle)
    assert result["status"] == "unsupported_mechanic"
    assert result["unsupported_reason"] == "ability_modifier"


def test_guts_request_start_conditions_apply_only_to_physical_attack_and_bypass_burn_penalty():
    conditions = ("burn", "paralysis", "poison", "toxic", "sleep", "freeze")
    baseline = _modifier_result(
        conditions=[{"side": "self", "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition"}],
    )
    for condition in conditions:
        result = _modifier_result(
            ability="guts",
            conditions=[{"side": "self", "condition_type": condition, "status": "user_confirmed", "source": "user_confirmed_current_condition"}],
        )
        assert result["status"] == "known", (condition, result)
        assert "ability_guts_status_attack_boost" in result["applied_damage_modifiers"]
        assert "burn_physical_reduction" not in result["applied_damage_modifiers"]
        assert result["damage_range"]["minimum"] > baseline["damage_range"]["minimum"]
        evidence = result["guts_status_attack_ability_evidence"]
        assert evidence["attacker_condition"] == condition
        assert evidence["condition_source"] == "runtime_strategy_d0_v1"
        assert evidence["modifier_q12"] == 6144

    special = _modifier_result(
        category="special", move_type="normal", move_id="swift", power=60, ability="guts",
        conditions=[{"side": "self", "condition_type": "burn", "status": "user_confirmed", "source": "user_confirmed_current_condition"}],
    )
    fixed = _modifier_result(
        category="physical", move_type="normal", move_id="seismic-toss", power=1, ability="guts",
        conditions=[{"side": "self", "condition_type": "burn", "status": "user_confirmed", "source": "user_confirmed_current_condition"}],
    )
    assert special["status"] == "known"
    assert "ability_guts_status_attack_boost" not in special["applied_damage_modifiers"]
    assert special["guts_status_attack_ability_evidence"]["physical_attack"] is False
    assert fixed["status"] == "known"
    assert fixed["mechanics_source"] == "native_level_based_fixed_damage"
    assert "guts_status_attack_ability_evidence" not in fixed


def test_guts_suppression_and_unknown_suppression_fail_closed():
    condition = [{"side": "self", "condition_type": "burn", "status": "user_confirmed", "source": "user_confirmed_current_condition"}]
    suppressed = _modifier_result(ability="guts", defender_ability="neutralizing-gas", conditions=condition)
    assert suppressed["status"] == "known"
    assert suppressed["applied_damage_modifiers"] == ["burn_physical_reduction"]
    assert suppressed["guts_status_attack_ability_evidence"]["suppression_status"] == "suppressed"
    assert suppressed["guts_status_attack_ability_evidence"]["modifier_q12"] == 4096

    unknown = _modifier_result(ability="guts", defender_ability="unknown", conditions=condition)
    assert unknown["status"] == "insufficient_context"
    assert "defender.ability" in unknown["missing_inputs"]


def test_full_hp_defender_multiscale_and_shadow_shield_use_existing_formula_reduction():
    baseline = _modifier_result(category="special", move_type="normal", move_id="swift", power=60)
    multiscale = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, defender_ability="multiscale")
    shadow_shield = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, defender_ability="shadow-shield")
    assert multiscale["status"] == shadow_shield["status"] == "known"
    assert multiscale["applied_damage_modifiers"] == ["defender_ability_multiscale_reduction"]
    assert shadow_shield["applied_damage_modifiers"] == ["defender_ability_shadow_shield_reduction"]
    assert multiscale["damage_range"]["maximum"] < baseline["damage_range"]["maximum"]
    assert shadow_shield["damage_range"] == multiscale["damage_range"]

    battle = _battle()
    battle["moves"]["my_available_moves"][0]["move_id"] = "swift"
    battle["direct_mechanics_context"]["defender"].update(current_hp=99, max_hp=100)
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("swift",))
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="swift", selectable_moves=("swift",), move_metadata={"category": "special", "power": 60, "type": "normal"})
    damage["battle_context"]["current_state"]["ability_context"] = {"current_abilities": [{"side": "opponent", "ability": "multiscale"}]}
    reduced_off = evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)
    assert reduced_off["status"] == "known"
    assert reduced_off["damage_range"] == baseline["damage_range"]


def test_exact_defender_assault_vest_reuses_canonical_special_defense_item_modifier():
    special = _modifier_result(category="special", move_type="normal", move_id="swift", power=60)
    vest = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, defender_item="assault-vest")
    physical = _modifier_result(category="physical", move_type="normal", move_id="tackle", power=60, defender_item="assault-vest")
    physical_baseline = _modifier_result(category="physical", move_type="normal", move_id="tackle", power=60)
    assert vest["status"] == "known"
    assert vest["applied_damage_modifiers"] == ["defender_item_assault_vest_special_defense"]
    assert vest["damage_range"]["maximum"] < special["damage_range"]["maximum"]
    assert physical["damage_range"] == physical_baseline["damage_range"]
    assert _modifier_result(category="special", move_type="normal", move_id="swift", power=60, defender_item="eviolite")["unsupported_reason"] == "defender_item_modifier"


def test_static_self_ability_boosts_use_canonical_move_conditions_only():
    baseline = _modifier_result(move_id="mach-punch")
    iron_fist = _modifier_result(move_id="mach-punch", ability="iron-fist")
    strong_jaw = _modifier_result(move_id="crunch", ability="strong-jaw")
    jaw_mismatch = _modifier_result(move_id="tackle", ability="strong-jaw")
    mega_launcher = _modifier_result(category="special", move_type="water", move_id="water-pulse", power=60, ability="mega-launcher", weather="none", side_effects=[])
    technician = _modifier_result(move_id="tackle", power=60, ability="technician")
    technician_mismatch = _modifier_result(move_id="tackle", power=61, ability="technician")
    assert iron_fist["damage_range"]["maximum"] > baseline["damage_range"]["maximum"]
    assert "ability_iron_fist_boost" in iron_fist["applied_damage_modifiers"]
    assert "ability_strong_jaw_boost" in strong_jaw["applied_damage_modifiers"]
    assert jaw_mismatch["status"] == "known" and "ability_strong_jaw_boost" not in jaw_mismatch["applied_damage_modifiers"]
    assert "ability_mega_launcher_boost" in mega_launcher["applied_damage_modifiers"]
    assert "ability_technician_boost" in technician["applied_damage_modifiers"]
    assert technician_mismatch["status"] == "known" and "ability_technician_boost" not in technician_mismatch["applied_damage_modifiers"]


def test_move_flag_offensive_abilities_are_production_reachable_through_strict_direct_gate():
    baseline_contact = _modifier_result(move_id="dragon-claw", power=80)
    tough_claws = _modifier_result(move_id="dragon-claw", power=80, ability="tough-claws")
    tough_claws_noncontact = _modifier_result(category="special", move_type="normal", move_id="hyper-voice", power=90, ability="tough-claws")
    reckless = _modifier_result(move_id="double-edge", power=120, ability="reckless")
    reckless_ineligible = _modifier_result(move_id="dragon-claw", power=80, ability="reckless")
    punk_rock = _modifier_result(category="special", move_type="normal", move_id="boomburst", power=140, ability="punk-rock")
    punk_rock_nonsound = _modifier_result(move_id="dragon-claw", power=80, ability="punk-rock")
    sheer_force = _modifier_result(move_id="iron-head", power=80, ability="sheer-force")
    sheer_force_ineligible = _modifier_result(move_id="dragon-claw", power=80, ability="sheer-force")
    sheer_force_life_orb = _modifier_result(move_id="iron-head", power=80, ability="sheer-force", item="life-orb")

    assert tough_claws["status"] == "known" and tough_claws["damage_range"]["maximum"] > baseline_contact["damage_range"]["maximum"]
    assert tough_claws["applied_damage_modifiers"] == ["ability_tough_claws_boost"]
    assert tough_claws_noncontact["status"] == "known" and tough_claws_noncontact["applied_damage_modifiers"] == []
    assert reckless["status"] == "known" and reckless["applied_damage_modifiers"] == ["ability_reckless_boost"]
    assert reckless_ineligible["status"] == "known" and reckless_ineligible["applied_damage_modifiers"] == []
    assert punk_rock["status"] == "known" and punk_rock["applied_damage_modifiers"] == ["ability_punk_rock_sound_boost"]
    assert punk_rock_nonsound["status"] == "known" and punk_rock_nonsound["applied_damage_modifiers"] == []
    assert sheer_force["status"] == "known" and sheer_force["applied_damage_modifiers"] == ["ability_sheer_force_secondary_boost"]
    assert sheer_force_ineligible["status"] == "known" and sheer_force_ineligible["applied_damage_modifiers"] == []
    assert sheer_force_life_orb["status"] == "known"
    assert sheer_force_life_orb["applied_damage_modifiers"] == ["ability_sheer_force_secondary_boost", "item_life_orb_boost"]


def test_low_hp_type_offensive_abilities_use_exact_request_start_hp_and_effective_type():
    cases = [
        ("blaze", "flamethrower", "fire", "ability_blaze_low_hp_fire_boost"),
        ("torrent", "water-gun", "water", "ability_torrent_low_hp_water_boost"),
        ("overgrow", "bullet-seed", "grass", "ability_overgrow_low_hp_grass_boost"),
        ("swarm", "bug-bite", "bug", "ability_swarm_low_hp_bug_boost"),
    ]
    for ability, move_id, move_type, tag in cases:
        active = _modifier_result(category="special", move_type=move_type, move_id=move_id, power=60, ability=ability, attacker_current_hp=33, attacker_max_hp=100, weather="none", side_effects=[])
        inactive = _modifier_result(category="special", move_type=move_type, move_id=move_id, power=60, ability=ability, attacker_current_hp=34, attacker_max_hp=100, weather="none", side_effects=[])
        wrong_type = _modifier_result(category="special", move_type="normal", move_id=move_id, power=60, ability=ability, attacker_current_hp=33, attacker_max_hp=100, weather="none", side_effects=[])

        assert active["status"] == "known"
        assert tag in active["applied_damage_modifiers"]
        assert active["low_hp_type_ability_evidence"]["threshold"]["active"] is True
        assert active["low_hp_type_ability_evidence"]["modifier_q12"] == 6144
        assert active["low_hp_type_ability_evidence"]["hp_source"] == "runtime_strategy_d0_v1"
        assert inactive["status"] == "known"
        assert tag not in inactive["applied_damage_modifiers"]
        assert inactive["low_hp_type_ability_evidence"]["threshold"]["active"] is False
        assert wrong_type["status"] == "known"
        assert tag not in wrong_type["applied_damage_modifiers"]
        assert wrong_type["low_hp_type_ability_evidence"]["type_matches"] is False


def test_low_hp_type_offensive_modifier_composes_with_life_orb_and_fixed_damage_stays_unboosted():
    boosted = _modifier_result(category="special", move_type="fire", move_id="flamethrower", power=60, ability="blaze", item="life-orb", attacker_current_hp=33, attacker_max_hp=100, weather="none", side_effects=[])
    fixed = _modifier_result(category="physical", move_type="fire", move_id="seismic-toss", power=1, ability="blaze", attacker_current_hp=33, attacker_max_hp=100)

    assert boosted["status"] == "known"
    assert boosted["applied_damage_modifiers"] == ["ability_blaze_low_hp_fire_boost", "item_life_orb_boost"]
    assert fixed["status"] == "known"
    assert fixed["mechanics_source"] == "native_level_based_fixed_damage"
    assert "low_hp_type_ability_evidence" not in fixed


def test_low_hp_type_offensive_ability_suppressed_by_exact_neutralizing_gas():
    suppressed = _modifier_result(category="special", move_type="fire", move_id="flamethrower", power=60, ability="blaze", defender_ability="neutralizing-gas", attacker_current_hp=33, attacker_max_hp=100, weather="none", side_effects=[])

    assert suppressed["status"] == "known"
    assert suppressed["applied_damage_modifiers"] == []


def test_move_flag_offensive_abilities_fail_closed_when_required_classification_is_unknown():
    for ability in ("tough-claws", "reckless", "punk-rock", "sheer-force"):
        result = _modifier_result(move_id="unmapped-move", power=80, ability=ability)
        assert result["status"] == "unsupported_mechanic"
        assert result["unsupported_reason"] == "move_flag_metadata"


def test_move_flag_offensive_ability_modifiers_preserve_critical_and_multihit_paths():
    critical = _modifier_result(move_id="dragon-claw", power=80, ability="tough-claws", is_critical=True)
    fixed_two_hit = _modifier_result(move_id="double-hit", power=35, min_hits=2, max_hits=2, ability="tough-claws")
    assert critical["status"] == "known"
    assert critical["applied_damage_modifiers"] == ["ability_tough_claws_boost"]
    assert fixed_two_hit["status"] == "known" and fixed_two_hit["hit_count"] == 2
    assert fixed_two_hit["applied_damage_modifiers"] == ["ability_tough_claws_boost"]


def test_ability_context_fails_closed_for_unknown_unsupported_and_missing_flag_metadata():
    unknown = _modifier_result(ability="unknown")
    unsupported = _modifier_result(ability="guts")
    missing_flags = _modifier_result(move_id="unmapped-move", ability="strong-jaw")
    assert unknown["status"] == "insufficient_context" and unknown["missing_inputs"] == ["attacker.ability"]
    assert unsupported["status"] == "unsupported_mechanic" and unsupported["unsupported_reason"] == "ability_modifier"
    assert missing_flags["status"] == "unsupported_mechanic" and missing_flags["unsupported_reason"] == "move_flag_metadata"


def test_ability_modifier_applies_per_fixed_hit_but_not_level_fixed_damage():
    baseline = _modifier_result(move_id="double-hit", min_hits=2, max_hits=2)
    technician = _modifier_result(move_id="double-hit", min_hits=2, max_hits=2, ability="technician")
    assert technician["status"] == "known" and technician["damage_range"]["maximum"] > baseline["damage_range"]["maximum"]
    assert technician["applied_damage_modifiers"] == ["ability_technician_boost"]

    battle = _battle()
    battle["moves"]["my_available_moves"][0]["move_id"] = "seismic-toss"
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("seismic-toss",))
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="seismic-toss", selectable_moves=("seismic-toss",), move_metadata={"category": "physical", "type": "normal"})
    damage["battle_context"]["current_state"]["ability_context"] = {"current_abilities": [{"side": "self", "ability": "iron-fist"}]}
    result = evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)
    assert result["status"] == "known" and result["fixed_damage"] == 50
    assert "applied_damage_modifiers" not in result


def test_static_ability_modifier_composes_with_known_weather_burn_screens_and_fixed_hits():
    weather = _modifier_result(
        category="special", move_type="water", move_id="water-pulse", power=60,
        ability="mega-launcher", weather="rain", side_effects=[],
    )
    burn_screen = _modifier_result(
        move_id="mach-punch", ability="iron-fist", weather="none",
        conditions=[{"side": "self", "condition_type": "burn"}],
        side_effects=[{"side": "opponent", "effect": "reflect"}], battle_format="singles",
    )
    fixed_hit = _modifier_result(
        move_id="double-hit", power=60, min_hits=2, max_hits=2, ability="technician",
        weather="none", side_effects=[], conditions=[{"side": "self", "condition_type": "none"}],
    )
    assert weather["applied_damage_modifiers"] == ["rain_water_boost", "ability_mega_launcher_boost"]
    assert burn_screen["applied_damage_modifiers"] == ["burn_physical_reduction", "reflect_reduction", "ability_iron_fist_boost"]
    assert fixed_hit["status"] == "known" and fixed_hit["hit_count"] == 2
    assert fixed_hit["applied_damage_modifiers"] == ["ability_technician_boost"]


def test_static_self_item_boosts_use_only_current_user_confirmed_item_authority():
    baseline = _modifier_result()
    life_orb = _modifier_result(item="life-orb")
    choice_band = _modifier_result(item="choice-band")
    choice_band_special = _modifier_result(category="special", item="choice-band")
    choice_specs = _modifier_result(category="special", item="choice-specs")
    muscle_band = _modifier_result(item="muscle-band")
    assert life_orb["damage_range"]["maximum"] > baseline["damage_range"]["maximum"]
    assert "item_life_orb_boost" in life_orb["applied_damage_modifiers"]
    assert "item_choice_band_boost" in choice_band["applied_damage_modifiers"]
    assert choice_band_special["status"] == "known" and "item_choice_band_boost" not in choice_band_special["applied_damage_modifiers"]
    assert "item_choice_specs_boost" in choice_specs["applied_damage_modifiers"]
    assert "item_muscle_band_boost" in muscle_band["applied_damage_modifiers"]


def test_item_authority_fails_closed_for_default_unknown_and_unsupported_profiles():
    unknown = _modifier_result(item="unknown")
    default = _modifier_result(item="system_default")
    no_item = _modifier_result(item="none")
    unsupported = _modifier_result(item="choice-scarf")
    excluded = _modifier_result(item="flame-plate")
    malformed = _modifier_result(item="not a canonical item")
    assert unknown["status"] == "insufficient_context" and unknown["missing_inputs"] == ["attacker.item"]
    assert default["status"] == "insufficient_context" and default["missing_inputs"] == ["attacker.item"]
    assert no_item["status"] == "known" and no_item["applied_damage_modifiers"] == []
    assert unsupported["status"] == "unsupported_mechanic" and unsupported["unsupported_reason"] == "item_modifier"
    assert excluded["status"] == "unsupported_mechanic" and excluded["unsupported_reason"] == "item_modifier"
    assert malformed["status"] == "unsupported_mechanic" and malformed["unsupported_reason"] == "item_modifier"


def test_static_item_modifier_composes_with_existing_modifiers_and_fixed_hit_but_not_fixed_damage():
    weather = _modifier_result(category="special", move_type="water", move_id="water-pulse", power=60, item="choice-specs", weather="rain", side_effects=[])
    burn_screen = _modifier_result(move_id="mach-punch", item="choice-band", weather="none", conditions=[{"side": "self", "condition_type": "burn"}], side_effects=[{"side": "opponent", "effect": "reflect"}], battle_format="singles", ability="iron-fist")
    fixed_hit = _modifier_result(move_id="double-hit", power=60, min_hits=2, max_hits=2, item="life-orb", weather="none", side_effects=[], conditions=[{"side": "self", "condition_type": "none"}])
    assert weather["applied_damage_modifiers"] == ["rain_water_boost", "item_choice_specs_boost"]
    assert burn_screen["applied_damage_modifiers"] == ["burn_physical_reduction", "reflect_reduction", "ability_iron_fist_boost", "item_choice_band_boost"]
    assert fixed_hit["status"] == "known" and fixed_hit["hit_count"] == 2
    assert fixed_hit["applied_damage_modifiers"] == ["item_life_orb_boost"]

    battle = _battle()
    battle["moves"]["my_available_moves"][0]["move_id"] = "seismic-toss"
    battle["item_profiles"] = {"my_active": {"status": "user_confirmed", "source": "user_input", "item_id": "life-orb"}}
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("seismic-toss",))
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="seismic-toss", selectable_moves=("seismic-toss",), move_metadata={"category": "physical", "type": "normal"})
    result = evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)
    assert result["status"] == "known" and result["fixed_damage"] == 50
    assert "applied_damage_modifiers" not in result


def test_static_defender_ability_modifiers_apply_only_to_matching_candidates():
    fire_baseline = _modifier_result(category="special", move_type="fire", weather="none", side_effects=[])
    thick_fat = _modifier_result(category="special", move_type="fire", weather="none", side_effects=[], defender_ability="thick-fat")
    thick_fat_mismatch = _modifier_result(category="special", move_type="water", weather="none", side_effects=[], defender_ability="thick-fat")
    fur_coat_physical = _modifier_result(weather="none", side_effects=[], conditions=[{"side": "self", "condition_type": "none"}], defender_ability="fur-coat")
    fur_coat_special = _modifier_result(category="special", weather="none", side_effects=[], defender_ability="fur-coat")
    ice_scales_special = _modifier_result(category="special", weather="none", side_effects=[], defender_ability="ice-scales")
    filter_super = _modifier_result(category="special", move_type="electric", weather="none", side_effects=[], defender_ability="filter", defender_types=["water"])
    solid_rock_super = _modifier_result(category="special", move_type="electric", weather="none", side_effects=[], defender_ability="solid-rock", defender_types=["water"])
    prism_armor_super = _modifier_result(category="special", move_type="electric", weather="none", side_effects=[], defender_ability="prism-armor", defender_types=["water"])
    wonder_guard_neutral = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, defender_ability="wonder-guard")
    wonder_guard_super = _modifier_result(category="special", move_type="electric", move_id="thunderbolt", power=60, defender_ability="wonder-guard", defender_types=["water"])
    filter_neutral = _modifier_result(category="special", weather="none", side_effects=[], defender_ability="filter")
    assert thick_fat["damage_range"]["maximum"] < fire_baseline["damage_range"]["maximum"]
    assert "defender_ability_thick_fat_reduction" in thick_fat["applied_damage_modifiers"]
    assert thick_fat_mismatch["applied_damage_modifiers"] == []
    assert "defender_ability_fur_coat_reduction" in fur_coat_physical["applied_damage_modifiers"]
    assert fur_coat_special["applied_damage_modifiers"] == []
    assert "defender_ability_ice_scales_reduction" in ice_scales_special["applied_damage_modifiers"]
    assert "defender_ability_filter_reduction" in filter_super["applied_damage_modifiers"]
    assert "defender_ability_solid_rock_reduction" in solid_rock_super["applied_damage_modifiers"]
    assert "defender_ability_prism_armor_reduction" in prism_armor_super["applied_damage_modifiers"]
    assert solid_rock_super["damage_range"] == prism_armor_super["damage_range"]
    assert filter_neutral["applied_damage_modifiers"] == []
    assert wonder_guard_neutral["damage_range"] == {"minimum": 0, "maximum": 0}
    assert wonder_guard_neutral["ko_result"]["single_hit_probability"] == 0.0
    assert wonder_guard_neutral["applied_damage_modifiers"] == ["defender_ability_wonder_guard_immunity"]
    assert wonder_guard_super["damage_range"]["minimum"] > 0
    assert wonder_guard_super["applied_damage_modifiers"] == []


def test_type_specific_defender_damage_abilities_reach_strict_direct_gate():
    fire_baseline = _modifier_result(category="special", move_type="fire", move_id="flamethrower", power=90, weather="none", side_effects=[])
    water_baseline = _modifier_result(category="special", move_type="water", move_id="water-pulse", power=60, weather="none", side_effects=[])
    sound_baseline = _modifier_result(category="special", move_type="normal", move_id="boomburst", power=140)

    heatproof = _modifier_result(category="special", move_type="fire", move_id="flamethrower", power=90, weather="none", side_effects=[], defender_ability="heatproof")
    heatproof_nonfire = _modifier_result(category="special", move_type="water", move_id="water-pulse", power=60, weather="none", side_effects=[], defender_ability="heatproof")
    water_bubble = _modifier_result(category="special", move_type="fire", move_id="flamethrower", power=90, weather="none", side_effects=[], defender_ability="water-bubble")
    water_bubble_nonfire = _modifier_result(category="special", move_type="water", move_id="water-pulse", power=60, weather="none", side_effects=[], defender_ability="water-bubble")
    punk_rock = _modifier_result(category="special", move_type="normal", move_id="boomburst", power=140, defender_ability="punk-rock")
    punk_rock_nonsound = _modifier_result(category="physical", move_type="normal", move_id="tackle", power=40, defender_ability="punk-rock")

    assert heatproof["status"] == water_bubble["status"] == punk_rock["status"] == "known"
    assert heatproof["damage_range"]["maximum"] < fire_baseline["damage_range"]["maximum"]
    assert heatproof["applied_damage_modifiers"] == ["defender_ability_heatproof_fire_reduction"]
    assert heatproof_nonfire["damage_range"] == water_baseline["damage_range"]
    assert heatproof_nonfire["applied_damage_modifiers"] == []
    assert water_bubble["damage_range"]["maximum"] < fire_baseline["damage_range"]["maximum"]
    assert water_bubble["applied_damage_modifiers"] == ["defender_ability_water_bubble_fire_reduction"]
    assert water_bubble_nonfire["damage_range"] == water_baseline["damage_range"]
    assert water_bubble_nonfire["applied_damage_modifiers"] == []
    assert punk_rock["damage_range"]["maximum"] < sound_baseline["damage_range"]["maximum"]
    assert punk_rock["applied_damage_modifiers"] == ["defender_ability_punk_rock_sound_reduction"]
    assert punk_rock_nonsound["applied_damage_modifiers"] == []


def test_fluffy_defensive_damage_matrix_uses_exact_contact_and_fire_inputs():
    tackle_baseline = _modifier_result(category="physical", move_type="normal", move_id="tackle", power=40)
    tackle_fluffy = _modifier_result(category="physical", move_type="normal", move_id="tackle", power=40, defender_ability="fluffy")
    hyper_voice_baseline = _modifier_result(category="special", move_type="normal", move_id="hyper-voice", power=90)
    hyper_voice_fluffy = _modifier_result(category="special", move_type="normal", move_id="hyper-voice", power=90, defender_ability="fluffy")
    flamethrower_baseline = _modifier_result(category="special", move_type="fire", move_id="flamethrower", power=90, weather="none", side_effects=[])
    flamethrower_fluffy = _modifier_result(category="special", move_type="fire", move_id="flamethrower", power=90, weather="none", side_effects=[], defender_ability="fluffy")
    fire_punch_baseline = _modifier_result(category="physical", move_type="fire", move_id="fire-punch", power=75, weather="none", side_effects=[], conditions=[{"side": "self", "condition_type": "none"}])
    fire_punch_fluffy = _modifier_result(category="physical", move_type="fire", move_id="fire-punch", power=75, weather="none", side_effects=[], conditions=[{"side": "self", "condition_type": "none"}], defender_ability="fluffy")

    assert tackle_fluffy["damage_range"]["maximum"] < tackle_baseline["damage_range"]["maximum"]
    assert tackle_fluffy["applied_damage_modifiers"] == ["defender_ability_fluffy_contact_reduction"]
    assert hyper_voice_fluffy["damage_range"] == hyper_voice_baseline["damage_range"]
    assert hyper_voice_fluffy["applied_damage_modifiers"] == []
    assert flamethrower_fluffy["damage_range"]["minimum"] > flamethrower_baseline["damage_range"]["minimum"]
    assert flamethrower_fluffy["applied_damage_modifiers"] == ["defender_ability_fluffy_fire_vulnerability"]
    assert fire_punch_fluffy["damage_range"] == fire_punch_baseline["damage_range"]
    assert fire_punch_fluffy["applied_damage_modifiers"] == [
        "defender_ability_fluffy_contact_reduction",
        "defender_ability_fluffy_fire_vulnerability",
    ]


def test_type_specific_defender_damage_abilities_fail_closed_and_preserve_scope():
    fluffy_unknown_flags = _modifier_result(move_id="missing-flags", defender_ability="fluffy")
    punk_rock_unknown_flags = _modifier_result(move_id="missing-flags", defender_ability="punk-rock")
    heatproof_unknown_type = _modifier_result(category="special", move_type="unknown", move_id="flamethrower", defender_ability="heatproof")
    suppressed_heatproof = _modifier_result(category="special", move_type="fire", move_id="flamethrower", power=90, weather="none", side_effects=[], ability="mold-breaker", defender_ability="heatproof")
    fire_baseline = _modifier_result(category="special", move_type="fire", move_id="flamethrower", power=90, weather="none", side_effects=[])
    suppressed_fluffy = _modifier_result(category="physical", move_type="fire", move_id="fire-punch", power=75, weather="none", side_effects=[], conditions=[{"side": "self", "condition_type": "none"}], ability="mold-breaker", defender_ability="fluffy")
    fire_punch_baseline = _modifier_result(category="physical", move_type="fire", move_id="fire-punch", power=75, weather="none", side_effects=[], conditions=[{"side": "self", "condition_type": "none"}])
    water_bubble_offense = _modifier_result(category="special", move_type="water", move_id="water-pulse", power=60, ability="water-bubble", weather="none", side_effects=[])
    punk_rock_offense = _modifier_result(category="special", move_type="normal", move_id="boomburst", power=140, ability="punk-rock")

    assert fluffy_unknown_flags["status"] == "unsupported_mechanic"
    assert fluffy_unknown_flags["unsupported_reason"] == "move_flag_metadata"
    assert punk_rock_unknown_flags["status"] == "unsupported_mechanic"
    assert punk_rock_unknown_flags["unsupported_reason"] == "move_flag_metadata"
    assert heatproof_unknown_type["status"] == "unsupported_mechanic"
    assert heatproof_unknown_type["unsupported_reason"] == "native_direct_damage"
    assert suppressed_heatproof["damage_range"] == fire_baseline["damage_range"]
    assert suppressed_heatproof["applied_damage_modifiers"] == []
    assert suppressed_fluffy["damage_range"] == fire_punch_baseline["damage_range"]
    assert suppressed_fluffy["applied_damage_modifiers"] == []
    assert water_bubble_offense["status"] == "unsupported_mechanic"
    assert water_bubble_offense["unsupported_reason"] == "ability_modifier"
    assert punk_rock_offense["status"] == "known"
    assert punk_rock_offense["applied_damage_modifiers"] == ["ability_punk_rock_sound_boost"]


def test_type_specific_defender_damage_abilities_preserve_critical_multihit_and_fixed_damage_boundaries():
    critical = _modifier_result(
        category="special", move_type="fire", move_id="flamethrower", power=90,
        weather="none", side_effects=[], defender_ability="heatproof", is_critical=True,
    )
    fixed_two_hit = _modifier_result(
        move_id="double-hit", power=35, min_hits=2, max_hits=2,
        conditions=[{"side": "self", "condition_type": "none"}], defender_ability="fluffy",
    )

    assert critical["status"] == "known"
    assert critical["applied_damage_modifiers"] == ["defender_ability_heatproof_fire_reduction"]
    assert fixed_two_hit["status"] == "known" and fixed_two_hit["hit_count"] == 2
    assert fixed_two_hit["damage_range"]["minimum"] == fixed_two_hit["per_hit_damage_range"]["minimum"] * 2
    assert fixed_two_hit["applied_damage_modifiers"] == ["defender_ability_fluffy_contact_reduction"]

    battle = _battle()
    battle["moves"]["my_available_moves"][0]["move_id"] = "seismic-toss"
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("seismic-toss",))
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="seismic-toss", selectable_moves=("seismic-toss",), move_metadata={"category": "physical", "type": "fire"})
    damage["battle_context"]["current_state"]["ability_context"] = {"current_abilities": [{"side": "opponent", "ability": "fluffy"}]}
    result = evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)
    assert result["status"] == "known" and result["damage_model"] == "level_based_fixed"
    assert result["fixed_damage"] == 50
    assert "applied_damage_modifiers" not in result


def test_static_attacker_type_effectiveness_abilities_use_exact_current_types():
    baseline_stab = _modifier_result(category="special", move_type="normal", move_id="swift", power=60)
    adaptability = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, ability="adaptability")
    adaptability_mismatch = _modifier_result(category="special", move_type="psychic", move_id="psychic", power=60, ability="adaptability")
    baseline_resisted = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, defender_types=["rock"])
    tinted_lens = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, ability="tinted-lens", defender_types=["rock"])
    tinted_lens_neutral = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, ability="tinted-lens")

    assert adaptability["damage_range"]["maximum"] > baseline_stab["damage_range"]["maximum"]
    assert adaptability["applied_damage_modifiers"] == ["ability_adaptability_stab_boost"]
    assert adaptability_mismatch["applied_damage_modifiers"] == []
    assert tinted_lens["damage_range"]["maximum"] > baseline_resisted["damage_range"]["maximum"]
    assert tinted_lens["applied_damage_modifiers"] == ["ability_tinted_lens_not_very_effective_boost"]
    assert tinted_lens_neutral["applied_damage_modifiers"] == []


def test_static_attacker_item_modifiers_use_exact_category_and_type_effectiveness():
    baseline_special = _modifier_result(category="special", move_type="normal", move_id="swift", power=60)
    wise_glasses = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, item="wise-glasses")
    wise_glasses_physical = _modifier_result(category="physical", move_type="normal", move_id="tackle", power=60, item="wise-glasses")
    baseline_super = _modifier_result(category="special", move_type="electric", move_id="thunderbolt", power=60, defender_types=["water"])
    expert_belt = _modifier_result(category="special", move_type="electric", move_id="thunderbolt", power=60, item="expert-belt", defender_types=["water"])
    expert_belt_neutral = _modifier_result(category="special", move_type="normal", move_id="swift", power=60, item="expert-belt")

    assert wise_glasses["damage_range"]["maximum"] > baseline_special["damage_range"]["maximum"]
    assert wise_glasses["applied_damage_modifiers"] == ["item_wise_glasses_special_boost"]
    assert wise_glasses_physical["applied_damage_modifiers"] == []
    assert expert_belt["damage_range"]["maximum"] > baseline_super["damage_range"]["maximum"]
    assert expert_belt["applied_damage_modifiers"] == ["item_expert_belt_super_effective_boost"]
    assert expert_belt_neutral["applied_damage_modifiers"] == []


def test_defender_type_resist_berries_and_chilan_reduce_only_one_matching_direct_hit():
    fire_baseline = _modifier_result(
        move_id="tackle", category="special", move_type="fire", power=180, weather="none", side_effects=[], defender_types=["grass"], defender_current_hp=100,
    )
    occa = _modifier_result(
        move_id="tackle", category="special", move_type="fire", power=180, weather="none", side_effects=[], defender_item="occa-berry", defender_types=["grass"], defender_current_hp=100,
    )
    occa_nonmatching = _modifier_result(
        move_id="tackle", category="special", move_type="water", power=180, weather="none", side_effects=[], defender_item="occa-berry", defender_types=["grass"], defender_current_hp=100,
    )
    water_baseline = _modifier_result(
        move_id="tackle", category="special", move_type="water", power=180, weather="none", side_effects=[], defender_types=["grass"], defender_current_hp=100,
    )
    chilan = _modifier_result(move_id="tackle", move_type="normal", power=180, defender_item="chilan-berry", defender_current_hp=50)
    normal_baseline = _modifier_result(move_id="tackle", move_type="normal", power=180, defender_current_hp=50)

    assert all(result["status"] == "known" for result in (fire_baseline, occa, occa_nonmatching, water_baseline, chilan, normal_baseline))
    assert occa["damage_range"]["maximum"] < fire_baseline["damage_range"]["maximum"]
    assert occa["ko_result"]["single_hit_probability"] < fire_baseline["ko_result"]["single_hit_probability"]
    assert occa["applied_damage_modifiers"] == ["defender_item_type_resist_berry_reduction"]
    assert occa_nonmatching["damage_range"] == water_baseline["damage_range"]
    assert occa_nonmatching["applied_damage_modifiers"] == []
    assert chilan["damage_range"]["maximum"] < normal_baseline["damage_range"]["maximum"]
    assert chilan["applied_damage_modifiers"] == ["defender_item_chilan_berry_reduction"]


def test_defender_resist_berry_preserves_unknown_and_complex_hit_boundaries():
    unknown = _modifier_result(move_id="tackle", category="special", move_type="fire", power=100, weather="none", side_effects=[], defender_item="unknown", defender_types=["grass"])
    multi_hit = _modifier_result(
        move_id="tackle", category="special", move_type="fire", power=50, weather="none", side_effects=[], min_hits=2, max_hits=2,
        defender_item="occa-berry", defender_types=["grass"],
    )
    unrelated = _modifier_result(move_id="tackle", category="special", move_type="fire", power=100, weather="none", side_effects=[], defender_item="leftovers", defender_types=["grass"])

    assert unknown["status"] == "insufficient_context"
    assert unknown["missing_inputs"] == ["defender.item"]
    assert multi_hit["status"] == "unsupported_mechanic"
    assert multi_hit["unsupported_reason"] == "defender_type_resist_berry_multi_hit"
    assert unrelated["status"] == "unsupported_mechanic"
    assert unrelated["unsupported_reason"] == "defender_item_modifier"


def test_relevant_trusted_stat_stages_adjust_formula_damage_without_affecting_fixed_damage():
    neutral = _modifier_result(stages=[("self", "attack", 0), ("opponent", "defense", 0)])
    boosted = _modifier_result(stages=[("self", "attack", 1), ("opponent", "defense", 0)])
    reduced = _modifier_result(stages=[("self", "attack", -1), ("opponent", "defense", 1)])
    special = _modifier_result(category="special", stages=[("self", "special-attack", 2), ("opponent", "special-defense", -1)])
    unknown = _modifier_result(stages=[("self", "attack", 1)])
    irrelevant = _modifier_result(stages=[("self", "attack", 0), ("opponent", "defense", 0), ("self", "special-attack", -6)])
    malformed = _modifier_result(stages=[("self", "attack", 7), ("opponent", "defense", 0)])
    assert boosted["damage_range"]["maximum"] > neutral["damage_range"]["maximum"] > reduced["damage_range"]["maximum"]
    assert special["stat_stage_evidence"] == {"offensive_stage_stat": "special-attack", "offensive_stage_value": 2, "defensive_stage_stat": "special-defense", "defensive_stage_value": -1, "stage_adjustment_applied": True}
    assert unknown["status"] == "insufficient_context" and unknown["missing_inputs"] == ["defender.defense_stage"]
    assert irrelevant["status"] == "known"
    assert malformed["status"] == "unsupported_mechanic"


def test_defender_ability_authority_fails_closed_and_fixed_damage_does_not_require_it():
    unknown = _modifier_result(defender_ability="unknown")
    unsupported = _modifier_result(defender_ability="grass-pelt")
    malformed = _modifier_result(defender_ability="bad/ability")
    fixed_hit = _modifier_result(move_id="double-hit", min_hits=2, max_hits=2, conditions=[{"side": "self", "condition_type": "none"}], defender_ability="fur-coat")
    assert unknown["status"] == "insufficient_context" and unknown["missing_inputs"] == ["defender.ability"]
    assert unsupported["status"] == "unsupported_mechanic" and unsupported["unsupported_reason"] == "defender_ability_modifier"
    assert malformed["status"] == "unsupported_mechanic" and malformed["unsupported_reason"] == "defender_ability_modifier"
    assert fixed_hit["status"] == "known" and fixed_hit["hit_count"] == 2
    assert "defender_ability_fur_coat_reduction" in fixed_hit["applied_damage_modifiers"]

    battle = _battle()
    battle["moves"]["my_available_moves"][0]["move_id"] = "seismic-toss"
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("seismic-toss",))
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="seismic-toss", selectable_moves=("seismic-toss",), move_metadata={"category": "physical", "type": "normal"})
    damage["battle_context"]["current_state"]["ability_context"] = {"current_abilities": [{"side": "opponent", "ability": "fur-coat"}]}
    result = evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)
    assert result["status"] == "known" and result["damage_model"] == "level_based_fixed"
    assert "applied_damage_modifiers" not in result


def test_request_start_self_ability_reaches_only_matching_candidate_and_presentation():
    battle = _battle()
    battle["moves"]["my_available_moves"] = [{"slot_index": 0, "move_id": "mach-punch"}, {"slot_index": 1, "move_id": "tackle"}]
    battle["ability_context"] = {"current_abilities": [{
        "side": "self", "ability": "iron-fist", "status": "user_confirmed",
        "source": "user_confirmed_current_ability", "confidence": "known",
        "provenance": {"side": "self", "slot_index": 0, "pokemon_id": "pikachu", "session_id": "s", "source": "user_confirmed_current_ability", "trust": "user_confirmed_current"},
    }]}
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "mach-punch"}, {"move_id": "tackle"}], battle_input=battle,
        move_repository={"mach-punch": {"category": "physical", "power": 40, "type": "fighting", "priority": 1}, "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}, species_repository=_Species(),
    )
    candidates = prepared["candidates"]
    assert candidates[0]["mechanics_result"]["applied_damage_modifiers"] == ["ability_iron_fist_boost"]
    assert candidates[1]["mechanics_result"]["status"] == "known"
    assert candidates[1]["mechanics_result"]["applied_damage_modifiers"] == []
    completed = complete_recommendation_cycle(prepared_cycle=prepared, response_payload={"recommendation_status": "resolved", "selected_candidate_id": 0, "explanation_code": "clear_ranked_winner"})
    text = format_recommendation_presentation_text(presentation_model=build_recommendation_presentation_model(completed_cycle=completed))
    assert "\uc544\uc774\uc5b8\ud53c\uc2a4\ud2b8\uc5d0 \uc758\ud55c \ud380\uce58 \uae30\uc220 \uac15\ud654" in text
    assert "ability_iron_fist_boost" not in text


def test_request_start_self_item_reaches_only_matching_candidate_and_presentation():
    battle = _battle()
    battle["moves"]["my_available_moves"] = [{"slot_index": 0, "move_id": "tackle"}, {"slot_index": 1, "move_id": "swift"}]
    battle["item_profiles"] = {"my_active": {"status": "user_confirmed", "source": "user_input", "item_id": "choice-band"}}
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}, {"move_id": "swift"}], battle_input=battle,
        move_repository={"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}, "swift": {"category": "special", "power": 60, "type": "normal", "priority": 0}}, species_repository=_Species(),
    )
    candidates = prepared["candidates"]
    assert candidates[0]["mechanics_result"]["applied_damage_modifiers"] == ["item_choice_band_boost"]
    assert candidates[1]["mechanics_result"]["status"] == "known"
    assert candidates[1]["mechanics_result"]["applied_damage_modifiers"] == []
    completed = complete_recommendation_cycle(prepared_cycle=prepared, response_payload={"recommendation_status": "resolved", "selected_candidate_id": 0, "explanation_code": "clear_ranked_winner"})
    text = format_recommendation_presentation_text(presentation_model=build_recommendation_presentation_model(completed_cycle=completed))
    assert "\uad6c\uc560\uc758\ubc34\ub4dc \uc18c\uc9c0\ud488\uc73c\ub85c \uc778\ud55c \ubb3c\ub9ac \ud53c\ud574 \uac15\ud654" in text
    assert "item_choice_band_boost" not in text


def test_request_start_opponent_ability_reaches_only_matching_candidate_and_presentation():
    battle = _battle()
    battle["moves"]["my_available_moves"] = [{"slot_index": 0, "move_id": "tackle"}, {"slot_index": 1, "move_id": "swift"}]
    battle["ability_context"] = {"current_abilities": [{
        "side": "opponent", "ability": "fur-coat", "status": "user_confirmed",
        "source": "user_confirmed_current_ability", "confidence": "known",
        "provenance": {**_provenance("opponent", 1, "eevee"), "source": "user_confirmed_current_ability"},
    }]}
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}, {"move_id": "swift"}], battle_input=battle,
        move_repository={"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}, "swift": {"category": "special", "power": 60, "type": "normal", "priority": 0}}, species_repository=_Species(),
    )
    candidates = prepared["candidates"]
    assert candidates[0]["mechanics_result"]["applied_damage_modifiers"] == ["defender_ability_fur_coat_reduction"]
    assert candidates[1]["mechanics_result"]["status"] == "known"
    assert candidates[1]["mechanics_result"]["applied_damage_modifiers"] == []
    completed = complete_recommendation_cycle(prepared_cycle=prepared, response_payload={"recommendation_status": "resolved", "selected_candidate_id": 1, "explanation_code": "clear_ranked_winner"})
    text = format_recommendation_presentation_text(presentation_model=build_recommendation_presentation_model(completed_cycle=completed))
    assert "\ud37c\ucf54\ud2b8 \ud2b9\uc131\uc73c\ub85c \ubb3c\ub9ac \ud53c\ud574 \uac10\uc18c" not in text
    assert "defender_ability_fur_coat_reduction" not in text


def test_presentation_exposes_only_selected_candidate_applied_modifier_labels():
    mechanics = _modifier_result(
        weather="rain", side_effects=[{"side": "opponent", "effect": "reflect"}],
        conditions=[{"side": "self", "condition_type": "burn"}], battle_format="singles",
    )
    presentation = {
        "status": "resolved", "recommended_move": "tackle", "recommended_slot_index": 0,
        "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": [],
        "selected_candidate": {
            "selected_action": {"slot_index": 0, "move": "tackle"},
            "explanation_code": "clear_ranked_winner",
            "evidence": {"mechanics_result": mechanics, "action_order": {"status": "insufficient_context"}, "comparison_facts": {}},
        },
    }
    text = format_recommendation_presentation_text(presentation_model=presentation)
    assert "\ud654\uc0c1\uc73c\ub85c \uc778\ud55c \ubb3c\ub9ac \ud53c\ud574 \uac10\uc18c" in text
    assert "\uc0c1\ub300 \uce21 \ub9ac\ud50c\ub809\ud130 \uc801\uc6a9" in text
    assert "rain_water_boost" not in text and "reflect_reduction" not in text


def test_request_start_field_snapshot_reaches_candidate_result_and_presentation():
    battle = _battle()
    battle["moves"]["my_available_moves"] = [{"slot_index": 0, "move_id": "water-pulse"}, {"slot_index": 1, "move_id": "tackle"}]
    battle["field_state_context"] = {
        "current_field": {
            "weather": "rain", "terrain": "none", "global_effects": [], "side_effects": [],
            "status": "user_confirmed", "source": "user_confirmed_current_field_state", "confidence": "known",
        }
    }
    battle["condition_context"] = {"current_conditions": [{"side": "self", "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"}]}
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "water-pulse"}, {"move_id": "tackle"}], battle_input=battle,
        move_repository={"water-pulse": {"category": "special", "power": 60, "type": "water", "priority": 0}, "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}},
        species_repository=_Species(),
    )
    mechanics = prepared["candidates"][0]["mechanics_result"]
    assert mechanics["status"] == "known"
    assert mechanics["applied_damage_modifiers"] == ["rain_water_boost"]
    assert prepared["candidates"][1]["mechanics_result"]["status"] == "known"
    completed = complete_recommendation_cycle(
        prepared_cycle=prepared,
        response_payload={"recommendation_status": "resolved", "selected_candidate_id": 0, "explanation_code": "clear_ranked_winner"},
    )
    text = format_recommendation_presentation_text(
        presentation_model=build_recommendation_presentation_model(completed_cycle=completed)
    )
    assert "\ube44\ub85c \uc778\ud55c \ubb3c\ud0c0\uc785 \uae30\uc220 \uac15\ud654" in text


def test_request_start_grounded_terrain_reaches_only_the_matching_candidate_and_presentation():
    battle = _battle()
    battle["moves"]["my_available_moves"] = [{"slot_index": 0, "move_id": "thunderbolt"}, {"slot_index": 1, "move_id": "tackle"}]
    battle["field_state_context"] = {
        "current_field": {
            "weather": "none", "terrain": "electric", "global_effects": [], "side_effects": [],
            "status": "user_confirmed", "source": "user_confirmed_current_field_state", "confidence": "known",
        }
    }
    battle["grounded_context"] = {
        "self": {"status": "known_grounded", "provenance": "user_confirmed_current"},
        "opponent": {"status": "unknown", "provenance": "unknown"},
    }
    battle["condition_context"] = {"current_conditions": [{"side": "self", "condition_type": "none"}]}
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "thunderbolt"}, {"move_id": "tackle"}], battle_input=battle,
        move_repository={"thunderbolt": {"category": "special", "power": 90, "type": "electric", "priority": 0}, "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}},
        species_repository=_Species(),
    )
    assert prepared["candidates"][0]["mechanics_result"]["applied_damage_modifiers"] == ["terrain_electric_boost"]
    assert prepared["candidates"][1]["mechanics_result"]["applied_damage_modifiers"] == []
    completed = complete_recommendation_cycle(
        prepared_cycle=prepared,
        response_payload={"recommendation_status": "resolved", "selected_candidate_id": 0, "explanation_code": "clear_ranked_winner"},
    )
    text = format_recommendation_presentation_text(
        presentation_model=build_recommendation_presentation_model(completed_cycle=completed)
    )
    assert "\uc77c\ub809\ud2b8\ub9ad\ud544\ub4dc\ub85c \uc804\uae30 \uae30\uc220 \ud53c\ud574 \uac15\ud654" in text
