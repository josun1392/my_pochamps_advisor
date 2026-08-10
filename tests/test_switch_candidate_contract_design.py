"""Design-only conservative contract for future trusted self-switch candidates."""
from __future__ import annotations

from copy import deepcopy


def _project(*, session, active_slot, roster, legality="unsupported_mechanic"):
    """Fixture-only model: no reducer, ranking, provider, or switch simulation."""
    rows = []
    for slot in sorted(roster):
        pokemon = roster[slot]
        if not isinstance(slot, int) or not isinstance(pokemon, dict) or not pokemon.get("pokemon_id"):
            continue
        if slot == active_slot:
            continue
        fainted = pokemon.get("fainted", {"knowledge": "unknown"})
        availability, selectable, reason = "complete", False, "switch_legality_unsupported"
        if fainted is True:
            availability, reason = "complete", "target_fainted"
        elif fainted is False:
            if legality == "complete":
                selectable, reason = True, "switch_available"
            elif legality == "insufficient_context":
                reason = "switch_legality_unknown"
        else:
            availability, reason = "insufficient_context", "target_availability_unknown"
        rows.append({
            "candidate_id": f"self-switch:{session}:{slot}:{pokemon['pokemon_id']}",
            "action_kind": "switch",
            "target_slot_index": slot,
            "target_pokemon_identity": pokemon["pokemon_id"],
            "potential_target": True,
            "identity_supportability": "complete",
            "availability_supportability": availability,
            "switch_legality_supportability": legality if availability == "complete" and fainted is not True else "not_applicable",
            "selectable": selectable,
            "reason_code": reason,
        })
    return rows


def _roster(*rows):
    return {slot: {"pokemon_id": pokemon_id, "fainted": fainted} for slot, pokemon_id, fainted in rows}


def test_active_and_empty_slots_are_excluded_while_bench_slot_order_is_stable():
    rows = _project(session="s", active_slot=1, roster=_roster((1, "active", False), (3, "third", False), (2, "second", False)), legality="complete")
    assert [row["target_slot_index"] for row in rows] == [2, 3]
    assert [row["candidate_id"] for row in rows] == ["self-switch:s:2:second", "self-switch:s:3:third"]
    assert all(row["action_kind"] == "switch" and row["candidate_id"].startswith("self-switch:") for row in rows)


def test_availability_tri_state_preserves_potential_target_without_promoting_unknown():
    rows = _project(session="s", active_slot=0, roster=_roster((0, "active", False), (1, "ready", False), (2, "fainted", True), (3, "unknown", {"knowledge": "unknown"})), legality="complete")
    by_identity = {row["target_pokemon_identity"]: row for row in rows}
    assert by_identity["ready"]["selectable"] is True and by_identity["ready"]["reason_code"] == "switch_available"
    assert by_identity["fainted"]["selectable"] is False and by_identity["fainted"]["reason_code"] == "target_fainted"
    assert by_identity["unknown"]["potential_target"] is True
    assert by_identity["unknown"]["availability_supportability"] == "insufficient_context"
    assert by_identity["unknown"]["selectable"] is False and by_identity["unknown"]["reason_code"] == "target_availability_unknown"


def test_known_available_remains_nonselectable_when_prospective_legality_is_unknown_or_unsupported():
    roster = _roster((0, "active", False), (1, "bench", False))
    unknown = _project(session="s", active_slot=0, roster=roster, legality="insufficient_context")[0]
    unsupported = _project(session="s", active_slot=0, roster=roster, legality="unsupported_mechanic")[0]
    assert (unknown["switch_legality_supportability"], unknown["selectable"], unknown["reason_code"]) == ("insufficient_context", False, "switch_legality_unknown")
    assert (unsupported["switch_legality_supportability"], unsupported["selectable"], unsupported["reason_code"]) == ("unsupported_mechanic", False, "switch_legality_unsupported")


def test_duplicate_species_and_sessions_remain_identity_bound_and_move_namespace_cannot_collide():
    roster = _roster((0, "active", False), (1, "pikachu", False), (2, "pikachu", False))
    current = _project(session="session-a", active_slot=0, roster=roster, legality="complete")
    next_session = _project(session="session-b", active_slot=0, roster=roster, legality="complete")
    assert len({row["candidate_id"] for row in current}) == 2
    assert current[0]["candidate_id"] != next_session[0]["candidate_id"]
    assert all(not row["candidate_id"].startswith("self:") for row in current)


def test_frozen_projection_is_detached_and_historical_switch_observation_is_not_prospective_legality():
    roster = _roster((0, "active", False), (1, "bench", {"knowledge": "unknown"}))
    frozen = _project(session="s", active_slot=0, roster=roster, legality="unsupported_mechanic")
    later = deepcopy(roster); later[1]["fainted"] = False
    next_request = _project(session="s", active_slot=0, roster=later, legality="complete")
    assert frozen[0]["selectable"] is False and frozen[0]["reason_code"] == "target_availability_unknown"
    assert next_request[0]["selectable"] is True
    observed_switch_event = {"switch_in_slot_index": 1, "switch_in_pokemon_id": "bench"}
    assert observed_switch_event["switch_in_slot_index"] == 1
    assert frozen[0]["availability_supportability"] == "insufficient_context"
    assert frozen[0]["switch_legality_supportability"] == "not_applicable"


def test_contract_has_no_move_ranking_provider_or_transition_surface():
    candidate = _project(session="s", active_slot=0, roster=_roster((0, "active", False), (1, "bench", False)), legality="complete")[0]
    forbidden = {"move_id", "threat_tier", "rank", "provider_reason", "incoming_damage", "entry_hazard_damage", "action_order"}
    assert not (forbidden & set(candidate))
