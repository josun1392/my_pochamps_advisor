from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import (
    STATE_MODEL_VERSION, make_unknown_battle_fact, project_atomic_transition,
    state_fingerprint,
)
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_current_critical_state_authority, freeze_runtime_strategy_d0,
)


def _state(session="critical-state"):
    state = create_unknown_bootstrap_battle_state(session, "attacker", "target")["state"]
    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon.update(current_hp=100, max_hp=100, fainted=False)
    return state


def _owner(state, side="self"):
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": state[f"{side}_side"]["pokemon"][0]["pokemon_id"]}


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _d0(state):
    snapshot = _snapshot(state)
    return snapshot, freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))


def _provenance(turn=1):
    return {"event_kind": "current_crit_volatiles_observed", "trust": "user_confirmed_observation", "turn_number": turn}


def _side_provenance(turn=1):
    return {"event_kind": "current_side_conditions_observed", "trust": "user_confirmed_observation", "turn_number": turn}


def test_d0_projects_exact_crit_volatile_presence_absence_and_lucky_chant_side_owner():
    state = _state()
    state["self_side"]["pokemon"][0]["current_crit_volatiles"] = ["focus-energy", "lansat"]
    state["self_side"]["pokemon"][0]["current_crit_volatiles_provenance"] = _provenance()
    state["opponent_side"]["pokemon"][0]["current_crit_volatiles"] = []
    state["opponent_side"]["pokemon"][0]["current_crit_volatiles_provenance"] = _provenance()
    state["self_side"].update(side_conditions=["tailwind"], side_conditions_provenance=_side_provenance())
    state["opponent_side"].update(side_conditions=["lucky-chant"], side_conditions_provenance=_side_provenance())
    snapshot, d0 = _d0(state)

    own = freeze_runtime_current_critical_state_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=_owner(state))
    foe = freeze_runtime_current_critical_state_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=_owner(state, "opponent"))
    assert own["status"] == "resolved"
    assert own["crit_volatiles"]["volatiles"]["focus-energy"]["status"] == "known_present"
    assert own["crit_volatiles"]["volatiles"]["lansat"]["status"] == "known_present"
    assert own["crit_volatiles"]["volatiles"]["dragon-cheer"]["status"] == "known_absent"
    assert own["lucky_chant"]["lucky_chant"]["status"] == "known_absent"
    assert foe["crit_volatiles"]["volatiles"]["focus-energy"]["status"] == "known_absent"
    assert foe["lucky_chant"]["side"] == "opponent"
    assert foe["lucky_chant"]["lucky_chant"]["status"] == "known_present"


def test_missing_snapshots_remain_unknown_and_projection_is_detached_and_stale_safe():
    state = _state(); snapshot, d0 = _d0(state)
    result = freeze_runtime_current_critical_state_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=_owner(state))
    assert result["crit_volatiles"]["volatiles"]["focus-energy"]["status"] == "unknown"
    assert result["lucky_chant"]["lucky_chant"]["status"] == "unknown"
    state["last_applied_observation_sequence"] = 1
    assert result["crit_volatiles"]["volatiles"]["dragon-cheer"]["status"] == "unknown"
    assert freeze_runtime_current_critical_state_authority(strategy_d0=d0, runtime_snapshot=_snapshot(state), owner=_owner(state))["status"] == "rejected"
    assert freeze_runtime_current_critical_state_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=_owner(state, "opponent"))["status"] == "resolved"
    mismatched = {**_owner(state), "pokemon_id": "other"}
    assert freeze_runtime_current_critical_state_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=mismatched)["status"] == "rejected"


def _reducer_state():
    return {
        "state_version": STATE_MODEL_VERSION, "session_id": "reducer-critical",
        "self_side": {"active_slot_index": 0, "pokemon": {
            0: {"pokemon_id": "active", "current_hp": 100, "max_hp": 100, "fainted": False, "condition": "none", "known_item": None},
            1: {"pokemon_id": "incoming", "current_hp": 100, "max_hp": 100, "fainted": False, "condition": "none", "known_item": None},
        }, "side_conditions": []},
        "opponent_side": {"active_slot_index": 0, "pokemon": {0: {"pokemon_id": "target", "current_hp": 100, "max_hp": 100, "fainted": False, "condition": "none", "known_item": None}}, "side_conditions": []},
        "field": {"weather": None, "terrain": None}, "last_applied_observation_sequence": None,
    }


def _step(oid, sequence, effect, **values):
    return {"observation_id": oid, "observation_sequence": sequence, "planned_effect": effect, "trust": "user_confirmed_observation", **values}


def _plan(*steps):
    return {"session_id": "reducer-critical", "status": "planned", "conflicts": [], "ordered_steps": list(steps)}


def _identity(slot=0, pokemon_id="active"):
    return {"side": "self", "slot_index": slot, "pokemon_id": pokemon_id}


def test_reducer_requires_exact_current_snapshot_and_switch_or_faint_invalidates_volatile_authority():
    state = _reducer_state()
    observed = _step("crit", 1, "set_current_crit_volatiles", **_identity(), crit_volatiles=["focus-energy", "dragon-cheer"], turn_number=1)
    projected = project_atomic_transition(state, _plan(observed), "reducer-critical")
    assert projected["status"] == "ready_with_projected_state"
    active = projected["projected_state"]["self_side"]["pokemon"][0]
    assert active["current_crit_volatiles"] == ["focus-energy", "dragon-cheer"]
    assert active["current_crit_volatiles_provenance"]["event_kind"] == "current_crit_volatiles_observed"
    bad = _step("bad", 1, "set_current_crit_volatiles", **_identity(), crit_volatiles=["unrelated"], turn_number=1)
    assert project_atomic_transition(state, _plan(bad), "reducer-critical")["status"] == "blocked_by_semantic_conflict"

    switched = project_atomic_transition(projected["projected_state"], _plan(_step("switch", 2, "switch_active", side="self", switch_out_slot_index=0, switch_out_pokemon_id="active", switch_in_slot_index=1, switch_in_pokemon_id="incoming")), "reducer-critical")
    assert switched["status"] == "ready_with_projected_state"
    for slot in (0, 1):
        assert switched["projected_state"]["self_side"]["pokemon"][slot]["current_crit_volatiles"] == make_unknown_battle_fact()
    faint_base = projected["projected_state"]
    faint_base["self_side"]["pokemon"][0]["current_hp"] = 0
    fainted = project_atomic_transition(faint_base, _plan(_step("faint", 2, "mark_fainted", **_identity())), "reducer-critical")
    assert fainted["projected_state"]["self_side"]["pokemon"][0]["current_crit_volatiles"] == make_unknown_battle_fact()


def test_lucky_chant_uses_existing_side_snapshot_path_without_touching_other_conditions():
    state = _reducer_state()
    step = _step("side", 1, "set_current_side_conditions", side="opponent", side_conditions=["tailwind", "lucky-chant"], turn_number=1)
    projected = project_atomic_transition(state, _plan(step), "reducer-critical")
    assert projected["status"] == "ready_with_projected_state"
    assert projected["projected_state"]["opponent_side"]["side_conditions"] == ["tailwind", "lucky-chant"]
    absent = _step("side-absent", 2, "set_current_side_conditions", side="opponent", side_conditions=[], turn_number=2)
    absent_result = project_atomic_transition(projected["projected_state"], _plan(absent), "reducer-critical")
    assert absent_result["status"] == "ready_with_projected_state"
    assert absent_result["projected_state"]["opponent_side"]["side_conditions"] == []
