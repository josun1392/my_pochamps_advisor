from copy import deepcopy

from llm.advisor_reducer_state_model import (
    STATE_MODEL_VERSION, execute_atomic_transition, project_atomic_transition,
    replay_batch_fingerprint, state_fingerprint,
)


def base(session="s"):
    return {"state_version": STATE_MODEL_VERSION, "session_id": session, "self_side": {"active_slot_index": 0, "pokemon": {0: {"pokemon_id": "pikachu", "current_hp": 80, "max_hp": 100, "fainted": False, "condition": None, "known_item": "berry"}}, "side_conditions": []}, "opponent_side": {"active_slot_index": 0, "pokemon": {}}, "field": {"weather": None, "terrain": None}, "last_applied_observation_sequence": None, "q12": {"rolls": [10, 11]}, "ranking": ["tackle"]}


def step(oid="hp", seq=1, **extra):
    return {"observation_id": oid, "observation_sequence": seq, "planned_effect": "apply_exact_hp_transition", "side": "self", "slot_index": 0, "pokemon_id": "pikachu", "hp_before": 80, "hp_after": 40, "trust": "user_confirmed_observation", **extra}


def plan(*steps, session="s"):
    return {"session_id": session, "status": "planned", "conflicts": [], "replay_policy_version": "v1", "ordered_steps": list(steps)}


def test_success_parity_fingerprint_and_detached_inputs():
    state, replay = base(), plan(step())
    before = deepcopy((state, replay)); digest = state_fingerprint(state)
    projection = project_atomic_transition(state, replay, "s")
    result = execute_atomic_transition(state, replay, expected_session_id="s", expected_base_fingerprint=digest)
    assert result["status"] == "committed" and result["committed_state"]["self_side"]["pokemon"][0]["current_hp"] == projection["projected_state"]["self_side"]["pokemon"][0]["current_hp"]
    assert result["applied_step_ids"] == ["hp"] and result["base_state_fingerprint"] == digest and (state, replay) == before
    result["committed_state"]["self_side"]["pokemon"][0]["current_hp"] = 1
    assert state["self_side"]["pokemon"][0]["current_hp"] == 80


def test_fingerprints_are_canonical_and_detect_semantic_change():
    state = base(); reordered = {key: deepcopy(state[key]) for key in reversed(list(state))}
    assert state_fingerprint(state) == state_fingerprint(reordered)
    changed = deepcopy(state); changed["self_side"]["pokemon"][0]["current_hp"] = 79
    assert state_fingerprint(state) != state_fingerprint(changed)
    assert replay_batch_fingerprint(plan(step())) == replay_batch_fingerprint(plan(step()))


def test_stale_already_applied_and_partial_overlap_are_atomic():
    state, replay = base(), plan(step())
    assert execute_atomic_transition(state, replay, expected_base_fingerprint="stale")["status"] == "stale_base_state"
    committed = execute_atomic_transition(state, replay)["committed_state"]
    again = execute_atomic_transition(committed, replay)
    assert again["status"] == "already_applied" and again["committed_state"] is None
    overlap = plan(step("old", 1), step("new", 2, hp_before=40, hp_after=20))
    assert execute_atomic_transition(committed, overlap)["status"] == "blocked_by_semantic_conflict"


def test_session_version_conflict_no_steps_and_q12_boundaries():
    assert execute_atomic_transition(base(), plan(session="old"))["status"] == "session_mismatch"
    wrong = base(); wrong["state_version"] = "battle-state-v2"
    assert execute_atomic_transition(wrong, plan())["status"] == "unsupported_state_version"
    assert execute_atomic_transition(base(), plan())["status"] == "no_reducer_steps"
    conflict = execute_atomic_transition(base(), plan(step(hp_before=79)))
    assert conflict["status"] == "blocked_by_semantic_conflict" and conflict["committed_state"] is None
    result = execute_atomic_transition(base(), plan(step()))
    assert result["committed_state"]["q12"] == {"rolls": [10, 11]} and result["committed_state"]["ranking"] == ["tackle"]
