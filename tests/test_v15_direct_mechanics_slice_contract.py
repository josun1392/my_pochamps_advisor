from copy import deepcopy

from llm.advisor_candidate_contract import build_recommendation_presentation_model, complete_recommendation_cycle, prepare_ui_recommendation_cycle
from llm.advisor_client import format_recommendation_presentation_text
from llm.advisor_direct_mechanics import evaluate_direct_damage_mechanics
from llm.advisor_turn_snapshot import (
    BASE_STAT_KEYS,
    build_request_start_recommendation_snapshot,
    build_snapshot_damage_input,
    build_snapshot_stat_provenance,
)


class _Species:
    def get(self, name):
        return {"en": name, "types_en": ["normal"], "base_stats": {key: 80 for key in BASE_STAT_KEYS}}


def _provenance(side, slot, pokemon):
    return {"side": side, "slot_index": slot, "pokemon_id": pokemon, "session_id": "s", "source": "user_confirmed_final_battle_stat", "trust": "user_confirmed_current"}


def _direct_context(*, generation="gen9"):
    absent = {"status": "known_absent"}
    side = {"ability": absent, "item": absent, "boosts": {key: 0 for key in BASE_STAT_KEYS if key != "hp"}, "current_hp": 100, "max_hp": 100, "status": absent}
    return {"generation": generation, "attacker": deepcopy(side), "defender": deepcopy(side), "field": {"weather": absent, "terrain": absent}}


def _battle(*, direct=True):
    entries = []
    for side, pokemon, slot in (("self", "pikachu", 0), ("opponent", "eevee", 1)):
        entries.extend({"side": side, "stat": key, "value": 100 + index, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "provenance": _provenance(side, slot, pokemon)} for index, key in enumerate(BASE_STAT_KEYS))
    battle = {"current_state_session_id": "s", "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 1}}, "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]}, "final_stat_context": {"current_final_stats": entries}, "trusted_level_context": {"current_levels": [{"side": "self", "value": 50, "provenance": {**_provenance("self", 0, "pikachu"), "source": "user_confirmed_current_level"}}]}}
    if direct:
        battle["direct_mechanics_context"] = _direct_context()
    return battle


def _direct_result(battle):
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("tackle",))
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="tackle", selectable_moves=("tackle",), move_metadata={"category": "physical", "power": 40, "type": "normal"})
    return evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)


def _modifier_result(*, category="physical", move_type="normal", move_id="tackle", power=40, min_hits=None, max_hits=None, weather=None, conditions=None, side_effects=None, battle_format=None, ability=None, item=None, defender_item=None, defender_ability=None, defender_types=None, stages=None):
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
        provenance["defender"]["known_item"] = {"status": "known", "value": defender_item}
    return evaluate_direct_damage_mechanics(damage, stat_provenance=provenance, trusted_level=50)


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
    dynamic_battle["moves"]["my_available_moves"][0]["move_id"] = "eruption"
    dynamic = build_request_start_recommendation_snapshot(dynamic_battle, selectable_moves=("eruption",))
    damage = build_snapshot_damage_input(dynamic, candidate_slot_index=0, candidate_move_id="eruption", selectable_moves=("eruption",), move_metadata={"category": "special", "power": 150, "type": "fire"})
    result = evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(dynamic, species_repository=_Species()), trusted_level=50)
    assert result["status"] == "unsupported_mechanic"
    assert result["unsupported_reason"] == "dynamic_base_power"

    modifier = _battle()
    modifier["direct_mechanics_context"]["attacker"]["item"] = {"status": "known", "value": "choice-band"}
    result = _direct_result(modifier)
    assert result["status"] == "unsupported_mechanic"
    assert result["unsupported_reason"] == "item_modifier"


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
