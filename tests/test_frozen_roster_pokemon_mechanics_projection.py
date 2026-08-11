from copy import deepcopy
import json

from llm.advisor_candidate_contract import build_ui_recommendation_snapshot_summary
from llm.advisor_reducer_state_model import make_unknown_battle_fact
from llm.advisor_roster_mechanics import (
    active_self_roster_mechanics_view,
    build_self_roster_mechanics_context_projection,
)
from llm.advisor_switch_candidates import build_switch_candidate_context_projection, build_switch_candidates
from llm.advisor_switch_transition import project_authorized_switch_transition
from llm.advisor_turn_snapshot import build_request_start_recommendation_snapshot
from llm.advisor_prospective_entry_authority import build_prospective_entry_interactions, build_prospective_speed_stage


def _state(session="roster-s"):
    u = make_unknown_battle_fact
    return {"state_version": "battle-state-v1", "session_id": session, "last_applied_observation_sequence": None,
            "self_side": {"active_slot_index": 0, "side_conditions": u(), "pokemon": {
                0: {"pokemon_id": "pikachu-a", "current_hp": 80, "max_hp": 100, "fainted": False, "condition": "burn", "known_item": "light-ball"},
                1: {"pokemon_id": "pikachu-b", "current_hp": 120, "max_hp": 150, "fainted": False, "condition": u(), "known_item": u()},
            }}, "opponent_side": {"active_slot_index": 0, "side_conditions": u(), "pokemon": {0: {"pokemon_id": "x", "current_hp": u(), "max_hp": u(), "fainted": False, "condition": u(), "known_item": u()}}}, "field": {"weather": u(), "terrain": u()}}


def _known(record, *, current_type=None, defense=None, ability=None):
    if current_type is not None: record["current_type_authority"] = {"status": "known", "value": current_type}
    if defense is not None: record["final_stat_authority"] = {"status": "known", "value": {"defense": defense, "special-defense": defense}}
    if ability is not None: record["ability_authority"] = {"status": "known", "value": ability}
    record["hp_authority"] = {"status": "known", "current_hp": record["hp_authority"]["current_hp"], "maximum_hp": record["hp_authority"]["maximum_hp"], "provenance": "user_confirmed_current_hp"}


def _snapshot(state, roster):
    switch = build_switch_candidate_context_projection(state)
    return build_request_start_recommendation_snapshot({"current_state_session_id": state["session_id"], "switch_candidate_context": switch, "self_roster_mechanics_context": roster, "pokemon": {"my_active": {"name_en": "pikachu-a", "slot_index": 0}, "opponent_active": {"name_en": "x", "slot_index": 0}}, "moves": {"my_available_moves": []}}, selectable_moves=())


def test_identity_bound_roster_projection_isolates_active_bench_duplicate_species_and_partial_authority():
    state = _state(); base = build_self_roster_mechanics_context_projection(state); records = deepcopy(base["entries"])
    _known(records[0], current_type=["electric"], defense=70, ability="static")
    _known(records[1], current_type=["water"], defense=200, ability="water-absorb")
    frozen = build_self_roster_mechanics_context_projection(state, roster_mechanics_records=records)
    a, b = frozen["entries"]
    assert [row["pokemon_id"] for row in frozen["entries"]] == ["pikachu-a", "pikachu-b"]
    assert a["current_type_authority"]["value"] == ["electric"] and b["current_type_authority"]["value"] == ["water"]
    assert a["final_stat_authority"]["value"]["defense"] == 70 and b["final_stat_authority"]["value"]["defense"] == 200
    assert a["ability_authority"]["value"] == "static" and b["ability_authority"]["value"] == "water-absorb"
    assert b["item_authority"] == {"status": "unknown"} and b["persistent_condition_authority"] == {"status": "unknown"}
    assert active_self_roster_mechanics_view(frozen, slot_index=0, pokemon_id="pikachu-a") == a


def test_unknown_hp_fainted_and_session_ownership_are_preserved_without_fallback():
    state = _state(); state["self_side"]["pokemon"][1].update(current_hp=make_unknown_battle_fact(), max_hp=make_unknown_battle_fact(), fainted=make_unknown_battle_fact())
    frozen = build_self_roster_mechanics_context_projection(state)
    b = frozen["entries"][1]
    assert b["current_type_authority"] == b["final_stat_authority"] == b["ability_authority"] == {"status": "unknown"}
    assert b["hp_authority"] == {"status": "unknown", "current_hp": None, "maximum_hp": None, "provenance": "unqualified_runtime_state"}
    assert b["fainted_authority"] == {"status": "unknown"}
    stale = deepcopy(frozen); stale["session_id"] = "old"
    try:
        _snapshot(state, stale)
    except ValueError as error:
        assert str(error) == "invalid_roster_mechanics_context"
    else: raise AssertionError("stale roster authority accepted")


def test_snapshot_transition_handoff_and_provider_redaction_are_detached_and_do_not_change_selectability():
    state = _state(); base = build_self_roster_mechanics_context_projection(state); records = deepcopy(base["entries"]); _known(records[1], current_type=["water"], defense=200, ability="water-absorb")
    roster = build_self_roster_mechanics_context_projection(state, roster_mechanics_records=records); snapshot = _snapshot(state, roster)
    candidate = build_switch_candidates(turn_snapshot=snapshot)[0]
    transition = project_authorized_switch_transition(turn_snapshot=snapshot, switch_candidate=candidate, switch_authorized=True)
    assert transition["post_switch_snapshot"]["target_roster_mechanics"]["pokemon_id"] == "pikachu-b"
    assert transition["post_switch_snapshot"]["target_roster_mechanics"]["current_type_authority"]["value"] == ["water"]
    transition["post_switch_snapshot"]["target_roster_mechanics"]["pokemon_id"] = "forged"
    assert snapshot.to_dict()["current_state"]["self_roster_mechanics_context"]["entries"][1]["pokemon_id"] == "pikachu-b"
    assert candidate["selectable"] is False
    summary = build_ui_recommendation_snapshot_summary(battle_input={"pokemon": {}}, turn_snapshot=snapshot)
    assert "self_roster_mechanics_context" not in json.dumps(summary, sort_keys=True)


def test_prospective_entry_authorities_are_bound_to_the_bench_identity_only():
    state = _state()
    state["self_side"]["pokemon"][1]["prospective_speed_stage_context"] = build_prospective_speed_stage(session_id="roster-s", side="self", slot_index=1, pokemon_id="pikachu-b", stage=2)
    state["self_side"]["pokemon"][1]["prospective_entry_interactions_context"] = build_prospective_entry_interactions(session_id="roster-s", side="self", slot_index=1, pokemon_id="pikachu-b", toxic_spikes="applicable", sticky_web="blocked")
    frozen = build_self_roster_mechanics_context_projection(state)
    a, b = frozen["entries"]
    assert a["prospective_speed_stage_authority"] == {"status": "unknown"}
    assert b["prospective_speed_stage_authority"] == {"status": "known", "value": 2}
    assert b["prospective_entry_interactions_authority"] == {"toxic_spikes": "applicable", "sticky_web": "blocked"}
