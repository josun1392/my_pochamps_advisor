"""Sanitized practical-1.0 scenarios through the supported advisor seams.

These are deliberately integration fixtures: each scenario crosses a frozen
snapshot or lifecycle/replay boundary before asserting its final consumer.
"""
from copy import deepcopy

from llm.advisor_candidate_contract import evaluate_move_candidate
from llm.advisor_combined_action_recommendation import build_combined_action_envelope
from llm.advisor_direct_mechanics import evaluate_direct_damage_mechanics
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    FIRST_END_OF_TURN_SOURCE,
    SAME_TURN_EVENT_SOURCE,
    TAILWIND_SOURCE,
    TRICK_ROOM_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_reducer_state_model import make_unknown_battle_fact
from llm.advisor_roster_mechanics import build_self_roster_mechanics_context_projection
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection
from llm.advisor_switch_candidates import build_switch_candidate_context_projection, build_switch_candidates
from llm.advisor_switch_hazard_authority import build_switch_hazard_context
from llm.advisor_switch_incoming_evaluator import evaluate_switch_incoming_opponent_action
from llm.advisor_switch_transition import project_authorized_switch_transition
from llm.advisor_turn_snapshot import (
    BASE_STAT_KEYS,
    build_request_start_recommendation_snapshot,
    build_snapshot_damage_input,
    build_snapshot_stat_provenance,
    build_turn_snapshot_from_battle_input,
)


class _Species:
    def get(self, name):
        return {"en": name, "types_en": ["normal"], "base_stats": {key: 80 for key in BASE_STAT_KEYS}}


def _stats(value):
    return {"hp": value, "attack": value, "defense": value, "special-attack": value, "special-defense": value, "speed": value}


def _switch_state():
    unknown = make_unknown_battle_fact
    return {
        "state_version": "battle-state-v1", "session_id": "incoming-s", "last_applied_observation_sequence": None,
        "self_side": {"active_slot_index": 0, "side_conditions": unknown(), "pokemon": {
            0: {"pokemon_id": "a", "current_hp": 100, "max_hp": 100, "fainted": False, "condition": unknown(), "known_item": unknown()},
            1: {"pokemon_id": "b", "current_hp": 40, "max_hp": 200, "fainted": False, "condition": unknown(), "known_item": unknown()},
        }},
        "opponent_side": {"active_slot_index": 0, "side_conditions": unknown(), "pokemon": {0: {"pokemon_id": "x", "current_hp": unknown(), "max_hp": unknown(), "fainted": False, "condition": unknown(), "known_item": unknown()}}},
        "field": {"weather": unknown(), "terrain": unknown()},
    }


def _opponent_action():
    metadata = {"move_id": "tackle", "category": "physical", "power": 40, "type": "normal", "priority": 0, "target": "selected-pokemon"}
    side = lambda ident, which, types, value: {"pokemon_identity": ident, "side": which, "types": {"available": True, "value": types}, "type_authority": {"status": "known", "basis": "current_type_context"}, "base_stats": {"available": True, "value": _stats(value)}, "final_stats": {"available": True, "value": _stats(value)}}
    return {"candidate_id": "opponent-action:incoming-s:x:tackle:0", "role": "opponent_action", "acting_side": "opponent", "target_side": "self", "session_id": "incoming-s", "pokemon_identity": "x", "move_id": "tackle", "metadata_supportability": "complete", "move_metadata": metadata, "mechanics_snapshot": {"attacker": {"species_id": "x", "slot_index": 0}, "defender": {"species_id": "a", "slot_index": 0}, "move": {"slot_index": 0, "owner_species_id": "x", **metadata}, "battle_context": {"current_state": {"trusted_level_context": {"current_levels": [{"side": "opponent", "value": 50, "provenance": {"pokemon_id": "x", "slot_index": 0}}]}}, "stat_provenance": {"attacker": side("x", "opponent", ["normal"], 100), "defender": side("a", "self", ["fire"], 10)}}}}


def _switch_snapshot(*, hazards=True, item=None, ability=None, hp=40):
    state = _switch_state()
    if hazards:
        state["switch_hazard_context"] = build_switch_hazard_context(session_id="incoming-s", affected_side="self", stealth_rock="absent", spikes_layers=3)
        state["self_side"]["pokemon"][1]["prospective_groundedness_context"] = {"schema_version": "identity-groundedness-v1", "session_id": "incoming-s", "side": "self", "slot_index": 1, "pokemon_id": "b", "status": "grounded"}
    records = deepcopy(build_self_roster_mechanics_context_projection(state)["entries"])
    records[1].update({"current_type_authority": {"status": "known", "value": ["water"]}, "base_stat_authority": {"status": "known", "value": _stats(200)}, "final_stat_authority": {"status": "known", "value": _stats(200)}, "hp_authority": {"status": "known", "current_hp": hp, "maximum_hp": 200, "provenance": "user_confirmed_current_hp"}, "item_authority": {"status": "known", "value": item}, "ability_authority": {"status": "known", "value": ability}})
    roster = build_self_roster_mechanics_context_projection(state, roster_mechanics_records=records)
    snapshot = build_request_start_recommendation_snapshot({"current_state_session_id": "incoming-s", "switch_candidate_context": build_switch_candidate_context_projection(state), "self_roster_mechanics_context": roster, "switch_hazard_context": state.get("switch_hazard_context"), "pokemon": {"my_active": {"name_en": "a", "slot_index": 0}, "opponent_active": {"name_en": "x", "slot_index": 0}}, "moves": {"my_available_moves": []}}, selectable_moves=())
    candidate = dict(build_switch_candidates(turn_snapshot=snapshot)[0], selectable=True)
    return snapshot, candidate


def _prepared(snapshot, candidate, *, move=True, opponent_actions=()):
    return {"candidates": [{"slot_index": 0, "move": "tackle", "availability": "available"}] if move else [], "evidence_bundle": {"turn_snapshot": snapshot, "switch_candidates": [candidate], "known_opponent_threat_summaries": {"threat_summaries": []}, "opponent_action_candidates": list(opponent_actions)}}


def test_proven_entry_hazard_ko_reaches_final_move_over_switch_recommendation():
    snapshot, candidate = _switch_snapshot(hazards=True, hp=40)
    envelope = build_combined_action_envelope(prepared_cycle=_prepared(snapshot, candidate))
    assert envelope["action_kind"] == "move"
    assert envelope["danger_tier"] == "neutral_no_positive_danger"


def test_same_danger_tier_preserves_move_preference_and_hard_blocked_switch_is_not_selected():
    snapshot, candidate = _switch_snapshot(hazards=False, hp=200)
    same_tier = build_combined_action_envelope(prepared_cycle=_prepared(snapshot, candidate))
    assert same_tier["action_kind"] == "move" and same_tier["selection_reason"] == "same_tier_move_preference"
    blocked = dict(candidate, selectable=False, reason_code="hard_blocked")
    only_switch = build_combined_action_envelope(prepared_cycle=_prepared(snapshot, blocked, move=False))
    assert only_switch["selection_status"] == "no_selectable_action"


def test_switch_transition_carries_focus_sash_to_the_direct_incoming_consumer():
    snapshot, candidate = _switch_snapshot(hazards=False, item="focus-sash", hp=200)
    transition = project_authorized_switch_transition(turn_snapshot=snapshot, switch_candidate=candidate, switch_authorized=True, opponent_action=_opponent_action())
    result = evaluate_switch_incoming_opponent_action(transition=transition)
    assert result["direct_incoming_supportability"] == "complete"
    assert result["damage_evidence"]["ko_interpretation"]["ko_supportability"] == "complete"


def _manager(*, hp=None, item=None):
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    if hp is not None:
        state["self_side"]["pokemon"][0].update(current_hp=hp, max_hp=100, known_item=item, fainted=False)
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _boundary():
    return LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})


def _apply(manager, confirmation):
    assert manager.admit_confirmation("s", confirmation)["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "applied"


def _action_snapshot(projection):
    return build_turn_snapshot_from_battle_input({"pokemon": {"my_active": {"slot_index": 0, "name_en": "pikachu", "name_ko": "Pikachu"}, "opponent_active": {"slot_index": 0, "name_en": "eevee", "name_ko": "Eevee"}}, "item_profiles": {"my_active": {}, "opponent_active": {}}, "moves": {"my_selected_move": {}}, "current_state_session_id": "s", "runtime_advice_state": projection}).to_dict()["current_state"]


def test_observed_tailwind_and_trick_room_flow_through_lifecycle_to_action_order():
    manager, boundary = _manager(), _boundary()
    for side in ("self", "opponent"):
        _apply(manager, boundary.confirm(event_kind="tailwind_side_condition_observed", payload={"status": "inactive"}, session_id="s", source=TAILWIND_SOURCE, trust=USER_TRUST, confirmed=True, side=side))
    _apply(manager, boundary.confirm(event_kind="trick_room_field_observed", payload={"status": "active"}, session_id="s", source=TRICK_ROOM_SOURCE, trust=USER_TRUST, confirmed=True))
    current = _action_snapshot(build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"])
    action = {"final_stat_context": {"current_final_stats": [{"side": "self", "stat": "speed", "value": 100, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}, {"side": "opponent", "stat": "speed", "value": 150, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}]}, "condition_context": {"current_conditions": [{"side": side, "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"} for side in ("self", "opponent")]}, "opponent_selected_move": {"move_id": "scratch"}, "field_state_context": current["field_state_context"]}
    result = evaluate_move_candidate(slot_index=0, move="tackle", battle_snapshot=action, repositories={"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}, "scratch": {"category": "physical", "power": 40, "type": "normal", "priority": 0}})
    assert result["action_order"]["status"] == "acts_first" and result["action_order"]["trick_room"] == "active"


def test_observed_same_turn_event_and_first_end_of_turn_hp_recovery_reach_frozen_consumers():
    manager, boundary = _manager(hp=80, item="leftovers"), _boundary()
    _apply(manager, boundary.confirm(event_kind="same_turn_event_observed", payload={"predicate": "received_qualifying_direct_damage", "occurred": True, "target_side": "opponent", "target_slot_index": 0, "target_pokemon_id": "eevee"}, session_id="s", source=SAME_TURN_EVENT_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", turn_number=4))
    projection = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    stats = [{"side": side, "stat": key, "value": 100, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known", "provenance": {"side": side, "slot_index": 0, "pokemon_id": name, "session_id": "s", "source": "user_confirmed_final_battle_stat", "trust": "user_confirmed_current"}} for side, name in (("self", "pikachu"), ("opponent", "eevee")) for key in BASE_STAT_KEYS]
    battle = {"current_state_session_id": "s", "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 0}}, "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "avalanche"}]}, "final_stat_context": {"current_final_stats": stats}, "condition_context": {"current_conditions": [{"side": side, "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"} for side in ("self", "opponent")]}, "field_state_context": {"current_field": {"weather": "none", "terrain": "none"}, "side_effects": []}, "trusted_level_context": {"current_levels": [{"side": "self", "value": 50, "provenance": {"side": "self", "slot_index": 0, "pokemon_id": "pikachu", "session_id": "s", "source": "user_confirmed_current_level", "trust": "user_confirmed_current"}}]}, "direct_mechanics_context": {"generation": "gen9", "attacker": {"ability": {"status": "known_absent"}, "item": {"status": "known_absent"}, "boosts": {key: 0 for key in BASE_STAT_KEYS if key != "hp"}, "current_hp": 100, "max_hp": 100, "status": {"status": "known_absent"}}, "defender": {"ability": {"status": "known_absent"}, "item": {"status": "known_absent"}, "boosts": {key: 0 for key in BASE_STAT_KEYS if key != "hp"}, "current_hp": 100, "max_hp": 100, "status": {"status": "known_absent"}}, "field": {"weather": {"status": "known_absent"}, "terrain": {"status": "known_absent"}}}, "runtime_advice_state": projection}
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=("avalanche",), trusted_turn_context={"status": "available", "session_id": "s", "turn_number": 4, "source": "explicit_application_turn_state", "trust": "user_or_application_confirmed"})
    event_context = snapshot.to_dict()["current_state"]["turn_event_context"]
    assert event_context["events"][0]["predicate"] == "received_qualifying_direct_damage"
    direct_battle = deepcopy(battle)
    for key in ("runtime_advice_state", "condition_context", "field_state_context"):
        direct_battle.pop(key)
    direct_snapshot = build_request_start_recommendation_snapshot(direct_battle, selectable_moves=("avalanche",))
    damage = build_snapshot_damage_input(direct_snapshot, candidate_slot_index=0, candidate_move_id="avalanche", selectable_moves=("avalanche",), move_metadata={"category": "physical", "power": 60, "type": "ice"})
    damage["battle_context"]["current_state"]["turn_event_context"] = event_context
    result = evaluate_direct_damage_mechanics(damage, stat_provenance=build_snapshot_stat_provenance(direct_snapshot, species_repository=_Species()), trusted_level=50)
    assert result["dynamic_power_evidence"]["effective_power"] == 120
    recovery_manager, recovery_boundary = _manager(hp=80, item="leftovers"), _boundary()
    _apply(recovery_manager, recovery_boundary.confirm(event_kind="first_end_of_turn_reached_observed", payload={}, session_id="s", source=FIRST_END_OF_TURN_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=4))
    recovered = _action_snapshot(build_runtime_advice_state_projection(recovery_manager.read_state()["state"])["runtime_advice_state"])
    assert recovered["runtime_advice_state"]["self"]["active_pokemon"]["current_hp"]["value"] == 86


def test_incomplete_candidate_authority_never_becomes_safe_switch_damage_evidence():
    snapshot, candidate = _switch_snapshot(hazards=False, hp=200)
    serialized = snapshot.to_dict()
    serialized["current_state"]["self_roster_mechanics_context"]["entries"][1]["current_type_authority"] = {"status": "unknown"}
    transition = project_authorized_switch_transition(turn_snapshot=type("Snapshot", (), {"to_dict": lambda self: deepcopy(serialized)})(), switch_candidate=candidate, switch_authorized=True, opponent_action=_opponent_action())
    result = evaluate_switch_incoming_opponent_action(transition=transition)
    assert result["direct_incoming_supportability"] == "insufficient_context"
    assert result["damage_evidence"]["status"] == "insufficient_context"
