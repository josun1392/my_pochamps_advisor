from copy import deepcopy

from llm.advisor_executable_switch_transition import execute_manual_switch_then_direct
from llm.advisor_transition_preview import fingerprint_transition_preview_state


def _owner(side, slot, pokemon): return {"session_id": "switch-exec", "side": side, "slot_index": slot, "pokemon_id": pokemon}


def _branch():
    return {"schema_version": "deterministic-transition-preview-v1", "active": {"self": {**_owner("self", 0, "outgoing"), "current_hp": 90, "max_hp": 100, "fainted": False}, "opponent": {**_owner("opponent", 0, "opponent"), "current_hp": 100, "max_hp": 100, "fainted": False}}, "current_state": {"current_state_session_id": "switch-exec", "outgoing": "must-not-leak"}}


def _incoming(hp=80):
    absent = {"status": "known_absent"}; side = lambda current: {"ability": absent, "item": absent, "boosts": {"attack": 0, "defense": 0, "special-attack": 0, "special-defense": 0, "speed": 0}, "current_hp": current, "max_hp": 100, "status": absent}
    return {"owner": _owner("self", 1, "incoming"), "provenance": "identity_bound_incoming_current_state_v1", "hp_authority": {"status": "known", "current_hp": hp, "maximum_hp": 100, "provenance": "incoming"}, "fainted_authority": {"status": "known", "value": False}, "current_state": {"current_state_session_id": "switch-exec", "current_hp_context": {"current_hp": [{"side": "self", "current_hp": hp, "maximum_hp": 100}, {"side": "opponent", "current_hp": 100, "maximum_hp": 100}]}, "direct_mechanics_context": {"generation": "gen9", "attacker": side(hp), "defender": side(100)}}}


def _snapshot(*, rock="present", spikes=1, toxic=0, sticky="absent"):
    target = {"session_id": "switch-exec", "side": "self", "slot_index": 1, "pokemon_id": "incoming", "hp_authority": {"status": "known", "current_hp": 80, "maximum_hp": 100, "provenance": "incoming"}, "item_authority": {"status": "known", "value": None}, "ability_authority": {"status": "known", "value": "torrent"}, "current_type_authority": {"status": "known", "value": ["fire"]}, "prospective_groundedness_authority": {"status": "grounded"}, "persistent_condition_authority": {"status": "known", "value": "none"}, "prospective_entry_interactions_authority": {"toxic_spikes": "applicable", "sticky_web": "applicable"}, "prospective_speed_stage_authority": {"status": "known", "value": 0}, "prospective_offensive_stages_authority": {"attack": 0, "special-attack": 0}}
    return {"current_state": {"switch_candidate_context": {"session_id": "switch-exec", "self_active_slot_index": 0, "self_pokemon": [{"slot_index": 0, "pokemon_id": "outgoing", "fainted": {"status": "known", "value": False}}, {"slot_index": 1, "pokemon_id": "incoming", "fainted": {"status": "known", "value": False}}]}, "self_roster_mechanics_context": {"session_id": "switch-exec", "side": "self", "entries": [target]}, "switch_hazard_context": {"schema_version": "switch-hazard-context-v2", "session_id": "switch-exec", "affected_side": "self", "stealth_rock": rock, "spikes_layers": spikes, "toxic_spikes_layers": toxic, "sticky_web": sticky}}}


def _candidate(selectable=True): return {"candidate_id": "self-switch:switch-exec:1:incoming", "action_kind": "switch", "session_id": "switch-exec", "target_slot_index": 1, "target_pokemon_id": "incoming", "selectable": selectable, "reason_code": "switch_available" if selectable else "switch_blocked"}


def _opponent():
    return {"owner": _owner("opponent", 0, "opponent"), "move": {"move_id": "seismic-toss", "slot_index": 0, "priority": 0, "category": "physical"}}


def _descriptor(source):
    return {"source_snapshot_fingerprint": source, "owner": _owner("opponent", 0, "opponent"), "move_metadata": {**_opponent()["move"], "type": "normal"}, "stat_provenance": {"attacker": {"pokemon_identity": "opponent", "types": {"available": True, "value": ["normal"]}, "known_item": {"status": "known_absent"}}, "defender": {"pokemon_identity": "incoming", "types": {"available": True, "value": ["fire"]}, "known_item": {"status": "known_absent"}}}, "trusted_level": 50}


def test_switch_materializes_then_applies_combined_sr_spikes_before_fresh_incoming_direct():
    branch = _branch(); before = deepcopy(branch)
    source = fingerprint_transition_preview_state(branch)
    result = execute_manual_switch_then_direct(source_branch=branch, source_branch_fingerprint=source, switch_snapshot=_snapshot(), switch_candidate=_candidate(), incoming_authority=_incoming(), opponent_action=_opponent(), opponent_direct_evaluation_input=_descriptor(source))
    assert result["status"] == "resolved", result
    # Fire takes 25 from Stealth Rock and 12 from one Spikes layer, then the
    # fresh level-based opponent hit uses the entry-adjusted incoming state.
    assert result["post_entry_branch_fingerprint"] == result["direct_evaluation"]["branch_state_fingerprint"]
    assert result["entry_effect_result"]["damage"] == 37
    assert result["next_state"]["active"]["self"]["pokemon_id"] == "incoming"
    assert result["next_state"]["active"]["self"]["current_hp"] == 0
    assert branch == before and "outgoing" not in result["next_state"]["current_state"]


def test_blocked_or_unsupported_entry_effects_fail_closed_without_materializing_execution():
    branch = _branch(); source = fingerprint_transition_preview_state(branch)
    blocked = execute_manual_switch_then_direct(source_branch=branch, source_branch_fingerprint=source, switch_snapshot=_snapshot(), switch_candidate=_candidate(False), incoming_authority=_incoming(), opponent_action=_opponent(), opponent_direct_evaluation_input=_descriptor(source))
    assert blocked == {"status": "incomplete", "reason": "switch_legality_unknown_or_blocked"}
    toxic = execute_manual_switch_then_direct(source_branch=branch, source_branch_fingerprint=source, switch_snapshot=_snapshot(toxic=1), switch_candidate=_candidate(), incoming_authority=_incoming(), opponent_action=_opponent(), opponent_direct_evaluation_input=_descriptor(source))
    assert toxic == {"status": "unsupported", "reason": "unsupported_material_switch_entry_effect"}
