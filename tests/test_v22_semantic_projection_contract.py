from copy import deepcopy

from llm.advisor_reducer_state_model import STATE_MODEL_VERSION, project_atomic_transition


def base():
    return {"state_version": STATE_MODEL_VERSION, "session_id": "s", "self_side": {"active_slot_index": 0, "pokemon": {0: {"pokemon_id": "pikachu", "current_hp": 80, "max_hp": 100, "fainted": False, "condition": None, "known_item": "berry"}, 1: {"pokemon_id": "raichu", "current_hp": "unknown", "max_hp": 100, "fainted": False, "condition": "unknown", "known_item": "unknown"}}, "side_conditions": []}, "opponent_side": {"active_slot_index": 0, "pokemon": {0: {"pokemon_id": "eevee", "current_hp": "unknown", "max_hp": 100, "fainted": "unknown", "condition": "unknown", "known_item": "leftovers"}}, "side_conditions": []}, "field": {"weather": None, "terrain": None}, "last_applied_observation_sequence": None, "q12": {"damage": 99}}


def step(oid, seq, effect, **values):
    return {"observation_id": oid, "observation_sequence": seq, "planned_effect": effect, "trust": "user_confirmed_observation", **values}


def plan(*steps): return {"session_id": "s", "status": "planned", "conflicts": [], "ordered_steps": list(steps)}
def owner(side="self", slot=0, pokemon="pikachu"): return {"side": side, "slot_index": slot, "pokemon_id": pokemon}


def test_successful_projection_is_detached_immutable_and_tracks_last_sequence():
    state, replay = base(), plan(step("hp", 2, "apply_exact_hp_transition", **owner(), hp_before=80, hp_after=40))
    before = deepcopy((state, replay)); result = project_atomic_transition(state, replay, "s")
    assert result["status"] == "ready_with_projected_state"
    assert result["projected_state"]["self_side"]["pokemon"][0]["current_hp"] == 40
    assert result["projected_state"]["last_applied_observation_sequence"] == 2
    assert result["projected_state"]["q12"] == {"damage": 99} and (state, replay) == before
    result["projected_state"]["self_side"]["pokemon"][0]["current_hp"] = 1
    assert state["self_side"]["pokemon"][0]["current_hp"] == 80


def test_exact_hp_unknown_policy_and_mismatch_are_atomic():
    unknown = project_atomic_transition(base(), plan(step("hp", 1, "apply_exact_hp_transition", **owner("opponent", 0, "eevee"), hp_before=70, hp_after=20)), "s")
    assert unknown["status"] == "ready_with_projected_state" and unknown["projected_state"]["opponent_side"]["pokemon"][0]["current_hp"] == 20
    failed = project_atomic_transition(base(), plan(step("first", 1, "set_condition", **owner(), condition="burn"), step("bad", 2, "apply_exact_hp_transition", **owner(), hp_before=79, hp_after=30)), "s")
    assert failed["status"] == "blocked_by_semantic_conflict" and failed["projected_state"] is None and failed["applied_step_ids"] == []


def test_switch_faint_and_atomic_hp_faint_switch_chain():
    steps = [step("hp", 1, "apply_exact_hp_transition", **owner(), hp_before=80, hp_after=0), step("faint", 2, "mark_fainted", **owner()), step("switch", 3, "switch_active", side="self", switch_out_slot_index=0, switch_out_pokemon_id="pikachu", switch_in_slot_index=1, switch_in_pokemon_id="raichu")]
    result = project_atomic_transition(base(), plan(*steps), "s")
    assert result["status"] == "ready_with_projected_state" and result["projected_state"]["self_side"]["active_slot_index"] == 1
    invalid_out = project_atomic_transition(base(), plan(step("sw", 1, "switch_active", side="self", switch_out_slot_index=1, switch_out_pokemon_id="raichu", switch_in_slot_index=0, switch_in_pokemon_id="pikachu")), "s")
    assert invalid_out["status"] == "blocked_by_semantic_conflict"
    state = base(); state["self_side"]["pokemon"][1]["fainted"] = True
    fainted_in = project_atomic_transition(state, plan(step("sw", 1, "switch_active", side="self", switch_out_slot_index=0, switch_out_pokemon_id="pikachu", switch_in_slot_index=1, switch_in_pokemon_id="raichu")), "s")
    assert fainted_in["status"] == "blocked_by_semantic_conflict"


def test_lifecycle_policies_condition_item_field_and_side_condition():
    steps = [step("set", 1, "set_condition", **owner(), condition="burn"), step("clear", 2, "clear_condition", **owner(), condition="burn"), step("item", 3, "consume_item", **owner(), item="berry"), step("weather", 4, "start_weather", weather="rain"), step("weather-end", 5, "end_weather", weather="rain"), step("terrain", 6, "start_terrain", terrain="electric"), step("terrain-end", 7, "end_terrain", terrain="electric"), step("side", 8, "start_side_condition", side="self", side_condition="reflect"), step("side-end", 9, "end_side_condition", side="self", side_condition="reflect")]
    result = project_atomic_transition(base(), plan(*steps), "s")
    assert result["status"] == "ready_with_projected_state"
    projected = result["projected_state"]
    assert projected["self_side"]["pokemon"][0]["condition"] is None and projected["self_side"]["pokemon"][0]["known_item"] is None
    assert projected["field"]["weather"] is None and projected["field"]["terrain"] is None and projected["self_side"]["side_conditions"] == []


def test_conflicting_known_lifecycle_values_and_already_fainted_are_rejected():
    mismatch = project_atomic_transition(base(), plan(step("clear", 1, "clear_condition", **owner(), condition="poison")), "s")
    assert mismatch["status"] == "blocked_by_semantic_conflict"
    state = base(); state["self_side"]["pokemon"][0]["fainted"] = True
    assert project_atomic_transition(state, plan(step("f", 1, "mark_fainted", **owner())), "s")["status"] == "blocked_by_semantic_conflict"


def test_same_sequence_policy_session_and_idempotency():
    independent = project_atomic_transition(base(), plan(step("condition", 1, "set_condition", **owner(), condition="burn"), step("weather", 1, "start_weather", weather="rain")), "s")
    assert independent["status"] == "ready_with_projected_state"
    dependent = project_atomic_transition(base(), plan(step("clear", 1, "clear_condition", **owner(), condition="burn"), step("set", 1, "set_condition", **owner(), condition="burn")), "s")
    assert dependent["status"] == "blocked_by_semantic_conflict" and dependent["projected_state"] is None
    already = base(); already["self_side"]["pokemon"][0]["condition"] = "burn"; replay = plan(step("same", 1, "set_condition", **owner(), condition="burn"))
    assert project_atomic_transition(already, replay, "s") == project_atomic_transition(already, replay, "s")
    assert project_atomic_transition(base(), plan(step("x", 1, "set_condition", **owner(), condition="burn")), "old")["status"] == "invalid_base_state"
    assert project_atomic_transition(base(), plan(step("missing", 1, "set_condition", condition="burn")), "s")["status"] == "invalid_replay_plan"
