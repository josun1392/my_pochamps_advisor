from copy import deepcopy

import pytest

from llm.advisor_turn_snapshot import (
    BASE_STAT_KEYS,
    build_q12_input_adapter,
    build_request_start_recommendation_snapshot,
    build_snapshot_damage_input,
    build_snapshot_stat_provenance,
)


class _SpeciesRepository:
    def __init__(self, entries):
        self.entries = entries

    def get(self, species_id):
        return self.entries.get(species_id)


def _entry(side, stat, value, pokemon, slot, session="s0"):
    return {
        "side": side, "stat": stat, "value": value,
        "provenance": {
            "side": side, "slot_index": slot, "pokemon_id": pokemon,
            "session_id": session, "source": "user_confirmed_final_battle_stat",
            "trust": "user_confirmed_current",
        },
    }


def _snapshot():
    final_entries = []
    for side, pokemon, slot, offset in (("self", "pikachu", 0, 0), ("opponent", "eevee", 1, 10)):
        for index, stat in enumerate(BASE_STAT_KEYS):
            final_entries.append(_entry(side, stat, 100 + offset + index, pokemon, slot))
    return build_request_start_recommendation_snapshot({
        "current_state_session_id": "s0",
        "pokemon": {
            "my_active": {"name_en": "pikachu", "slot_index": 0},
            "opponent_active": {"name_en": "eevee", "slot_index": 1},
        },
        "moves": {"my_selected_move": {"move_id": "tackle"}, "my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]},
        "final_stat_context": {"current_final_stats": final_entries},
        "stat_stage_context": {"current_stages": [{
            "side": "self", "stat": "attack", "stage": 2,
            "provenance": {"side": "self", "slot_index": 0, "pokemon_id": "pikachu", "session_id": "s0", "source": "user_confirmed_current_stat_stage", "trust": "user_confirmed_current"},
        }]},
    }, selectable_moves=("tackle",))


def _repo():
    stats = {key: 90 for key in BASE_STAT_KEYS}
    return _SpeciesRepository({
        "pikachu": {"en": "pikachu", "types_en": ["electric"], "base_stats": stats},
        "eevee": {"en": "eevee", "types_en": ["normal"], "base_stats": stats},
    })


def test_snapshot_identity_keys_detached_type_base_and_confirmed_final_stat_provenance():
    snapshot = _snapshot()
    repository = _repo()
    provenance = build_snapshot_stat_provenance(snapshot, species_repository=repository)

    assert provenance["attacker"]["types"] == {"available": True, "value": ["electric"], "source": "repository_metadata", "trust": "deterministic_metadata", "reason": None}
    assert provenance["defender"]["base_stats"]["value"]["attack"] == 90
    assert provenance["attacker"]["final_stats"]["available"] is True
    assert provenance["attacker"]["stat_stages"]["value"] == {"attack": 2}

    frozen = deepcopy(provenance)
    repository.entries["pikachu"]["base_stats"]["attack"] = 1
    assert provenance == frozen


def test_missing_or_wrong_species_metadata_never_fabricates_bridge_values():
    snapshot = _snapshot()
    missing = build_snapshot_stat_provenance(snapshot, species_repository=_SpeciesRepository({}))
    assert missing["attacker"]["types"]["available"] is False
    assert missing["attacker"]["base_stats"]["reason"] == "missing_base_stat_metadata"

    wrong = _SpeciesRepository({"pikachu": {"en": "raichu", "types_en": ["electric"], "base_stats": {key: 1 for key in BASE_STAT_KEYS}}})
    with pytest.raises(ValueError, match="species_metadata_identity_mismatch"):
        build_snapshot_stat_provenance(snapshot, species_repository=wrong)


def test_q12_adapter_requires_confirmed_final_stats_and_keeps_events_modifiers_unknown():
    snapshot = _snapshot()
    damage_input = build_snapshot_damage_input(
        snapshot, candidate_slot_index=0, candidate_move_id="tackle",
        selectable_moves=("tackle",), move_metadata={"category": "physical", "power": 40, "type": "normal"},
    )
    ready = build_q12_input_adapter(damage_input, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_repo()))
    assert ready["status"] == "ready_for_existing_q12_boundary"
    assert ready["attacker"]["known_ability"]["available"] is False

    no_final = build_request_start_recommendation_snapshot({
        "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 1}},
        "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]},
    }, selectable_moves=("tackle",))
    unavailable = build_q12_input_adapter(
        build_snapshot_damage_input(no_final, candidate_slot_index=0, candidate_move_id="tackle", selectable_moves=("tackle",), move_metadata={}),
        stat_provenance=build_snapshot_stat_provenance(no_final, species_repository=_repo()),
    )
    assert unavailable == {"status": "unavailable", "reason": "final_stats_unavailable"}
