from copy import deepcopy

from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_two_turn_execution import execute_explicit_two_turn


def _snapshot(*, self_hp=100, opponent_hp=100):
    return {
        "battle_state": {"active_player": {"slot_index": 0, "species_id": "pikachu"}, "active_opponent": {"slot_index": 1, "species_id": "arcanine"}},
        "current_state": {
            "current_state_session_id": "two-turn-session",
            "current_hp_context": {"current_hp": [
                {"side": "self", "current_hp": self_hp, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp", "confidence": "known"},
                {"side": "opponent", "current_hp": opponent_hp, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp", "confidence": "known"},
            ]},
            "condition_context": {"current_conditions": [
                {"side": "self", "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition"},
                {"side": "opponent", "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition"},
            ]},
            "ability_context": {"current_abilities": [
                {"side": "self", "ability": "blaze", "status": "user_confirmed", "source": "user_confirmed_current_ability"},
                {"side": "opponent", "ability": "blaze", "status": "user_confirmed", "source": "user_confirmed_current_ability"},
            ]},
            "direct_mechanics_context": {"generation": "gen9"},
        },
    }


def _action(side, move_id, slot):
    return {"owner": {"session_id": "two-turn-session", "side": side, "slot_index": 0 if side == "self" else 1, "pokemon_id": "pikachu" if side == "self" else "arcanine"}, "move": {"move_id": move_id, "slot_index": slot, "priority": 0, "category": "special"}}


def _candidate(action, damage):
    probability = 1.0 if damage >= 100 else 0.0
    return {"slot_index": action["move"]["slot_index"], "move": action["move"]["move_id"], "accuracy_evidence": {"status": "known_accuracy", "canonical_accuracy": 100, "adjusted_accuracy": 100}, "mechanics_result": {"status": "known", "mechanics_source": "native_q12_direct_damage", "hit_count": 1, "damage_range": {"minimum": damage, "maximum": damage}, "ko_result": {"status": "resolved", "single_hit_probability": probability}}}


def _order(self_action, opponent_action):
    return {"status": "acts_first", "self_action": {"move_id": self_action["move"]["move_id"], "priority": 0}, "opponent_action": {"move_id": opponent_action["move"]["move_id"], "priority": 0}}


def _post_first(snapshot, *, self_hp, opponent_hp):
    state = {"schema_version": "deterministic-transition-preview-v1", "active": {
        "self": {**_action("self", "x", 0)["owner"], "current_hp": self_hp, "max_hp": 100, "fainted": self_hp == 0},
        "opponent": {**_action("opponent", "x", 1)["owner"], "current_hp": opponent_hp, "max_hp": 100, "fainted": opponent_hp == 0},
    }, "current_state": deepcopy(snapshot["current_state"])}
    for row in state["current_state"]["current_hp_context"]["current_hp"]:
        row["current_hp"] = self_hp if row["side"] == "self" else opponent_hp
    return state


def _plan(snapshot, *, self_damage=20, opponent_damage=10, start_branch_fingerprint=None):
    self_action, opponent_action = _action("self", "thunderbolt", 0), _action("opponent", "flamethrower", 1)
    state = _post_first(snapshot, self_hp=snapshot["current_state"]["current_hp_context"]["current_hp"][0]["current_hp"], opponent_hp=snapshot["current_state"]["current_hp_context"]["current_hp"][1]["current_hp"] - self_damage)
    plan = {"self_action": self_action, "opponent_action": opponent_action, "self_candidate": _candidate(self_action, self_damage), "opponent_candidate": _candidate(opponent_action, opponent_damage), "action_order": _order(self_action, opponent_action), "post_first_candidate": {"branch_state_fingerprint": fingerprint_transition_preview_state(state), "candidate": _candidate(opponent_action, opponent_damage)}}
    if start_branch_fingerprint is not None:
        plan["start_branch_fingerprint"] = start_branch_fingerprint
    return plan


def test_explicit_two_turn_direct_damage_uses_handoff_hp_and_preserves_provenance():
    source = _snapshot(); before = deepcopy(source)
    first_plan = _plan(source)
    # The second plan is constructed only after its canonical handoff fingerprint
    # is known; this mirrors explicit later-turn ownership rather than rebinding.
    from llm.advisor_end_of_turn_preview import project_poison_end_of_turn
    from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
    from llm.advisor_transition_preview import project_exact_direct_damage_branch
    first = project_exact_direct_damage_branch(turn_snapshot=source, **first_plan)
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=project_poison_end_of_turn(pre_end_of_turn=first))
    second_snapshot = {"battle_state": source["battle_state"], "current_state": handoff["next_state"]["current_state"]}
    second_plan = _plan(second_snapshot, start_branch_fingerprint=handoff["resulting_branch_fingerprint"])
    result = execute_explicit_two_turn(starting_turn_snapshot=source, turn_one=first_plan, turn_two=second_plan)
    assert result["status"] == "resolved", result
    assert result["next_turn_start"]["next_state"]["active"]["self"]["current_hp"] == 90
    assert result["turn_two_end_of_turn"]["next_state"]["active"]["self"]["current_hp"] == 80
    assert result["turn_two_end_of_turn"]["next_state"]["active"]["opponent"]["current_hp"] == 60
    assert source == before and result["boundary"] == {"phase": "end_of_turn", "turn": 2}


def test_turn_two_requires_new_handoff_fingerprint_and_terminal_turn_one_stops():
    source = _snapshot(); first_plan = _plan(source)
    rejected = execute_explicit_two_turn(starting_turn_snapshot=source, turn_one=first_plan, turn_two={**first_plan, "start_branch_fingerprint": "turn-one"})
    assert rejected["status"] == "rejected" and rejected["reason"] == "turn_two_branch_fingerprint_mismatch"

    lethal = _plan(source, self_damage=100)
    stopped = execute_explicit_two_turn(starting_turn_snapshot=source, turn_one=lethal, turn_two={**first_plan, "start_branch_fingerprint": "unused"})
    assert stopped["status"] == "unsupported" and stopped["reason"] == "replacement_required_before_turn_two"
