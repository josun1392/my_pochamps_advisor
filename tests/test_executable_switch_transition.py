from copy import deepcopy

from llm.advisor_executable_switch_transition import execute_manual_switch_then_direct
from llm.advisor_transition_preview import fingerprint_transition_preview_state


def _owner(side, slot, pokemon): return {"session_id": "switch-exec", "side": side, "slot_index": slot, "pokemon_id": pokemon}


def _branch():
    return {"schema_version": "deterministic-transition-preview-v1", "active": {"self": {**_owner("self", 0, "outgoing"), "current_hp": 90, "max_hp": 100, "fainted": False}, "opponent": {**_owner("opponent", 0, "opponent"), "current_hp": 100, "max_hp": 100, "fainted": False}}, "current_state": {"current_state_session_id": "switch-exec", "outgoing": "must-not-leak"}}


def _incoming(hp=80, ability="torrent", opponent_attack=0, opponent_ability="blaze", attack=0, special_attack=0):
    absent = {"status": "known_absent"}; side = lambda current, attack=0: {"ability": absent, "item": absent, "boosts": {"attack": attack, "defense": 0, "special-attack": 0, "special-defense": 0, "speed": 0}, "current_hp": current, "max_hp": 100, "status": absent}
    return {"owner": _owner("self", 1, "incoming"), "provenance": "identity_bound_incoming_current_state_v1", "hp_authority": {"status": "known", "current_hp": hp, "maximum_hp": 100, "provenance": "incoming"}, "fainted_authority": {"status": "known", "value": False}, "current_state": {"current_state_session_id": "switch-exec", "current_hp_context": {"current_hp": [{"side": "self", "current_hp": hp, "maximum_hp": 100}, {"side": "opponent", "current_hp": 100, "maximum_hp": 100}]}, "condition_context": {"current_conditions": [{"side": "self", "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition"}, {"side": "opponent", "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition"}]}, "ability_context": {"current_abilities": [{"side": "self", "ability": ability, "status": "user_confirmed", "source": "user_confirmed_current_ability"}, {"side": "opponent", "ability": opponent_ability, "status": "user_confirmed", "source": "user_confirmed_current_ability"}]}, "stat_stage_context": {"current_stages": [{"side": "self", "stat": "speed", "stage": 0, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}, {"side": "self", "stat": "defense", "stage": 0, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}, {"side": "self", "stat": "attack", "stage": attack, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}, {"side": "self", "stat": "special-attack", "stage": special_attack, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}, {"side": "opponent", "stat": "attack", "stage": opponent_attack, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}, {"side": "opponent", "stat": "defense", "stage": 0, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}, {"side": "opponent", "stat": "special-defense", "stage": 0, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}]}, "direct_mechanics_context": {"generation": "gen9", "attacker": side(hp), "defender": side(100, opponent_attack), "field": {"weather": absent, "terrain": absent}}}}


def _snapshot(*, rock="present", spikes=1, toxic=0, sticky="absent", ability="torrent", intimidate=None, download=None, attack=0, special_attack=0):
    target = {"session_id": "switch-exec", "side": "self", "slot_index": 1, "pokemon_id": "incoming", "hp_authority": {"status": "known", "current_hp": 80, "maximum_hp": 100, "provenance": "incoming"}, "item_authority": {"status": "known", "value": None}, "ability_authority": {"status": "known", "value": ability}, "current_type_authority": {"status": "known", "value": ["fire"]}, "prospective_groundedness_authority": {"status": "grounded"}, "persistent_condition_authority": {"status": "known", "value": "none"}, "prospective_entry_interactions_authority": {"toxic_spikes": "applicable", "sticky_web": "applicable"}, "prospective_speed_stage_authority": {"status": "known", "value": 0}, "prospective_offensive_stages_authority": {"attack": attack, "special-attack": special_attack}}
    state = {"switch_candidate_context": {"session_id": "switch-exec", "self_active_slot_index": 0, "self_pokemon": [{"slot_index": 0, "pokemon_id": "outgoing", "fainted": {"status": "known", "value": False}}, {"slot_index": 1, "pokemon_id": "incoming", "fainted": {"status": "known", "value": False}}]}, "self_roster_mechanics_context": {"session_id": "switch-exec", "side": "self", "entries": [target]}, "switch_hazard_context": {"schema_version": "switch-hazard-context-v2", "session_id": "switch-exec", "affected_side": "self", "stealth_rock": rock, "spikes_layers": spikes, "toxic_spikes_layers": toxic, "sticky_web": sticky}}
    if intimidate is not None: state["switch_entry_intimidate_authority"] = intimidate
    if download is not None: state["switch_entry_download_authority"] = download
    return {"current_state": state}


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
    assert toxic["status"] == "resolved" and toxic["next_state"]["predicted_condition_context"]["condition_type"] == "poison"


def test_entry_hp_ko_stops_before_sticky_web_toxic_spikes_or_opponent_action():
    branch = _branch(); source = fingerprint_transition_preview_state(branch)
    result = execute_manual_switch_then_direct(
        source_branch=branch, source_branch_fingerprint=source,
        switch_snapshot=_snapshot(toxic=2, sticky="present"),
        switch_candidate=_candidate(), incoming_authority=_incoming(hp=1),
        opponent_action=_opponent(), opponent_direct_evaluation_input=_descriptor(source),
    )
    assert result["status"] == "unsupported"
    assert result["reason"] == "replacement_required_after_entry_hazard_ko"
    state = result["next_state"]
    assert state["active"]["self"]["fainted"] is True
    assert state["current_state"]["stat_stage_context"]["current_stages"][0]["stage"] == 0
    assert "predicted_condition_context" not in state and "direct_evaluation" not in result


def test_intimidate_mutates_only_exact_opponent_attack_stage_before_fresh_direct():
    from llm.advisor_hypothetical_direct_mechanics import evaluate_hypothetical_direct_mechanics
    from llm.advisor_switch_entry_intimidate_authority import build_switch_entry_intimidate_authority

    branch = _branch(); source = fingerprint_transition_preview_state(branch)
    authority = build_switch_entry_intimidate_authority(
        session_id="switch-exec", source={"side": "self", "slot_index": 1, "pokemon_id": "incoming"},
        target={"side": "opponent", "slot_index": 0, "pokemon_id": "opponent"},
        interaction="lowered", target_attack_stage=0,
    )
    result = execute_manual_switch_then_direct(
        source_branch=branch, source_branch_fingerprint=source,
        switch_snapshot=_snapshot(rock="absent", spikes=0, ability="intimidate", intimidate=authority),
        switch_candidate=_candidate(), incoming_authority=_incoming(ability="intimidate", opponent_ability="sturdy"),
        opponent_action=_opponent(), opponent_direct_evaluation_input=_descriptor(source),
    )
    assert result["status"] == "resolved", result
    state = result["next_state"]
    opponent_stage = next(row for row in state["current_state"]["stat_stage_context"]["current_stages"] if row["side"] == "opponent" and row["stat"] == "attack")
    assert opponent_stage["stage"] == -1
    assert state["current_state"]["direct_mechanics_context"]["defender"]["boosts"]["attack"] == 0
    assert result["direct_evaluation"]["branch_state_fingerprint"] == result["post_entry_branch_fingerprint"]
    assert any(row["event"] == "switch_entry_intimidate" for row in result["consequence_trace"])

    physical = {"owner": _owner("opponent", 0, "opponent"), "move": {"move_id": "tackle", "slot_index": 1, "priority": 0, "category": "physical"}}
    stats = {"hp": 100, "attack": 100, "defense": 100, "special-attack": 100, "special-defense": 100, "speed": 100}
    descriptor = {"source_snapshot_fingerprint": source, "owner": physical["owner"], "move_metadata": {**physical["move"], "power": 40, "type": "normal"}, "stat_provenance": {"attacker": {"pokemon_identity": "opponent", "types": {"available": True, "value": ["normal"]}, "final_stats": {"available": True, "value": stats}, "known_item": {"status": "known_absent"}}, "defender": {"pokemon_identity": "incoming", "types": {"available": True, "value": ["fire"]}, "final_stats": {"available": True, "value": stats}, "known_item": {"status": "known_absent"}}}, "trusted_level": 50}
    direct_state = deepcopy(state)
    direct_state["current_state"].pop("ability_context")
    lowered = evaluate_hypothetical_direct_mechanics(branch_state=direct_state, source_snapshot_fingerprint=source, action=physical, expected_owner=physical["owner"], direct_evaluation_input=descriptor)
    baseline_state = deepcopy(direct_state)
    next(row for row in baseline_state["current_state"]["stat_stage_context"]["current_stages"] if row["side"] == "opponent" and row["stat"] == "attack")["stage"] = 0
    baseline = evaluate_hypothetical_direct_mechanics(branch_state=baseline_state, source_snapshot_fingerprint=source, action=physical, expected_owner=physical["owner"], direct_evaluation_input=descriptor)
    assert lowered["status"] == baseline["status"] == "known"
    assert lowered["mechanics_result"]["damage_range"]["maximum"] < baseline["mechanics_result"]["damage_range"]["maximum"]

    from llm.advisor_end_of_turn_preview import project_poison_end_of_turn
    from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=project_poison_end_of_turn(pre_end_of_turn=result))
    assert handoff["status"] == "resolved"
    turn_two_stage = next(row for row in handoff["next_state"]["current_state"]["stat_stage_context"]["current_stages"] if row["side"] == "opponent" and row["stat"] == "attack")
    assert turn_two_stage["stage"] == -1
    assert handoff["resulting_branch_fingerprint"] != result["resulting_branch_fingerprint"]


def test_intimidate_missing_or_foreign_authority_fails_closed():
    from llm.advisor_switch_entry_intimidate_authority import build_switch_entry_intimidate_authority

    branch = _branch(); source = fingerprint_transition_preview_state(branch)
    missing = execute_manual_switch_then_direct(
        source_branch=branch, source_branch_fingerprint=source,
        switch_snapshot=_snapshot(rock="absent", spikes=0, ability="intimidate"),
        switch_candidate=_candidate(), incoming_authority=_incoming(ability="intimidate"),
        opponent_action=_opponent(), opponent_direct_evaluation_input=_descriptor(source),
    )
    assert missing == {"status": "incomplete", "reason": "switch_entry_authority"}
    foreign = build_switch_entry_intimidate_authority(
        session_id="switch-exec", source={"side": "self", "slot_index": 0, "pokemon_id": "outgoing"},
        target={"side": "opponent", "slot_index": 0, "pokemon_id": "opponent"}, interaction="lowered", target_attack_stage=0,
    )
    rejected = execute_manual_switch_then_direct(
        source_branch=branch, source_branch_fingerprint=source,
        switch_snapshot=_snapshot(rock="absent", spikes=0, ability="intimidate", intimidate=foreign),
        switch_candidate=_candidate(), incoming_authority=_incoming(ability="intimidate"),
        opponent_action=_opponent(), opponent_direct_evaluation_input=_descriptor(source),
    )
    assert rejected == {"status": "incomplete", "reason": "switch_entry_authority"}


def test_download_raises_exact_selected_offensive_stage_and_handoff_preserves_it():
    from llm.advisor_end_of_turn_preview import project_poison_end_of_turn
    from llm.advisor_hypothetical_direct_mechanics import evaluate_hypothetical_direct_mechanics
    from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
    from llm.advisor_switch_entry_download_authority import build_switch_entry_download_authority

    branch = _branch(); source = fingerprint_transition_preview_state(branch)
    authority = build_switch_entry_download_authority(
        session_id="switch-exec", source={"side": "self", "slot_index": 1, "pokemon_id": "incoming"},
        target={"side": "opponent", "slot_index": 0, "pokemon_id": "opponent"},
        applicability="applicable", target_defense=90, target_special_defense=100,
    )
    result = execute_manual_switch_then_direct(
        source_branch=branch, source_branch_fingerprint=source,
        switch_snapshot=_snapshot(rock="absent", spikes=0, ability="download", download=authority),
        switch_candidate=_candidate(), incoming_authority=_incoming(ability="download"),
        opponent_action=_opponent(), opponent_direct_evaluation_input=_descriptor(source),
    )
    assert result["status"] == "resolved", result
    stages = {(row["side"], row["stat"]): row["stage"] for row in result["next_state"]["current_state"]["stat_stage_context"]["current_stages"]}
    assert stages[("self", "attack")] == 1 and stages[("self", "special-attack")] == 0
    assert any(row["event"] == "switch_entry_download" and row["boosted_stat"] == "attack" for row in result["consequence_trace"])
    physical = {"owner": _owner("self", 1, "incoming"), "move": {"move_id": "tackle", "slot_index": 1, "priority": 0, "category": "physical"}}
    stats = {"hp": 100, "attack": 100, "defense": 100, "special-attack": 100, "special-defense": 100, "speed": 100}
    descriptor = {"source_snapshot_fingerprint": source, "owner": physical["owner"], "move_metadata": {**physical["move"], "power": 40, "type": "normal"}, "stat_provenance": {"attacker": {"pokemon_identity": "incoming", "types": {"available": True, "value": ["fire"]}, "final_stats": {"available": True, "value": stats}, "known_item": {"status": "known_absent"}}, "defender": {"pokemon_identity": "opponent", "types": {"available": True, "value": ["normal"]}, "final_stats": {"available": True, "value": stats}, "known_item": {"status": "known_absent"}}}, "trusted_level": 50}
    direct_state = deepcopy(result["next_state"]); direct_state["current_state"].pop("ability_context")
    raised = evaluate_hypothetical_direct_mechanics(branch_state=direct_state, source_snapshot_fingerprint=source, action=physical, expected_owner=physical["owner"], direct_evaluation_input=descriptor)
    neutral = deepcopy(direct_state); next(row for row in neutral["current_state"]["stat_stage_context"]["current_stages"] if row["side"] == "self" and row["stat"] == "attack")["stage"] = 0
    baseline = evaluate_hypothetical_direct_mechanics(branch_state=neutral, source_snapshot_fingerprint=source, action=physical, expected_owner=physical["owner"], direct_evaluation_input=descriptor)
    assert raised["status"] == baseline["status"] == "known"
    assert raised["mechanics_result"]["damage_range"]["minimum"] > baseline["mechanics_result"]["damage_range"]["minimum"]
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=project_poison_end_of_turn(pre_end_of_turn=result))
    assert handoff["status"] == "resolved"
    assert next(row for row in handoff["next_state"]["current_state"]["stat_stage_context"]["current_stages"] if row["side"] == "self" and row["stat"] == "attack")["stage"] == 1


def test_download_tie_raises_special_attack_and_missing_or_foreign_authority_fails_closed():
    from llm.advisor_hypothetical_direct_mechanics import evaluate_hypothetical_direct_mechanics
    from llm.advisor_switch_entry_download_authority import build_switch_entry_download_authority

    branch = _branch(); source = fingerprint_transition_preview_state(branch)
    authority = build_switch_entry_download_authority(
        session_id="switch-exec", source={"side": "self", "slot_index": 1, "pokemon_id": "incoming"},
        target={"side": "opponent", "slot_index": 0, "pokemon_id": "opponent"},
        applicability="applicable", target_defense=100, target_special_defense=100,
    )
    result = execute_manual_switch_then_direct(
        source_branch=branch, source_branch_fingerprint=source,
        switch_snapshot=_snapshot(rock="absent", spikes=0, ability="download", download=authority),
        switch_candidate=_candidate(), incoming_authority=_incoming(ability="download"),
        opponent_action=_opponent(), opponent_direct_evaluation_input=_descriptor(source),
    )
    assert result["status"] == "resolved", result
    stages = {(row["side"], row["stat"]): row["stage"] for row in result["next_state"]["current_state"]["stat_stage_context"]["current_stages"]}
    assert stages[("self", "attack")] == 0 and stages[("self", "special-attack")] == 1
    special = {"owner": _owner("self", 1, "incoming"), "move": {"move_id": "tackle", "slot_index": 1, "priority": 0, "category": "special"}}
    stats = {"hp": 100, "attack": 100, "defense": 100, "special-attack": 100, "special-defense": 100, "speed": 100}
    descriptor = {"source_snapshot_fingerprint": source, "owner": special["owner"], "move_metadata": {**special["move"], "power": 40, "type": "normal"}, "stat_provenance": {"attacker": {"pokemon_identity": "incoming", "types": {"available": True, "value": ["fire"]}, "final_stats": {"available": True, "value": stats}, "known_item": {"status": "known_absent"}}, "defender": {"pokemon_identity": "opponent", "types": {"available": True, "value": ["normal"]}, "final_stats": {"available": True, "value": stats}, "known_item": {"status": "known_absent"}}}, "trusted_level": 50}
    direct_state = deepcopy(result["next_state"]); direct_state["current_state"].pop("ability_context")
    raised = evaluate_hypothetical_direct_mechanics(branch_state=direct_state, source_snapshot_fingerprint=source, action=special, expected_owner=special["owner"], direct_evaluation_input=descriptor)
    neutral = deepcopy(direct_state); next(row for row in neutral["current_state"]["stat_stage_context"]["current_stages"] if row["side"] == "self" and row["stat"] == "special-attack")["stage"] = 0
    baseline = evaluate_hypothetical_direct_mechanics(branch_state=neutral, source_snapshot_fingerprint=source, action=special, expected_owner=special["owner"], direct_evaluation_input=descriptor)
    assert raised["status"] == baseline["status"] == "known"
    assert raised["mechanics_result"]["damage_range"]["minimum"] > baseline["mechanics_result"]["damage_range"]["minimum"]
    missing = execute_manual_switch_then_direct(
        source_branch=branch, source_branch_fingerprint=source,
        switch_snapshot=_snapshot(rock="absent", spikes=0, ability="download"),
        switch_candidate=_candidate(), incoming_authority=_incoming(ability="download"),
        opponent_action=_opponent(), opponent_direct_evaluation_input=_descriptor(source),
    )
    assert missing == {"status": "incomplete", "reason": "switch_entry_authority"}
    foreign = {**authority, "source": {"side": "self", "slot_index": 0, "pokemon_id": "outgoing"}}
    rejected = execute_manual_switch_then_direct(
        source_branch=branch, source_branch_fingerprint=source,
        switch_snapshot=_snapshot(rock="absent", spikes=0, ability="download", download=foreign),
        switch_candidate=_candidate(), incoming_authority=_incoming(ability="download"),
        opponent_action=_opponent(), opponent_direct_evaluation_input=_descriptor(source),
    )
    assert rejected == {"status": "incomplete", "reason": "switch_entry_authority"}


def test_two_layer_toxic_spikes_keeps_application_lineage_through_eot_and_handoff():
    from llm.advisor_end_of_turn_preview import project_poison_end_of_turn
    from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start

    branch = _branch(); source = fingerprint_transition_preview_state(branch)
    result = execute_manual_switch_then_direct(
        source_branch=branch, source_branch_fingerprint=source,
        switch_snapshot=_snapshot(rock="absent", spikes=0, toxic=2),
        switch_candidate=_candidate(), incoming_authority=_incoming(),
        opponent_action=_opponent(), opponent_direct_evaluation_input=_descriptor(source),
    )
    assert result["status"] == "resolved", result
    state = result["next_state"]
    condition = state["predicted_condition_context"]
    lifecycle = state["predicted_toxic_lifecycle"]
    assert condition["condition_type"] == "toxic" and lifecycle["current_stage"] == 1
    assert condition["source_snapshot_fingerprint"] == lifecycle["source_snapshot_fingerprint"] != source
    assert result["post_entry_branch_fingerprint"] == result["direct_evaluation"]["branch_state_fingerprint"]

    eot = project_poison_end_of_turn(pre_end_of_turn=result)
    assert eot["status"] == "resolved", eot
    assert eot["next_state"]["predicted_toxic_lifecycle"]["current_stage"] == 2
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot)
    assert handoff["status"] == "resolved", handoff
    assert handoff["next_state"]["active"]["self"]["pokemon_id"] == "incoming"
    assert handoff["next_state"]["predicted_condition_context"]["condition_type"] == "toxic"
    assert handoff["next_state"]["predicted_toxic_lifecycle"]["current_stage"] == 2

    foreign = deepcopy(result)
    foreign["next_state"]["predicted_toxic_lifecycle"]["source_snapshot_fingerprint"] = "foreign-branch"
    assert project_poison_end_of_turn(pre_end_of_turn=foreign) == {"status": "rejected", "reason": "stale_predicted_condition_overlay"}


def test_authorized_switch_target_must_match_materialized_incoming_owner():
    branch = _branch(); source = fingerprint_transition_preview_state(branch)
    other = _incoming()
    other["owner"] = _owner("self", 2, "different-incoming")
    result = execute_manual_switch_then_direct(
        source_branch=branch, source_branch_fingerprint=source, switch_snapshot=_snapshot(),
        switch_candidate=_candidate(), incoming_authority=other, opponent_action=_opponent(),
        opponent_direct_evaluation_input=_descriptor(source),
    )
    assert result == {"status": "rejected", "reason": "switch_candidate_incoming_authority_mismatch"}


def test_sticky_web_mutates_incoming_speed_only_and_handoff_preserves_it():
    from llm.advisor_end_of_turn_preview import project_poison_end_of_turn
    from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
    branch = _branch(); source = fingerprint_transition_preview_state(branch)
    result = execute_manual_switch_then_direct(source_branch=branch, source_branch_fingerprint=source, switch_snapshot=_snapshot(rock="absent", spikes=0, sticky="present"), switch_candidate=_candidate(), incoming_authority=_incoming(), opponent_action=_opponent(), opponent_direct_evaluation_input=_descriptor(source))
    assert result["status"] == "resolved", result
    stage = result["next_state"]["current_state"]["stat_stage_context"]["current_stages"][0]
    assert stage["stage"] == -1 and result["post_entry_branch_fingerprint"] == result["direct_evaluation"]["branch_state_fingerprint"]
    eot = project_poison_end_of_turn(pre_end_of_turn=result); assert eot["status"] == "resolved"
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=eot); assert handoff["status"] == "resolved"
    assert handoff["next_state"]["active"]["self"]["pokemon_id"] == "incoming"
    assert handoff["next_state"]["current_state"]["stat_stage_context"]["current_stages"][0]["stage"] == -1
