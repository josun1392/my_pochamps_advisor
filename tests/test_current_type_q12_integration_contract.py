from __future__ import annotations

from copy import deepcopy

import pytest

from llm.advisor_direct_mechanics import evaluate_direct_damage_mechanics
from llm.advisor_q12_snapshot_adapter import invoke_existing_q12_from_snapshot
from llm.advisor_turn_snapshot import (
    BASE_STAT_KEYS,
    build_request_start_recommendation_snapshot,
    build_snapshot_damage_input,
    build_snapshot_stat_provenance,
)


class _Species:
    def get(self, name: str) -> dict[str, object]:
        return {"en": name, "types_en": ["normal"], "base_stats": {key: 80 for key in BASE_STAT_KEYS}}


def _provenance(side: str, slot: int, pokemon: str) -> dict[str, object]:
    return {"side": side, "slot_index": slot, "pokemon_id": pokemon, "session_id": "s", "source": "user_confirmed_final_battle_stat", "trust": "user_confirmed_current"}


def _type(side: str, types: list[str]) -> dict[str, object]:
    source, status, trust = "user_confirmed_current_type", "user_confirmed", "user_confirmed_current"
    pokemon, slot = ("pikachu", 0) if side == "self" else ("eevee", 1)
    return {"side": side, "state": "known", "types": types, "status": status, "source": source, "authority_provenance": trust, "provenance": {**_provenance(side, slot, pokemon), "source": source, "trust": trust}}


def _unknown(side: str) -> dict[str, object]:
    return {"side": side, "state": "unknown", "status": "unknown", "source": "unknown", "authority_provenance": "unknown"}


def _direct_context() -> dict[str, object]:
    absent = {"status": "known_absent"}
    side = {"ability": absent, "item": absent, "boosts": {key: 0 for key in BASE_STAT_KEYS if key != "hp"}, "current_hp": 100, "max_hp": 100, "status": absent}
    return {"generation": "gen9", "attacker": deepcopy(side), "defender": deepcopy(side), "field": {"weather": absent, "terrain": absent}}


def _snapshot(*, current_types: object = None, move_id: str = "flamethrower"):
    stats = []
    for side, pokemon, slot in (("self", "pikachu", 0), ("opponent", "eevee", 1)):
        stats.extend({"side": side, "stat": key, "value": 100 + index, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known", "provenance": _provenance(side, slot, pokemon)} for index, key in enumerate(BASE_STAT_KEYS))
    battle = {
        "current_state_session_id": "s",
        "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 1}},
        "moves": {"my_available_moves": [{"slot_index": 0, "move_id": move_id}]},
        "final_stat_context": {"current_final_stats": stats},
        "trusted_level_context": {"current_levels": [{"side": "self", "value": 50, "provenance": {**_provenance("self", 0, "pikachu"), "source": "user_confirmed_current_level"}}]},
        "direct_mechanics_context": _direct_context(),
        "field_state_context": {"current_field": {"weather": "none", "terrain": "none", "global_effects": [], "side_effects": [], "status": "user_confirmed", "source": "user_confirmed_current_field_state", "confidence": "known"}},
    }
    if current_types is not None:
        battle["current_type_context"] = {"current_types": current_types}
    return build_request_start_recommendation_snapshot(battle, selectable_moves=(move_id,))


def _inputs(*, current_types: object = None, move_id: str = "flamethrower", move_type: str = "fire"):
    snapshot = _snapshot(current_types=current_types, move_id=move_id)
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id=move_id, selectable_moves=(move_id,), move_metadata={"category": "special", "power": 90, "type": move_type})
    provenance = build_snapshot_stat_provenance(snapshot, species_repository=_Species())
    return damage, provenance


def test_known_current_types_override_species_for_q12_and_direct_formula_evidence():
    legacy_damage, legacy_provenance = _inputs()
    damage, provenance = _inputs(current_types=[_type("self", ["fire"]), _type("opponent", ["water"])])
    legacy = invoke_existing_q12_from_snapshot(legacy_damage, stat_provenance=legacy_provenance, trusted_level=50)
    resolved = invoke_existing_q12_from_snapshot(damage, stat_provenance=provenance, trusted_level=50)
    direct = evaluate_direct_damage_mechanics(damage, stat_provenance=provenance, trusted_level=50)
    assert provenance["attacker"]["types"]["value"] == ["fire"] and provenance["defender"]["types"]["value"] == ["water"]
    assert resolved["status"] == "resolved" and direct["status"] == "known"
    assert resolved["max_damage"] < legacy["max_damage"]
    assert resolved["type_damage_evidence"] == direct["type_damage_evidence"]
    assert resolved["type_damage_evidence"]["current_type_override_used"] is True


def test_explicit_unknown_and_malformed_current_type_fail_closed_without_species_fallback():
    unknown_damage, unknown_provenance = _inputs(current_types=[_unknown("self"), _type("opponent", ["water"])])
    unknown_q12 = invoke_existing_q12_from_snapshot(unknown_damage, stat_provenance=unknown_provenance, trusted_level=50)
    unknown_direct = evaluate_direct_damage_mechanics(unknown_damage, stat_provenance=unknown_provenance, trusted_level=50)
    malformed_damage, malformed_provenance = _inputs(current_types=[_type("self", ["fire"]), _type("self", ["water"])])
    malformed_q12 = invoke_existing_q12_from_snapshot(malformed_damage, stat_provenance=malformed_provenance, trusted_level=50)
    malformed_direct = evaluate_direct_damage_mechanics(malformed_damage, stat_provenance=malformed_provenance, trusted_level=50)
    assert unknown_q12["status"] == "unavailable" and unknown_q12["limitations"] == ["attacker.current_type"]
    assert unknown_direct["status"] == "insufficient_context" and unknown_direct["missing_inputs"] == ["attacker.current_type"]
    assert malformed_q12["status"] == malformed_direct["status"] == "unsupported_mechanic"
    assert malformed_q12["limitations"] == ["current_type_context"]


def test_omitted_current_type_keeps_legacy_evidence():
    damage, provenance = _inputs()
    formula = invoke_existing_q12_from_snapshot(damage, stat_provenance=provenance, trusted_level=50)
    assert formula["status"] == "resolved"
    assert formula["type_damage_evidence"] == {
        "attacker_type_authority": "legacy_species", "defender_type_authority": "legacy_species",
        "stab_basis": "legacy_species", "effectiveness_basis": "legacy_species",
        "current_type_override_used": False, "legacy_species_type_compatibility_used": True,
        "type_related_damage_supportability": "complete",
    }


def test_level_based_fixed_damage_keeps_its_legacy_type_boundary_when_current_type_is_unknown():
    snapshot = _snapshot(current_types=[_unknown("self"), _unknown("opponent")], move_id="seismic-toss")
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="seismic-toss", selectable_moves=("seismic-toss",), move_metadata={"category": "physical", "power": 1, "type": "normal"})
    result = evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)
    assert result["status"] == "known" and result["damage_model"] == "level_based_fixed"


@pytest.mark.parametrize(
    ("move_type", "attacker_types", "defender_types", "effectiveness"),
    [
        ("fire", ["fire"], ["normal"], 1.0),
        ("fire", ["water", "fire"], ["grass"], 2.0),
        ("fire", ["water", "fire"], ["water", "dragon"], 0.25),
        ("normal", ["normal"], ["ghost", "dark"], 0.0),
    ],
)
def test_formula_q12_uses_single_or_dual_current_types_without_species_union(move_type, attacker_types, defender_types, effectiveness):
    damage, provenance = _inputs(
        current_types=[_type("self", attacker_types), _type("opponent", defender_types)],
        move_id=f"current-{move_type}", move_type=move_type,
    )
    direct = evaluate_direct_damage_mechanics(damage, stat_provenance=provenance, trusted_level=50)
    assert direct["status"] == "known" and direct["type_effectiveness"] == effectiveness
    assert direct["type_damage_evidence"]["current_type_override_used"] is True
    assert direct["type_damage_evidence"]["legacy_species_type_compatibility_used"] is False


@pytest.mark.parametrize(
    ("current_types", "missing"),
    [
        ([_unknown("self"), _type("opponent", ["water"])], "attacker.current_type"),
        ([_type("self", ["fire"]), _unknown("opponent")], "defender.current_type"),
    ],
)
def test_formula_q12_requires_each_explicit_current_type_authority_independently(current_types, missing):
    damage, provenance = _inputs(current_types=current_types)
    q12 = invoke_existing_q12_from_snapshot(damage, stat_provenance=provenance, trusted_level=50)
    direct = evaluate_direct_damage_mechanics(damage, stat_provenance=provenance, trusted_level=50)
    assert q12["status"] == "unavailable" and q12["limitations"] == [missing]
    assert direct["status"] == "insufficient_context" and direct["missing_inputs"] == [missing]


def test_formula_q12_keeps_side_omission_legacy_compatible_without_converting_explicit_unknown():
    damage, provenance = _inputs(current_types=[_type("self", ["fire"])])
    formula = invoke_existing_q12_from_snapshot(damage, stat_provenance=provenance, trusted_level=50)
    evidence = formula["type_damage_evidence"]
    assert formula["status"] == "resolved"
    assert evidence["attacker_type_authority"] == "current_type_context"
    assert evidence["defender_type_authority"] == "legacy_species"
    assert evidence["current_type_override_used"] is True
    assert evidence["legacy_species_type_compatibility_used"] is True
