"""Flail and Reversal consume canonical current-HP brackets in direct Q12."""

import pytest

from llm.advisor_direct_mechanics import evaluate_direct_damage_mechanics
from llm.advisor_turn_snapshot import BASE_STAT_KEYS, build_request_start_recommendation_snapshot, build_snapshot_damage_input, build_snapshot_stat_provenance


class _Species:
    def get(self, name):
        return {"en": name, "types_en": ["normal"], "base_stats": {key: 80 for key in BASE_STAT_KEYS}}


def _provenance(side, slot, pokemon):
    return {"side": side, "slot_index": slot, "pokemon_id": pokemon, "session_id": "s", "source": "user_confirmed_final_battle_stat", "trust": "user_confirmed_current"}


def _resolve(move, hp, maximum=100):
    stats = []
    for side, pokemon, slot in (("self", "pikachu", 0), ("opponent", "eevee", 1)):
        stats.extend({"side": side, "stat": key, "value": 100 + index, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "provenance": _provenance(side, slot, pokemon)} for index, key in enumerate(BASE_STAT_KEYS))
    battle = {"current_state_session_id": "s", "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 1}}, "moves": {"my_available_moves": [{"slot_index": 0, "move_id": move}]}, "final_stat_context": {"current_final_stats": stats}, "trusted_level_context": {"current_levels": [{"side": "self", "value": 50, "provenance": {**_provenance("self", 0, "pikachu"), "source": "user_confirmed_current_level"}}]}, "direct_mechanics_context": {"generation": "gen9", "attacker": {"ability": {"status": "known_absent"}, "item": {"status": "known_absent"}, "boosts": {key: 0 for key in BASE_STAT_KEYS if key != "hp"}, "current_hp": hp, "max_hp": maximum, "status": {"status": "known_absent"}}, "defender": {"ability": {"status": "known_absent"}, "item": {"status": "known_absent"}, "boosts": {key: 0 for key in BASE_STAT_KEYS if key != "hp"}, "current_hp": 100, "max_hp": 100, "status": {"status": "known_absent"}}, "field": {"weather": {"status": "known_absent"}, "terrain": {"status": "known_absent"}}}}
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=(move,))
    metadata = {"category": "physical", "power": 20, "type": "normal" if move == "flail" else "fighting"}
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id=move, selectable_moves=(move,), move_metadata=metadata)
    return evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)


@pytest.mark.parametrize(("move", "hp", "power"), [("flail", 100, 20), ("flail", 69, 20), ("flail", 4, 200), ("reversal", 20, 100)])
def test_flail_and_reversal_canonical_brackets_reach_direct_q12(move, hp, power):
    result = _resolve(move, hp)
    assert result["status"] == "known"
    assert result["dynamic_power_evidence"]["mechanic"] == "current_hp_bracket_power"
    assert result["dynamic_power_evidence"]["effective_power"] == power
    assert result["damage_range"]["maximum"] >= result["damage_range"]["minimum"]
    assert result["ko_result"]["status"] == "resolved"


def test_flail_boundaries_and_unavailable_hp_remain_conservative():
    assert _resolve("flail", 68)["dynamic_power_evidence"]["effective_power"] == 40
    assert _resolve("flail", 5)["dynamic_power_evidence"]["effective_power"] == 150
    unknown = _resolve("flail", {"status": "unknown"})
    malformed = _resolve("reversal", 101)
    assert unknown["status"] == "insufficient_context" and "attacker.current_hp" in unknown["missing_inputs"]
    assert malformed["status"] == "unsupported_mechanic" and malformed["unsupported_reason"] == "current_hp_bracket_context"
