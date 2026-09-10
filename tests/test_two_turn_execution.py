from copy import deepcopy

from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_two_turn_execution import execute_explicit_two_turn
from llm.advisor_post_eot_replacement_transition import (
    advance_post_eot_entry, freeze_replacement_intent, freeze_post_eot_transition,
    prepare_post_eot_replacements,
)
from tests.test_post_eot_replacement_transition import _entry, _source


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


def test_manual_switch_plan_cannot_execute_a_foreign_source_branch():
    source = _snapshot()
    foreign = _post_first(source, self_hp=100, opponent_hp=100)
    foreign["active"]["self"].update(session_id="foreign-session", pokemon_id="foreign-self")
    foreign["active"]["opponent"].update(session_id="foreign-session", pokemon_id="foreign-opponent")
    result = execute_explicit_two_turn(
        starting_turn_snapshot=source,
        turn_one={"transition": "manual_switch_then_direct", "source_branch": foreign},
        turn_two={},
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "manual_switch_source_branch_mismatch"
    assert result["failed_stage"] == "turn_one_transition"


def _replacement_cursor():
    source = _source(self_hp=0, opponent_hp=50)
    request = freeze_post_eot_transition(**source)
    intent = freeze_replacement_intent(
        transition=request, side="self", incoming_owner=request["requirements"]["self"]["candidates"][0],
    )
    cursor = prepare_post_eot_replacements(transition=request, intents={"self": intent})
    while cursor["status"] == "entry_pending":
        cursor = advance_post_eot_entry(transition=cursor, entry_authority=_entry(cursor))
    return cursor


def _replacement_start_snapshot():
    source = _snapshot(self_hp=100, opponent_hp=70)
    source["battle_state"] = {"active_player": {"slot_index": 0, "species_id": "a"}, "active_opponent": {"slot_index": 0, "species_id": "b"}}
    source["current_state"]["current_state_session_id"] = "s"
    return source


def _replacement_action(side, move_id, slot, pokemon_id):
    return {"owner": {"session_id": "s", "side": side, "slot_index": slot, "pokemon_id": pokemon_id}, "move": {"move_id": move_id, "slot_index": 0, "priority": 0, "category": "special"}}


def _replacement_plan(snapshot, *, self_owner, opponent_owner, self_damage=20, opponent_damage=10, start_branch_fingerprint=None):
    self_action = _replacement_action("self", "thunderbolt", self_owner["slot_index"], self_owner["pokemon_id"])
    opponent_action = _replacement_action("opponent", "flamethrower", opponent_owner["slot_index"], opponent_owner["pokemon_id"])
    own_hp = next(row["current_hp"] for row in snapshot["current_state"]["current_hp_context"]["current_hp"] if row["side"] == "self")
    foe_hp = next(row["current_hp"] for row in snapshot["current_state"]["current_hp_context"]["current_hp"] if row["side"] == "opponent")
    state = {"schema_version": "deterministic-transition-preview-v1", "active": {
        "self": {**self_owner, "current_hp": own_hp, "max_hp": 100, "fainted": own_hp == 0},
        "opponent": {**opponent_owner, "current_hp": foe_hp - self_damage, "max_hp": 100, "fainted": foe_hp == self_damage},
    }, "current_state": deepcopy(snapshot["current_state"])}
    for row in state["current_state"]["current_hp_context"]["current_hp"]:
        row["current_hp"] = own_hp if row["side"] == "self" else foe_hp - self_damage
    plan = {"self_action": self_action, "opponent_action": opponent_action, "self_candidate": _candidate(self_action, self_damage), "opponent_candidate": _candidate(opponent_action, opponent_damage), "action_order": _order(self_action, opponent_action), "post_first_candidate": {"branch_state_fingerprint": fingerprint_transition_preview_state(state), "candidate": _candidate(opponent_action, opponent_damage)}}
    if start_branch_fingerprint is not None:
        plan["start_branch_fingerprint"] = start_branch_fingerprint
    return plan


def test_completed_post_eot_replacement_cursor_resumes_turn_two_with_incoming_owner():
    cursor = _replacement_cursor()
    start = _replacement_start_snapshot()
    first = _replacement_plan(start, self_owner={"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "a"}, opponent_owner={"session_id": "s", "side": "opponent", "slot_index": 0, "pokemon_id": "b"}, opponent_damage=100)
    next_state = cursor["detached_next_decision_state"]
    second_snapshot = {"battle_state": {"active_player": {"slot_index": 1, "species_id": "self-1"}, "active_opponent": {"slot_index": 0, "species_id": "b"}}, "current_state": next_state["current_state"]}
    second = _replacement_plan(second_snapshot, self_owner=next_state["active"]["self"], opponent_owner=next_state["active"]["opponent"], self_damage=10, opponent_damage=10, start_branch_fingerprint=cursor["next_decision_fingerprint"])
    result = execute_explicit_two_turn(starting_turn_snapshot=start, turn_one=first, turn_two=second, post_eot_replacement_transition=cursor)
    assert result["status"] == "resolved", result
    assert result["next_turn_start"]["next_state"]["active"]["self"]["pokemon_id"] == "self-1"
    assert result["turn_two"]["next_state"]["active"]["self"]["pokemon_id"] == "self-1"


def test_replacement_cursor_incomplete_or_forged_or_stale_turn_two_owner_fails_closed():
    cursor = _replacement_cursor()
    start = _replacement_start_snapshot()
    first = _replacement_plan(start, self_owner={"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "a"}, opponent_owner={"session_id": "s", "side": "opponent", "slot_index": 0, "pokemon_id": "b"}, opponent_damage=100)
    incomplete = freeze_post_eot_transition(**_source(self_hp=0, opponent_hp=50))
    assert execute_explicit_two_turn(starting_turn_snapshot=start, turn_one=first, turn_two={}, post_eot_replacement_transition=incomplete)["reason"] == "post_eot_replacement_not_completed"
    forged = deepcopy(cursor); forged["next_decision_fingerprint"] = "foreign"
    assert execute_explicit_two_turn(starting_turn_snapshot=start, turn_one=first, turn_two={}, post_eot_replacement_transition=forged)["reason"] == "invalid_post_eot_replacement_transition"
    stale = deepcopy(cursor)
    stale["detached_next_decision_state"]["active"]["self"]["pokemon_id"] = "a"
    assert execute_explicit_two_turn(starting_turn_snapshot=start, turn_one=first, turn_two={}, post_eot_replacement_transition=stale)["reason"] == "invalid_post_eot_replacement_transition"

    stale_owner_plan = _replacement_plan({"battle_state": start["battle_state"], "current_state": cursor["detached_next_decision_state"]["current_state"]}, self_owner={"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "a"}, opponent_owner=cursor["detached_next_decision_state"]["active"]["opponent"], start_branch_fingerprint=cursor["next_decision_fingerprint"])
    assert execute_explicit_two_turn(starting_turn_snapshot=start, turn_one=first, turn_two=stale_owner_plan, post_eot_replacement_transition=cursor)["reason"] == "stale_or_mismatched_turn_two_action_owner"

    foreign_start = _replacement_start_snapshot()
    foreign_start["current_state"]["current_hp_context"]["current_hp"][1]["current_hp"] = 80
    foreign_first = _replacement_plan(foreign_start, self_owner={"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "a"}, opponent_owner={"session_id": "s", "side": "opponent", "slot_index": 0, "pokemon_id": "b"}, opponent_damage=100)
    assert execute_explicit_two_turn(starting_turn_snapshot=foreign_start, turn_one=foreign_first, turn_two={}, post_eot_replacement_transition=cursor)["reason"] == "post_eot_replacement_source_handoff_mismatch"


def test_battle_terminal_post_eot_transition_cannot_resume_turn_two():
    terminal = freeze_post_eot_transition(**_source(self_hp=0, opponent_hp=50, members={"self": []}))
    start = _replacement_start_snapshot()
    first = _replacement_plan(start, self_owner={"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "a"}, opponent_owner={"session_id": "s", "side": "opponent", "slot_index": 0, "pokemon_id": "b"}, opponent_damage=100)
    result = execute_explicit_two_turn(starting_turn_snapshot=start, turn_one=first, turn_two={}, post_eot_replacement_transition=terminal)
    assert result["status"] == "unsupported" and result["reason"] == "battle_terminal_post_eot_replacement_transition"
