from copy import deepcopy

import pytest

from llm.advisor_direct_mechanics import evaluate_direct_damage_mechanics
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import SAME_TURN_EVENT_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection
from llm.advisor_turn_snapshot import BASE_STAT_KEYS, build_request_start_recommendation_snapshot, build_snapshot_damage_input, build_snapshot_stat_provenance


class _Species:
    def get(self, name):
        return {"en": name, "types_en": ["normal"], "base_stats": {key: 80 for key in BASE_STAT_KEYS}}


def _battle(projection=None):
    entries = []
    for side, pokemon, slot in (("self", "pikachu", 0), ("opponent", "eevee", 0)):
        entries.extend({"side": side, "stat": key, "value": 100 + index, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known", "provenance": {"side": side, "slot_index": slot, "pokemon_id": pokemon, "session_id": "s", "source": "user_confirmed_final_battle_stat", "trust": "user_confirmed_current"}} for index, key in enumerate(BASE_STAT_KEYS))
    absent = {"status": "known_absent"}
    direct_side = {"ability": absent, "item": absent, "boosts": {key: 0 for key in BASE_STAT_KEYS if key != "hp"}, "current_hp": 100, "max_hp": 100, "status": absent}
    return {"current_state_session_id": "s", "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 0}}, "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "avalanche"}]}, "final_stat_context": {"current_final_stats": entries}, "trusted_level_context": {"current_levels": [{"side": "self", "value": 50, "provenance": {"side": "self", "slot_index": 0, "pokemon_id": "pikachu", "session_id": "s", "source": "user_confirmed_current_level", "trust": "user_confirmed_current"}}]}, "direct_mechanics_context": {"generation": "gen9", "attacker": deepcopy(direct_side), "defender": deepcopy(direct_side), "field": {"weather": absent, "terrain": absent}}, "runtime_advice_state": projection}


def _event(boundary, predicate, occurred, *, subject, target, turn=4):
    return boundary.confirm(event_kind="same_turn_event_observed", payload={"predicate": predicate, "occurred": occurred, "target_side": target[0], "target_slot_index": 0, "target_pokemon_id": target[1]}, session_id="s", source=SAME_TURN_EVENT_SOURCE, trust=USER_TRUST, confirmed=True, side=subject[0], slot_index=0, pokemon_id=subject[1], turn_number=turn)


def test_confirmed_same_turn_events_project_only_for_matching_turn_and_active_identities():
    manager = BattleObservationRuntimeSessionManager.create("s", create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"])["manager"]
    boundary = LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})
    event = _event(boundary, "received_qualifying_direct_damage", True, subject=("self", "pikachu"), target=("opponent", "eevee"))
    assert manager.admit_confirmation("s", event)["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "applied"
    projection = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    current = build_request_start_recommendation_snapshot(_battle(projection), selectable_moves=("avalanche",), trusted_turn_context={"status": "available", "session_id": "s", "turn_number": 4, "source": "explicit_application_turn_state", "trust": "user_or_application_confirmed"}).to_dict()["current_state"]
    assert current["turn_event_context"]["events"][0]["predicate"] == "received_qualifying_direct_damage"
    next_turn = build_request_start_recommendation_snapshot(_battle(projection), selectable_moves=("avalanche",), trusted_turn_context={"status": "available", "session_id": "s", "turn_number": 5, "source": "explicit_application_turn_state", "trust": "user_or_application_confirmed"}).to_dict()["current_state"]
    assert next_turn["turn_event_context"]["events"] == []
    assert current["turn_event_context"] is not projection["field"]["same_turn_events"]


@pytest.mark.parametrize(("move", "metadata", "predicate", "subject", "target"), [("avalanche", {"category": "physical", "power": 60, "type": "ice"}, "received_qualifying_direct_damage", ("self", "pikachu"), ("opponent", "eevee")), ("revenge", {"category": "physical", "power": 60, "type": "fighting"}, "received_qualifying_direct_damage", ("self", "pikachu"), ("opponent", "eevee")), ("payback", {"category": "physical", "power": 50, "type": "dark"}, "acted_earlier_this_turn", ("opponent", "eevee"), ("self", "pikachu")), ("assurance", {"category": "physical", "power": 60, "type": "dark"}, "lost_hp_this_turn", ("opponent", "eevee"), ("self", "pikachu"))])
def test_turn_event_power_moves_consume_only_their_exact_trusted_predicate(move, metadata, predicate, subject, target):
    event = {"session_id": "s", "turn_number": 4, "predicate": predicate, "occurred": True, "side": subject[0], "slot_index": 0, "pokemon_id": subject[1], "target_side": target[0], "target_slot_index": 0, "target_pokemon_id": target[1], "provenance": {"event_kind": "same_turn_event_observed", "trust": "user_confirmed_observation"}}
    battle = _battle(); battle["moves"]["my_available_moves"][0]["move_id"] = move
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=(move,))
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id=move, selectable_moves=(move,), move_metadata=metadata)
    damage["battle_context"]["current_state"]["turn_event_context"] = {"status": "known", "projection_source": "runtime_same_turn_event_projection", "session_id": "s", "turn_number": 4, "events": [event]}
    result = evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)
    assert result["status"] == "known" and result["dynamic_power_evidence"]["effective_power"] == metadata["power"] * 2
    damage["battle_context"]["current_state"].pop("turn_event_context")
    missing = evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)
    assert missing["status"] == "insufficient_context" and "same_turn_event" in missing["missing_inputs"]


def test_turn_event_power_rejects_nonprojected_context_and_false_observation_keeps_base_power():
    battle = _battle(); snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("avalanche",))
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="avalanche", selectable_moves=("avalanche",), move_metadata={"category": "physical", "power": 60, "type": "ice"})
    event = {"session_id": "s", "turn_number": 4, "predicate": "received_qualifying_direct_damage", "occurred": False, "side": "self", "slot_index": 0, "pokemon_id": "pikachu", "target_side": "opponent", "target_slot_index": 0, "target_pokemon_id": "eevee", "provenance": {"event_kind": "same_turn_event_observed", "trust": "user_confirmed_observation"}}
    damage["battle_context"]["current_state"]["turn_event_context"] = {"status": "known", "session_id": "s", "turn_number": 4, "events": [event]}
    rejected = evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)
    assert rejected["status"] == "insufficient_context"
    damage["battle_context"]["current_state"]["turn_event_context"]["projection_source"] = "runtime_same_turn_event_projection"
    result = evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(snapshot, species_repository=_Species()), trusted_level=50)
    assert result["status"] == "known" and result["dynamic_power_evidence"]["effective_power"] == 60
