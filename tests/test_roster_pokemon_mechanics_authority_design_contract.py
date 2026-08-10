"""Design matrix for future identity-bound self roster mechanics authority."""
from __future__ import annotations

from copy import deepcopy


def _record(*, session: str, slot: int, pokemon_id: str, type_state="unknown", hp_state="unknown"):
    return {
        "session_id": session, "side": "self", "slot_index": slot, "pokemon_id": pokemon_id,
        "current_type_authority": {"supportability": type_state, "value": ["water"] if type_state == "complete" else None},
        "final_stat_authority": {"supportability": "complete", "value": {"defense": 200, "special-defense": 180}} if type_state == "complete" else {"supportability": "insufficient_context", "value": None},
        "ability_authority": {"supportability": type_state, "value": "water-absorb" if type_state == "complete" else None},
        "item_authority": {"supportability": "complete", "value": "leftovers"},
        "hp_authority": {"supportability": hp_state, "precision": "exact" if hp_state == "complete" else "unknown", "current_hp": 120 if hp_state == "complete" else None, "maximum_hp": 200 if hp_state == "complete" else None},
        "fainted_authority": {"supportability": "complete", "value": False},
        "persistent_condition_authority": {"supportability": "complete", "value": "burn"},
    }


def test_active_and_bench_authority_are_identity_bound_not_side_or_species_bound():
    a = _record(session="s", slot=0, pokemon_id="charizard-a", type_state="complete", hp_state="complete")
    b = _record(session="s", slot=1, pokemon_id="blastoise-b", type_state="complete", hp_state="complete")
    a["current_type_authority"]["value"] = ["fire", "flying"]
    a["final_stat_authority"]["value"]["defense"] = 100
    a["ability_authority"]["value"] = "blaze"
    assert a["pokemon_id"] != b["pokemon_id"]
    assert a["current_type_authority"]["value"] != b["current_type_authority"]["value"]
    assert a["final_stat_authority"]["value"]["defense"] != b["final_stat_authority"]["value"]["defense"]
    assert a["ability_authority"]["value"] != b["ability_authority"]["value"]


def test_unknown_bench_and_hp_provenance_never_gain_values_from_active_or_defaults():
    active = _record(session="s", slot=0, pokemon_id="a", type_state="complete", hp_state="complete")
    bench = _record(session="s", slot=1, pokemon_id="b")
    assert bench["current_type_authority"]["value"] is None
    assert bench["final_stat_authority"]["value"] is None
    assert bench["ability_authority"]["value"] is None
    assert bench["hp_authority"] == {"supportability": "unknown", "precision": "unknown", "current_hp": None, "maximum_hp": None}
    assert active["hp_authority"]["current_hp"] != bench["hp_authority"]["current_hp"]


def test_duplicate_species_session_and_switch_back_preserve_identity_and_frozen_detachment():
    first = _record(session="s1", slot=1, pokemon_id="pikachu-a", type_state="complete", hp_state="complete")
    second = _record(session="s1", slot=2, pokemon_id="pikachu-b")
    frozen = deepcopy([first, second])
    assert frozen[0]["pokemon_id"] != frozen[1]["pokemon_id"] and frozen[0]["slot_index"] != frozen[1]["slot_index"]
    # A switch-back selects the same B record; it does not create a species record.
    assert next(row for row in frozen if row["pokemon_id"] == "pikachu-b")["session_id"] == "s1"
    later = deepcopy(frozen); later[1]["hp_authority"]["supportability"] = "complete"
    assert frozen[1]["hp_authority"]["supportability"] == "unknown"
    stale = _record(session="s0", slot=2, pokemon_id="pikachu-b")
    assert (stale["session_id"], stale["slot_index"], stale["pokemon_id"]) != (frozen[1]["session_id"], frozen[1]["slot_index"], frozen[1]["pokemon_id"])


def test_side_field_and_action_facts_are_not_roster_pokemon_authority():
    record = _record(session="s", slot=1, pokemon_id="b")
    forbidden = {"screens", "tailwind", "hazards", "weather", "terrain", "trick_room", "selected_move", "pair_evidence", "threat_tier", "provider_payload"}
    assert forbidden.isdisjoint(record)
    assert "stat_stage_authority" not in record  # temporary stages stay distinct from final stats
