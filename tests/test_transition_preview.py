from copy import deepcopy

from llm.advisor_transition_preview import project_guaranteed_terminal_direct_ko_branch


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
    assert _project(self_candidate=_candidate(_action("self", "thunderbolt", 0), minimum=29, probability=0.5))["reason"] == "non_terminal_damage_range"


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
