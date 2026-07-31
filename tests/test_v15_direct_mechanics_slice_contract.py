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
    assert provider_result == candidate["mechanics_result"]
    assert "damage_rolls" not in provider_result
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
