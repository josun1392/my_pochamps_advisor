from copy import deepcopy

from llm.advisor_transition_preview import (
    fingerprint_transition_preview_state,
    project_exact_direct_damage_branch,
    project_guaranteed_terminal_direct_ko_branch,
    project_self_recovery_direct_branch,
    project_self_stage_then_direct_branch,
)
from llm.advisor_hypothetical_stage_effects import project_self_stage_change
from llm.advisor_hypothetical_direct_mechanics import evaluate_hypothetical_direct_mechanics
from llm.advisor_hypothetical_recovery_effects import project_self_recovery


def _snapshot():
    return {
        "battle_state": {
            "active_player": {"slot_index": 0, "species_id": "pikachu"},
            "active_opponent": {"slot_index": 1, "species_id": "arcanine"},
        },
        "current_state": {
            "current_state_session_id": "turn-session",
            "current_hp_context": {"current_hp": [
                {"side": "self", "current_hp": 80, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp", "confidence": "known"},
                {"side": "opponent", "current_hp": 30, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp", "confidence": "known"},
            ]},
        },
    }


def _action(side, move_id, move_slot, priority=0, category="special"):
    owner = {"session_id": "turn-session", "side": side, "slot_index": 0 if side == "self" else 1, "pokemon_id": "pikachu" if side == "self" else "arcanine"}
    return {"owner": owner, "move": {"move_id": move_id, "slot_index": move_slot, "priority": priority, "category": category}}


def _candidate(action, *, minimum=30, probability=1.0, status="known", hit_count=1):
    move = action["move"]
    return {
        "slot_index": move["slot_index"], "move": move["move_id"],
        "accuracy_evidence": {"status": "known_accuracy", "canonical_accuracy": 100, "adjusted_accuracy": 100},
        "mechanics_result": {
            "status": status, "mechanics_source": "native_q12_direct_damage", "hit_count": hit_count,
            "damage_range": {"minimum": minimum, "maximum": minimum + 4},
            "ko_result": {"status": "resolved", "single_hit_probability": probability},
        },
    }


def _order(self_action, opponent_action, status="acts_first"):
    return {"status": status, "self_action": {"move_id": self_action["move"]["move_id"], "priority": self_action["move"]["priority"]}, "opponent_action": {"move_id": opponent_action["move"]["move_id"], "priority": opponent_action["move"]["priority"]}}


def _project(*, snapshot=None, self_action=None, opponent_action=None, self_candidate=None, opponent_candidate=None, order=None):
    self_action = self_action or _action("self", "thunderbolt", 0)
    opponent_action = opponent_action or _action("opponent", "flamethrower", 1)
    return project_guaranteed_terminal_direct_ko_branch(
        turn_snapshot=snapshot or _snapshot(), self_action=self_action, opponent_action=opponent_action,
        self_candidate=self_candidate or _candidate(self_action), opponent_candidate=opponent_candidate or _candidate(opponent_action),
        action_order=order or _order(self_action, opponent_action),
    )


def test_self_first_guaranteed_ko_projects_detached_pre_end_of_turn_state():
    snapshot = _snapshot()
    before = deepcopy(snapshot)
    result = _project(snapshot=snapshot)
    assert result["status"] == "resolved"
    assert result["next_state"]["active"]["opponent"]["current_hp"] == 0
    assert result["next_state"]["active"]["opponent"]["fainted"] is True
    assert result["consequence_trace"][1]["execution_status"] == "skipped"
    assert result["boundary"] == {"phase": "pre_end_of_turn", "end_of_turn": "not_entered"}
    assert snapshot == before
    result["next_state"]["active"]["self"]["current_hp"] = 1
    assert snapshot == before


def test_opponent_first_guaranteed_ko_projects_self_faint():
    self_action, opponent_action = _action("self", "thunderbolt", 0), _action("opponent", "flamethrower", 1)
    result = _project(
        self_action=self_action, opponent_action=opponent_action,
        self_candidate=_candidate(self_action), opponent_candidate=_candidate(opponent_action, minimum=80),
        order=_order(self_action, opponent_action, "acts_second"),
    )
    assert result["status"] == "resolved"
    assert result["next_state"]["active"]["self"]["current_hp"] == 0
    assert result["consequence_trace"][0]["actor_side"] == "opponent"


def test_preview_fails_closed_for_order_hp_and_nonterminal_damage():
    assert _project(order={"status": "speed_tie"})["reason"] == "speed_tie"
    missing_hp = _snapshot(); missing_hp["current_state"]["current_hp_context"]["current_hp"] = missing_hp["current_state"]["current_hp_context"]["current_hp"][:1]
    assert _project(snapshot=missing_hp)["reason"] == "opponent_exact_hp"
    missing_actor_hp = _snapshot(); missing_actor_hp["current_state"]["current_hp_context"]["current_hp"] = missing_actor_hp["current_state"]["current_hp_context"]["current_hp"][1:]
    assert _project(snapshot=missing_actor_hp)["reason"] == "self_exact_hp"
    assert _project(self_candidate=_candidate(_action("self", "thunderbolt", 0), minimum=29, probability=0.5))["reason"] == "non_unique_damage_outcome"


def test_preview_rejects_stale_owner_wrong_move_slot_and_action_order_mismatch():
    stale = _action("self", "thunderbolt", 0); stale["owner"]["session_id"] = "old-session"
    assert _project(self_action=stale, self_candidate=_candidate(stale))["status"] == "rejected"
    wrong_slot = _action("self", "thunderbolt", 0)
    candidate = _candidate(wrong_slot); candidate["slot_index"] = 2
    assert _project(self_action=wrong_slot, self_candidate=candidate)["reason"] == "candidate_action_mismatch"
    self_action, opponent_action = _action("self", "thunderbolt", 0), _action("opponent", "flamethrower", 1)
    bad_order = _order(self_action, opponent_action); bad_order["self_action"]["move_id"] = "fake-out"
    assert _project(self_action=self_action, opponent_action=opponent_action, order=bad_order)["reason"] == "action_order_action_mismatch"


def test_preview_does_not_promote_uncertain_or_out_of_slice_effects():
    self_action = _action("self", "thunderbolt", 0)
    uncertain = _candidate(self_action); uncertain["accuracy_evidence"]["adjusted_accuracy"] = 90
    assert _project(self_action=self_action, self_candidate=uncertain)["reason"] == "move_success_uncertain"
    multi = _candidate(self_action, hit_count=2)
    assert _project(self_action=self_action, self_candidate=multi)["status"] == "unsupported"
    status_action = _action("self", "swords-dance", 0, category="status")
    assert _project(self_action=status_action, self_candidate=_candidate(status_action))["status"] == "unsupported"


def _post_first_state(*, self_hp, opponent_hp, snapshot=None):
    state = {
        "schema_version": "deterministic-transition-preview-v1",
        "active": {
            "self": {"session_id": "turn-session", "side": "self", "slot_index": 0, "pokemon_id": "pikachu", "current_hp": self_hp, "max_hp": 100, "fainted": False},
            "opponent": {"session_id": "turn-session", "side": "opponent", "slot_index": 1, "pokemon_id": "arcanine", "current_hp": opponent_hp, "max_hp": 100, "fainted": False},
        },
    }
    state["current_state"] = deepcopy((snapshot or _snapshot())["current_state"])
    for entry in state["current_state"]["current_hp_context"]["current_hp"]:
        entry["current_hp"] = self_hp if entry["side"] == "self" else opponent_hp
    return state


def _fixed_direct_context(*, self_hp=80, opponent_hp=100):
    absent = {"status": "known_absent"}
    side = lambda hp: {"ability": absent, "item": absent, "boosts": {"attack": 0, "defense": 0, "special-attack": 0, "special-defense": 0, "speed": 0}, "current_hp": hp, "max_hp": 100, "status": absent}
    return {"generation": "gen9", "attacker": side(self_hp), "defender": side(opponent_hp), "field": {"weather": absent, "terrain": absent}}


def _second_direct_input(*, owner, move, snapshot):
    return {
        "source_snapshot_fingerprint": fingerprint_transition_preview_state(snapshot),
        "owner": owner,
        "move_metadata": deepcopy(move),
        "stat_provenance": {"attacker": {"types": {"available": True, "value": ["normal"]}}, "defender": {"types": {"available": True, "value": ["normal"]}}},
        "trusted_level": 50,
    }


def _stage_action(*, stat="attack", move_id="swords-dance"):
    action = _action("self", move_id, 0, priority=1, category="status")
    action["move"].update(target="user", accuracy=None, stat_changes=[{"stat": stat, "change": 2}])
    return action


def _recovery_action():
    action = _action("self", "recover", 0, priority=1, category="status")
    action["move"].update(target="user", accuracy=None, effect_category="heal", ailment="none", healing=50)
    return action


def _recovery_snapshot(*, self_hp=80):
    snapshot = _snapshot()
    snapshot["current_state"]["current_hp_context"]["current_hp"][0]["current_hp"] = self_hp
    snapshot["current_state"]["direct_mechanics_context"] = _fixed_direct_context(self_hp=self_hp, opponent_hp=30)
    return snapshot


def _exact_candidate(action, damage):
    candidate = _candidate(action, minimum=damage, probability=1.0)
    candidate["mechanics_result"]["damage_range"]["maximum"] = damage
    return candidate


def _stage_snapshot(*, stage=0):
    snapshot = _snapshot()
    snapshot["current_state"]["stat_stage_context"] = {"current_stages": [
        {"side": "self", "stat": "attack", "stage": stage, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"},
        {"side": "self", "stat": "defense", "stage": 0, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"},
        {"side": "opponent", "stat": "attack", "stage": 0, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"},
    ]}
    snapshot["current_state"]["direct_mechanics_context"] = _fixed_direct_context()
    return snapshot


def test_exact_nonterminal_first_and_second_actions_apply_sequentially():
    self_action, opponent_action = _action("self", "thunderbolt", 0), _action("opponent", "flamethrower", 1)
    snapshot = _snapshot(); snapshot["current_state"]["current_hp_context"]["current_hp"][1]["current_hp"] = 100
    first = _candidate(self_action, minimum=42, probability=0.0); first["mechanics_result"]["damage_range"]["maximum"] = 42
    second = _candidate(opponent_action, minimum=10, probability=0.0); second["mechanics_result"]["damage_range"]["maximum"] = 10
    result = project_exact_direct_damage_branch(
        turn_snapshot=snapshot, self_action=self_action, opponent_action=opponent_action,
        self_candidate=first, opponent_candidate=_candidate(opponent_action), action_order=_order(self_action, opponent_action),
        post_first_candidate={"branch_state_fingerprint": fingerprint_transition_preview_state(_post_first_state(self_hp=80, opponent_hp=58, snapshot=snapshot)), "candidate": second},
    )
    assert result["status"] == "resolved"
    assert result["reason"] == "two_action_exact_direct_damage"
    assert result["next_state"]["active"]["opponent"]["current_hp"] == 58
    assert result["next_state"]["active"]["self"]["current_hp"] == 70
    assert [row["execution_status"] for row in result["consequence_trace"]] == ["executed", "executed"]


def test_opponent_first_exact_nonterminal_damage_updates_self_exactly():
    self_action, opponent_action = _action("self", "thunderbolt", 0), _action("opponent", "flamethrower", 1)
    snapshot = _snapshot(); snapshot["current_state"]["current_hp_context"]["current_hp"][0]["current_hp"] = 100
    first = _candidate(opponent_action, minimum=42, probability=0.0); first["mechanics_result"]["damage_range"]["maximum"] = 42
    second = _candidate(self_action, minimum=10, probability=0.0); second["mechanics_result"]["damage_range"]["maximum"] = 10
    result = project_exact_direct_damage_branch(
        turn_snapshot=snapshot, self_action=self_action, opponent_action=opponent_action,
        self_candidate=_candidate(self_action), opponent_candidate=first, action_order=_order(self_action, opponent_action, "acts_second"),
        post_first_candidate={"branch_state_fingerprint": fingerprint_transition_preview_state(_post_first_state(self_hp=58, opponent_hp=30, snapshot=snapshot)), "candidate": second},
    )
    assert result["status"] == "resolved"
    assert result["next_state"]["active"]["self"]["current_hp"] == 58
    assert result["next_state"]["active"]["opponent"]["current_hp"] == 20


def test_exact_nonterminal_then_branch_bound_terminal_second_action():
    self_action, opponent_action = _action("self", "thunderbolt", 0), _action("opponent", "flamethrower", 1)
    snapshot = _snapshot(); snapshot["current_state"]["current_hp_context"]["current_hp"][1]["current_hp"] = 100
    first = _candidate(self_action, minimum=42, probability=0.0); first["mechanics_result"]["damage_range"]["maximum"] = 42
    second = _candidate(opponent_action, minimum=80, probability=1.0)
    result = project_exact_direct_damage_branch(
        turn_snapshot=snapshot, self_action=self_action, opponent_action=opponent_action,
        self_candidate=first, opponent_candidate=_candidate(opponent_action), action_order=_order(self_action, opponent_action),
        post_first_candidate={"branch_state_fingerprint": fingerprint_transition_preview_state(_post_first_state(self_hp=80, opponent_hp=58, snapshot=snapshot)), "candidate": second},
    )
    assert result["status"] == "resolved"
    assert result["reason"] == "two_action_terminal_direct_ko"
    assert result["next_state"]["active"]["self"]["current_hp"] == 0
    assert result["next_state"]["active"]["self"]["fainted"] is True


def test_second_action_requires_evidence_bound_to_detached_first_state():
    self_action, opponent_action = _action("self", "thunderbolt", 0), _action("opponent", "flamethrower", 1)
    snapshot = _snapshot(); snapshot["current_state"]["current_hp_context"]["current_hp"][1]["current_hp"] = 100
    first = _candidate(self_action, minimum=42, probability=0.0); first["mechanics_result"]["damage_range"]["maximum"] = 42
    assert project_exact_direct_damage_branch(turn_snapshot=snapshot, self_action=self_action, opponent_action=opponent_action, self_candidate=first, opponent_candidate=_candidate(opponent_action), action_order=_order(self_action, opponent_action))["reason"] == "post_first_direct_mechanics_evidence"
    stale = {"branch_state_fingerprint": "old-branch", "candidate": _candidate(opponent_action, minimum=10, probability=0.0)}
    assert project_exact_direct_damage_branch(turn_snapshot=snapshot, self_action=self_action, opponent_action=opponent_action, self_candidate=first, opponent_candidate=_candidate(opponent_action), action_order=_order(self_action, opponent_action), post_first_candidate=stale)["reason"] == "post_first_candidate_branch_mismatch"


def test_second_action_native_mechanics_is_generated_from_detached_branch_state():
    self_action = _action("self", "thunderbolt", 0)
    opponent_action = _action("opponent", "seismic-toss", 1, category="physical")
    snapshot = _snapshot(); snapshot["current_state"]["current_hp_context"]["current_hp"][1]["current_hp"] = 100
    snapshot["current_state"]["direct_mechanics_context"] = _fixed_direct_context()
    first = _candidate(self_action, minimum=42, probability=0.0); first["mechanics_result"]["damage_range"]["maximum"] = 42
    result = project_exact_direct_damage_branch(
        turn_snapshot=snapshot, self_action=self_action, opponent_action=opponent_action,
        self_candidate=first, opponent_candidate=_candidate(opponent_action), action_order=_order(self_action, opponent_action),
        second_direct_evaluation_input=_second_direct_input(owner=opponent_action["owner"], move=opponent_action["move"], snapshot=snapshot),
    )
    assert result["status"] == "resolved"
    assert result["next_state"]["active"]["opponent"]["current_hp"] == 58
    assert result["next_state"]["active"]["self"]["current_hp"] == 30
    assert result["consequence_trace"][1]["damage"] == 50


def test_hypothetical_second_action_rejects_stale_source_or_owner():
    self_action = _action("self", "thunderbolt", 0)
    opponent_action = _action("opponent", "seismic-toss", 1, category="physical")
    snapshot = _snapshot(); snapshot["current_state"]["current_hp_context"]["current_hp"][1]["current_hp"] = 100
    snapshot["current_state"]["direct_mechanics_context"] = _fixed_direct_context()
    first = _candidate(self_action, minimum=42, probability=0.0); first["mechanics_result"]["damage_range"]["maximum"] = 42
    descriptor = _second_direct_input(owner=opponent_action["owner"], move=opponent_action["move"], snapshot=snapshot)
    descriptor["source_snapshot_fingerprint"] = "stale-source"
    result = project_exact_direct_damage_branch(turn_snapshot=snapshot, self_action=self_action, opponent_action=opponent_action, self_candidate=first, opponent_candidate=_candidate(opponent_action), action_order=_order(self_action, opponent_action), second_direct_evaluation_input=descriptor)
    assert result["status"] == "rejected"
    assert result["reason"] == "source_snapshot_fingerprint_mismatch"


def test_hypothetical_second_action_preserves_material_unknown_authority():
    self_action = _action("self", "thunderbolt", 0)
    opponent_action = _action("opponent", "seismic-toss", 1, category="physical")
    snapshot = _snapshot(); snapshot["current_state"]["current_hp_context"]["current_hp"][1]["current_hp"] = 100
    snapshot["current_state"]["direct_mechanics_context"] = _fixed_direct_context()
    snapshot["current_state"]["direct_mechanics_context"]["defender"]["ability"] = {"status": "unknown"}
    first = _candidate(self_action, minimum=42, probability=0.0); first["mechanics_result"]["damage_range"]["maximum"] = 42
    result = project_exact_direct_damage_branch(
        turn_snapshot=snapshot, self_action=self_action, opponent_action=opponent_action,
        self_candidate=first, opponent_candidate=_candidate(opponent_action), action_order=_order(self_action, opponent_action),
        second_direct_evaluation_input=_second_direct_input(owner=opponent_action["owner"], move=opponent_action["move"], snapshot=snapshot),
    )
    assert result["status"] == "incomplete"
    assert "attacker.ability" in result["missing_inputs"]


def test_self_stage_action_mutates_only_detached_predicted_stage_overlay():
    snapshot = _stage_snapshot()
    before = deepcopy(snapshot)
    self_action = _stage_action()
    opponent_action = _action("opponent", "seismic-toss", 1, category="physical")
    result = project_self_stage_then_direct_branch(
        turn_snapshot=snapshot, self_action=self_action, opponent_action=opponent_action,
        self_candidate=_candidate(self_action), opponent_candidate=_candidate(opponent_action), action_order=_order(self_action, opponent_action, "acts_first"),
        second_direct_evaluation_input=_second_direct_input(owner=opponent_action["owner"], move=opponent_action["move"], snapshot=snapshot),
    )
    assert result["status"] == "resolved"
    predicted = result["next_state"]["predicted_stage_context"]
    assert (predicted["stat"], predicted["previous_stage"], predicted["delta"], predicted["projected_stage"]) == ("attack", 0, 2, 2)
    assert snapshot == before
    assert result["consequence_trace"][0]["consequence"] == "exact_self_stage_change"


def test_self_stage_effect_caps_and_requires_exact_canonical_stage_authority():
    action = _stage_action()
    capped = project_self_stage_change(branch_state={"schema_version": "deterministic-transition-preview-v1", "current_state": _stage_snapshot(stage=6)["current_state"]}, action=action, expected_owner=action["owner"])
    assert capped["status"] == "resolved" and capped["projected_stage"] == 6
    unknown = _stage_snapshot(); unknown["current_state"].pop("stat_stage_context")
    missing = project_self_stage_change(branch_state={"schema_version": "deterministic-transition-preview-v1", "current_state": unknown["current_state"]}, action=action, expected_owner=action["owner"])
    assert missing == {"status": "incomplete", "reason": "self.attack_stage"}


def test_stage_move_metadata_and_order_fail_closed():
    action = _stage_action(); state = {"schema_version": "deterministic-transition-preview-v1", "current_state": _stage_snapshot()["current_state"]}
    action["move"]["target"] = "selected-pokemon"
    assert project_self_stage_change(branch_state=state, action=action, expected_owner=action["owner"])["status"] == "unsupported"
    self_action = _stage_action(); opponent_action = _action("opponent", "seismic-toss", 1, category="physical")
    assert project_self_stage_then_direct_branch(turn_snapshot=_stage_snapshot(), self_action=self_action, opponent_action=opponent_action, self_candidate=_candidate(self_action), opponent_candidate=_candidate(opponent_action), action_order=_order(self_action, opponent_action, "acts_second"), second_direct_evaluation_input=_second_direct_input(owner=opponent_action["owner"], move=opponent_action["move"], snapshot=_stage_snapshot()))["reason"] == "self_stage_action_not_first"


def test_later_hypothetical_direct_mechanics_consumes_predicted_stage_overlay():
    snapshot = _stage_snapshot()
    self_action = _stage_action(stat="defense", move_id="iron-defense")
    opponent_action = _action("opponent", "seismic-toss", 1, category="physical")
    branch = project_self_stage_then_direct_branch(
        turn_snapshot=snapshot, self_action=self_action, opponent_action=opponent_action,
        self_candidate=_candidate(self_action), opponent_candidate=_candidate(opponent_action), action_order=_order(self_action, opponent_action, "acts_first"),
        second_direct_evaluation_input=_second_direct_input(owner=opponent_action["owner"], move=opponent_action["move"], snapshot=snapshot),
    )["next_state"]
    tackle = _action("opponent", "tackle", 1, category="physical")
    stats = {"hp": 100, "attack": 100, "defense": 100, "special-attack": 100, "special-defense": 100, "speed": 100}
    direct = evaluate_hypothetical_direct_mechanics(
        branch_state=branch, source_snapshot_fingerprint=fingerprint_transition_preview_state(snapshot), action=tackle, expected_owner=tackle["owner"],
            direct_evaluation_input={"source_snapshot_fingerprint": fingerprint_transition_preview_state(snapshot), "owner": tackle["owner"], "move_metadata": {**tackle["move"], "power": 40, "type": "normal"}, "stat_provenance": {"attacker": {"pokemon_identity": "arcanine", "types": {"available": True, "value": ["normal"]}, "final_stats": {"available": True, "value": stats}, "known_item": {"status": "known_absent"}}, "defender": {"pokemon_identity": "pikachu", "types": {"available": True, "value": ["normal"]}, "final_stats": {"available": True, "value": stats}, "known_item": {"status": "known_absent"}}}, "trusted_level": 50},
    )
    assert direct["status"] == "known", direct
    assert direct["mechanics_result"]["stat_stage_evidence"]["defensive_stage_value"] == 2


def test_self_recovery_projects_exact_detached_hp_and_caps_at_maximum():
    snapshot = _recovery_snapshot(self_hp=80); before = deepcopy(snapshot)
    recovery, opponent = _recovery_action(), _action("opponent", "seismic-toss", 1, category="physical")
    result = project_self_recovery_direct_branch(
        turn_snapshot=snapshot, self_action=recovery, opponent_action=opponent,
        self_candidate=_candidate(recovery), opponent_candidate=_candidate(opponent), action_order=_order(recovery, opponent, "acts_first"),
        opponent_direct_evaluation_input=_second_direct_input(owner=opponent["owner"], move=opponent["move"], snapshot=snapshot),
    )
    assert result["status"] == "resolved"
    assert result["next_state"]["active"]["self"]["current_hp"] == 50
    trace = result["consequence_trace"][0]
    assert (trace["consequence"], trace["recovery"], trace["hp_before"], trace["post_hp"]) == ("exact_self_recovery", 20, 80, 100)
    assert snapshot == before


def test_opponent_first_exact_damage_then_recovery_uses_detached_post_damage_hp():
    snapshot = _recovery_snapshot(self_hp=80)
    recovery, opponent = _recovery_action(), _action("opponent", "flamethrower", 1)
    result = project_self_recovery_direct_branch(
        turn_snapshot=snapshot, self_action=recovery, opponent_action=opponent,
        self_candidate=_candidate(recovery), opponent_candidate=_exact_candidate(opponent, 30), action_order=_order(recovery, opponent, "acts_second"),
    )
    assert result["status"] == "resolved"
    assert result["next_state"]["active"]["self"]["current_hp"] == 100
    assert result["consequence_trace"][1]["hp_before"] == 50
    assert result["consequence_trace"][1]["recovery"] == 50


def test_terminal_opponent_direct_damage_skips_self_recovery():
    snapshot = _recovery_snapshot(self_hp=80)
    recovery, opponent = _recovery_action(), _action("opponent", "flamethrower", 1)
    result = project_self_recovery_direct_branch(
        turn_snapshot=snapshot, self_action=recovery, opponent_action=opponent,
        self_candidate=_candidate(recovery), opponent_candidate=_exact_candidate(opponent, 80), action_order=_order(recovery, opponent, "acts_second"),
    )
    assert result["status"] == "resolved" and result["next_state"]["active"]["self"]["fainted"] is True
    assert result["consequence_trace"][1]["execution_status"] == "skipped"


def test_self_recovery_requires_exact_authority_and_supported_metadata():
    action = _recovery_action(); state = {"schema_version": "deterministic-transition-preview-v1", "active": {"self": {**action["owner"], "fainted": False}}, "current_state": _recovery_snapshot()["current_state"]}
    assert project_self_recovery(branch_state=state, action=action, expected_owner=action["owner"])["status"] == "resolved"
    odd = deepcopy(state); odd["current_state"]["current_hp_context"]["current_hp"][0].update(current_hp=1, maximum_hp=301)
    odd_effect = project_self_recovery(branch_state=odd, action=action, expected_owner=action["owner"])
    assert (odd_effect["recovery"], odd_effect["hp_after"]) == (150, 151)
    missing = deepcopy(state); missing["current_state"]["current_hp_context"]["current_hp"] = missing["current_state"]["current_hp_context"]["current_hp"][1:]
    assert project_self_recovery(branch_state=missing, action=action, expected_owner=action["owner"])["reason"] == "self_exact_hp"
    invalid = deepcopy(action); invalid["move"].pop("healing")
    assert project_self_recovery(branch_state=state, action=invalid, expected_owner=action["owner"])["reason"] == "self_recovery_effect_metadata"
    secondary = deepcopy(action); secondary["move"]["stat_changes"] = [{"stat": "attack", "change": 1}]
    assert project_self_recovery(branch_state=state, action=secondary, expected_owner=action["owner"])["reason"] == "self_recovery_secondary_effect"
    stale = deepcopy(action); stale["owner"]["pokemon_id"] = "replacement"
    assert project_self_recovery(branch_state=state, action=stale, expected_owner=action["owner"])["status"] == "rejected"
